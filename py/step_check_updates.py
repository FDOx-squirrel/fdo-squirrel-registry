"""S2 — report newer versions and unlisted community records. Changes nothing.

A network step, never part of the default run:

    python main.py --only check-updates

Two questions, both answered from Zenodo and written to
data/raw/check-updates.json and to the terminal:

1. For every pinned record in registry/sources.json: is there a newer version
   of the same concept? Zenodo answers this from the pinned record itself via
   /api/records/<id>/versions/latest, so no concept DOI is needed to ask.
2. Which records of the Zenodo community `squirrel-fdo` are not yet in
   sources.json?

Following a newer version or adding a community record is a curatorial
decision: this step reports, the human edits sources.json (PRIMER A4).
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Callable

import registry_utils as u
from step_harvest import (GIVE_UP_AFTER, ZENODO_API, HttpStatusError, Unreachable,
                          find_metadata_file, http_get, load_sources, package_files)

COMMUNITY = "squirrel-fdo"
# Zenodo runs InvenioRDM. Proven by probe on 2026-09-03: these paths answer
# 200 *without* query parameters, and 400 as soon as `size` and `page` are
# appended. So none are appended: the first page is fetched bare and every
# further page is taken from the `links.next` the API itself returns. A client
# that constructs its own paging URLs is guessing at a contract the server
# already states.
COMMUNITY_SEARCH = [
    "https://zenodo.org/api/communities/{community}/records",
    "https://zenodo.org/api/records?q=parent.communities.entries.slug%3A%22{community}%22",
    "https://zenodo.org/api/records?communities={community}",
]
MAX_PAGES = 50          # a stop, in case `links.next` ever cycles
REPORT_ATTEMPTS = 2     # a stale report costs less than a long wait

REPORT = u.RAW / "check-updates.json"

Fetcher = Callable[[str], bytes]


def latest_version(record_id: str, fetch: Fetcher) -> dict:
    """The latest version record of the concept the pinned record belongs to."""
    return json.loads(fetch(f"{ZENODO_API}{record_id}/versions/latest"))


def community_endpoint(fetch: Fetcher) -> tuple[str, dict] | tuple[None, None]:
    """The first template that answers, with its first page already parsed."""
    for template in COMMUNITY_SEARCH:
        url = template.format(community=COMMUNITY)
        try:
            payload = json.loads(fetch(url))
        except HttpStatusError as error:
            print(f"  community endpoint not available ({error})")
            continue
        return url, payload
    return None, None


def community_records(fetch: Fetcher) -> tuple[list[dict], str | None]:
    """All hits of the community search. Returns (hits, the endpoint that answered).

    Paging follows `links.next`; Zenodo decides the page size.
    """
    url, payload = community_endpoint(fetch)
    if url is None:
        return [], None

    hits: list[dict] = []
    seen_urls = {url}
    for _ in range(MAX_PAGES):
        hits.extend((payload.get("hits") or {}).get("hits") or [])
        nxt = (payload.get("links") or {}).get("next")
        if not nxt or nxt in seen_urls:
            return hits, url
        seen_urls.add(nxt)
        payload = json.loads(fetch(nxt))

    print(f"  stopped after {MAX_PAGES} pages — the report may be short")
    return hits, url


def cheap_get(url: str) -> bytes:
    """Fewer retries than the harvest uses: this step only writes a report."""
    return http_get(url, attempts=REPORT_ATTEMPTS)


def main(strict: bool = False, *, fetch: Fetcher = cheap_get, today: str | None = None) -> dict:
    if not u.SOURCES.exists():
        u.skipped(f"{u.SOURCES.relative_to(u.ROOT)} does not exist")
        return {}
    sources = load_sources()
    if not sources:
        u.skipped("registry/sources.json lists no sources")
        return {}

    pinned = {u.zenodo_record_id(s["version_doi"]): s for s in sources}
    today = today or dt.date.today().isoformat()  # data about this check, see step_harvest

    # The community listing is fetched first, because it answers most of the
    # question on its own: Zenodo returns the newest version per concept, so a
    # pinned record whose concept appears there needs no separate request. That
    # turns one call per record into one call in total — the difference between
    # a few seconds and several minutes when the API is slow.
    unreachable: list[str] = []
    endpoint: str | None = None
    try:
        hits, endpoint = community_records(fetch)
        if endpoint is None:
            print(f"  community '{COMMUNITY}' could not be searched on any known endpoint")
            unreachable.append(f"community:{COMMUNITY}")
    except (Unreachable, HttpStatusError) as error:
        print(f"  community search failed: {error}")
        hits = []
        unreachable.append(f"community:{COMMUNITY}")

    latest_by_concept = {str(hit.get("conceptrecid")): hit for hit in hits}

    # Concept ids of everything already pinned, so a newer version of a listed
    # record is reported once (as an update) and not twice (again as unlisted).
    concepts: set[str] = set()
    for record_id in pinned:
        on_disk = u.RAW_FDO / record_id / "record.json"
        if on_disk.exists():
            concepts.add(str(json.loads(on_disk.read_bytes()).get("conceptrecid")))

    # 1. newer versions of pinned records
    updates: list[dict] = []
    asked = 0
    for record_id, source in pinned.items():
        on_disk = u.RAW_FDO / record_id / "record.json"
        concept = (str(json.loads(on_disk.read_bytes()).get("conceptrecid"))
                   if on_disk.exists() else None)

        latest = latest_by_concept.get(concept) if concept else None
        if latest is None:
            # Not covered by the listing — restricted, not in the community, or
            # the search failed. Only these cost a request.
            try:
                latest = latest_version(record_id, fetch)
                asked += 1
            except (Unreachable, HttpStatusError) as error:
                print(f"  {record_id:>9}  unreachable  {error}")
                unreachable.append(record_id)
                if len(unreachable) >= GIVE_UP_AFTER:
                    print(f"\n  {GIVE_UP_AFTER} in a row unreachable — stopping. Zenodo is not answering.")
                    break
                continue

        concepts.add(str(latest.get("conceptrecid")))
        latest_id = str(latest.get("id"))
        if latest_id != record_id:
            entry, _ = find_metadata_file(latest)
            updates.append({
                "pinned_record_id": record_id,
                "pinned_version_doi": source["version_doi"],
                "latest_record_id": latest_id,
                "latest_doi": latest.get("doi"),
                "latest_version": (latest.get("metadata") or {}).get("version"),
                "latest_publication_date": (latest.get("metadata") or {}).get("publication_date"),
                "latest_has_metadata_ttl": entry is not None,
                "latest_packages": [p.get("key") for p in package_files(latest)],
            })

    # 2. community records not in sources.json
    unlisted: list[dict] = []
    for hit in hits:
        hit_id = str(hit.get("id"))
        if hit_id not in pinned and str(hit.get("conceptrecid")) not in concepts:
            entry, _ = find_metadata_file(hit)
            unlisted.append({
                "record_id": hit_id,
                "doi": hit.get("doi"),
                "concept_doi": hit.get("conceptdoi"),
                "title": (hit.get("metadata") or {}).get("title"),
                "publication_date": (hit.get("metadata") or {}).get("publication_date"),
                "has_metadata_ttl": entry is not None,
                "packages": [p["key"] for p in package_files(hit)],
            })
    unlisted.sort(key=lambda h: h["record_id"])

    report = {"checked": today, "community": COMMUNITY, "community_endpoint": endpoint,
              "pinned": len(pinned),
              "unreachable": unreachable, "extra_requests": asked,
              "newer_versions": updates, "unlisted_community_records": unlisted}
    u.write_json(report, REPORT)

    print(f"  {len(pinned)} pinned record(s) checked, community '{COMMUNITY}' searched "
          f"({len(hits)} records; {asked} extra request(s) needed)")
    if updates:
        print(f"\n  newer versions ({len(updates)}):")
        for up in updates:
            what = TTL_NAME if up["latest_has_metadata_ttl"] else ", ".join(up["latest_packages"]) or "no package"
            print(f"    {up['pinned_record_id']} -> {up['latest_record_id']}  "
                  f"({up['latest_doi']}, v{up['latest_version']}, {what})")
    else:
        print("  no newer versions")
    if unlisted:
        print(f"\n  community records not in sources.json ({len(unlisted)}):")
        for hit in unlisted:
            what = (TTL_NAME if hit["has_metadata_ttl"]
                    else ", ".join(hit["packages"])
                    or "no package — a paper or slides, not an FDO to harvest")
            print(f"    {hit['record_id']}  {hit['title'][:70]}")
            print(f"               {what}")
    else:
        print("  every community record is listed")
    print(f"\n  report: {REPORT.relative_to(u.ROOT)}")

    if unreachable:
        print(f"\n  {len(unreachable)} of {len(pinned)} record(s) could not be asked: "
              f"{', '.join(unreachable)} — this report is incomplete")
    if strict and (updates or unlisted or unreachable):
        raise SystemExit("check-updates found something to curate and --strict is set")
    return report


if __name__ == "__main__":
    main()
