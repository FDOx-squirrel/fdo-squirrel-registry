"""S2 — harvest FDOx metadata from Zenodo into data/raw/fdo/.

A network step, never part of the default run:

    python main.py --only harvest
    python py\\step_harvest.py --force                 re-fetch even if up to date
    python py\\step_harvest.py --only 18724635         one record
    python py\\step_harvest.py --full                  whole-ZIP download, no Range reads
    python py\\step_harvest.py --resolve              what does each DOI resolve to?
    python py\\step_harvest.py --resolve --write      pin the resolved versions
    python py\\step_harvest.py --offline               no network at all (see below)
    python py\\step_harvest.py --offline --zip 18724635=C:\\tmp\\fdo\\CO074-148----.zip

What it does per entry of registry/sources.json:

1. Derive the Zenodo record id from the pinned version DOI, fetch
   https://zenodo.org/api/records/<id>, keep it unchanged as record.json.
2. Locate `fdo-metadata.ttl`. An FDOx package is a ZIP that carries the data
   *and* its metadata, so the TTL is normally *inside* the ZIP (found
   2026-09-03 on record 18724635: one ZIP of ~300 MB, TTL at its root). The
   file is obtained by the cheapest trustworthy route, in this order:
     a. a top-level file of the record named exactly fdo-metadata.ttl
        (direct download, MD5 checked against Zenodo);
     b. a local copy of the package ZIP — `--zip <id>=<path>`, or
        `package_dir` in config.local.json holding a file of the same name —
        whose MD5 matches the record's checksum, read with zipfile;
     c. the package ZIP on Zenodo via HTTP Range requests: central directory
        plus the one member, CRC-32 checked, a few requests instead of the
        whole file;
     d. a full download of the ZIP (`--full`, or when the server does not
        serve ranges), MD5 checked.
   Name variants are reported, not guessed. A record without the file is
   skipped with the reason in harvest.json — a finding for the quality
   report (S5), not a failure of the harvest.
3. Write harvest.json: ids, DOIs, title, record dates, package name, route,
   what was verified, the member's SHA-256 (fdoreg:sha256 later) and the
   fetch date.

`--offline` reaches for nothing: record.json is reused when present, the ZIP
comes from `--zip` or `package_dir`. Without a record.json the entry is still
harvested — with the record fields empty and a warning — so S3/S4 can proceed
while Zenodo is down; a later online run completes it.

A second run downloads nothing when the TTL is present with the recorded
SHA-256, so `git status` stays clean. The fetch date is the one place a clock
is read: it is data about the harvest, written once into data/raw/ and read
from there by every later step (PRIMER A3).

The registry reads, it does not correct: nothing from the record or the TTL
is altered here. Curated facts in sources.json (concept DOI) are checked
against the record and a mismatch reported, never overwritten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import posixpath
import shutil
from pathlib import Path
from typing import Callable

import package_zip as pz
import registry_utils as u

ZENODO_API = "https://zenodo.org/api/records/"
TTL_NAME = "fdo-metadata.ttl"
USER_AGENT = ("fdo-squirrel-registry/" + u.RELEASE
              + " (+https://github.com/Research-Squirrel-Engineers/fdo-squirrel-registry)")
TIMEOUT = 120         # seconds per request
RETRIES = 5           # attempts per URL
BACKOFF = (2, 5, 10, 20)    # seconds between attempts; Zenodo's API answers 504
                            # under load and recovers within a minute or two.
                            # Kept short on purpose: when Zenodo is down for the
                            # day, waiting 75 s per URL across a growing list of
                            # records only delays the message that says so.
GIVE_UP_AFTER = 3           # consecutive unreachable records before stopping

Fetcher = Callable[[str], bytes]


class Unreachable(RuntimeError):
    """Zenodo did not answer after all retries. Not a statement about the record."""


class HttpStatusError(RuntimeError):
    """A 4xx answer. The server understood and said no — so it carries meaning.

    Typed here rather than passed through as requests.HTTPError, so that callers
    can distinguish "this URL is wrong" from "the network is down" without
    importing requests and without matching on message text.
    """

    def __init__(self, status: int, url: str):
        super().__init__(f"{status} for {url}")
        self.status, self.url = status, url


# ---------------------------------------------------------------------------
# Network — the only functions in this step that go online
# ---------------------------------------------------------------------------


def _with_retries(request, attempts: int = RETRIES):
    """Run `request()` up to RETRIES times on 5xx or connection problems.

    Zenodo's API regularly answers 504 Gateway Time-out under load and is fine
    a minute later (seen 2026-09-03 on /api/records/18724635). 4xx answers
    are not retried: a 404 is a finding about the record, not the network.
    """
    import time

    import requests

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = request()
            if 400 <= response.status_code < 500:
                response.close()
                raise HttpStatusError(response.status_code, response.url)
            if response.status_code < 400:
                return response
            response.close()
            last_error = requests.HTTPError(f"{response.status_code} for {response.url}")
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
        if attempt < attempts - 1:
            wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            print(f"             retry {attempt + 1}/{attempts - 1} in {wait} s: {last_error}")
            time.sleep(wait)
    raise Unreachable(f"gave up after {attempts} attempts: {last_error}")


def http_get(url: str, attempts: int = RETRIES) -> bytes:
    """GET with retries. `attempts` is lower for reporting than for ingest:
    waiting three quarters of a minute on a dead URL is worth it when the run
    would otherwise have no data, and not worth it when it would only have a
    slightly staler report."""
    import requests  # imported here so --list, --dry-run and --offline stay offline

    return _with_retries(
        lambda: requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT),
        attempts,
    ).content


def http_get_range(url: str, start: int, end: int | None) -> tuple[int, bytes, str | None]:
    """One Range request. Returns (status, body, Content-Range).

    start < 0 with end None is a suffix range: the last -start bytes.

    Streams, so that a server ignoring the Range header (status 200) costs a
    closed connection rather than a whole-file download.
    """
    import requests

    span = f"bytes={start}" if start < 0 else f"bytes={start}-{end}"   # "-65536" is a suffix range
    headers = {"User-Agent": USER_AGENT, "Range": span}
    response = _with_retries(
        lambda: requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
    )
    try:
        if response.status_code != 206:
            return response.status_code, b"", response.headers.get("Content-Range")
        return 206, response.content, response.headers.get("Content-Range")
    finally:
        response.close()


# ---------------------------------------------------------------------------
# Record handling — pure functions over the Zenodo JSON, testable offline
# ---------------------------------------------------------------------------


def find_metadata_file(record: dict) -> tuple[dict | None, list[str]]:
    """A top-level record file named exactly fdo-metadata.ttl, plus look-alikes."""
    exact, variants = None, []
    for entry in record.get("files") or []:
        key = entry.get("key", "")
        if key == TTL_NAME:
            exact = entry
        elif key.lower().endswith(".ttl") or "fdo-metadata" in key.lower():
            variants.append(key)
    return exact, sorted(variants)


def package_files(record: dict) -> list[dict]:
    """The record's ZIP files — the FDOx packages — in name order.

    A record with no ZIP is not empty: it is usually a paper or a slide deck,
    which is why the community report says "no package" and not "no files".
    """
    return sorted((e for e in record.get("files") or [] if e.get("key", "").lower().endswith(".zip")),
                  key=lambda e: e["key"])


def parse_checksum(value: str | None) -> tuple[str, str]:
    """'md5:abc…' -> ('md5', 'abc…'). Zenodo currently publishes MD5 only."""
    if not value or ":" not in value:
        raise ValueError(f"unexpected Zenodo checksum format: {value!r}")
    algorithm, _, digest = value.partition(":")
    return algorithm.lower(), digest.lower()


def digests(data: bytes) -> dict[str, str]:
    return {"md5": hashlib.md5(data).hexdigest(), "sha256": hashlib.sha256(data).hexdigest()}


def verify_checksum(label: str, data_or_path, checksum: str | None) -> str:
    """Compare a whole file with Zenodo's checksum; raises on mismatch."""
    algorithm, expected = parse_checksum(checksum)
    if isinstance(data_or_path, Path):
        digest = hashlib.new(algorithm)
        with data_or_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
    else:
        actual = hashlib.new(algorithm, data_or_path).hexdigest()
    if actual != expected:
        raise ValueError(f"{label}: checksum mismatch — Zenodo says {algorithm}:{expected}, "
                         f"file has {algorithm}:{actual}")
    return f"{algorithm}:{actual}"


