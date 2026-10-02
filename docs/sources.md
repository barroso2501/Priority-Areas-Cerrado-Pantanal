# Sources: inventory, provenance and structure

Evidence tags: **[E]** verified in the files · **[H]** hypothesis · **[L]** gap.

## 1. Timeline of the assessment cycles (Cerrado & Pantanal)

| Cycle | Process year | Legal act | Areas | Source in this repo |
|---|---|---|---|---|
| Original | 1998 | Decree 5,092/2004 → MMA Ordinance 126/2004 | Cerrado 68 · Pantanal 19 | cited only |
| 1st update | 2006 | MMA Ordinance 9/2007 | Cerrado 431 · Pantanal 50 | `ap2006/` shapefiles |
| 2nd update | 2011–2012 (final workshop 23–26 Oct 2012, Brasília) | MMA Ordinance 223/2016; consolidated in MMA Ordinance 463/2018 | 300 codes (Cerrado + Pantanal together) | MMA layers, fact sheets, target GDB, WWF/MMA report |

- [E] The MMA page states that the 2nd update follows the methodology approved by CONABIO (Deliberation 39/2005). It used Marxan plus expert validation.
- [E] The MMA page also states that the current areas match the 2016 version, except that overlaps with other biomes are now delivered separately as "hybrid areas".
- **Comparability caveat.** The 2006 cycle was essentially expert workshops. The 2012 cycle was formal systematic conservation planning (SCP) with Marxan. Differences between 2006 and 2012 polygons are not, by themselves, changes on the ground.

## 2. Sources

### 2.1 WWF-Brasil/MMA (Dec 2015). *Áreas Prioritárias para Conservação da Biodiversidade no Cerrado e Pantanal*. 132 pp.
Methodological report of the **2nd update**.
- **Methods (pp. 13–33).** SCP (Margules & Pressey 2000) in 8 steps: targets → goals → planning units (PUs) → gap analysis → cost → Marxan → C-Plan → expert post-selection.
- **Annex I (pp. 40–55).** Area list: name, states, "Prioridade" (see [findings](findings.md) §2: this column is biological importance), % native vegetation, recommended creation (UCPI/UCUS/UC) and management actions. There is **no code column**. The text layer has a corrupted font, so the table is readable only as images.
- **Protected areas list (p. 56 ff.).** Indigenous lands and protected areas considered in the study.
- **Annex II (pp. 61–122).** Every target with total, protected, excluded and available area, goal (km²) and % of goal met (gap analysis). Groups: amphibians, birds, mammals, fishes, plants, Land Systems (codes such as `AAcDnSa`), aquatic systems (17), karst regions (6), aquifers (4). Text-extractable.
- **Annex V.** Marxan parameters: BLM 0.75; 1,000 runs; 100 M iterations; PROP 0.3.

Key parameters [E]:
- **PUs.** HydroSHEDS micro-basins with a mean of ~40,000 ha. Strict protected areas become their own PU above 25,000 ha (or 35,000 ha; the text gives both).
- **Species distributions.** Species with ≥ 20 records were modelled with Maxent (WorldClim, topography, ESALQ soils) and adjusted by experts. Species with < 20 records were assigned to the PUs holding records.
- **Ecosystem targets.** Land Systems (Silva et al. 2006) were crossed with MMA 2009 native-vegetation remnants. This gives 214 landscape units and 495 savanna, seasonal-forest and chaco ecosystems used as targets.
- **Cost surface.** Three themes, each rescaled 0–10 and summed per PU: (1) deforestation probability (Land Change Modeler, 2002→2008, regionalized by basin); (2) infrastructure density (roads, railways, urban, agricultural and mining areas); (3) land price.
- **Connectivity.** Boundary length between PUs counted only where native vegetation is present.
- **Pre-selection.** PUs intersecting the 2006 priority areas were seeded into Marxan, so continuity with 2006 is partly built in.
- **Gap analysis.** 62% of targets had no representation in strict protected areas; 21% were partially protected; 17% met their goal.
- **Result.** 300 areas. Total area fell 11% relative to 2006, and 55.8% overlaps the 2006 areas.
- **Side products.** Inventory-priority regions (GDM; 529 plant, 95 amphibian, 63 bird and 55 lizard localities) and a biological-importance surface (C-Plan irreplaceability, 0–1 per PU).

### 2.2 MMA fact sheets (*fichas*), 2nd update (1,031 pp.)
One sheet per area with fixed structure:
- `CÓDIGO`, `NOME`, `IMPORTÂNCIA BIOLÓGICA`, `PRIORIDADE DE AÇÃO`, `ÁREA (ha)`, main action plus up to 3 secondary actions.
- `ALVOS`, grouped as ANFIBIO, AVES, MAMIFEROS, PEIXES, PLANTAS, REPTEIS, SISTEMAS_DE_TERRAS, ECOSSISTEMA_AQUATICO.

What the extraction shows:
- [E] 278 sheets, codes between 1 and 300 (22 codes missing; explained in [findings](findings.md) §3). They hold 33,016 area–target pairs, a median of 100 targets per area (range 27–511).
- [E] Land-system targets appear at level 5 (e.g. `3BC1N`), without the vegetation group.
- [E] Importance and priority are distinct axes; their cross-tabulation is not diagonal.

### 2.3 `Alvos_CERRADO_PANTANAL.gdb`: target distributions
FileGDB, SIRGAS 2000 (EPSG:4674), packaged Mar 2022.

