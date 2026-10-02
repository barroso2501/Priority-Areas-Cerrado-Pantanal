# Data

Raw data is **not versioned**. Download each item below and place it under `data/raw/` with the folder name shown. The scripts expect exactly these paths.

Official page for the 2nd update (MMA): <https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/biomas-e-ecossistemas/conservacao-1/areas-prioritarias/2a-atualizacao-das-areas-prioritarias-para-conservacao-da-biodiversidade-2018>

| Folder / file in `data/raw/` | Content | Source | Notes |
|---|---|---|---|
| `cerrado_pantanal/` | `Cerrado_Pantanal_2a_atualizacao.shp`: 294 priority areas, 2nd update | [MMA zip](https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/biomas-e-ecossistemas/conservacao-1/areas-prioritarias/arquivos/cerrado_pantanal.zip) | SIRGAS 2000 (EPSG:4674); edited until Mar/2022 |
| `areas_hibridas/` | `Areas_hibridas_2a_atualizacao.shp`: 163 inter-biome hybrid areas (national) | [MMA zip](https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/biomas-e-ecossistemas/conservacao-1/areas-prioritarias/arquivos/areas_hibridas.zip) | Use only `COD_area` containing `CerraPa` |
| `alvos/` | `Alvos_CERRADO_PANTANAL.gdb`: distribution of conservation targets | [MMA zip](https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/biomas-e-ecossistemas/conservacao-1/areas-prioritarias/arquivos/alvos_cerrado_pantanal.zip) | ~340 MB unzipped; 532k land-system polygons |
| `fichas_cerrado_pantanal_2a_atualizacao_2018-2.pdf` | Fact sheets per area (1,031 pp.) | [MMA PDF](https://www.gov.br/mma/pt-br/assuntos/biodiversidade-e-biomas/biomas-e-ecossistemas/conservacao-1/areas-prioritarias/fichas_cerrado_pantanal_2a_atualizacao_2018-2.pdf) | input of `parse_fichas.py` |
| `publicacao_areasprioritarias_cerrado_pantanal_1.pdf` | WWF-Brasil/MMA (2015) methodological report of the 2nd update | WWF-Brasil | Annex I (area list) only as images; Annex II (targets) text-extractable |
| `ap2006/` | `Areas_prioritarias_2006_{codigos,importancia,prioridade}.shp`: 1st update | MMA (copy provided by project lead; WWF-Brasil processing, Jun/2012) | SAD69 / Polyconic, CM −54°; contains invalid geometries |

KML versions of the 2nd-update layers are also on the MMA page and are not used.

## `data/derived/`
Small tables derived from the public sources above, committed for convenience and fully reproducible with `scripts/`:

| File | Rows | Produced by | Description |
|---|---|---|---|
| `fichas_areas.csv` | 278 | `parse_fichas.py` | code, name, biological importance, action priority, area (ha), main and 3 secondary actions |
| `fichas_targets.csv` | 33,016 | `parse_fichas.py` | code, target group, target name |
| `reconciliation_2nd_update.csv` | 300 | `reconcile_2nd_update.py` | all codes of the 2nd update: MMA attributes, `has_ficha`, hybrids within 2 km, 6 Annex-I-only areas |