def record_summary(record: dict) -> dict:
    """The few record fields the registry keeps beside the raw record.json."""
    metadata = record.get("metadata") or {}
    return {
        "record_id": str(record.get("id")),
        "doi": record.get("doi"),
        "concept_doi_record": record.get("conceptdoi"),
        "concept_record_id": record.get("conceptrecid"),
        "title": metadata.get("title"),
        "version": metadata.get("version"),
        "publication_date": metadata.get("publication_date"),
        "created": record.get("created"),
        "updated": record.get("updated"),
        "access_right": metadata.get("access_right") or (record.get("access") or {}).get("files"),
    }


def is_up_to_date(target: Path) -> bool:
    """True when nothing about this record needs fetching again.

    Harvested: harvest.json says so and the TTL on disk matches its SHA-256.
    Skipped: harvest.json says so and was written from a real record — a
    published Zenodo record is immutable, so a package without the TTL will
    not grow one; a fix arrives as a new version with a new record id, and
    that is a sources.json edit, not a re-fetch. `--force` re-checks anyway.
    Entries harvested offline without a record are never up to date.
    """
    manifest, ttl = target / "harvest.json", target / TTL_NAME
    if not manifest.exists():
        return False
    try:
        recorded = u.read_json(manifest)
    except json.JSONDecodeError:
        return False
    if not recorded.get("record_available", True):
        return False
    if recorded.get("status") == "skipped":
        return True
    return (recorded.get("status") == "harvested" and ttl.exists()
            and recorded.get("sha256") == u.sha256_file(ttl))


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------


