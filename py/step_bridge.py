"""S3 - crosswalks/*.csv -> metadata/crm_bridge.ttl, metadata/vocab/role.ttl, docs/crosswalk.html.

The crosswalk CSV is the single source. Three kinds of row leave this step as
RDF and the rest leave it as documentation:

    axiom       a statement about a term in our own namespace (fdo:, fdoreg:)
    ext-axiom   a statement quoted verbatim from an external ontology - CRMdig,
                GeoSPARQL, the NFDI4Objects application profile - never invented
                here, and carrying the source it was quoted from
    normalise   an abbreviated class IRI the generator writes and S4 replaces
    instance    an anchor S4 materialises per object, because the subject is in
                a foreign namespace we do not axiomatise (PRIMER A3)
    none        no anchor, with the reason in the note column

Two checks run at build time and fail the step, because a bridge that quietly
asserts something about dcat: is worse than no bridge at all:

  * an `axiom` row whose subject is outside fdo:/fdoreg:
  * an `ext-axiom` row without a named source
"""

from __future__ import annotations

import csv
from pathlib import Path

import registry_utils as u

MECHANISMS = {"axiom", "ext-axiom", "normalise", "instance", "none"}
RDF_MECHANISMS = {"axiom", "ext-axiom"}

# Predicate per kind of statement. A class row relates two classes, a property
# row two properties; getting this from the row rather than from a guess is
# what keeps rdfs:subPropertyOf out of a class hierarchy.
PREDICATE = {"class": "rdfs:subClassOf", "property": "rdfs:subPropertyOf"}


