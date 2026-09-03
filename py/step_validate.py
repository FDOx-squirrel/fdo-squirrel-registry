"""S5 - the SHACL gate and the quality report.

The gate validates the bundle *together with* the vocabularies it relies on:
metadata/crm_bridge.ttl, metadata/vocab/role.ttl and
metadata/registry_ontology.ttl. SHACL follows rdfs:subClassOf for sh:targetClass
and sh:class on its own - checked against pyshacl, no inference needed - but it
does not invent the axioms, and the axioms are not in the published bundle. A
gate run against the bundle alone would report half the corpus as unanchored
while the anchoring sits exactly where PRIMER A3 requires it, materialised per
instance.

The union it validated is written out as dist/fdo-registry-n4o.ttl, because
what goes into the NFDI4Objects knowledge graph should be the graph that was
checked and not a subset of it. dist/fdo-registry.ttl stays as it is: the
catalogue, without the vocabularies mixed into it.

Two exits, and they mean different things:

    violations  the registry broke its own promise - a record without its
                checksum, a class with no CRM anchor, a construct the profile
                forbids. The build stops.
    warnings    a harvested package is unclean. That is a statement about the
                package, not about the registry, so it goes to
                dist/quality_report.md and travels back to the author. It never
                fails the build, not even under --strict: a published Zenodo
                record is immutable, so those 46 findings cannot be fixed
                downstream and a CI that is red for a year is a CI nobody
                reads. The same reasoning already applies to the person-name
                collision reported in S4.

--strict is fatal on exactly one thing here, and it is the one thing the
repository controls: a rule in shapes.ttl that no fixture triggers any more.
"""

from __future__ import annotations

import re
from collections import defaultdict

import registry_utils as u

SH = "http://www.w3.org/ns/shacl#"

# Enough to see the pattern, few enough to keep the report readable. The full
# list is in the bundle; a report that prints 492 IRIs is one nobody scrolls.
MAX_NODES_PER_RULE = 8

RECORD_IN_IRI = re.compile(r"/record/(\d+)")
ZENODO_IN_IRI = re.compile(r"zenodo\.(\d+)")


# ---------------------------------------------------------------------------
# Loading and running
# ---------------------------------------------------------------------------


def validated_graph():
    """The bundle plus every vocabulary the anchoring depends on."""
    from rdflib import Graph

    graph = Graph()
    for prefix, namespace in u.PREFIXES.items():
        graph.bind(prefix, namespace)
    sources = [u.BUNDLE, u.CRM_BRIDGE, u.ROLE_VOCAB, u.REGISTRY_ONTOLOGY]
    present = [path for path in sources if path.exists()]
    for path in present:
        graph.parse(path, format="turtle")
    return graph, present


def run_gate(data_graph, shapes_graph):
    """(conforms ignoring warnings, results graph). Inference stays off.

    allow_warnings makes pyshacl report sh:Warning without failing, which is
    the split this step needs: violations stop the build, warnings are the
    report. The severities themselves come from shapes.ttl, where they mirror
    the modal verb of the application profile.
    """
    from pyshacl import validate

    conforms, results, _ = validate(
        data_graph, shacl_graph=shapes_graph, inference="none",
        advanced=True, allow_warnings=True,
    )
    return conforms, results


def findings(results) -> dict[tuple[str, str], list[str]]:
    """(severity, message) -> sorted focus nodes. Deterministic by construction."""
    from rdflib import URIRef

    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for result in set(results.subjects(URIRef(SH + "focusNode"), None)):
        focus = next(results.objects(result, URIRef(SH + "focusNode")), None)
        message = next(results.objects(result, URIRef(SH + "resultMessage")), "")
        severity = next(results.objects(result, URIRef(SH + "resultSeverity")), "")
        grouped[(str(severity).rsplit("#", 1)[-1], str(message))].add(str(focus))
    return {key: sorted(nodes) for key, nodes in grouped.items()}


# ---------------------------------------------------------------------------
# The self-test
# ---------------------------------------------------------------------------


