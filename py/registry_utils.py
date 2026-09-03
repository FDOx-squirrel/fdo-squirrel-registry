"""Shared constants and helpers for the FDOx registry.

Every generator imports paths, the release date, the IRI builders and the
canonical writers from here. Two reasons: moving a directory stays a one-line
change, and the output stays deterministic because there is exactly one place
that decides how a graph is serialised.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------

# The one date that may appear in generated output. Never datetime.now():
# an artefact must change exactly when data or model changed, otherwise its
# diff is noise and nobody reads it any more (PRIMER A3).
RELEASE = "2026-09-03"

# ---------------------------------------------------------------------------
# Namespaces (PRIMER A6)
# ---------------------------------------------------------------------------

FDO_NS = "https://w3id.org/fdo-squirrel/"
REGISTRY_NS = FDO_NS + "registry/"
CATALOG_IRI = REGISTRY_NS + "catalog"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry"
SOURCES = REGISTRY / "sources.json"
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_FDO = RAW / "fdo"
DERIVED = DATA / "derived"
CROSSWALKS = ROOT / "crosswalks"
METADATA = ROOT / "metadata"
DIST = ROOT / "dist"
DOCS = ROOT / "docs"

BUNDLE = DIST / "fdo-registry.ttl"
INDEX = DIST / "registry-index.json"


def ensure_dirs(*paths: Path) -> None:
    """Create generated directories on demand, so none sit empty in git."""
    for path in paths or (RAW_FDO, DIST, DOCS):
        path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# IRI construction
# ---------------------------------------------------------------------------


def record_iri(record_id: str | int) -> str:
    """The dcat:CatalogRecord for one harvested FDO."""
    return f"{REGISTRY_NS}record/{record_id}"


def distribution_iri(record_id: str | int, sha256: str) -> str:
    """Replaces urn:fdo-squirrel:dist/<sha>, which is only unique per package."""
    return f"{record_iri(record_id)}/dist/{sha256[:16]}"


def content_iri(record_id: str | int, path_in_zip: str) -> str:
    """Replaces urn:fdo-squirrel:content/<path>, which collides across packages
    whenever two FDOs contain a file of the same name (PRIMER A1, Befund 2)."""
    from urllib.parse import quote

    return f"{record_iri(record_id)}/content/{quote(path_in_zip)}"


def agent_iri(record_id: str | int, name: str) -> str:
    """Fallback for a creator without an ORCID; ORCID IRIs are used directly."""
    return f"{record_iri(record_id)}/agent/{slugify(name)}"


def slugify(text: str) -> str:
    """ASCII, lower case, hyphens — stable across runs and safe in an IRI."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-") or "unnamed"


def zenodo_record_id(doi: str) -> str:
    """'10.5281/zenodo.18724635', a DOI URL, or a bare '18724635' -> '18724635'.

    The bare form is accepted because that is how a record is named on the
    command line (`--zip 18724635=...`) and in a Zenodo URL; sources.json is
    still validated separately, so a bare id cannot slip into the curated list.
    """
    doi = doi.strip()
    if doi.isdigit():
        return doi
    match = re.search(r"zenodo\.(\d+)", doi)
    if not match:
        raise ValueError(f"not a Zenodo DOI or record id: {doi}")
    return match.group(1)


# ---------------------------------------------------------------------------
# Deterministic writers
# ---------------------------------------------------------------------------


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(data, path: Path) -> Path:
    """Sorted keys, real UTF-8, trailing newline — so diffs mean something."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def write_canonical_turtle(graph, path: Path, *, keep_nt: bool = True) -> Path:
    """Serialise a graph reproducibly.

    rdflib's Turtle output is not stable across runs, so the canonical form is
    sorted N-Triples and the Turtle file is produced from that. Skolemise blank
    nodes before calling this: a blank node gets a fresh id on every parse and
    makes two otherwise identical runs differ.
    """
    from rdflib import Graph  # imported here so --list stays cheap

    path.parent.mkdir(parents=True, exist_ok=True)

    lines = sorted(
        line for line in graph.serialize(format="nt").splitlines() if line.strip()
    )
    nt_path = path.with_suffix(".nt")
    nt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    canonical = Graph()
    for prefix, namespace in graph.namespaces():
        canonical.bind(prefix, namespace)
    canonical.parse(nt_path, format="nt")
    path.write_text(canonical.serialize(format="turtle"), encoding="utf-8")

    if not keep_nt:
        nt_path.unlink()
    return path


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_fingerprint(*paths: Path) -> str:
    """A short hash over inputs and generator, for provenance in the output.

    Binds an artefact to the state it was made from without using a clock: it
    changes when the inputs or the generating script change, and not otherwise.
    """
    digest = hashlib.sha256()
    for path in sorted(paths, key=str):
        try:
            label = str(path.relative_to(ROOT))
        except ValueError:      # outside the repo: use the bare name, so the
            label = path.name   # hash carries no machine-local path
        digest.update(label.encode("utf-8"))
        digest.update(sha256_file(path).encode("ascii"))
    return digest.hexdigest()[:16]


def git_revision() -> str | None:
    """Short commit hash, or None outside a checkout. Never fails the build."""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


# ---------------------------------------------------------------------------
# Step protocol
# ---------------------------------------------------------------------------


def skipped(reason: str) -> None:
    """Report a step that has nothing to do yet.

    Every step checks its own precondition and says why it did nothing, rather
    than failing or silently succeeding. Until the later steps are implemented
    this is also what makes `python main.py` a meaningful smoke test.
    """
    print(f"skipped (no input): {reason}")


def harvested_records() -> list[Path]:
    """Directories under data/raw/fdo/ that hold an fdo-metadata.ttl."""
    if not RAW_FDO.exists():
        return []
    return sorted(p.parent for p in RAW_FDO.glob("*/fdo-metadata.ttl"))


# ---------------------------------------------------------------------------
# Local, uncommitted configuration
# ---------------------------------------------------------------------------

LOCAL_CONFIG = ROOT / "config.local.json"


def local_config() -> dict:
    """config.local.json — machine-specific paths, gitignored. Missing is fine.

    Known keys:
      package_dir   folder holding FDOx package ZIPs by their Zenodo file name,
                    so the harvest reads them instead of downloading (S2).
    Path values are returned as Path objects.
    """
    if not LOCAL_CONFIG.exists():
        return {}
    config = read_json(LOCAL_CONFIG)
    for key in ("package_dir",):
        if config.get(key):
            config[key] = Path(config[key]).expanduser()
    return config
