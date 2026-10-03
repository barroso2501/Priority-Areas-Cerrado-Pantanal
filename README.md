# Priority Areas for Biodiversity Conservation — Cerrado & Pantanal

State assessment of Brazil's **Priority Areas for Conservation, Sustainable Use and Benefit-Sharing of Biodiversity** (*Áreas Prioritárias para Conservação*, MMA) in the Cerrado and Pantanal biomes. We assess the areas across the two official revision cycles (1st update, 2006; 2nd update, 2012, legally recognized in 2016/2018) using MapBiomas time series of land use/cover, fire, surface water, pasture, agriculture and degradation.

## Purpose and audience
- **Primary product:** a diagnostic for the **Ministry of Environment (MMA)** at the start of a new revision cycle of the priority areas. The revision will cover all biomes and the coastal-marine system.
- **Secondary product:** a scientific publication.
- **Scope:** the **Cerrado (with the Pantanal) is the pilot**. The pipeline is parameterized by biome so it can be extended; known limits of that extension are recorded in [D12](docs/decisions/D12_scope_generalization.md).

> **Status (2026-10-02): planning.** Sources are inventoried and reconciled. The work plan is v1. Some methodological decisions are still open (see [`docs/decisions/`](docs/decisions/)). The extraction-zone partition is built and the Earth Engine extraction scripts are written and tested offline; they have not been run against Earth Engine yet.

## Questions
| # | Question | Type |
|---|---|---|
| Q1 | What are the state and trajectory of the priority areas at each milestone? | descriptive |
| Q2 | Did they change differently from comparable non-priority areas? | effect (needs counterfactual) |
| Q3 | Does the network still meet the conservation targets that justified it? | function |
| Q4 | Did the recommended actions happen? | implementation |
| Q5 | How did the conservation-planning cost surface change, and would the areas still be selected? | cost / solution stability |
| Q6 | Did the 2012 revision respond to the state of the 2006 areas? | meta-assessment |

Details are in [`docs/work_plan.md`](docs/work_plan.md).

## Repository layout
```
README.md
docs/
  sources.md          inventory, provenance and structure of every source
  findings.md         verified findings from source reconciliation
  work_plan.md        assessment plan (v1)
  open_issues.md      unresolved data issues (P1–P9)
  data_governance.md  lessons on data governance for the next revision cycle
  decisions/          one record per methodological decision (D1–D12)
scripts/
  parse_fichas.py           MMA fact sheets (PDF) -> tables
  reconcile_2nd_update.py   300-code reconciliation of the 2nd update
  build_zones.py            flat partition of extraction zones (D7)
  gee/                      Earth Engine extraction (Phase 1); see scripts/gee/README.md
notebooks/
  colab_phase1_extraction.ipynb   Colab runbook for the Earth Engine steps
tests/
  test_gee_logic.py         offline tests: key encodings and fire-interval algorithm
data/
  README.md           where to download each raw dataset (raw data is not versioned)
  derived/            small tables derived from public data
```

## Platform
Raster processing (MapBiomas zonal statistics per unit and year) runs in **Google Earth Engine** through its Python API. Tabular analysis, statistics and Marxan re-runs run in **Python (Colab/Jupyter)**. Code lives in versioned scripts; notebooks only orchestrate.

## Quick start
```bash
pip install -r requirements.txt          # plus poppler-utils for pdftotext
# download raw data as described in data/README.md, then:
python scripts/parse_fichas.py
python scripts/reconcile_2nd_update.py
python scripts/build_zones.py            # ~20 min; needs data/grids/br_ibge_SAD69_003.tif
```

## Conventions
- **Evidence tags** used throughout the docs: **[E]** evidence directly verified in the files · **[H]** plausible hypothesis, not verified · **[L]** known gap.
- CRS for area computations: South America Albers Equal Area (SIRGAS 2000-based layers reprojected; the 2006 SAD69 layer is transformed with the official grid).
- MapBiomas: Collection 11, 1985–2025, integrated national asset; no mixing of collections ([D6](docs/decisions/D6_mapbiomas_collection.md)).

## Data statement
The repository is public by decision of the project lead (2026-10-02). All source data are already published by MMA. The species targets are **historical**: they reflect the threat and endemism lists used in 2011–2012, which have since been revised several times. They do not represent the current list of threatened species and must not be read as such.

## License
Code and documentation: MIT (see `LICENSE`). Source datasets keep their original terms (MMA, WWF-Brasil, MapBiomas) and are not redistributed here.