def selftest(shapes_graph) -> tuple[int, list[str]]:
    """Check that every message in shapes.ttl can actually fire.

    A rule that no longer matches anything reports green for a reason that has
    nothing to do with the data, and it does so silently for as long as nobody
    looks. Five of the rules here cannot fire against the current corpus at all
    - they exist for the day somebody "improves" the mapping into an E55 Type -
    so without a fixture their being green would mean nothing. It is offline
    and tiny, so it runs on every build.
    """
    from rdflib import Graph, URIRef

    if not u.SHAPES_SELFTEST.exists():
        return 0, [f"{u.SHAPES_SELFTEST.relative_to(u.ROOT)} is missing"]

    expected = {str(message) for message
                in shapes_graph.objects(None, URIRef(SH + "message"))}
    broken = Graph()
    broken.parse(u.SHAPES_SELFTEST, format="turtle")
    _, results = run_gate(broken, shapes_graph)
    fired = {message for _, message in findings(results)}
    return len(expected), sorted(expected - fired)


# ---------------------------------------------------------------------------
# The quality report
# ---------------------------------------------------------------------------


def record_of(iri: str, concept_to_record: dict[str, str]) -> str | None:
    """Which harvested package a flagged node belongs to, or None if it spans them.

    Registry IRIs carry the record id; the nodes the generator minted under
    doi.org carry the concept DOI, which the catalogue maps back to a record.
    Agent IRIs deliberately match neither: they are registry-global, so a
    finding on a person is a finding about the corpus and not about one package.
    """
    match = RECORD_IN_IRI.search(iri)
    if match:
        return match.group(1)
    match = ZENODO_IN_IRI.search(iri)
    if match:
        return concept_to_record.get(match.group(1))
    return None


def concept_map(graph) -> dict[str, str]:
    """Zenodo id of a concept DOI -> record id of the catalogue entry for it."""
    from rdflib import URIRef

    mapping: dict[str, str] = {}
    concept = URIRef(u.expand("fdoreg:conceptDoi"))
    for record, doi in graph.subject_objects(concept):
        record_match = RECORD_IN_IRI.search(str(record))
        doi_match = ZENODO_IN_IRI.search(str(doi))
        if record_match and doi_match:
            mapping[doi_match.group(1)] = record_match.group(1)
    return mapping


def corpus_state() -> list[dict[str, str]]:
    """One row per pinned record: what was harvested and how it reads.

    Read from disk rather than from the bundle, because the interesting rows
    are exactly the ones the bundle does not contain.
    """
    rows = []
    for record_id in sorted(u.pinned_record_ids()):
        directory = u.RAW_FDO / record_id
        row = {"record": record_id, "title": "", "state": "not harvested", "repairs": ""}
        harvest = directory / "harvest.json"
        if harvest.exists():
            row["title"] = u.read_json(harvest).get("title") or ""
        if (directory / "fdo-metadata.ttl").exists():
            reading = u.read_fdo(directory)
            if reading.graph is None:
                row["state"] = f"unreadable: {reading.reason}"
            elif reading.repairs:
                row["state"] = "read with declared repairs"
                row["repairs"] = ", ".join(reading.repairs)
            else:
                row["state"] = "read as published"
        elif harvest.exists():
            row["state"] = "no fdo-metadata.ttl in the package"
        rows.append(row)
    return rows