class Options:
    """Everything that steers one harvest run, in one place for tests."""

    def __init__(self, *, force=False, only=None, full=False, offline=False,
                 resolve=False, write=False, prune=False,
                 zips: dict[str, Path] | None = None, package_dir: Path | None = None,
                 fetch: Fetcher = http_get, fetch_range: pz.RangeFetcher = http_get_range,
                 today: str | None = None):
        self.force, self.only, self.full, self.offline = force, only, full, offline
        self.resolve, self.write, self.prune = resolve, write, prune
        self.zips = zips or {}
        self.package_dir = package_dir
        self.fetch, self.fetch_range = fetch, fetch_range
        # The one clock read in the repository, by design (PRIMER A3).
        self.today = today or dt.date.today().isoformat()


def local_package(record_id: str, key: str | None, options: Options) -> Path | None:
    """A package ZIP on disk: --zip beats package_dir/<key>."""
    if record_id in options.zips:
        return options.zips[record_id]
    if key and options.package_dir and (options.package_dir / key).is_file():
        return options.package_dir / key
    return None


# ---------------------------------------------------------------------------
# Obtaining the TTL — the four routes
# ---------------------------------------------------------------------------


def obtain_ttl(record_id: str, record: dict | None, options: Options, warnings: list[str]) -> tuple[bytes | None, dict]:
    """Return (ttl bytes or None, provenance). None means: not in this record."""
    # `inspected` is the licence to retire a TTL already on disk: it means the
    # package contents were actually read and did not contain the file. Failing
    # to look — offline, no local copy — must never count as looking.
    prov: dict = {"route": None, "package": None, "package_checksum_zenodo": None,
                  "package_md5_verified": False, "crc32_verified": False,
                  "lookalikes": [], "inspected": False}

    # a. top-level fdo-metadata.ttl in the record
    if record is not None:
        entry, variants = find_metadata_file(record)
        prov["lookalikes"] = variants
        if entry is not None:
            if options.offline:
                warnings.append("top-level fdo-metadata.ttl in the record cannot be fetched offline")
            else:
                data = options.fetch(entry["links"]["self"])
                verify_checksum(f"{record_id}/{TTL_NAME}", data, entry.get("checksum"))
                prov.update({"route": "direct", "package": None, "package_md5_verified": True,
                             "source_url": entry["links"]["self"]})
                return data, prov

    # the package ZIP(s) to look into
    packages = package_files(record) if record is not None else []
    if record is None:
        packages = [{"key": None, "checksum": None, "links": {}}]   # offline, --zip only
    if record is not None and not packages and not record.get("files"):
        warnings.append("the record lists no files at all (restricted, embargoed or empty)")
        prov["inspected"] = True     # the file list is conclusive on its own
    elif record is not None and not packages:
        prov["inspected"] = True     # files, but no package and no direct TTL

    for package in packages:
        key = package.get("key")
        checksum = package.get("checksum")
        label = f"{record_id}/{key or '<local zip>'}"

        # b. local copy
        local = local_package(record_id, key, options)
        if local is not None:
            if checksum:
                prov["package_checksum_zenodo"] = verify_checksum(label, local, checksum)
                prov["package_md5_verified"] = True
            else:
                warnings.append(f"local ZIP {local.name} used without a record to verify it against")
            data, info = pz.member_from_local_zip(local, TTL_NAME)
            prov.update({"route": "local", "package": key or local.name, "local_path_name": local.name,
                         "inspected": True,
                         **{k: v for k, v in info.items() if k != "fetch_mode"}})
            if data is not None:
                return data, prov
            continue
        if options.offline or record is None:
            continue

        url = package["links"]["self"]
        prov["package_checksum_zenodo"] = checksum

        # c. HTTP Range
        if not options.full:
            try:
                data, info = pz.member_from_remote_zip(url, TTL_NAME, options.fetch_range)
                prov.update({"route": "range", "package": key, "source_url": url,
                             "inspected": True,
                             **{k: v for k, v in info.items() if k != "fetch_mode"}})
                if data is not None:
                    return data, prov
                continue
            except pz.RangeUnsupported as error:
                warnings.append(f"{error}; falling back to a full download")

        # d. full download
        blob = options.fetch(url)
        prov["package_checksum_zenodo"] = verify_checksum(label, blob, checksum)
        prov["package_md5_verified"] = True
        data, info = pz.member_from_zip_bytes(blob, TTL_NAME)
        prov.update({"route": "full", "package": key, "source_url": url,
                     "inspected": True,
                     **{k: v for k, v in info.items() if k != "fetch_mode"}})
        if data is not None:
            return data, prov

    return None, prov


