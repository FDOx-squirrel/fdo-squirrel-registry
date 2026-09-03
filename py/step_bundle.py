"""S4 - build dist/fdo-registry.ttl as a DCAT catalogue.

Order matters: vereindeutigen before merging. The package-relative `urn:` IRIs
are only unique inside their own ZIP, so two packages that each contain a
`CITATION.cff` collide on one node the moment their graphs are merged (PRIMER
A1, Befund 2). Everything below therefore happens per record, in its own graph,
and only the finished result is added to the catalogue:

    1  parse the package through registry_utils.read_fdo (repairs are declared)
    2  persons -> registry-global <registry>/agent/<hash>
    3  urn:fdo-squirrel:* -> <record-IRI>/dist|content/..., original kept
    4  abbreviated class IRIs -> the official ones (crosswalk `normalise` rows)
    5  CRM anchors materialised per instance (crosswalk `instance` rows)
    6  hang into the catalogue
    7  serialise canonically

What the bundle does not do: it never dereferences the Wikidata, OSM or
ChronOntology IRIs the packages point at. The catalogue carries the IRIs;
whoever wants more federates. A registry that copies foreign holdings along is
out of date on the next run and wrong on the one after.
"""

from __future__ import annotations

import registry_utils as u
from step_bridge import base_term, read_crosswalk

URN_PREFIX = "urn:fdo-squirrel:"

# Handled together in anchor_temporal rather than by the generic rule, because
# the object has to be retyped on the way out.
TEMPORAL_TERMS = {"dcat:startDate", "dcat:endDate", "dct:PeriodOfTime"}


# ---------------------------------------------------------------------------
# The registry's own vocabulary
# ---------------------------------------------------------------------------

# Declared here because this is the step that mints the terms. Domain and range
# name foreign classes, which is allowed: the subject of every statement is one
# of our own properties, so nothing is asserted about dcat: itself (PRIMER A3).
ONTOLOGY_TERMS: list[dict[str, str]] = [
    {
        "term": "fdoreg:conceptDoi", "kind": "object",
        "label": "concept DOI",
        "comment": "The Zenodo concept DOI of the FDO a catalogue record "
                   "describes. It is the DOI the harvested fdo-metadata.ttl "
                   "uses as its own subject, and therefore the identity that "
                   "survives a new version.",
        "domain": "dcat:CatalogRecord", "range": "dcat:Dataset",
    },
    {
        "term": "fdoreg:versionDoi", "kind": "object",
        "label": "version DOI",
        "comment": "The pinned Zenodo version DOI the registry harvested. One "
                   "catalogue record per version DOI; several records may "
                   "share a concept DOI.",
        "domain": "dcat:CatalogRecord", "range": "dcat:Dataset",
    },
    {
        "term": "fdoreg:sha256", "kind": "datatype",
        "label": "SHA-256 of the harvested metadata file",
        "comment": "Of the fdo-metadata.ttl exactly as it lies in the "
                   "published package - never of a repaired reading of it, so "
                   "the value can be checked against Zenodo.",
        "domain": "dcat:CatalogRecord", "range": "xsd:string",
    },
    {
        "term": "fdoreg:readRepair", "kind": "datatype",
        "label": "encoding repair applied on reading",
        "comment": "Names a declared repair from py/repair.py that had to be "
                   "applied before the harvested Turtle would parse. Present "
                   "only where the published file is not valid Turtle; its "
                   "absence means the file was read exactly as published.",
        "domain": "dcat:CatalogRecord", "range": "xsd:string",
    },
]


