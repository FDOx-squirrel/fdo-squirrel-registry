"""S7 — queries.yaml -> docs/sparql.html (rdflib under Pyodide) and .rq files.

Two products from one source, so they cannot drift apart:

    docs/sparql.html               the page: editable queries, run in the browser
    docs/downloads/queries/*.rq    the same queries as plain files, prefixes included

There is no endpoint and no server. The bundle is a static Turtle file, fetched
by the browser and parsed client-side by rdflib under Pyodide. That is
deliberate for a catalogue meant to outlive its funding: an archived copy of
this repository stays queryable with no service kept alive for it, and nothing
the reader types leaves their machine.

Every query is executed against the real bundle here, at build time, before any
page is written, and **a query that returns no rows fails the build**. That is
not pedantry: SPARQL does not fail on a mistyped IRI, it returns nothing, so an
empty result is the ordinary symptom of a broken graph rather than of a boring
question. A page whose examples do not run is worse than no page, because the
reader cannot tell whether they broke it or it arrived broken.

Queries may additionally declare a `crosscheck` against dist/registry-index.json
(S6). The index is the second reading of the same bundle; if a query counts
something different from the facet the page shows, one of the two is wrong, and
finding out which costs nothing here and a lot later.
"""

from __future__ import annotations

import shutil
import textwrap

import registry_utils as u

QUERIES = u.ROOT / "queries.yaml"
PAGE = u.DOCS / "sparql.html"
RQ_DIR = u.DOCS / "downloads" / "queries"

# Pinned so an archived copy keeps working. An unpinned CDN path follows
# whatever Pyodide ships next, and an rdflib that no longer parses this Turtle
# would break the page silently, years after anyone is watching. Bump these
# deliberately, and re-run the page in a browser when you do.
PYODIDE_VERSION = "0.26.4"
RDFLIB_VERSION = "7.1.1"

# How many result rows the browser renders. The anchor query is deliberately
# unbounded and the bundle grows with every package; an unlimited table can
# hang a phone.
MAX_ROWS = 500


# ---------------------------------------------------------------------------
# Reading the source
# ---------------------------------------------------------------------------


def load_config() -> dict:
    import yaml

    config = yaml.safe_load(QUERIES.read_text(encoding="utf-8")) or {}
    for key in ("graph", "prefixes", "queries"):
        if key not in config:
            raise SystemExit(f"queries.yaml has no '{key}' section")
    seen: set[str] = set()
    for query in config["queries"]:
        for key in ("id", "title", "sparql"):
            if not query.get(key):
                raise SystemExit(f"a query in queries.yaml has no '{key}'")
        if query["id"] in seen:
            raise SystemExit(f"duplicate query id: {query['id']}")
        seen.add(query["id"])
        needs = query.get("needs")
        if needs and needs not in (config["graph"].get("extra") or {}):
            raise SystemExit(f"query {query['id']} needs unknown graph '{needs}'")
    return config


def load_graphs(config: dict):
    """The bundle, and each extra graph named under graph.extra, as rdflib Graphs."""
    from rdflib import Graph

    base = Graph()
    base.parse(u.BUNDLE, format="turtle")
    print(f"  {u.rel(u.BUNDLE)}: {len(base)} triples")

    extra = {}
    for key, spec in (config["graph"].get("extra") or {}).items():
        graph = Graph()
        for name in spec["files"]:
            path = u.ROOT / name
            if not path.exists():
                raise SystemExit(f"graph.extra.{key} names a missing file: {name}")
            graph.parse(path, format="turtle")
        extra[key] = graph
        print(f"  extra graph '{key}': {len(graph)} triples from "
              f"{len(spec['files'])} file(s)")
    return base, extra


# ---------------------------------------------------------------------------
# Running the queries
# ---------------------------------------------------------------------------