# ---------------------------------------------------------------------------
# One entry
# ---------------------------------------------------------------------------


def harvest_one(source: dict, options: Options) -> dict:
    version_doi = source["version_doi"]
    requested_id = u.zenodo_record_id(version_doi)
    target = u.RAW_FDO / requested_id
    warnings: list[str] = []

    if not options.force and is_up_to_date(target):
        recorded = u.read_json(target / "harvest.json")
        recorded["_action"] = "skipped" if recorded.get("status") == "skipped" else "up to date"
        recorded["_cached"] = True
        return recorded

    # -- the record
    record_bytes: bytes | None = None
    if options.offline:
        if (target / "record.json").exists():
            record_bytes = (target / "record.json").read_bytes()
        else:
            warnings.append("offline and no record.json on disk — record fields left empty; "
                            "re-run online to complete this entry")
    else:
        record_bytes = options.fetch(ZENODO_API + requested_id)
    record = json.loads(record_bytes) if record_bytes else None

    summary = record_summary(record) if record else {
        k: None for k in ("doi", "concept_doi_record", "concept_record_id", "title", "version",
                          "publication_date", "created", "updated", "access_right")}
    summary["record_id"] = requested_id
    if record and record_summary(record)["record_id"] != requested_id:
        # Zenodo resolves a concept record id to its latest version. A pinned
        # registry must not ingest a record it did not ask for — but neither
        # should one bad pin stop the harvest: the entry is skipped with the
        # replacement named, and `--resolve` turns that into a sources.json edit.
        resolved = record_summary(record)["record_id"]
        resolved_doi = record_summary(record)["doi"]
        manifest = {**summary, "version_doi": version_doi, "concept_doi": curated_concept
                    if (curated_concept := source.get("concept_doi")) else None,
                    "record_available": False, "fetched": options.today,
                    "status": "skipped", "resolves_to": resolved,
                    "reason": f"{version_doi} is a concept DOI: Zenodo resolves it to record "
                              f"{resolved} ({resolved_doi}). Pin the version DOI in sources.json "
                              f"— `python py\\step_harvest.py --resolve` proposes the edit",
                    "warnings": warnings, "_action": "skipped"}
        return manifest

    curated_concept = source.get("concept_doi")
    if record:
        if curated_concept is None:
            warnings.append(f"concept_doi missing in sources.json; the record says "
                            f"{summary['concept_doi_record']!r}")
        elif summary["concept_doi_record"] and curated_concept != summary["concept_doi_record"]:
            warnings.append(f"concept_doi in sources.json ({curated_concept}) differs from the "
                            f"record ({summary['concept_doi_record']})")

    manifest = {**summary, "version_doi": version_doi, "concept_doi": curated_concept,
                "record_available": record is not None, "fetched": options.today, "warnings": warnings}

    # -- the TTL
    data, prov = obtain_ttl(requested_id, record, options, warnings)
    if data is None:
        if record is None and not local_package(requested_id, None, options):
            reason = "offline, no record.json on disk and no --zip given for this record"
        else:
            reason = (f"no {TTL_NAME} in the record" if prov.get("inspected")
                      else f"{TTL_NAME} could not be looked for (offline, no local package)")
            if prov.get("package"):
                reason += f" (looked into {prov['package']})"
            if prov.get("lookalikes"):
                reason += f"; look-alikes not used: {', '.join(prov['lookalikes'])}"
        existing = target / "harvest.json"
        if not prov.get("inspected") and (target / TTL_NAME).exists() and existing.exists():
            # Nothing was checked, so nothing is known that the previous run did
            # not already know. Overwriting a good manifest with a skip would
            # turn "I could not look" into "there is nothing there" — the one
            # confusion this step exists to prevent.
            kept = u.read_json(existing)
            kept["_action"] = "unchecked"
            return kept

        manifest.update({"status": "skipped", "reason": reason, **prov})
        target.mkdir(parents=True, exist_ok=True)
        if record_bytes:
            (target / "record.json").write_bytes(record_bytes)   # unchanged, as obtained
        stale = target / TTL_NAME
        if stale.exists() and prov.get("inspected"):
            # Only a real record may retire a TTL: it is the authority on what
            # the package contains. A skip for want of network or of a local
            # copy says nothing about the record, and deleting good data on
            # that basis loses what an offline run cannot fetch back.
            stale.unlink()
            warnings.append("removed a previously harvested fdo-metadata.ttl no longer in the record")
        elif stale.exists():
            warnings.append("keeping the fdo-metadata.ttl already on disk; this run could not check it")
        u.write_json(manifest, target / "harvest.json")
        manifest["_action"] = "skipped"
        return manifest

    # Written only now, so a failed download leaves no half-harvested record
    # behind: either the files are there or none of the new ones is.
    target.mkdir(parents=True, exist_ok=True)
    if record_bytes:
        (target / "record.json").write_bytes(record_bytes)   # unchanged, as obtained
    (target / TTL_NAME).write_bytes(data)
    manifest.update({"status": "harvested", "file": TTL_NAME, "size": len(data), **digests(data), **prov})
    u.write_json(manifest, target / "harvest.json")
    manifest["_action"] = "harvested"
    return manifest


