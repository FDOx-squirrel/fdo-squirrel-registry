"""S6 - query the bundle into dist/registry-index.json for the facet page.

The facet page reads this file rather than the graph, so nobody waits for a
WASM runtime just to filter by "3D". It is also the machine-readable form of
the catalogue for anyone who wants the registry without RDF.

Everything here is read out of `dist/fdo-registry.ttl` with SPARQL, and
nothing is invented on the way:

  * labels for foreign IRIs come from `registry/labels.json` (curated), never
    from dereferencing - the network belongs to S2 (PRIMER A3)
  * the SquirrelBase item comes from `registry/sources.json` (curated), because
    no package names it
  * where a package carries several dct:description, the longest is shown and
    the rest are kept, so the page can say that the source is ambiguous rather
    than hide it

Two checks make the acceptance criterion of S6 executable: the number of
entries has to match `dcat:record` in the bundle, and every entry has to carry
at least one value in at least one facet, because an entry no facet reaches is
an entry the page cannot show.
"""

from __future__ import annotations

import registry_utils as u

# The facets the page offers, in the order it shows them. Each is a key in the
# per-entry "facets" mapping below; keeping the list here rather than in the
# template means the build can check that every entry is reachable.
FACETS: list[tuple[str, str]] = [
    ("type", "FDO type"),
    ("license", "Licence"),
    ("keyword", "Keyword"),
    ("place", "Place"),
    ("year", "Published"),
    ("creator", "Creator"),
]

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

PREFIX = "\n".join(f"PREFIX {prefix}: <{namespace}>"
                   for prefix, namespace in sorted(u.PREFIXES.items())) + "\n"


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def curated_label(iri: str, labels: dict) -> str | None:
    entry = labels.get(iri)
    if isinstance(entry, dict):
        return entry.get("label") or None
    return entry or None


def derived_label(iri: str) -> str | None:
    """A label that follows from the IRI itself, for namespaces we control.

    Only two: our own FDO types, and the SPDX licence ids, whose last path
    segment *is* the licence id. Everything else needs a human (labels.json) -
    splitting a foreign IRI on its last slash produces plausible nonsense.
    """
    if iri.startswith(u.FDO_NS):
        local = iri[len(u.FDO_NS):]
        if local and "/" not in local:
            return local
    if iri.startswith("https://spdx.org/licenses/"):
        return iri.rsplit("/", 1)[-1].removesuffix(".html")
    return None


def display(iri: str, labels: dict, graph=None) -> tuple[str, bool]:
    """(label, is it named rather than guessed).

    The fallback is deliberate and visible: 'OSM relation 62273' says what the
    facet filters on and links where the reader can look it up, which is more
    honest than a place name nobody stated.
    """
    if graph is not None:
        from rdflib import URIRef
        from rdflib.namespace import RDFS, SKOS
        for predicate in (RDFS.label, SKOS.prefLabel, URIRef(u.expand("schema:name"))):
            for value in graph.objects(URIRef(iri), predicate):
                return str(value), True

    for candidate in (curated_label(iri, labels), derived_label(iri)):
        if candidate:
            return candidate, True

    if iri.startswith("https://www.openstreetmap.org/"):
        kind, _, ident = iri[len("https://www.openstreetmap.org/"):].partition("/")
        return f"OSM {kind} {ident}", False
    if iri.startswith("http://www.wikidata.org/entity/"):
        return iri.rsplit("/", 1)[-1], False
    return iri.rsplit("/", 1)[-1] or iri, False


# ---------------------------------------------------------------------------
# Reading the bundle
# ---------------------------------------------------------------------------


def query(graph, text: str):
    return list(graph.query(PREFIX + text))


def one(values, default=None):
    return values[0] if values else default