| Layer | Features | Attributes |
|---|---|---|
| alvo_anfibio | 82 | ESPECIE1, SUM_NAT_2 |
| alvo_aves | 46 | same |
| alvo_mamiferos | 59 | same |
| alvo_repteis | 123 | same |
| alvo_peixes | 250 | same (includes per-basin populations, e.g. "… RioNovo") |
| alvo_plantas_1a/1b/1c/1d | 401+400+300+277 = 1,378 | same (alphabetical slices) |
| alvo_plantas_2 | 76 | same; [H] widespread species under a different goal or modelling rule |
| alvo_ecossistemas_aquaticos | 18 | SISTEMA1, SUM_NAT_2 |
| alvo_sistemas_de_terra | 532,301 polygons | GRUPO_VEG (30 classes), LANDSCAPE5 (214), Landscp4, Landscape3 (40), CODN, C |

- [E] **Every** target named in the fact sheets exists in the GDB: all 7 groups and all 123 land-system codes. The GDB is therefore the full target universe of the 2nd update; its 214 LANDSCAPE5 units match the report's 214 landscape units.
- [H] `SUM_NAT_2` is native-vegetation area (ha) within the target's distribution. The order of magnitude matches Annex II total area but the values are not equal (see open issue P3).
- [H] `C` = 1 and `GRUPO_VEG` values such as `CAGR`, `DESM` and `FAGR` flag anthropic or deforested polygons.

### 2.4 MMA layer `Cerrado_Pantanal_2a_atualizacao.shp`: 2nd update, official geometry
- [E] 294 polygons, SIRGAS 2000. Fields:
  - `COD_area`: unique, 1–300; same code as the fact sheets.
  - `NOME`, `Import_bio`, `Prior_acao`, `Area_ha`, `Estados`.
  - `Acao1`: main action; `Acao2`–`Acao4`: secondary actions.
- [E] Total 74.28 Mha; geometry area and `Area_ha` agree.
- [E] Lineage (metadata): post-workshop editing (`CerradoPantanal_pos_v5…v7`, RepairGeometry). Fields of the original process were dropped (`Nativo`, `Desmatado`, `UCPI/UCUS/UC`, `Inventario`, `RESUMO`).
- [E] Codes are ordered north→south (r = −0.97 between code and centroid latitude).
- [E] 2 invalid geometries. Labels need normalization: "Muita Alta" / "Muito alta"; actions in mixed case.

### 2.5 MMA layer `Areas_hibridas_2a_atualizacao.shp`: inter-biome hybrid areas (national)
- [E] Where priority areas of two biomes overlapped, the overlap was erased from each biome layer and re-issued as a hybrid area. Each hybrid has re-assessed classes `IB_pos` / `PA_pos` / `AçãoP_p`. Protected areas, indigenous lands and quilombola territories (`UC_TI_TQ`) were then erased.
- [E] Prefixes relevant here: `AMZ_CerraPant` (41), `CAA_CerraPa` (8) and `CerraPa_MA` (5), i.e. 54 polygons and 1.91 Mha. Other prefixes (`MAZC`, `AMZ_ZCM`, `PAZC`, `CA_MA`…) belong to other biome pairs.
- [E] Hybrids and the Cerrado/Pantanal layer are complementary: their intersection is ~4 km² of edge slivers.
- [E] No name field. 12 of 163 geometries are invalid.

### 2.6 1st update shapefiles `Areas_prioritarias_2006_*` (SAD69 / Polyconic, CM −54°; WWF processing, Jun 2012)

| Layer | Features | Content |
|---|---|---|
| `_codigos` | 554 (479 unique codes: Ce001–Ce429, Pa001–Pa050) | COD_ID, biome, type (Nova/Protegida), importance, priority |
| `_importancia` | 344 | dissolved by importance class (includes "Insuficientemente Conhecida") |
| `_prioridade` | 386 | dissolved by priority class |

- [E] After dissolving by code: Cerrado 429 areas / 934,561 km²; Pantanal 50 areas / 83,440 km². The report gives 431 / 939,753 and 50 / 83,562, a difference under 1%.
- [E] Type "Protegida" = existing protected areas and indigenous lands included as priority areas (179 in the Cerrado).
- [E] Invalid geometries are present.
- [E] The importance class "Insuficientemente Conhecida" exists only in 2006.

## 3. Implicit data model

```
2nd-update area (code 1–300)
 ├─ attributes  : MMA layer (= fichas, 100% match)  ←→ Annex I by NAME (no code)
 ├─ geometry    : Cerrado_Pantanal_2a_atualizacao.shp (COD_area); 6 areas absorbed into hybrids
 ├─ hybrid parts: Areas_hibridas (*CerraPa*), linked only by geometry
 └─ N targets   : fichas → target GDB (distribution geometry)
                    └─ goal, protected area, % met: Annex II (by name)
1st-update area (Ce###/Pa###): geometry + classes only; no targets, no actions
```

Join keys:
- `COD_area` = fact-sheet code.
- Normalized names (upper-case, no accents) link fact sheets ↔ Annex I ↔ GDB ↔ Annex II.
- Land-system codes in Annex II (`AAcDnSa`) differ from GDB/fact-sheet codes (`1Ba1n` + `GRUPO_VEG`) and need a crosswalk (open issue P4).
