"""S6 - render docs/ for GitHub Pages and publish the bundle next to it.

Three things leave this step:

    docs/index.html          the facet page, with the index embedded in it
    docs/record/<id>.html    one static page per catalogue record
    docs/fdo-registry.ttl    the bundle and the index, beside the pages that
    docs/registry-index.json show them

The index is *embedded* in index.html rather than fetched from
registry-index.json. Not a preference: `fetch()` from a `file://` page is
blocked as a cross-origin request in Chrome and, since 68, in Firefox, so a
page that loads its data would fail exactly the acceptance test S6 asks for -
open it from the repository, without a server and without a network. The same
file is written next to it for machines, and that copy is what anyone else
should read.

One page per record rather than a fragment route, because PRIMER A6 gives
`https://w3id.org/fdo-squirrel/registry/record/{id}` its own path in the IRI
map: a w3id redirect can point at a file, and it cannot point at a fragment of
one that JavaScript has to resolve first.
"""

from __future__ import annotations

import json
import shutil

import registry_utils as u

TEMPLATES = u.ROOT / "py" / "templates"


def environment():
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )
    env.filters["filesize"] = filesize
    env.filters["json"] = lambda value: json.dumps(
        value, sort_keys=True, ensure_ascii=False)
    return env


def filesize(count: int | None) -> str:
    """Bytes as a short human string. Binary steps, because file managers use them."""
    if not count:
        return "-"
    size = float(count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def facet_values(index: dict) -> list[dict]:
    """Every facet with its values and counts, sorted so the page is stable.

    Counted here rather than in the browser: the same numbers then appear in
    the build log, and a facet that has quietly lost its values is visible
    without opening the page.
    """
    facets = []
    for facet in index["facets"]:
        counts: dict[str, int] = {}
        for entry in index["entries"]:
            for value in entry["facets"][facet["key"]]:
                counts[value] = counts.get(value, 0) + 1
        facets.append({
            "key": facet["key"],
            "label": facet["label"],
            "options": [{"value": value, "count": counts[value]}
                       for value in sorted(counts, key=lambda v: (-counts[v], v))],
        })
    return facets


def main(strict: bool = False) -> None:
    if not u.INDEX.exists():
        u.skipped(f"{u.INDEX.relative_to(u.ROOT)} does not exist yet (built in S6)")
        return
    if not TEMPLATES.exists():
        u.skipped("py/templates/ does not exist yet (written in S6)")
        return

    index = u.read_json(u.INDEX)
    env = environment()
    facets = facet_values(index)

    u.ensure_dirs(u.DOCS, u.SITE_RECORDS)
    page = env.get_template("index.html.j2").render(
        release=u.RELEASE,
        catalog=index["catalog"],
        entries=index["entries"],
        facets=facets,
        index_json=json.dumps(index, sort_keys=True, ensure_ascii=False),
    )
    u.SITE_INDEX.write_text(page, encoding="utf-8")

    record_template = env.get_template("record.html.j2")
    written = []
    for entry in index["entries"]:
        target = u.SITE_RECORDS / f"{entry['record_id']}.html"
        target.write_text(record_template.render(
            release=u.RELEASE, catalog=index["catalog"], entry=entry),
            encoding="utf-8")
        written.append(target)

    # Records that were dropped from sources.json would otherwise keep their
    # page for ever, and a stale page is worse than a missing one: it is
    # reachable, it looks current, and nothing in the build mentions it.
    keep = {target.name for target in written}
    stale = sorted(path for path in u.SITE_RECORDS.glob("*.html")
                   if path.name not in keep)
    for path in stale:
        path.unlink()
        print(f"  removed stale page {u.rel(path)}")

    copies = [(u.BUNDLE, u.DOCS / u.BUNDLE.name), (u.INDEX, u.DOCS / u.INDEX.name)]
    for source, target in copies:
        shutil.copyfile(source, target)

    print(f"  {u.rel(u.SITE_INDEX)}: {len(index['entries'])} tiles, "
          f"{len(facets)} facets")
    print("  " + ", ".join(f"{facet['label']} {len(facet['options'])}"
                           for facet in facets))
    print(f"  {u.rel(u.SITE_RECORDS)}/: {len(written)} record page(s)")
    for _, target in copies:
        print(f"  {u.rel(target)}: {target.stat().st_size // 1024} KB")

    unnamed = sum(1 for entry in index["entries"]
                  for place in entry["places"] if not place["named"])
    if unnamed:
        print(f"  note: {unnamed} place(s) shown as a bare OSM id - "
              f"add them to {u.rel(u.LABELS)}")


if __name__ == "__main__":
    main()