def description(values: list[str]) -> tuple[str | None, list[str]]:
    """Pick one dct:description and keep the others.

    Five of the seven packages carry four values, because MD.cff fields for
    purpose, quality and resolution ended up in the description (PRIMER A1,
    Befund 5). The registry has to show one of them; it takes the longest,
    says so on the record page, and keeps the rest. It does not decide which
    field the short ones belong to - only their author knows that.
    """
    ordered = sorted(values, key=lambda value: (-len(value), value))
    return (ordered[0] if ordered else None), ordered[1:]


def merge_keywords(keywords: list[dict]) -> list[dict]:
    """Fold a keyword that appears both as an IRI and as a string into one.

    The packages carry the same subject twice - `wd:Q2016147` and the string
    "Ogham Stone" - because the generator writes both, and once the IRI has a
    label the two read identically on a card. Compared case-insensitively,
    because the two spellings differ in case as often as not, and the IRI wins,
    because it is the one that can be anchored and looked up.

    This is display only. Nothing is merged in the graph, where both statements
    stay exactly as the package made them.
    """
    merged: dict[str, dict] = {}
    for keyword in sorted(keywords, key=lambda item: (item["iri"] is None, item["label"])):
        merged.setdefault(keyword["label"].casefold(), keyword)
    return sorted(merged.values(), key=lambda item: item["label"].casefold())


def entry_for(graph, record, labels, sources) -> dict:
    """One catalogue entry, flattened for the page."""
    record_iri = str(record.record)
    dataset = str(record.dataset)
    record_id = record_iri.rsplit("/", 1)[-1]
    source = sources.get(record_id, {})

    values: dict[str, list[str]] = {}
    for row in query(graph, f"SELECT ?p ?o WHERE {{ <{dataset}> ?p ?o }}"):
        values.setdefault(str(row.p), []).append(str(row.o))

    def objects(curie: str) -> list[str]:
        return sorted(set(values.get(u.expand(curie), [])))

    text, other_descriptions = description(objects("dct:description"))
    types = sorted(iri for iri in set(values.get(RDF_TYPE, []))
                   if iri.startswith(u.FDO_NS))

    keywords = []
    for value in objects("dcat:keyword"):
        if value.startswith("http"):
            label, named = display(value, labels)
            keywords.append({"iri": value, "label": label, "named": named})
        else:
            keywords.append({"iri": None, "label": value, "named": True})
    keywords = merge_keywords(keywords)

    places = []
    for iri in objects("dct:spatial"):
        label, named = display(iri, labels, graph)
        places.append({"iri": iri, "label": label, "named": named})

    geometry = one(query(graph, f"""
        SELECT ?wkt WHERE {{ <{dataset}> geosparql:hasGeometry/geosparql:asWKT ?wkt }}
    """))
    issued = one(objects("dct:issued")) or one(objects("dct:created"))

    entry = {
        "record_id": record_id,
        "record_iri": record_iri,
        "dataset_iri": dataset,
        "title": one(objects("dct:title")) or record_id,
        "description": text,
        "other_descriptions": other_descriptions,
        "types": [{"iri": iri, "label": display(iri, labels)[0]} for iri in types],
        "licenses": [{"iri": iri, "label": display(iri, labels)[0]}
                     for iri in objects("dct:license")],
        "creators": [{"iri": iri, "name": display(iri, labels, graph)[0]}
                     for iri in objects("dct:creator")],
        "keywords": keywords,
        "places": places,
        "geometry": str(geometry.wkt) if geometry else None,
        "period": period_for(graph, dataset),
        "issued": issued,
        "files": files_for(graph, dataset),
        "context": one(objects("fdo:context")),
        "zenodo_url": str(record.source) if record.source else None,
        "version_doi": str(record.version) if record.version else None,
        "metadata_url": str(record.derived) if record.derived else None,
        "sha256": str(record.sha256) if record.sha256 else None,
        "repairs": sorted({str(row.repair) for row in query(graph, f"""
            SELECT ?repair WHERE {{ <{record_iri}> fdoreg:readRepair ?repair }}
        """)}),
        "squirrelbase": ({
            "item": source["squirrelbase_item"],
            "iri": u.squirrelbase_iri(source["squirrelbase_item"]),
        } if source.get("squirrelbase_item") else None),
    }
    entry["facets"] = {
        "type": [term["label"] for term in entry["types"]],
        "license": [term["label"] for term in entry["licenses"]],
        "keyword": [term["label"] for term in entry["keywords"]],
        "place": [term["label"] for term in entry["places"]],
        "year": [issued[:4]] if issued else [],
        "creator": [person["name"] for person in entry["creators"]],
    }
    return entry


