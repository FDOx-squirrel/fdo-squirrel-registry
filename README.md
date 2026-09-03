# FDOx Registry

A registry for **FAIR Digital Objects** packaged with the
[FDOx Squirrel reference implementation](https://github.com/Research-Squirrel-Engineers/fdo-squirrel).

`fdo-squirrel` makes *one* package machine-readable. This repository makes
*many* of them findable: it harvests the RDF descriptions of FDOx packages
published on Zenodo, bundles them into a DCAT catalogue anchored in CIDOC CRM,
validates the result with SHACL, and publishes a filter page and a browser-based
SPARQL page as a static site — no server, no endpoint, no database.

> **Status: S3 of the work plan.** The skeleton, the orchestrator, the Zenodo
> harvest and the CIDOC CRM crosswalk are in place; the remaining pipeline
> steps report `skipped (no input)` until the step that implements them is
> done. See [`PRIMER.md`](PRIMER.md) for the plan.

## Pipeline

```
registry/sources.json            curated list of DOIs
        │  py/step_harvest.py    Zenodo REST: record → files → fdo-metadata.ttl
        ▼
data/raw/fdo/<record-id>/        harvested, unchanged, read-only
        │                        crosswalks/fdo--crm.csv
        │  py/step_bridge.py     → metadata/crm_bridge.ttl, vocab/role.ttl,
        │                          docs/crosswalk.html
        │  py/step_bundle.py     catalogue, IRI disambiguation, CRM anchors
        ▼
dist/fdo-registry.ttl            DCAT + FDOx + CRM/CRMdig + GeoSPARQL + SKOS
        │  py/step_validate.py   SHACL gate → the build stops on a violation
        ▼
docs/                            index.html (facets) · sparql.html (Pyodide)
```

## Requirements

Python ≥ 3.10.

```
pip install -r requirements.txt
```

## Running

There is exactly one entry point:

```
python main.py                     run every step, in order
python main.py --list              print the steps and exit
python main.py --only bundle       run one step
python main.py --from bundle       run this step and everything after it
python main.py --dry-run           print the plan, run nothing
python main.py --strict            warnings become errors (this is what CI runs)
```

`main.py` writes `dist/pipeline_report.txt` with the same lines it prints, plus
a timing table.

**Harvesting is not part of the default run.** It is the only step that reaches
the network, so it has to be asked for:

```
python main.py --only harvest          fetch the FDO metadata
python main.py --only check-updates    report newer versions, change nothing
```

### Harvesting

`registry/sources.json` is the curated list of pinned Zenodo version DOIs. For
each entry the harvest fetches the record, obtains `fdo-metadata.ttl` and
writes it unchanged to `data/raw/fdo/<record-id>/` beside the record and a
`harvest.json` manifest.

An FDOx package is a single ZIP holding the data *and* its metadata, so the TTL
is normally inside a file of several hundred megabytes. It is obtained by the
cheapest trustworthy route: a top-level file in the record if there is one, a
local copy of the package if you have one, otherwise the one ZIP member read
through HTTP Range requests — one or two requests and a few kilobytes instead
of the whole archive. `harvest.json` records which route was taken and whether
the ZIP's MD5 or the member's CRC-32 was verified.

```
python py\step_harvest.py --resolve              what does each DOI resolve to?
python py\step_harvest.py --resolve --write      pin the resolved versions
python py\step_harvest.py --force                 re-fetch even if up to date
python py\step_harvest.py --only 18724635         one record
python py\step_harvest.py --full                  whole-ZIP download, no Range reads
python py\step_harvest.py --offline               no network; local packages only
python py\step_harvest.py --offline --zip 18724635=C:\tmp\fdo\CO074-148----.zip
```

Repeated runs fetch nothing when the metadata is already present and unchanged.

A DOI taken from a paper or a Zenodo landing page is usually the *concept* DOI,
which always resolves to the newest version — the opposite of a pin. `--resolve`
asks Zenodo what each entry really is, reports entries that turn out to be the
same record seen from two directions, and proposes a corrected `sources.json`;
`--write` applies it. Run it once before the first harvest.

`check-updates` additionally searches the Zenodo community `squirrel-fdo` for
records that are not listed yet. Zenodo runs InvenioRDM and has moved that
endpoint before, so the known forms are tried in order and the report says
which one answered; if none does, the report is marked incomplete rather than
failing the step.

A record that cannot be reached is a statement about Zenodo, not about the
record: nothing is written, nothing is remembered, and the run continues with
the next entry, stopping after three consecutive failures.

### Local configuration

Machine-specific paths go into `config.local.json`, which is not committed:

```json
{ "package_dir": "C:\\tmp\\fdo" }
```

With `package_dir` set, the harvest reads a package from disk whenever the
folder holds a file of the record's file name, and falls back to Zenodo
otherwise. The file may be absent.

### The CIDOC CRM bridge

`crosswalks/fdo--crm.csv` is the single source for `metadata/crm_bridge.ttl`,
`metadata/vocab/role.ttl` and the human-readable page `docs/crosswalk.html`.
Every row carries one of five mechanisms, and the distinction is the point: this
repository asserts nothing about a namespace it does not own.

| Mechanism | Meaning |
|---|---|
| `axiom` | a statement about a term in `fdo:`/`fdoreg:`, written into the bridge |
| `ext-axiom` | a statement about a foreign term, quoted verbatim from that term's own ontology or from the application profile, with the source named |
| `normalise` | an abbreviated class IRI the generator writes, replaced when the bundle is built |
| `instance` | an anchor materialised per object, because the subject is in a foreign namespace |
| `none` | deliberately unanchored, with the reason in the row |

The build fails on an `axiom` about a foreign namespace, an `ext-axiom` without
a named source, an unknown prefix, or a row with neither a target nor a reason.

The anchors follow the
[NFDI4Objects CIDOC-CRM in RDF application profile](https://nfdi4objects.github.io/crm-rdf-ap/),
which forbids several constructs a naive CRM mapping reaches for first — `E55
Type` for keywords, `E32 Authority Document`, `E95 Spacetime Primitive`, the
`P82a`/`P82b` time properties. The profile says nothing about CRMdig, so the
CRMdig subclass axioms are quoted from CRMdig itself: every FDO is reachable as
a `crm:E73_Information_Object` by a consumer that reads only CRM core.

Every step is also runnable on its own, for example `python py/step_bundle.py`.

## Layout

| Path | Contents |
|---|---|
| `main.py` | the orchestrator, the only entry point |
| `py/registry_utils.py` | release date, paths, IRI builders, deterministic writers |
| `py/step_*.py` | one module per pipeline step |
| `registry/sources.json` | the curated list of harvested DOIs |
| `data/raw/fdo/` | harvested FDO metadata, unchanged and read-only (generated) |
| `crosswalks/` | `fdo--crm.csv` and `fdo-role--skos.csv`, the sources of the bridge |
| `metadata/` | registry vocabulary, CRM bridge, role vocabulary, SHACL shapes (generated) |
| `dist/` | the products: bundle, index, reports (generated, versioned) |
| `docs/` | the published site (generated) |
| `PRIMER.md` | the work plan — German, internal, and the place decisions live |

Anything under `dist/`, `docs/` and `metadata/` is rebuilt by `python main.py`. It is
versioned all the same, because the bundle is the citable output of this
repository. Edit the generator, never the artefact.

## Reproducibility

A rebuild produces byte-identical files when nothing has changed: no generator
reads the clock, graphs are serialised through sorted N-Triples, and JSON is
written with sorted keys. The check is to run the pipeline twice and confirm
`git status` is empty the second time.

## AI usage

Parts of the Python code in this repository were written with the assistance of
Claude (Anthropic). All AI-assisted code was reviewed, validated and supervised
by Florian Thiery (research software engineering).

## Licence

Code: MIT (see [`LICENSE`](LICENSE)). The generated bundle is CC BY 4.0; the
licences of the harvested FDOs are preserved per entry.

## Citation

See [`CITATION.cff`](CITATION.cff).

## Acknowledgements

This work is part of the DFG-funded NFDI initiative, specifically the
[Research Data Infrastructure for the Material Remains of Human History
(NFDI4Objects)](https://www.nfdi4objects.net/) — DFG project number
**501836407**.
