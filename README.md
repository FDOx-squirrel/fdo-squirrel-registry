# FDOx Registry

A registry for **FAIR Digital Objects** packaged with the
[FDOx Squirrel reference implementation](https://github.com/Research-Squirrel-Engineers/fdo-squirrel).

`fdo-squirrel` makes *one* package machine-readable. This repository makes
*many* of them findable: it harvests the RDF descriptions of FDOx packages
published on Zenodo, bundles them into a DCAT catalogue anchored in CIDOC CRM,
validates the result with SHACL, and publishes a filter page and a browser-based
SPARQL page as a static site — no server, no endpoint, no database.

> **Status: S1 of the work plan.** The skeleton and the orchestrator are in
> place; every pipeline step reports `skipped (no input)` until the step that
> implements it is done. See [`PRIMER.md`](PRIMER.md) for the plan.

## Pipeline

```
registry/sources.json            curated list of DOIs
        │  py/step_harvest.py    Zenodo REST: record → files → fdo-metadata.ttl
        ▼
data/raw/fdo/<record-id>/        harvested, unchanged, read-only
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
python main.py --only harvest
```

Every step is also runnable on its own, for example `python py/step_bundle.py`.

## Layout

| Path | Contents |
|---|---|
| `main.py` | the orchestrator, the only entry point |
| `py/registry_utils.py` | release date, paths, IRI builders, deterministic writers |
| `py/step_*.py` | one module per pipeline step |
| `registry/sources.json` | the curated list of harvested DOIs |
| `data/raw/fdo/` | harvested FDO metadata, unchanged and read-only (generated) |
| `crosswalks/` | `fdo--crm.csv`, the source of the CIDOC CRM bridge |
| `metadata/` | registry vocabulary, CRM bridge, SHACL shapes |
| `dist/` | the products: bundle, index, reports (generated, versioned) |
| `docs/` | the published site (generated) |
| `PRIMER.md` | the work plan — German, internal, and the place decisions live |

Anything under `dist/` and `docs/` is rebuilt by `python main.py`. It is
versioned all the same, because the bundle is the citable output of this
repository. Edit the generator, never the artefact.

## Reproducibility

A rebuild produces byte-identical files when nothing has changed: no generator
reads the clock, graphs are serialised through sorted N-Triples, and JSON is
written with sorted keys. The check is to run the pipeline twice and confirm
`git status` is empty the second time.

## Licence

Code: MIT (see [`LICENSE`](LICENSE)). The generated bundle is CC BY 4.0; the
licences of the harvested FDOs are preserved per entry.

## Citation

See [`CITATION.cff`](CITATION.cff).