def period_for(graph, dataset) -> dict | None:
    """The time span as the profile has it, plus the bounds as harvested."""
    rows = query(graph, f"""
        SELECT ?period ?label ?start ?end WHERE {{
          <{dataset}> dct:temporal ?period .
          OPTIONAL {{ ?period rdfs:label ?label }}
          OPTIONAL {{ ?period dcat:startDate ?start }}
          OPTIONAL {{ ?period dcat:endDate ?end }}
        }}
    """)
    if not rows:
        return None
    row = rows[0]
    literal = one([str(item.value) for item in query(graph, f"""
        SELECT ?value WHERE {{
          <{dataset}> crm:P4_has_time-span ?value .
          FILTER(isLiteral(?value))
        }}
    """)])
    return {
        "iri": str(row.period),
        "label": str(row.label) if row.label else None,
        "start": str(row.start) if row.start is not None else None,
        "end": str(row.end) if row.end is not None else None,
        "value": literal,
    }


def files_for(graph, dataset) -> dict:
    """Count, total size and role distribution of the distributions."""
    rows = query(graph, f"""
        SELECT ?dist ?path ?role ?size ?media WHERE {{
          <{dataset}> dcat:distribution ?dist .
          OPTIONAL {{ ?dist fdo:path ?path }}
          OPTIONAL {{ ?dist fdo:role ?role }}
          OPTIONAL {{ ?dist dcat:byteSize ?size }}
          OPTIONAL {{ ?dist dcat:mediaType ?media }}
        }}
    """)
    roles: dict[str, int] = {}
    total = 0
    files: list[dict] = []
    for row in rows:
        if row.role:
            roles[str(row.role)] = roles.get(str(row.role), 0) + 1
        size = int(row.size) if row.size is not None else 0
        total += size
        files.append({
            "path": str(row.path) if row.path else str(row.dist),
            "role": str(row.role) if row.role else None,
            "bytes": size,
            "media_type": str(row.media) if row.media else None,
        })
    # Only the largest few travel into the page: a package with 242 files
    # would otherwise put a quarter of a megabyte of file names into an HTML
    # document nobody scrolls through.
    files.sort(key=lambda item: (-item["bytes"], item["path"]))
    return {
        "count": len(rows),
        "bytes": total,
        "roles": dict(sorted(roles.items())),
        "largest": files[:12],
    }


# ---------------------------------------------------------------------------
# Missing labels
# ---------------------------------------------------------------------------


def missing_labels(entries: list[dict]) -> list[dict]:
    """Every IRI the page shows without a curated label, ready to paste.

    This is the support half of the curated list: filling registry/labels.json
    is then typing labels, not hunting for which IRIs need one.
    """
    seen: dict[str, dict] = {}
    for entry in entries:
        for kind, items in (("keyword", entry["keywords"]), ("place", entry["places"])):
            for item in items:
                if item["iri"] and not item["named"]:
                    found = seen.setdefault(item["iri"], {
                        "iri": item["iri"], "used_as": kind,
                        "shown_as": item["label"], "records": [],
                    })
                    found["records"].append(entry["record_id"])
    for found in seen.values():
        found["records"] = sorted(set(found["records"]))
    return [seen[iri] for iri in sorted(seen)]


# ---------------------------------------------------------------------------
# The step
# ---------------------------------------------------------------------------


