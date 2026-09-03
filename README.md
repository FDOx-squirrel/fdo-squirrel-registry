# FDOx Registry

A registry for **FAIR Digital Objects** packaged with the
[FDOx Squirrel reference implementation](https://github.com/Research-Squirrel-Engineers/fdo-squirrel).

`fdo-squirrel` makes *one* package machine-readable. This repository makes
*many* of them findable: it harvests the RDF descriptions of FDOx packages
published on Zenodo, bundles them into a DCAT catalogue anchored in CIDOC CRM,
validates the result with SHACL, and publishes a filter page and a browser-based
SPARQL page as a static site — no server, no endpoint, no database.

> **Status: S4 of the work plan.** The skeleton, the orchestrator, the Zenodo
> harvest, the CIDOC CRM crosswalk and the catalogue bundle are in place; the
> remaining pipeline steps report `skipped (no input)` until the step that
> implements them is done. See [`PRIMER.md`](PRIMER.md) for the plan.

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
dist/fdo-registry.ttl            DCAT + FDOx + CRM/CRMdig/CRMgeo + GeoSPARQL + SKOS
        │                        metadata/shapes.ttl
        │  py/step_validate.py   SHACL gate → the build stops on a violation
        │                        → dist/fdo-registry-n4o.ttl, dist/quality_report.md
        │  py/step_index.py      SPARQL → dist/registry-index.json
        │                        registry/labels.json
        │  py/step_site.py       → docs/index.html, docs/record/<id>.html
        ▼
docs/                            index.html (facets) · record/<id>.html ·
                                 sparql.html (Pyodide, S7) · fdo-registry.ttl
```

The facet page carries its index inside it rather than fetching it, so
`docs/index.html` works opened straight from disk, with no server and no
network. The same data is written beside it as `docs/registry-index.json` for
anyone who wants the catalogue without RDF.

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
python main.py --open              build, then open docs/index.html from disk
python main.py --serve             build, then serve docs/ on 127.0.0.1:8000
```

`main.py` writes `dist/pipeline_report.txt` with the same lines it prints, plus
a timing table.

The facet page needs no server — `--open` hands the file to the browser and the
page carries its data inside it. `--serve` is there for the pages that will
need an `http://` origin, and takes a port (`--serve 8080`). It is a plain
Python process holding that port: Ctrl+C, or closing the window, frees it
again, and nothing is left behind. If a port is still taken by an earlier run,
`netstat -ano | findstr :8000` names the process and `taskkill /PID <id> /F`
ends it.

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

### Reading a published package

Four of the eight pinned packages are not valid Turtle: three use `crm:` and
`crmdig:` without declaring the prefixes, one carries unescaped quotes in the
JSON literal at `dct:provenance`. Both defects were fixed in the generator
afterwards, but a published Zenodo record never changes, so no upstream
correction can reach them.

`py/repair.py` therefore applies two declared repairs before parsing. They are
*encoding* repairs, in the same sense as the `normalise` rows of the crosswalk:
the repaired form is what the same generator writes in a later package, not
something this repository invented. Every repair reports itself — in the build
log, on the crosswalk page and as `fdoreg:readRepair` on the catalogue record —
and `fdoreg:sha256` stays the hash of the original file as Zenodo holds it. A
defect that cannot be fixed without guessing at content is not repaired; it goes
into the quality report instead.

### The gate

`metadata/shapes.ttl` validates the bundle together with the vocabularies its
anchoring depends on — the CRM bridge, the role vocabulary and the registry
vocabulary. SHACL follows `rdfs:subClassOf` for `sh:targetClass` and `sh:class`
without inference, but only for axioms that are in the graph it is given, and
those axioms deliberately do not live in the published bundle. The union that
was validated is written out as `dist/fdo-registry-n4o.ttl`: what goes into a
knowledge graph should be the graph that was checked.

Severity mirrors the modal verb of the [NFDI4Objects CIDOC-CRM application
profile](https://nfdi4objects.github.io/crm-rdf-ap/). What the profile says
MUST NOT be used, and what the registry promises about its own entries, is a
violation and stops the build. What the profile says SHOULD or SHOULD NOT, and
what is merely unclean in a harvested package, is a warning and goes to
`dist/quality_report.md` as feedback for the package author. Warnings never
fail the build: a published Zenodo record is immutable, so a red CI would stay
red.

Five of the rules cannot fire against the current corpus — they exist for the
day somebody "improves" the mapping into a `crm:E55_Type`. Every rule is
therefore checked against `metadata/shapes_selftest.ttl`, a deliberately broken
graph, on every run. A rule that has never fired is a rule nobody has checked.

### The catalogue

`dist/fdo-registry.ttl` is a `dcat:Catalog`. DCAT's own distinction carries the
versioning: the **dataset** is the FDO, identified by its Zenodo concept DOI,
which is the IRI the harvested `fdo-metadata.ttl` uses as its own subject; the
**catalogue record** is this registry's entry for one pinned version of it. Two
pinned versions of one FDO give two records over one dataset.

Everything that is only unique inside its own package is rewritten before the
graphs are merged, and the original is kept as `dct:identifier`. Distributions
and file entries are scoped to the record; people are registry-global, because
the hash in `urn:fdo-squirrel:person/…` identifies the person and not the
package. People known by an ORCID keep it. Two nodes that carry the same name
are reported and never merged — asserting identity on a matching name is not
this registry's job.

`dist/fdo-registry.nt` is written beside it, as sorted N-Triples. That is the
canonical form; comparing two runs means comparing the `.nt`.

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
| `registry/labels.json` | curated display labels for IRIs the packages do not name |
| `data/raw/fdo/` | harvested FDO metadata, unchanged and read-only (generated) |
| `crosswalks/` | `fdo--crm.csv` and `fdo-role--skos.csv`, the sources of the bridge |
| `metadata/shapes.ttl` | the SHACL gate; `shapes_selftest.ttl` is the broken graph it is tested against |
| `metadata/` | registry vocabulary, CRM bridge, role vocabulary (generated) |
| `dist/` | the products: bundle, index, reports (generated, versioned) |
| `docs/` | the published site (generated) |
| `PRIMER.md` | the work plan — German, internal, and the place decisions live |

`metadata/shapes.ttl` and `metadata/shapes_selftest.ttl` are written by hand;
everything else under `dist/`, `docs/` and `metadata/` is rebuilt by `python main.py`. It is
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