def run_queries(config: dict, base, extra) -> dict[str, list[dict]]:
    """Execute every query and record its row count. Zero rows is a failure."""
    results: dict[str, list[dict]] = {}
    failures: list[str] = []

    merged: dict[str, object] = {}
    for query in config["queries"]:
        target = base
        needs = query.get("needs")
        if needs:
            # Merged into a copy, so the other queries keep answering over the
            # published bundle and not over a graph nobody can download.
            if needs not in merged:
                merged[needs] = base + extra[needs]
            target = merged[needs]
        try:
            rows = list(target.query(config["prefixes"] + "\n" + query["sparql"]))
        except Exception as error:                      # noqa: BLE001
            print(f"  !! {query['id']}: {type(error).__name__}: {error}")
            failures.append(query["id"])
            continue

        columns = [str(variable) for variable in rows[0].labels] if rows else []
        results[query["id"]] = [
            {column: (None if row[index] is None else str(row[index]))
             for index, column in enumerate(columns)}
            for row in rows
        ]
        query["rows_at_build"] = len(rows)
        mark = "  " if rows else "!!"
        note = "" if rows else "  - parses, matches nothing"
        print(f"  {mark} {query['id']:<26} {len(rows):4d} rows"
              f"{'  (+ ' + needs + ')' if needs else ''}{note}")
        if not rows:
            failures.append(query["id"])

    if failures:
        raise SystemExit("a query returned no rows or did not run: "
                         + ", ".join(failures) + " - nothing written")
    return results


def crosscheck(config: dict, results: dict[str, list[dict]]) -> list[str]:
    """Compare declared queries against dist/registry-index.json (S6).

    The index is built from the same bundle by a different route. Where the two
    readings can be compared they must agree; a mismatch means the facet page
    and the query page are telling visitors different things about one file.
    """
    declared = [query for query in config["queries"] if query.get("crosscheck")]
    if not declared:
        return []
    if not u.INDEX.exists():
        return [f"{u.rel(u.INDEX)} is missing - {len(declared)} cross-check(s) "
                f"skipped (run the index step)"]

    index = u.read_json(u.INDEX)
    for query in declared:
        spec = query["crosscheck"]
        rows = results[query["id"]]
        if spec.get("entries"):
            expected = len(index["entries"])
            if len(rows) != expected:
                raise SystemExit(
                    f"{query['id']}: {len(rows)} rows, but the index has "
                    f"{expected} entries")
            print(f"  ok {query['id']:<26} {expected} entries, as in the index")
            continue

        facet = spec["facet"]
        counted: dict[str, int] = {}
        for entry in index["entries"]:
            for value in entry["facets"][facet]:
                counted[value] = counted.get(value, 0) + 1
        answered = {row[spec["value"]]: int(row[spec["count"]]) for row in rows}
        if answered != counted:
            raise SystemExit(
                f"{query['id']}: the query and the '{facet}' facet disagree.\n"
                f"    query: {dict(sorted(answered.items()))}\n"
                f"    index: {dict(sorted(counted.items()))}")
        print(f"  ok {query['id']:<26} matches the '{facet}' facet "
              f"({len(counted)} value(s))")
    return []


# ---------------------------------------------------------------------------
# Writing the products
# ---------------------------------------------------------------------------


def write_rq_files(config: dict) -> None:
    """Each query as a plain .rq file, for use outside the browser."""
    RQ_DIR.mkdir(parents=True, exist_ok=True)
    keep = {f"{query['id']}.rq" for query in config["queries"]}
    for stale in sorted(RQ_DIR.glob("*.rq")):
        if stale.name not in keep:
            stale.unlink()
            print(f"  removed stale query file {u.rel(stale)}")

    for query in config["queries"]:
        intro = "\n".join(
            f"# {line}" for line in
            textwrap.wrap(" ".join(str(query.get("intro", "")).split()), 76))
        needs = query.get("needs")
        extra_note = ""
        if needs:
            files = config["graph"]["extra"][needs]["files"]
            extra_note = "#\n# Needs, besides the bundle: " + ", ".join(files) + "\n"
        text = (f"# {query['title']}\n{intro}\n{extra_note}\n"
                f"{config['prefixes'].rstrip()}\n\n{query['sparql'].rstrip()}\n")
        u.write_text(RQ_DIR / f"{query['id']}.rq", text)
    print(f"  {u.rel(RQ_DIR)}/: {len(config['queries'])} .rq file(s)")