# ---------------------------------------------------------------------------
# Step entry point
# ---------------------------------------------------------------------------


def load_sources() -> list[dict]:
    payload = u.read_json(u.SOURCES)
    if payload.get("schema_version") != "1":
        raise ValueError(f"unsupported sources.json schema_version: {payload.get('schema_version')!r}")
    sources = payload.get("sources", [])
    seen: set[str] = set()
    for source in sources:
        if "version_doi" not in source:
            raise ValueError(f"sources.json entry without version_doi: {source}")
        if not str(source["version_doi"]).startswith("10."):
            # The curated list holds DOIs, not record ids: a bare id says
            # nothing about which repository it belongs to, and the whole
            # point of sources.json is that it is citable on its own.
            raise ValueError(f"sources.json wants a DOI, not a record id: {source['version_doi']!r}")
        record_id = u.zenodo_record_id(source["version_doi"])
        if record_id in seen:
            raise ValueError(f"sources.json lists record {record_id} twice")
        seen.add(record_id)
    return sources


# ---------------------------------------------------------------------------
# --resolve: turn concept DOIs in sources.json into pinned version DOIs
# ---------------------------------------------------------------------------


def resolve_sources(sources: list[dict], options: Options, *, write: bool) -> int:
    """Ask Zenodo what each pinned DOI actually resolves to, and propose edits.

    The candidate list of a project usually starts life as concept DOIs — they
    are what a paper cites and what a Zenodo page shows first. The registry
    pins versions (A4), so somebody has to do the translation. Doing it by hand
    for ten entries invites exactly the transcription error the checksums are
    there to catch, so it is done here — but as a *proposal* that is printed,
    and only written with --write, because changing what the registry points at
    is a curatorial act.
    """
    print("  asking Zenodo what each DOI resolves to\n")
    proposals: list[dict] = []
    seen: dict[str, str] = {}
    unreachable = 0

    for source in sources:
        requested = u.zenodo_record_id(source["version_doi"])
        try:
            record = json.loads(options.fetch(ZENODO_API + requested))
        except Unreachable as error:
            print(f"  {requested:>9}  unreachable  {error}")
            unreachable += 1
            if unreachable >= GIVE_UP_AFTER:
                print(f"\n  {GIVE_UP_AFTER} in a row unreachable — stopping.")
                return 1
            proposals.append(dict(source))
            continue
        unreachable = 0

        summary = record_summary(record)
        resolved, resolved_doi = summary["record_id"], summary["doi"]
        concept = summary["concept_doi_record"] or source.get("concept_doi")
        entry = {**source, "version_doi": resolved_doi or source["version_doi"],
                 "concept_doi": concept}

        # Duplicates first: two entries can point at one record from different
        # directions — an old concept DOI and the version it now resolves to.
        # Checking identity first would let the second one look untouched.
        if resolved in seen:
            note = (f"same record as {seen[resolved]} — DROP one of the two")
            entry["_duplicate_of"] = seen[resolved]
        elif resolved == requested:
            note = "already a version DOI"
            if source.get("concept_doi") != concept:
                note += f"; concept_doi {source.get('concept_doi')!r} -> {concept!r}"
        else:
            note = f"concept DOI -> version {resolved} ({summary['title']})"

        seen.setdefault(resolved, source["version_doi"])
        proposals.append(entry)
        print(f"  {requested:>9}  {note}")

    duplicates = [e for e in proposals if "_duplicate_of" in e]
    kept = [{k: v for k, v in e.items() if not k.startswith("_")}
            for e in proposals if "_duplicate_of" not in e]

    print(f"\n  {len(proposals)} entries -> {len(kept)} distinct records"
          + (f", {len(duplicates)} duplicate(s) dropped" if duplicates else ""))
    for entry in duplicates:
        print(f"    dropped: {entry['version_doi']}  (same record as {entry['_duplicate_of']})")

    if not write:
        print("\n  nothing written — re-run with --write to apply this to "
              "registry/sources.json")
        return 0

    payload = u.read_json(u.SOURCES)
    payload["sources"] = kept
    u.write_json(payload, u.SOURCES)
    print(f"\n  written: {u.SOURCES.relative_to(u.ROOT)} — check the diff before committing")
    return 0