def build_ontology():
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import OWL, RDF, RDFS

    graph = Graph()
    for prefix, namespace in u.PREFIXES.items():
        graph.bind(prefix, namespace)

    ontology = URIRef(u.REGISTRY_NS)
    graph.add((ontology, RDF.type, OWL.Ontology))
    graph.add((ontology, RDFS.label, Literal("FDOx registry vocabulary", lang="en")))
    graph.add((ontology, RDFS.comment, Literal(
        "The few terms the registry needs for its own catalogue records and "
        "which neither DCAT nor PROV provides. Everything the registry says "
        "about the FDOs themselves is said in DCAT, CIDOC CRM and CRMdig; "
        "this vocabulary is deliberately small.", lang="en")))
    graph.add((ontology, URIRef(u.expand("dct:license")),
               URIRef("https://spdx.org/licenses/CC-BY-4.0.html")))
    graph.add((ontology, RDFS.seeAlso, URIRef(u.FDO_NS + "crm/")))

    kinds = {"object": OWL.ObjectProperty, "datatype": OWL.DatatypeProperty}
    for spec in ONTOLOGY_TERMS:
        term = URIRef(u.expand(spec["term"]))
        graph.add((term, RDF.type, kinds[spec["kind"]]))
        graph.add((term, RDFS.isDefinedBy, ontology))
        graph.add((term, RDFS.label, Literal(spec["label"], lang="en")))
        graph.add((term, RDFS.comment, Literal(spec["comment"], lang="en")))
        graph.add((term, RDFS.domain, URIRef(u.expand(spec["domain"]))))
        graph.add((term, RDFS.range, URIRef(u.expand(spec["range"]))))
    return graph


# ---------------------------------------------------------------------------
# 2 + 3 - making the package-local IRIs unique
# ---------------------------------------------------------------------------


def term_map(graph, record_id: str) -> tuple[dict, list[str]]:
    """IRI -> IRI for everything that is only unique inside its own package.

    Persons are keyed on the hash in their URN and become registry-global: the
    hash is derived from the person and is the same in every package naming
    them (A1, Befund 11), so scoping it to the record would give one human as
    many IRIs as they have FDOs. Distributions and content entries are the
    opposite case - `urn:fdo-squirrel:content/CITATION.cff` names a different
    file in every package - and are therefore scoped to the record.
    """
    from rdflib import URIRef

    mapping: dict = {}
    unknown: list[str] = []
    for node in set(graph.all_nodes()):
        if not isinstance(node, URIRef):
            continue
        iri = str(node)
        if not iri.startswith(URN_PREFIX):
            continue
        kind, _, local = iri[len(URN_PREFIX):].partition("/")
        if kind == "person":
            mapping[node] = URIRef(u.person_iri(iri))
        elif kind == "dist":
            mapping[node] = URIRef(u.distribution_iri(record_id, local))
        elif kind == "content":
            mapping[node] = URIRef(u.content_iri(record_id, local))
        else:
            # Not silently passed through: an unhandled urn: in the output is
            # exactly the collision this step exists to prevent.
            unknown.append(iri)
    return mapping, unknown


def rewrite(graph, mapping: dict):
    """Return a new graph with every mapped term replaced, keeping the original.

    The replaced IRI is preserved as dct:identifier on the new node, so the
    package-local name stays findable and the rewrite is reversible (A4).
    """
    from rdflib import Graph, Literal, URIRef

    identifier = URIRef(u.expand("dct:identifier"))
    out = Graph()
    for prefix, namespace in graph.namespaces():
        out.bind(prefix, namespace)
    for subject, predicate, obj in graph:
        out.add((mapping.get(subject, subject),
                 mapping.get(predicate, predicate),
                 mapping.get(obj, obj)))
    for old, new in mapping.items():
        if str(old).startswith(URN_PREFIX):
            out.add((new, identifier, Literal(str(old))))
    return out


# ---------------------------------------------------------------------------
# 5 - CRM anchors, materialised per instance
# ---------------------------------------------------------------------------