def publish_extra_graphs(config: dict) -> dict:
    """Copy the on-demand graphs into docs/, and say where the browser finds them.

    They live in metadata/ because that is where they are built; the browser can
    only reach what GitHub Pages serves, which is docs/. Copying rather than
    referencing keeps the page self-contained - the same reason the bundle is
    published beside it.
    """
    published = {}
    for key, spec in (config["graph"].get("extra") or {}).items():
        directory = spec.get("dir", key)
        target_dir = u.DOCS / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        urls = []
        for name in spec["files"]:
            source = u.ROOT / name
            target = target_dir / source.name
            shutil.copyfile(source, target)
            urls.append(f"{directory}/{source.name}")
        published[key] = {"label": spec.get("label", key),
                          "note": spec.get("note", ""),
                          "urls": urls}
        print(f"  {u.rel(target_dir)}/: {len(urls)} file(s) for graph '{key}'")
    return published


def render(config: dict, published: dict, triples: int) -> None:
    graph = dict(config["graph"])
    graph["extra"] = published
    queries = []
    for query in config["queries"]:
        item = dict(query)
        item["sparql"] = query["sparql"].rstrip("\n")
        # Size the editor to the query, so nothing hides behind a scrollbar the
        # reader has to discover first.
        item["rows"] = max(6, item["sparql"].count("\n") + 2)
        queries.append(item)

    page = u.template_environment().get_template("sparql.html.j2").render(
        release=u.RELEASE,
        page=config.get("page", {}),
        graph=graph,
        triples=triples,
        queries=queries,
        pyodide_version=PYODIDE_VERSION,
        rdflib_version=RDFLIB_VERSION,
        max_rows=MAX_ROWS,
        prefixes_json=u.script_json(config["prefixes"]),
        graph_json=u.script_json({"url": graph["url"], "extra": published}),
        queries_json=u.script_json({query["id"]: query["sparql"] for query in queries}),
    )
    u.write_text(PAGE, page)
    print(f"  {u.rel(PAGE)}: {len(queries)} queries, "
          f"{PAGE.stat().st_size // 1024} KB")


# ---------------------------------------------------------------------------


def main(strict: bool = False) -> None:
    if not QUERIES.exists():
        u.skipped("queries.yaml does not exist yet (written in S7)")
        return
    if not u.BUNDLE.exists():
        u.skipped(f"{u.rel(u.BUNDLE)} does not exist yet (built in S4)")
        return
    if not (u.TEMPLATES / "sparql.html.j2").exists():
        u.skipped("py/templates/sparql.html.j2 does not exist yet (written in S7)")
        return

    config = load_config()
    base, extra = load_graphs(config)
    results = run_queries(config, base, extra)
    warnings = crosscheck(config, results)
    published = publish_extra_graphs(config)
    write_rq_files(config)
    u.ensure_dirs(u.DOCS)
    render(config, published, len(base))

    # The page fetches the bundle from docs/; the site step (S6) puts it there.
    # Saying so is cheaper than a page that loads and then reports HTTP 404.
    if not (u.DOCS / config["graph"]["url"]).exists():
        warnings.append(f"docs/{config['graph']['url']} is not there yet - "
                        f"the site step publishes it")

    for warning in warnings:
        print(f"  warning: {warning}")
    if warnings and strict:
        raise SystemExit("--strict: the warnings above are errors")


if __name__ == "__main__":
    main()
