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
from typing import NamedTuple

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
ROLE_SCHEME = REGISTRY_NS + "role/"

# Prefixes used across the repository. One table, so the bridge file, the
# bundle and the query page cannot disagree about what `crmdig:` means.
PREFIXES: dict[str, str] = {
    "bibo": "http://purl.org/ontology/bibo/",
    "cff": "https://citation-file-format.github.io/terms/",
    "codemeta": "https://codemeta.github.io/terms/",
    "crm": "http://www.cidoc-crm.org/cidoc-crm/",
    "crmdig": "http://www.ics.forth.gr/isl/CRMdig/",
    "crmgeo": "http://www.ics.forth.gr/isl/CRMgeo/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "edtf": "http://id.loc.gov/datatypes/edtf/",
    "fdo": FDO_NS,
    "fdoreg": REGISTRY_NS,
    "foaf": "http://xmlns.com/foaf/0.1/",
    "geosparql": "http://www.opengis.net/ont/geosparql#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "role": REGISTRY_NS + "role/",
    "schema": "https://schema.org/",
    "sf": "http://www.opengis.net/ont/sf#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "time": "http://www.w3.org/2006/time#",
    "wd": "http://www.wikidata.org/entity/",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

# Namespaces this repository is allowed to make axiomatic statements about.
# Everything else is either quoted from its own ontology or materialised per
# instance (PRIMER A3).
OWN_NAMESPACES = (FDO_NS, REGISTRY_NS)


def expand(curie: str) -> str:
    """'crm:E73_Information_Object' -> the full IRI. Raises on an unknown prefix.

    Refusing an unknown prefix is the point: a typo in the crosswalk would
    otherwise become a triple in a namespace nobody owns.
    """
    if curie.startswith("http://") or curie.startswith("https://"):
        return curie
    prefix, _, local = curie.partition(":")
    if not local or prefix not in PREFIXES:
        raise ValueError(f"unknown prefix in {curie!r}")
    return PREFIXES[prefix] + local

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
VOCAB = METADATA / "vocab"
DIST = ROOT / "dist"
DOCS = ROOT / "docs"
TEMPLATES = ROOT / "py" / "templates"

BUNDLE = DIST / "fdo-registry.ttl"
# The graph the gate validated, bundle plus the vocabularies it relies on, in
# one file. The published bundle stays free of them (A4); this is the form the
# NFDI4Objects knowledge graph is handed, because a consumer that loads only
# the bundle cannot see the CRM anchoring the bundle claims to conform to.
N4O_BUNDLE = DIST / "fdo-registry-n4o.ttl"
INDEX = DIST / "registry-index.json"
CRM_CROSSWALK = CROSSWALKS / "fdo--crm.csv"
ROLE_CROSSWALK = CROSSWALKS / "fdo-role--skos.csv"
CRM_BRIDGE = METADATA / "crm_bridge.ttl"
REGISTRY_ONTOLOGY = METADATA / "registry_ontology.ttl"
ROLE_VOCAB = VOCAB / "role.ttl"
SHAPES = METADATA / "shapes.ttl"
SHAPES_SELFTEST = METADATA / "shapes_selftest.ttl"
QUALITY_REPORT = DIST / "quality_report.md"


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


def person_iri(person_urn: str) -> str:
    """urn:fdo-squirrel:person/<hash> -> <registry>/agent/<hash>, registry-global.

    Not per record. The hash in the URN is derived from the person, not from
    the package, and it is the same in every package that names them (A1,
    Befund 11) - so rewriting it per record would give one human as many IRIs
    as they have FDOs. A creator that already carries an ORCID keeps it; this
    is only for the ones the source could not identify.
    """
    local = person_urn.rsplit("/", 1)[-1]
    return f"{REGISTRY_NS}agent/{local}"


def role_iri(value: str) -> str:
    """A skos:Concept for one value of fdo:role, in the registry role scheme."""
    return f"{ROLE_SCHEME}{slugify(value)}"


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


def bind_remaining(graph) -> list[str]:
    """Give every unbound namespace a prefix, assigned in a fixed order.

    Sorted N-Triples are byte-identical across runs; the Turtle made from them
    was not. rdflib invents `ns1`, `ns2`, ... for namespaces that have no
    prefix, in the order it happens to meet them, and that order comes out of a
    set - so `codemeta:` was ns2 in one run and ns3 in the next, and 84 lines
    of a 6000-triple file changed without a single triple changing with them.

    Binding them here, sorted by namespace IRI, makes the label a function of
    the graph rather than of the process. Everything actually used in this
    repository belongs in PREFIXES and gets a readable prefix; this is the
    floor under a package that brings a namespace nobody has seen yet.
    """
    from rdflib import URIRef
    from rdflib.namespace import split_uri

    bound = {str(namespace) for _, namespace in graph.namespaces()}
    unbound = set()
    for triple in graph:
        for term in triple:
            if not isinstance(term, URIRef):
                continue
            try:
                namespace, _ = split_uri(str(term))
            except Exception:               # not splittable: rdflib writes it out in full
                continue
            if namespace not in bound:
                unbound.add(namespace)
    assigned = []
    for number, namespace in enumerate(sorted(unbound), start=1):
        graph.bind(f"ns{number:02d}", namespace)
        assigned.append(namespace)
    return assigned


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
    bind_remaining(canonical)
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


def pending(step: str) -> None:
    """Report a step whose input is ready but whose code is not written yet.

    Raising here would stop the pipeline the moment an earlier step starts
    delivering — which is exactly when the smoke test becomes useful. So the
    step says what is missing and yields (PRIMER A4, Schrittvertrag).
    """
    print(f"pending: input is ready; implemented in {step}")


def skipped(reason: str) -> None:
    """Report a step that has nothing to do yet.

    Every step checks its own precondition and says why it did nothing, rather
    than failing or silently succeeding. Until the later steps are implemented
    this is also what makes `python main.py` a meaningful smoke test.
    """
    print(f"skipped (no input): {reason}")


def pinned_record_ids() -> set[str]:
    """Record ids of the version DOIs in registry/sources.json."""
    if not SOURCES.exists():
        return set()
    return {zenodo_record_id(entry["version_doi"])
            for entry in read_json(SOURCES).get("sources", [])
            if entry.get("version_doi")}


def harvested_records() -> list[Path]:
    """Directories under data/raw/fdo/ that hold an fdo-metadata.ttl *and* are pinned.

    The filter is not tidiness. A directory left over from an earlier pin still
    holds a valid TTL, and an unfiltered glob would bundle it — for a concept
    DOI that was later resolved, that means the same FDO twice, under two
    record IRIs, with nothing in the graph to say they are one thing.
    `step_harvest` reports such directories; only sources.json decides what is
    in the registry.
    """
    if not RAW_FDO.exists():
        return []
    pinned = pinned_record_ids()
    return sorted(p.parent for p in RAW_FDO.glob("*/fdo-metadata.ttl")
                  if not pinned or p.parent.name in pinned)


class Reading(NamedTuple):
    """The result of reading one harvested package."""

    graph: object | None            # rdflib.Graph, or None if unreadable
    reason: str | None              # why it could not be read
    repairs: tuple[str, ...] = ()   # encoding repairs applied on the way in


def read_fdo(directory: Path) -> Reading:
    """Parse one harvested fdo-metadata.ttl, repairing its encoding if needed.

    Four of the seven packages harvested on 2026-09-03 are not valid Turtle:
    three use crm:/crmdig: without declaring the prefixes, one carries
    unescaped quotes in the JSON literal at dct:provenance. Both defects were
    fixed in the generator afterwards, and a published Zenodo record never
    changes - so skipping them means losing four of eight FDOs permanently.
    Since 2026-09-03 the registry therefore applies the declared repairs in
    `repair.py` and names every one of them (A4). It still does not touch the
    *content*: what a repair cannot fix without guessing stays unread.

    Every step that touches the corpus goes through this function, so the
    bridge, the bundle and the quality report can never disagree about which
    packages are in and which were repaired to get there.
    """
    from rdflib import Graph  # kept out of module import so --list stays cheap

    import repair as repair_rules

    path = directory / "fdo-metadata.ttl"
    if not path.exists():
        return Reading(None, "no fdo-metadata.ttl in the package")

    text = path.read_text(encoding="utf-8")

    def parse(candidate: str) -> None:
        Graph().parse(data=candidate, format="turtle")

    try:
        parse(text)
        repairs: list[str] = []
    except Exception:                               # rdflib raises BadSyntax
        text, repairs = repair_rules.repair(text, parse, PREFIXES)

    graph = Graph()
    try:
        graph.parse(data=text, format="turtle")
    except Exception as error:
        detail = parse_error(error)
        if repairs:
            detail += f" (after {', '.join(repairs)})"
        return Reading(None, f"not valid Turtle: {detail}", tuple(repairs))
    return Reading(graph, None, tuple(repairs))


def read_fdo_graph(directory: Path):
    """(graph, reason) for callers that do not care which repairs were needed."""
    reading = read_fdo(directory)
    return reading.graph, reading.reason


def parse_error(error: Exception) -> str:
    """One readable line out of an rdflib BadSyntax.

    Its str() spans four lines and buries the actual complaint under a line
    number and an excerpt; a report that says "at line 17 of <>" tells nobody
    which of the two known defects they are looking at.
    """
    lines = [line.strip() for line in str(error).strip().splitlines() if line.strip()]
    location = next((line for line in lines if line.startswith("at line ")), "")
    location = location.split(" of ")[0]            # 'at line 17'
    complaint = next((line for line in lines if line.startswith("Bad syntax")), "")
    complaint = complaint.split(" at ^")[0]         # drop the excerpt pointer
    detail = ", ".join(part for part in (location, complaint) if part)
    return detail or lines[0] if lines else type(error).__name__


def orphan_records() -> list[Path]:
    """Harvested directories whose record is no longer in sources.json."""
    if not RAW_FDO.exists():
        return []
    pinned = pinned_record_ids()
    if not pinned:
        return []
    return sorted(d for d in RAW_FDO.iterdir() if d.is_dir() and d.name not in pinned)


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