def build(graph) -> dict:
    labels = u.load_labels()
    sources = u.pinned_sources()

    records = query(graph, f"""
        SELECT ?record ?dataset ?source ?version ?derived ?sha256 WHERE {{
          <{u.CATALOG_IRI}> dcat:record ?record .
          ?record foaf:primaryTopic ?dataset .
          OPTIONAL {{ ?record dct:source ?source }}
          OPTIONAL {{ ?record fdoreg:versionDoi ?version }}
          OPTIONAL {{ ?record prov:wasDerivedFrom ?derived }}
          OPTIONAL {{ ?record fdoreg:sha256 ?sha256 }}
        }}
    """)
    entries = sorted((entry_for(graph, record, labels, sources) for record in records),
                     key=lambda entry: entry["record_id"])

    catalogue = one(query(graph, f"""
        SELECT ?title ?description ?license ?issued WHERE {{
          <{u.CATALOG_IRI}> dct:title ?title ; dct:description ?description .
          OPTIONAL {{ <{u.CATALOG_IRI}> dct:license ?license }}
          OPTIONAL {{ <{u.CATALOG_IRI}> dct:issued ?issued }}
        }}
    """))
    return {
        "release": u.RELEASE,
        "catalog": {
            "iri": u.CATALOG_IRI,
            "title": str(catalogue.title) if catalogue else "FDOx Registry",
            "description": str(catalogue.description) if catalogue else None,
            "license": str(catalogue.license) if catalogue and catalogue.license else None,
            "issued": str(catalogue.issued) if catalogue and catalogue.issued else None,
            "bundle": u.rel(u.BUNDLE),
            "triples": len(graph),
        },
        "facets": [{"key": key, "label": label} for key, label in FACETS],
        "entries": entries,
    }


def main(strict: bool = False) -> None:
    if not u.BUNDLE.exists():
        u.skipped(f"{u.BUNDLE.relative_to(u.ROOT)} does not exist yet (built in S4)")
        return

    from rdflib import Graph

    graph = Graph()
    graph.parse(u.BUNDLE, format="turtle")

    index = build(graph)
    entries = index["entries"]
    u.ensure_dirs(u.DIST)
    u.write_json(index, u.INDEX)

    unnamed = missing_labels(entries)
    u.write_json({"note": "IRIs the page shows without a curated label. "
                          "Fill them in registry/labels.json.",
                  "missing": unnamed}, u.MISSING_LABELS)

    declared = len(query(graph, f"SELECT ?r WHERE {{ <{u.CATALOG_IRI}> dcat:record ?r }}"))
    print(f"  {u.rel(u.INDEX)}: {len(entries)} entries, "
          f"{declared} dcat:record in the bundle")
    print("  facets: " + ", ".join(
        f"{label} {len({value for entry in entries for value in entry['facets'][key]})}"
        for key, label in FACETS))
    print(f"  {sum(entry['files']['count'] for entry in entries)} distributions, "
          f"{sum(entry['files']['bytes'] for entry in entries) / 1e9:.1f} GB described")

    if unnamed:
        print(f"  {len(unnamed)} IRI(s) without a curated label, listed in "
              f"{u.rel(u.MISSING_LABELS)}:")
        for item in unnamed:
            print(f"      {item['shown_as']:<24} <{item['iri']}>  "
                  f"{item['used_as']}, {len(item['records'])} record(s)")

    # The acceptance criterion of S6, checked rather than asserted.
    problems = []
    if len(entries) != declared:
        problems.append(f"{len(entries)} entries but {declared} dcat:record in the bundle")
    problems += [f"{entry['record_id']} carries no value in any facet" for entry in entries
                 if not any(entry["facets"][key] for key, _ in FACETS)]
    for problem in problems:
        print(f"  warning: {problem}")
    if problems and strict:
        raise SystemExit(f"{len(problems)} problem(s) building the index")


if __name__ == "__main__":
    main()