def report_orphans(*, prune: bool) -> list[Path]:
    """Name harvested directories that sources.json no longer lists.

    They arise normally: a concept DOI resolved to a version leaves the old id
    behind, holding a TTL that is a duplicate of the new one. Removing them is
    a curatorial act like any other change to what the registry contains, so it
    takes --prune; the default is to say so and leave them alone.
    """
    orphans = u.orphan_records()
    if not orphans:
        return []

    print(f"\n  {len(orphans)} harvested record(s) not in sources.json:")
    for directory in orphans:
        has_ttl = (directory / TTL_NAME).exists()
        note = "holds a TTL — it would be a duplicate entry" if has_ttl else "nothing harvested"
        print(f"    {directory.name}  {note}")
        if prune:
            shutil.rmtree(directory)
    print("    removed" if prune else
          "    left in place; they are ignored by later steps. Remove with --prune")
    return orphans


def parse_zip_args(values: list[str]) -> dict[str, Path]:
    zips: dict[str, Path] = {}
    for value in values:
        record_id, _, path = value.partition("=")
        if not path:
            raise SystemExit(f"--zip expects RECORD_ID=PATH, got {value!r}")
        zips[u.zenodo_record_id(record_id)] = Path(path)
    return zips


def main(strict: bool = False, options: Options | None = None) -> list[dict]:
    options = options or Options(package_dir=u.local_config().get("package_dir"))
    if not u.SOURCES.exists():
        u.skipped(f"{u.SOURCES.relative_to(u.ROOT)} does not exist")
        return []
    sources = load_sources()
    if options.only:
        sources = [s for s in sources if u.zenodo_record_id(s["version_doi"]) == options.only]
        if not sources:
            raise SystemExit(f"record {options.only} is not in sources.json")
    if not sources:
        u.skipped("registry/sources.json lists no sources")
        return []

    if options.resolve:
        raise SystemExit(resolve_sources(sources, options, write=options.write))

    if options.offline:
        print("  offline: no network, packages from --zip / package_dir only")
    if options.package_dir:
        print(f"  package_dir: {options.package_dir}")
    u.ensure_dirs(u.RAW_FDO)

    results: list[dict] = []
    unreachable = 0
    for source in sources:
        try:
            result = harvest_one(source, options)
            unreachable = 0
        except Unreachable as error:
            # A network failure is about Zenodo, not about this record: note it,
            # write nothing, and carry on. Nothing is cached, so the next run
            # picks the entry up again.
            unreachable += 1
            record_id = u.zenodo_record_id(source["version_doi"])
            print(f"  {record_id:>9}  unreachable  {source['version_doi']}")
            print(f"             {error}")
            results.append({"record_id": record_id, "version_doi": source["version_doi"],
                            "_action": "unreachable", "warnings": []})
            if unreachable >= GIVE_UP_AFTER:
                print(f"\n  {GIVE_UP_AFTER} records in a row unreachable — stopping. "
                      f"Zenodo is not answering; try again later, or work from local "
                      f"packages with --offline --zip / package_dir.")
                break
            continue
        results.append(result)
        label = result.get("title") or result["version_doi"]
        route = f" via {result['route']}" if result.get("route") and result["_action"] == "harvested" else ""
        print(f"  {result['record_id']:>9}  {result['_action']:<11} {label}{route}")
        if result["_action"] == "skipped":
            cached = " (from harvest.json; --force re-checks)" if result.get("_cached") else ""
            print(f"             reason: {result['reason']}{cached}")
        for warning in result.get("warnings", []):
            print(f"             warning: {warning}")

    counts = {a: sum(1 for r in results if r["_action"] == a)
              for a in ("harvested", "up to date", "unchecked", "skipped", "unreachable")}
    print(f"\n  {len(results)} sources: " + ", ".join(f"{n} {a}" for a, n in counts.items()))
    warnings_total = sum(len(r.get("warnings", [])) for r in results)
    if warnings_total:
        print(f"  {warnings_total} warning(s) — see harvest.json per record")
        if strict:
            raise SystemExit("harvest finished with warnings and --strict is set")
    report_orphans(prune=options.prune)

    if counts["unreachable"]:
        raise SystemExit(f"{counts['unreachable']} record(s) could not be reached")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S2 — harvest FDOx metadata from Zenodo")
    parser.add_argument("--force", action="store_true", help="re-fetch even if up to date")
    parser.add_argument("--only", metavar="RECORD_ID", help="harvest one Zenodo record id")
    parser.add_argument("--full", action="store_true", help="download whole ZIPs, no Range reads")
    parser.add_argument("--offline", action="store_true", help="no network; local packages only")
    parser.add_argument("--zip", metavar="RECORD_ID=PATH", action="append", default=[],
                        help="local package ZIP for a record (repeatable)")
    parser.add_argument("--package-dir", metavar="DIR", help="folder of local package ZIPs "
                        "(default: package_dir in config.local.json)")
    parser.add_argument("--resolve", action="store_true",
                        help="report what each DOI in sources.json resolves to")
    parser.add_argument("--write", action="store_true",
                        help="with --resolve: apply the proposal to sources.json")
    parser.add_argument("--prune", action="store_true",
                        help="delete harvested records that sources.json no longer lists")
    parser.add_argument("--strict", action="store_true", help="warnings become errors")
    args = parser.parse_args()
    package_dir = Path(args.package_dir) if args.package_dir else u.local_config().get("package_dir")
    main(strict=args.strict, options=Options(
        force=args.force, only=args.only, full=args.full, offline=args.offline,
        resolve=args.resolve, write=args.write, prune=args.prune,
        zips=parse_zip_args(args.zip), package_dir=package_dir))