def read_crosswalk(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [{k: (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(handle)]
    return rows


def check(rows: list[dict[str, str]]) -> list[str]:
    """Return the problems found. An empty list is the acceptance criterion."""
    problems: list[str] = []
    for number, row in enumerate(rows, start=2):     # line 1 is the header
        term = row["fdo_term"]
        where = f"{u.CRM_CROSSWALK.name}:{number} ({term})"

        if row["mechanism"] not in MECHANISMS:
            problems.append(f"{where}: unknown mechanism {row['mechanism']!r}")
            continue
        if not row["target"] and not row["note"]:
            problems.append(f"{where}: neither a target nor a reason")
        if row["target"] and row["kind"] not in PREDICATE and row["kind"] != "field":
            problems.append(f"{where}: unknown kind {row['kind']!r}")

        # An unknown prefix is reported, not raised: one typo should not hide
        # the other four problems in the file.
        bad_prefix = False
        # kind=field names a path in MD.cff, not an RDF term, so it has no
        # prefix to resolve. Those rows exist to record that a field of the
        # source metadata has no counterpart in the harvested graph at all.
        candidates = ([] if row["kind"] == "field" else [base_term(term)])
        for curie in candidates + [row["target"]]:
            if not curie:
                continue
            try:
                u.expand(curie)
            except ValueError as error:
                problems.append(f"{where}: {error}")
                bad_prefix = True
        if bad_prefix:
            continue

        if row["mechanism"] in RDF_MECHANISMS:
            subject = u.expand(base_term(term))
            own = subject.startswith(u.OWN_NAMESPACES)
            if row["mechanism"] == "axiom" and not own:
                problems.append(
                    f"{where}: axiom about a foreign namespace - use ext-axiom "
                    f"with a source, or materialise it per instance")
            if row["mechanism"] == "ext-axiom":
                if own:
                    problems.append(f"{where}: ext-axiom about our own term - use axiom")
                if not row["source"]:
                    problems.append(f"{where}: ext-axiom without a named source")
            if not row["target"]:
                problems.append(f"{where}: {row['mechanism']} without a target")

        if row["mechanism"] == "normalise" and not row["target"]:
            problems.append(f"{where}: normalise without a target")

    return problems


def base_term(term: str) -> str:
    """'dcat:keyword@iri' -> 'dcat:keyword'.

    Two rows may describe the same predicate under different conditions - an
    IRI-valued keyword is anchored, a string-valued one cannot be - so the
    condition is carried in the term and stripped before the IRI is built.
    """
    return term.split("@", 1)[0]


def build_bridge(rows: list[dict[str, str]]):
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import OWL, RDF, RDFS

    graph = Graph()
    for prefix, namespace in u.PREFIXES.items():
        graph.bind(prefix, namespace)

    # A6: the bridge is published under https://w3id.org/fdo-squirrel/crm/
    ontology = URIRef(u.FDO_NS + "crm/")
    graph.add((ontology, RDF.type, OWL.Ontology))
    graph.add((ontology, RDFS.label, Literal("FDOx to CIDOC CRM bridge", lang="en")))
    graph.add((ontology, RDFS.comment, Literal(
        "Generated from crosswalks/fdo--crm.csv. Every statement about a term "
        "outside the FDOx namespace is quoted from that term's own ontology or "
        "from the NFDI4Objects application profile; nothing is asserted here "
        "about a namespace this registry does not own.", lang="en")))
    graph.add((ontology, RDFS.seeAlso,
               URIRef("https://nfdi4objects.github.io/crm-rdf-ap/")))

    # Row-level attribution lives in the CSV and on the crosswalk page. Here it
    # is collected on the ontology, because rdfs:comment on crmdig:D1 would read
    # as part of CRMdig's own definition rather than as our note about it.
    for source in sorted({row["source"] for row in rows
                          if row["mechanism"] == "ext-axiom" and row["source"]}):
        graph.add((ontology, URIRef(u.expand("dct:source")), Literal(source)))

    for row in rows:
        if row["mechanism"] not in RDF_MECHANISMS:
            continue
        subject = URIRef(u.expand(base_term(row["fdo_term"])))
        predicate = URIRef(u.expand(PREDICATE[row["kind"]]))
        graph.add((subject, predicate, URIRef(u.expand(row["target"]))))
    return graph


def build_role_vocabulary(roles: list[dict[str, str]]):
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF, SKOS

    graph = Graph()
    for prefix, namespace in u.PREFIXES.items():
        graph.bind(prefix, namespace)

    scheme = URIRef(u.ROLE_SCHEME)
    graph.add((scheme, RDF.type, SKOS.ConceptScheme))
    graph.add((scheme, URIRef(u.expand("dct:title")),
               Literal("FDOx distribution roles", lang="en")))
    graph.add((scheme, URIRef(u.expand("dct:description")), Literal(
        "The values fdo:role takes on a dcat:Distribution inside an FDOx "
        "package. A flat list: the source draws no hierarchy between the "
        "values, and inventing one here would put structure into the registry "
        "that the packages do not carry.", lang="en")))

    for role in roles:
        concept = URIRef(u.role_iri(role["value"]))
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.inScheme, scheme))
        graph.add((concept, SKOS.prefLabel, Literal(role["pref_label"], lang="en")))
        graph.add((concept, SKOS.notation, Literal(role["value"])))
        graph.add((concept, SKOS.definition, Literal(role["definition"], lang="en")))
        graph.add((scheme, SKOS.hasTopConcept, concept))
    return graph


def observed_roles() -> tuple[dict[str, int], list[tuple[str, str]]]:
    """Count fdo:role values in the harvested corpus; report what could not be read.

    Not decoration: the vocabulary is only worth having if it covers the stock,
    and the packages the registry cannot read are the first entries of the
    quality report in S5.
    """
    from rdflib import URIRef

    counts: dict[str, int] = {}
    unreadable: list[tuple[str, str]] = []
    predicate = URIRef(u.expand("fdo:role"))

    for directory in sorted(u.RAW_FDO.glob("*")) if u.RAW_FDO.exists() else []:
        if not directory.is_dir():
            continue
        reading = u.read_fdo(directory)
        if reading.graph is None:
            unreadable.append((directory.name, reading.reason))
            continue
        if reading.repairs:
            # Named here as well as in S4, because the crosswalk page states
            # what the role counts were counted over. A number whose corpus is
            # not stated is a number nobody can check.
            print(f"  repaired: {directory.name}: {', '.join(reading.repairs)}")
        for value in graph_objects(reading.graph, predicate):
            counts[value] = counts.get(value, 0) + 1
    return counts, unreadable


def graph_objects(graph, predicate) -> list[str]:
    return [str(value) for value in graph.objects(None, predicate)]


def render_page(rows, roles, counts, unreadable) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    environment = Environment(
        loader=FileSystemLoader(str(u.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )
    template = environment.get_template("crosswalk.html.j2")
    groups = [(mechanism, [r for r in rows if r["mechanism"] == mechanism])
              for mechanism in ("axiom", "ext-axiom", "normalise", "instance", "none")]
    return template.render(
        release=u.RELEASE,
        groups=groups,
        roles=[dict(role, count=counts.get(role["value"], 0)) for role in roles],
        unreadable=unreadable,
        role_scheme=u.ROLE_SCHEME,
    )


def main(strict: bool = False) -> None:
    if not u.CRM_CROSSWALK.exists():
        u.skipped(f"{u.CRM_CROSSWALK.relative_to(u.ROOT)} does not exist yet (written in S3)")
        return

    rows = read_crosswalk(u.CRM_CROSSWALK)
    roles = read_crosswalk(u.ROLE_CROSSWALK)

    problems = check(rows)
    if problems:
        for problem in problems:
            print(f"  error: {problem}")
        raise SystemExit(f"{len(problems)} problem(s) in {u.CRM_CROSSWALK.name}")

    bridge = build_bridge(rows)
    u.write_canonical_turtle(bridge, u.CRM_BRIDGE, keep_nt=False)
    vocabulary = build_role_vocabulary(roles)
    u.write_canonical_turtle(vocabulary, u.ROLE_VOCAB, keep_nt=False)

    counts, unreadable = observed_roles()
    u.DOCS.mkdir(parents=True, exist_ok=True)
    page = u.DOCS / "crosswalk.html"
    page.write_text(render_page(rows, roles, counts, unreadable), encoding="utf-8")

    by_mechanism: dict[str, int] = {}
    for row in rows:
        by_mechanism[row["mechanism"]] = by_mechanism.get(row["mechanism"], 0) + 1
    print(f"  {len(rows)} crosswalk rows: "
          + ", ".join(f"{count} {name}" for name, count in sorted(by_mechanism.items())))
    print(f"  {u.CRM_BRIDGE.relative_to(u.ROOT)}: {len(bridge)} triples")
    print(f"  {u.ROLE_VOCAB.relative_to(u.ROOT)}: {len(vocabulary)} triples, "
          f"{len(roles)} concepts")
    print(f"  {page.relative_to(u.ROOT)}")

    # The vocabulary has to cover the stock, and it can only be checked against
    # the packages that parse.
    unknown = sorted(set(counts) - {role["value"] for role in roles})
    if unknown:
        message = f"fdo:role value(s) not in the vocabulary: {', '.join(unknown)}"
        if strict:
            raise SystemExit(message)
        print(f"  warning: {message}")
    if counts:
        print("  fdo:role in the readable corpus: "
              + ", ".join(f"{value} {count}" for value, count in sorted(counts.items())))
    for name, reason in unreadable:
        print(f"  skipped (no input): package {name}: {reason}")


if __name__ == "__main__":
    main()