def anchor(graph, rows: list[dict[str, str]]) -> dict[str, int]:
    """Add the `instance` anchors of the crosswalk to one record's graph.

    Per instance and not as an axiom, because the subjects live in namespaces
    this registry does not own (PRIMER A3): `schema:Person rdfs:subClassOf
    crm:E21_Person` would be a statement about schema.org. The same anchor on
    the eleven people in the corpus is a statement about them.
    """
    from rdflib import URIRef
    from rdflib.namespace import RDF

    counts: dict[str, int] = {}
    for row in rows:
        if row["mechanism"] != "instance":
            continue
        term = base_term(row["fdo_term"])
        if term in TEMPORAL_TERMS:
            continue                      # see anchor_temporal
        target = URIRef(u.expand(row["target"]))
        added = 0
        if row["kind"] == "class":
            for subject in set(graph.subjects(RDF.type, URIRef(u.expand(term)))):
                if (subject, RDF.type, target) not in graph:
                    graph.add((subject, RDF.type, target))
                    added += 1
        else:
            predicate = URIRef(u.expand(term))
            iri_only = row["fdo_term"].endswith("@iri")
            for subject, obj in set(graph.subject_objects(predicate)):
                if iri_only and not isinstance(obj, URIRef):
                    continue
                if (subject, target, obj) not in graph:
                    graph.add((subject, target, obj))
                    added += 1
        if added:
            counts[row["fdo_term"]] = counts.get(row["fdo_term"], 0) + added
    return counts


def anchor_temporal(graph, targets: dict[str, str]) -> int:
    """Type the dct:PeriodOfTime node and give its bounds as xsd:gYear.

    The source writes the bounds as xsd:integer, which the profile does not
    carry as a date (Befund 15). The integer is left exactly as harvested and
    the CRM view is added beside it. A span whose start equals its end carries
    the same gYear on both bounds - that is how a single year is written, and
    nothing here invents an interval the source did not state.
    """
    from rdflib import Literal, URIRef
    from rdflib.namespace import RDF, XSD

    period_class = URIRef(u.expand("dct:PeriodOfTime"))
    time_span = URIRef(u.expand(targets["dct:PeriodOfTime"]))
    has_time_span = URIRef(u.expand("crm:P4_has_time-span"))
    temporal = URIRef(u.expand("dct:temporal"))
    bounds = ((URIRef(u.expand("dcat:startDate")), "dcat:startDate"),
              (URIRef(u.expand("dcat:endDate")), "dcat:endDate"))
    added = 0

    for period in set(graph.subjects(RDF.type, period_class)):
        if (period, RDF.type, time_span) not in graph:
            graph.add((period, RDF.type, time_span))
            added += 1
        for subject in set(graph.subjects(temporal, period)):
            if (subject, has_time_span, period) not in graph:
                graph.add((subject, has_time_span, period))
                added += 1
        for predicate, key in bounds:
            for value in set(graph.objects(period, predicate)):
                year = as_gyear(value)
                if year is None:
                    continue
                triple = (period, URIRef(u.expand(targets[key])),
                          Literal(year, datatype=XSD.gYear))
                if triple not in graph:
                    graph.add(triple)
                    added += 1
    return added


def anchor_roles(graph) -> tuple[int, set[str]]:
    """Point crm:P2_has_type at the role concept, not at the role string.

    The crosswalk declares `fdo:role rdfs:subPropertyOf crm:P2_has_type` as an
    axiom, and the source writes the role as a plain literal - so on its own
    that axiom would put a string where CRM wants a type, which is precisely
    what the SHACL gate in S5 exists to reject. The concepts were minted in S3;
    this resolves the literal against them and leaves the literal in place.
    """
    from rdflib import URIRef
    from rdflib.namespace import RDF

    role = URIRef(u.expand("fdo:role"))
    has_type = URIRef(u.expand("crm:P2_has_type"))
    concept = URIRef(u.expand("skos:Concept"))
    added, values = 0, set()

    for subject, value in set(graph.subject_objects(role)):
        if isinstance(value, URIRef):
            continue                    # already a concept: nothing to resolve
        target = URIRef(u.role_iri(str(value)))
        values.add(str(value))
        for triple in ((subject, has_type, target), (target, RDF.type, concept)):
            if triple not in graph:
                graph.add(triple)
                added += 1
    return added, values