def write_report(by_rule, corpus, concept_to_record, sources) -> str:
    """dist/quality_report.md - deterministic, no clock, sorted throughout."""
    lines: list[str] = []
    add = lines.append

    add("# FDOx registry quality report")
    add("")
    add(f"Release {u.RELEASE}. Written by `python main.py --only validate` from "
        + ", ".join(f"`{u.rel(path)}`" for path in sources)
        + f" against `{u.rel(u.SHAPES)}`.")
    add("")
    add("Everything below is a **warning**: a statement about a harvested package, "
        "not about the registry. The registry reads and reports, it does not correct "
        "(PRIMER A3), so each entry is feedback for `fdo-squirrel` or for whoever "
        "published the package. Violations never reach this file, because they stop "
        "the build.")
    add("")

    add("## Corpus")
    add("")
    add("| Record | Title | State | Repairs |")
    add("|---|---|---|---|")
    for row in corpus:
        add(f"| `{row['record']}` | {row['title'] or '—'} | {row['state']} "
            f"| {row['repairs'] or '—'} |")
    add("")
    missing = [row for row in corpus if not row["state"].startswith("read")]
    if missing:
        add(f"{len(missing)} of {len(corpus)} pinned records are not in the catalogue. "
            "A published Zenodo record never changes, so these can only be fixed by "
            "publishing a new version.")
        add("")

    warnings = {key: nodes for key, nodes in by_rule.items() if key[0] != "Violation"}
    add("## Findings")
    add("")
    if not warnings:
        add("None. Every harvested package satisfies every rule in the gate.")
        add("")
        return "\n".join(lines) + "\n"

    total = sum(len(nodes) for nodes in warnings.values())
    add(f"{total} finding(s) over {len(warnings)} rule(s).")
    add("")
    for (_, message), nodes in sorted(warnings.items(), key=lambda item: item[0][1]):
        add(f"### {message}")
        add("")
        add(f"{len(nodes)} node(s):")
        add("")
        for node in nodes[:MAX_NODES_PER_RULE]:
            add(f"- `{node}`")
        if len(nodes) > MAX_NODES_PER_RULE:
            add(f"- … and {len(nodes) - MAX_NODES_PER_RULE} more")
        add("")

    add("## Findings per package")
    add("")
    add("| Record | Findings |")
    add("|---|---|")
    per_record: dict[str, int] = defaultdict(int)
    for nodes in warnings.values():
        for node in nodes:
            per_record[record_of(node, concept_to_record) or "across packages"] += 1
    for record in sorted(per_record, key=lambda name: (name == "across packages", name)):
        add(f"| `{record}` | {per_record[record]} |")
    add("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The step
# ---------------------------------------------------------------------------


def main(strict: bool = False) -> None:
    if not u.BUNDLE.exists():
        u.skipped(f"{u.BUNDLE.relative_to(u.ROOT)} does not exist yet (built in S4)")
        return
    if not u.SHAPES.exists():
        u.skipped(f"{u.SHAPES.relative_to(u.ROOT)} does not exist yet (written in S5)")
        return

    from rdflib import Graph

    shapes = Graph()
    shapes.parse(u.SHAPES, format="turtle")

    expected, never_fired = selftest(shapes)
    if never_fired:
        for message in never_fired:
            print(f"  warning: no fixture triggers this rule: {message}")
    else:
        print(f"  selftest: all {expected} rules fire against "
              f"{u.SHAPES_SELFTEST.relative_to(u.ROOT)}")

    graph, sources = validated_graph()
    print("  validating "
          + ", ".join(str(path.relative_to(u.ROOT)) for path in sources)
          + f" - {len(graph)} triples")

    conforms, results = run_gate(graph, shapes)
    by_rule = findings(results)
    violations = {key: nodes for key, nodes in by_rule.items() if key[0] == "Violation"}
    warnings = {key: nodes for key, nodes in by_rule.items() if key[0] != "Violation"}

    u.ensure_dirs(u.DIST)
    u.write_canonical_turtle(graph, u.N4O_BUNDLE, keep_nt=False)
    u.write_text(u.QUALITY_REPORT,
                 write_report(by_rule, corpus_state(), concept_map(graph), sources))

    if violations:
        for (_, message), nodes in sorted(violations.items(), key=lambda item: item[0][1]):
            print(f"  error: {message}")
            for node in nodes[:MAX_NODES_PER_RULE]:
                print(f"      {node}")
            if len(nodes) > MAX_NODES_PER_RULE:
                print(f"      … and {len(nodes) - MAX_NODES_PER_RULE} more")
        raise SystemExit(f"SHACL gate: "
                         f"{sum(len(nodes) for nodes in violations.values())} "
                         f"violation(s) over {len(violations)} rule(s)")

    print(f"  conforms: {conforms}, {len(u.pinned_record_ids())} pinned records")
    print(f"  {u.N4O_BUNDLE.relative_to(u.ROOT)}: {len(graph)} triples")
    print(f"  {u.QUALITY_REPORT.relative_to(u.ROOT)}: "
          f"{sum(len(nodes) for nodes in warnings.values())} warning(s) "
          f"over {len(warnings)} rule(s)")
    for (_, message), nodes in sorted(warnings.items(), key=lambda item: item[0][1]):
        print(f"    {len(nodes):4d}  {message[:92]}")

    # Warnings are deliberately not fatal, see the module docstring. An
    # untested rule is, because that one is ours to fix.
    if strict and never_fired:
        raise SystemExit(f"--strict: {len(never_fired)} rule(s) in "
                         f"{u.SHAPES.name} that no fixture triggers")


if __name__ == "__main__":
    main()
