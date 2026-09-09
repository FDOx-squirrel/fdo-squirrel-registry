# FDOx registry quality report

Release 2026-09-03. Written by `python main.py --only validate` from `dist/fdo-registry.ttl`, `metadata/crm_bridge.ttl`, `metadata/vocab/role.ttl`, `metadata/registry_ontology.ttl` against `metadata/shapes.ttl`.

Everything below is a **warning**: a statement about a harvested package, not about the registry. The registry reads and reports, it does not correct (PRIMER A3), so each entry is feedback for `fdo-squirrel` or for whoever published the package. Violations never reach this file, because they stop the build.

## Corpus

| Record | Title | State | Repairs |
|---|---|---|---|
| `18369126` | o3d-epidoc-extractor (FAIR Digital Object) | read with declared repairs | missing-prefix:crmdig, missing-prefix:crm |
| `18369157` | ogham-analysis (FAIR Digital Object) | read with declared repairs | missing-prefix:crmdig, missing-prefix:crm |
| `18369866` | GEARS/1 (FAIR Digital Object) | read with declared repairs | missing-prefix:crmdig, missing-prefix:crm, unescaped-quote |
| `18732893` | Steinmännchen / Lago di Anterselva (Antholzer See) 03.01.2026 14:36h (FAIR Digital Object) | read with declared repairs | unescaped-quote |
| `18740524` | Kunstwerk "Heinz Eau" in Köln (FAIR Digital Object) | no fdo-metadata.ttl in the package | — |
| `18742694` | Beuys-Stele B 1036 in Kassel als Teil der "7000 Eichen" (FAIR Digital Object) | read as published | — |
| `18744583` | CHUIS/1 (FAIR Digital Object) | read as published | — |
| `22675886` | CO074-148---- (FAIR Digital Object) | read as published | — |
| `22676380` | Freshford: St Lachtain's Well (FDOx) | read as published | — |

1 of 9 pinned records are not in the catalogue. A published Zenodo record never changes, so these can only be fixed by publishing a new version.

## Findings

47 finding(s) over 10 rule(s).

### A person without an ORCID. The profile asks for the established IRI (DOI, ORCID, ROR); the registry-minted agent IRI is a fallback that only works inside this catalogue.

3 node(s):

- `https://w3id.org/fdo-squirrel/registry/agent/1ef85dc7cadee6db`
- `https://w3id.org/fdo-squirrel/registry/agent/2424425c3325db08`
- `https://w3id.org/fdo-squirrel/registry/agent/8e916ce55425de21`

### More than one dct:description. In the harvested packages these are different MD.cff fields (purpose, quality, resolution) that ran into the description; which one is the description cannot be decided here.

5 node(s):

- `https://doi.org/10.5281/zenodo.18369720`
- `https://doi.org/10.5281/zenodo.18369865`
- `https://doi.org/10.5281/zenodo.18724635`
- `https://doi.org/10.5281/zenodo.18732892`
- `https://doi.org/10.5281/zenodo.18742693`

### More than one dct:license. The catalogue page and the SPARQL facets both key on the SPDX-form IRI (S6, derived_label); an additional non-SPDX IRI for the same licence is carried in the bundle but excluded from the facet and the overview query, so it does not appear twice there.

1 node(s):

- `https://doi.org/10.5281/zenodo.22676379`

### The same name is carried by more than one person node. The registry never merges on a matching name - that would invent identity - so the decision is left to a human.

2 node(s):

- `https://orcid.org/0000-0002-3246-3531`
- `https://w3id.org/fdo-squirrel/registry/agent/8e916ce55425de21`

### dcat:bbox is a DCAT string. The profile prefers geosparql:hasBoundingBox; the registry reports this rather than rewriting it, because converting the value would be a content change.

2 node(s):

- `https://doi.org/10.5281/zenodo.18369125`
- `https://doi.org/10.5281/zenodo.18369156`

### dcat:endDate is written as xsd:integer, as dcat:startDate.

6 node(s):

- `https://doi.org/10.5281/zenodo.18369125_temporal`
- `https://doi.org/10.5281/zenodo.18369156_temporal`
- `https://doi.org/10.5281/zenodo.18369720_temporal`
- `https://doi.org/10.5281/zenodo.18369865_temporal`
- `https://doi.org/10.5281/zenodo.18732892_temporal`
- `https://doi.org/10.5281/zenodo.18742693_temporal`

### dcat:keyword carries a bare string. Only IRI-valued keywords can be anchored as a type; a string cannot become a concept and must not become an E55 Type.

8 node(s):

- `https://doi.org/10.5281/zenodo.18369125`
- `https://doi.org/10.5281/zenodo.18369156`
- `https://doi.org/10.5281/zenodo.18369720`
- `https://doi.org/10.5281/zenodo.18369865`
- `https://doi.org/10.5281/zenodo.18724635`
- `https://doi.org/10.5281/zenodo.18732892`
- `https://doi.org/10.5281/zenodo.18742693`
- `https://doi.org/10.5281/zenodo.22676379`

### dcat:startDate is written as xsd:integer. The profile lists only XSD date types and EDTF for temporal values; the registry adds the typed literal beside it but does not touch the original.

6 node(s):

- `https://doi.org/10.5281/zenodo.18369125_temporal`
- `https://doi.org/10.5281/zenodo.18369156_temporal`
- `https://doi.org/10.5281/zenodo.18369720_temporal`
- `https://doi.org/10.5281/zenodo.18369865_temporal`
- `https://doi.org/10.5281/zenodo.18732892_temporal`
- `https://doi.org/10.5281/zenodo.18742693_temporal`

### geosparql:hasGeometry hangs on the FDO itself. The geometry belongs on the crm:E53_Place the FDO refers to; an information object has no coordinates.

7 node(s):

- `https://doi.org/10.5281/zenodo.18369125`
- `https://doi.org/10.5281/zenodo.18369156`
- `https://doi.org/10.5281/zenodo.18369720`
- `https://doi.org/10.5281/zenodo.18369865`
- `https://doi.org/10.5281/zenodo.18724635`
- `https://doi.org/10.5281/zenodo.18732892`
- `https://doi.org/10.5281/zenodo.18742693`

### schema:funding carries a bare string with no funder IRI. There is nothing to anchor and nothing to aggregate.

7 node(s):

- `https://doi.org/10.5281/zenodo.18369125`
- `https://doi.org/10.5281/zenodo.18369156`
- `https://doi.org/10.5281/zenodo.18369720`
- `https://doi.org/10.5281/zenodo.18369865`
- `https://doi.org/10.5281/zenodo.18724635`
- `https://doi.org/10.5281/zenodo.18732892`
- `https://doi.org/10.5281/zenodo.18742693`

## Findings per package

| Record | Findings |
|---|---|
| `18369126` | 6 |
| `18369157` | 6 |
| `18369866` | 6 |
| `18732893` | 6 |
| `18742694` | 6 |
| `18744583` | 6 |
| `22675886` | 4 |
| `22676380` | 2 |
| `across packages` | 5 |