def as_gyear(value) -> str | None:
    """300 -> '0300'. None if the value is not a plain year.

    xsd:gYear is CCYY, so a bare '300' is not a legal lexical form; a naive
    str() would produce an invalid literal that only a validator finds later.
    """
    text = str(value).strip()
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    if not digits or not digits.isdigit():
        return None
    return ("-" if negative else "") + digits.zfill(4)


# ---------------------------------------------------------------------------
# 6 - the catalogue
# ---------------------------------------------------------------------------


def name_collisions(graph) -> list[tuple[str, list[str]]]:
    """Names carried by more than one person node, reported and never merged.

    The corpus splits the same human two ways depending on how the package was
    built: a CITATION.cff gives an ORCID, a directory scan gives only a name
    and therefore a `urn:fdo-squirrel:person/<hash>`. Both then describe
    "Thiery, Florian". Asserting owl:sameAs on the strength of a matching name
    is how a registry invents identity - two people share a name often enough
    that the rule is wrong before it is useful. So the build names the
    candidates and leaves the decision to a human.
    """
    from rdflib import URIRef
    from rdflib.namespace import RDF

    by_name: dict[str, set[str]] = {}
    name = URIRef(u.expand("schema:name"))
    for person in graph.subjects(RDF.type, URIRef(u.expand("schema:Person"))):
        for label in graph.objects(person, name):
            by_name.setdefault(str(label), set()).add(str(person))
    return [(label, sorted(iris)) for label, iris in sorted(by_name.items())
            if len(iris) > 1]


def fdo_subject(graph) -> str | None:
    """The IRI the package uses for the FDO itself: its dcat:Dataset subject."""
    from rdflib import URIRef
    from rdflib.namespace import RDF

    subjects = sorted(str(s) for s in
                      graph.subjects(RDF.type, URIRef(u.expand("dcat:Dataset"))))
    return subjects[0] if len(subjects) == 1 else None


def catalogue_frame(records: list[dict]):
    """The dcat:Catalog and one dcat:CatalogRecord per harvested version.

    DCAT's own distinction carries the version question S0 left open: the
    *dataset* is the FDO, identified by its concept DOI - which is what the
    harvested TTL uses as its subject - and the *catalogue record* is this
    registry's entry for one pinned version of it. Two pinned versions of one
    FDO therefore give two records over one dataset, without further modelling
    and without counting the same object twice on the facet page.
    """
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF, XSD

    graph = Graph()
    for prefix, namespace in u.PREFIXES.items():
        graph.bind(prefix, namespace)

    P = {name: URIRef(u.expand(name)) for name in (
        "dct:title", "dct:description", "dct:license", "dct:issued", "dct:source",
        "dct:publisher", "dct:conformsTo", "dcat:record", "dcat:dataset",
        "foaf:primaryTopic", "fdoreg:conceptDoi", "fdoreg:versionDoi",
        "fdoreg:sha256", "fdoreg:readRepair", "prov:wasDerivedFrom")}

    catalog = URIRef(u.CATALOG_IRI)
    graph.add((catalog, RDF.type, URIRef(u.expand("dcat:Catalog"))))
    graph.add((catalog, P["dct:title"], Literal("FDOx Registry", lang="en")))
    graph.add((catalog, P["dct:description"], Literal(
        "A catalogue of FAIR Digital Objects published with fdo-squirrel. Each "
        "record points at one pinned Zenodo version; the metadata is harvested "
        "from the package itself and anchored in CIDOC CRM through the bridge "
        "at https://w3id.org/fdo-squirrel/crm/.", lang="en")))
    graph.add((catalog, P["dct:license"],
               URIRef("https://spdx.org/licenses/CC-BY-4.0.html")))
    graph.add((catalog, P["dct:issued"], Literal(u.RELEASE, datatype=XSD.date)))
    graph.add((catalog, P["dct:conformsTo"], URIRef(u.FDO_NS + "crm/")))
    graph.add((catalog, P["dct:publisher"],
               URIRef("http://www.wikidata.org/entity/Q73901970")))

    for record in records:
        node = URIRef(u.record_iri(record["record_id"]))
        dataset = URIRef(record["concept_doi_url"])
        graph.add((catalog, P["dcat:record"], node))
        graph.add((catalog, P["dcat:dataset"], dataset))
        graph.add((node, RDF.type, URIRef(u.expand("dcat:CatalogRecord"))))
        graph.add((node, P["foaf:primaryTopic"], dataset))
        graph.add((node, P["fdoreg:conceptDoi"], dataset))
        graph.add((node, P["fdoreg:versionDoi"], URIRef(record["version_doi_url"])))
        graph.add((node, P["dct:source"], URIRef(record["zenodo_url"])))
        if record.get("title"):
            graph.add((node, P["dct:title"], Literal(record["title"], lang="en")))
        if record.get("issued"):
            graph.add((node, P["dct:issued"],
                       Literal(record["issued"], datatype=XSD.date)))
        if record.get("sha256"):
            graph.add((node, P["fdoreg:sha256"], Literal(record["sha256"])))
        if record.get("source_url"):
            graph.add((node, P["prov:wasDerivedFrom"], URIRef(record["source_url"])))
        for label in record.get("repairs", ()):
            graph.add((node, P["fdoreg:readRepair"], Literal(label)))
    return graph


