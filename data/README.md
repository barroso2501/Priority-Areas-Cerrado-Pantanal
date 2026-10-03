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
| `biomas_2004/` | `Biomas5000.shp`: IBGE biome limits, 2004 (1:5,000,000) | IBGE (copy provided by project lead) | CRS ships as `Biomas5000.prj.txt` (unread by GDAL); content is SIRGAS 2000, assigned explicitly. Includes inland-water and marine classes. |
| `biomas_2019/` | `lm_bioma_250.shp`: IBGE biome limits, 2019 (1:250,000) | IBGE (copy provided by project lead) | same limit used by MapBiomas |
| `uf/` | `BR_UF_2025.shp`: IBGE state limits, 2025 | IBGE (copy provided by project lead) | assumed stable over the assessment period (project lead) |

Also required, outside `data/raw/`:

| Path | Content | Source |
|---|---|---|
| `data/grids/br_ibge_SAD69_003.tif` | Official IBGE SAD69 → SIRGAS 2000 transformation grid (D10) | [PROJ-data](https://github.com/OSGeo/PROJ-data/tree/master/br_ibge) |

KML versions of the 2nd-update layers are also on the MMA page and are not used.

## `data/reference/`
| File | Description |
|---|---|
| `mapbiomas_col11_legend_groups.csv` | Collection 11 legend with the 4 MapBiomas hierarchical levels and project groupings (`nature`, `fire_domain`). Pixel values need verification (P8). Hierarchy and names from the official Collection 11 legend PDF. |

## `data/derived/`
Small tables derived from the public sources above, committed for convenience and fully reproducible with `scripts/`:

| File | Rows | Produced by | Description |
|---|---|---|---|
| `fichas_areas.csv` | 278 | `parse_fichas.py` | code, name, biological importance, action priority, area (ha), main and 3 secondary actions |
| `fichas_targets.csv` | 33,016 | `parse_fichas.py` | code, target group, target name |
| `reconciliation_2nd_update.csv` | 300 | `reconcile_2nd_update.py` | all codes of the 2nd update: MMA attributes, `has_ficha`, hybrids within 2 km, 6 Annex-I-only areas |
| `zones_attributes.csv` | 3,387 | `build_zones.py` | extraction zones (D7): `zone_id`, the 7 markers, `area_ha` |
| `zones_qc.txt` | — | `build_zones.py` | QC report of the partition |

## `data/interim/` (not versioned)
| File | Produced by | Description |
|---|---|---|
| `zones.gpkg` | `build_zones.py` (~20 min) | zone polygons, layers `zones_sirgas` (EPSG:4674, for GEE upload) and `zones_albers` (~190 MB) |