# ---------------------------------------------------------------------------
# The step
# ---------------------------------------------------------------------------


def main(strict: bool = False) -> None:
    records = u.harvested_records()
    if not records:
        u.skipped("no harvested FDO metadata under data/raw/fdo/ "
                  "(run: python main.py --only harvest)")
        return
    if not u.CRM_CROSSWALK.exists():
        u.skipped(f"{u.CRM_CROSSWALK.relative_to(u.ROOT)} does not exist yet (written in S3)")
        return

    from rdflib import BNode, Graph, URIRef

    rows = read_crosswalk(u.CRM_CROSSWALK)
    normalise = {URIRef(u.expand(base_term(row["fdo_term"]))): URIRef(u.expand(row["target"]))
                 for row in rows if row["mechanism"] == "normalise"}
    temporal_targets = {base_term(row["fdo_term"]): row["target"] for row in rows
                        if row["mechanism"] == "instance"
                        and base_term(row["fdo_term"]) in TEMPORAL_TERMS}

    ontology = build_ontology()
    u.write_canonical_turtle(ontology, u.REGISTRY_ONTOLOGY, keep_nt=False)
    print(f"  {u.REGISTRY_ONTOLOGY.relative_to(u.ROOT)}: {len(ontology)} triples, "
          f"{len(ONTOLOGY_TERMS)} terms")

    merged = Graph()
    for prefix, namespace in u.PREFIXES.items():
        merged.bind(prefix, namespace)

    entries: list[dict] = []
    problems: list[str] = []
    anchor_totals: dict[str, int] = {}
    role_values: set[str] = set()
    normalised = repaired = 0

    for directory in records:
        record_id = directory.name
        reading = u.read_fdo(directory)
        if reading.graph is None:
            print(f"  skipped: {record_id}: {reading.reason}")
            problems.append(f"{record_id}: {reading.reason}")
            continue
        if reading.repairs:
            repaired += 1
            print(f"  repaired: {record_id}: {', '.join(reading.repairs)}")

        harvest = u.read_json(directory / "harvest.json")

        mapping, unknown = term_map(reading.graph, record_id)
        for iri in unknown:
            problems.append(f"{record_id}: unhandled {iri}")
        present = [old for old in normalise if (None, None, old) in reading.graph]
        mapping.update({old: normalise[old] for old in present})
        normalised += len(present)

        graph = rewrite(reading.graph, mapping)

        for term, count in anchor(graph, rows).items():
            anchor_totals[term] = anchor_totals.get(term, 0) + count
        if temporal_targets:
            added = anchor_temporal(graph, temporal_targets)
            if added:
                anchor_totals["dct:temporal"] = anchor_totals.get("dct:temporal", 0) + added
        added, values = anchor_roles(graph)
        if added:
            anchor_totals["fdo:role"] = anchor_totals.get("fdo:role", 0) + added
        role_values |= values

        # The FDO identifies itself by its concept DOI, so that is what the
        # catalogue record takes as its primary topic. A package that ever
        # names something else would make the record point at the wrong thing,
        # and it should say so here rather than in a graph nobody re-reads.
        subject = fdo_subject(graph)
        concept = (f"https://doi.org/{harvest['concept_doi']}"
                   if harvest.get("concept_doi") else None)
        if subject is None:
            problems.append(f"{record_id}: no single dcat:Dataset subject in the package")
        elif concept and subject != concept:
            problems.append(f"{record_id}: package subject {subject} is not its "
                            f"concept DOI {concept}")

        entries.append({
            "record_id": record_id,
            "concept_doi_url": concept or subject,
            "version_doi_url": f"https://doi.org/{harvest['version_doi']}",
            "zenodo_url": f"https://zenodo.org/records/{record_id}",
            "title": harvest.get("title"),
            "issued": harvest.get("publication_date"),
            "sha256": harvest.get("sha256"),
            "source_url": harvest.get("source_url"),
            "repairs": reading.repairs,
        })
        merged += graph
        print(f"  {record_id}: {len(graph)} triples")

    if not entries:
        u.skipped("no package in the pinned list could be read")
        return

    merged += catalogue_frame(entries)

    leftover = sorted({str(term) for triple in merged for term in triple
                       if isinstance(term, URIRef) and str(term).startswith("urn:")})
    blank = len({term for triple in merged for term in triple
                 if isinstance(term, BNode)})
    problems += [f"urn: IRI left in the bundle: {iri}" for iri in leftover]
    if blank:
        problems.append(f"{blank} blank node(s) in the bundle")

    u.ensure_dirs(u.DIST)
    u.write_canonical_turtle(merged, u.BUNDLE)

    pinned = len(u.pinned_record_ids()) or len(records)
    print(f"  {len(entries)} of {pinned} pinned records in the catalogue, "
          f"{repaired} read with declared repairs")

    # Reported on every run, but never a build failure: the corpus will carry
    # this split until somebody decides the identity, and a --strict CI that is
    # red for a year is a CI nobody reads.
    for label, iris in name_collisions(merged):
        print(f"  note: {label!r} is carried by {len(iris)} person nodes "
              f"({', '.join(iris)}) - not merged, see S5")
    print(f"  {normalised} abbreviated class IRI(s) normalised, "
          f"{sum(anchor_totals.values())} CRM anchor triples added")
    print("  anchors: " + ", ".join(f"{term} {count}" for term, count
                                    in sorted(anchor_totals.items())))
    print(f"  {u.BUNDLE.relative_to(u.ROOT)}: {len(merged)} triples, "
          f"{len(leftover)} urn: IRIs, {blank} blank nodes")

    # The concepts were minted in S3 from the crosswalk; a role the corpus uses
    # and the vocabulary does not have would leave a dangling skos:Concept in
    # the bundle, which is worse than an unmapped literal.
    known_roles = {row["value"] for row in read_crosswalk(u.ROLE_CROSSWALK)}
    unknown_roles = sorted(role_values - known_roles)
    if unknown_roles:
        problems.append("fdo:role value(s) not in the vocabulary: "
                        + ", ".join(unknown_roles))

    if problems:
        for problem in problems:
            print(f"  warning: {problem}")
        if strict:
            raise SystemExit(f"{len(problems)} problem(s) in the bundle build")


if __name__ == "__main__":
    main()
