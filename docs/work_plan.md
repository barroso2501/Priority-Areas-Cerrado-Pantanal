# Work plan v1 — State assessment of priority areas with MapBiomas

*Status: v1, approved by the project lead as the planning baseline (2026-10-02). Open decisions are in [`decisions/`](decisions/).*
Tags: **[E]** evidence · **[H]** hypothesis · **[L]** gap · **[D]** decision pending.

## 0. Original proposal
Use MapBiomas products (land use/cover, fire, water, pasture, agriculture, degradation, etc.) to assess the priority areas at three moments: before the 1st assessment, before the 2nd assessment, and after the 2nd assessment. Assessment parameters cover state, degradation and, if possible, cost variation.

## 1. Critical review (what a skeptical reviewer would attack)
1. **Ambiguous milestones.** Each cycle has three distinct dates:
   - the **data year** that fed the selection (~2002 for 2006; 2009 remnants and 2002–2008 deforestation for 2012);
   - the **workshop year** (2006, 2012);
   - the **legal-act year** (Ordinance 9/2007; Ordinances 223/2016 and 463/2018).

   Choosing the wrong one shifts "before/after" by 4–6 years.
2. **Before/after is not an effect.** Areas were selected because they had remnants and, in 2012, lower cost; the Marxan cost surface included deforestation probability. They would lose less vegetation even without designation. Tracking only the inside describes state, not effect. Effectiveness requires a counterfactual.
3. **Units change between cycles.** 2006 and 2012 geometries differ (55.8% overlap). Treating "the priority area" as a continuous entity is an identity error.
4. **Three snapshots waste the series.** MapBiomas is annual since 1985. Snapshots hide pre-trends, trend breaks and extreme years (e.g. Pantanal fire and drought in 2020). Unequal periods require annualized rates.
5. **Fire is not degradation by definition in the Cerrado.** Fire is part of the savanna and grassland regime. Degradation is a departure from that regime: excess frequency, late-dry-season burning, fire in forest formations, veredas and gallery forests.
6. **Surface water responds to climate before management.** In the Pantanal, the flood-pulse variability dominates. Indicators must be normalized by climate or regional hydrology.
7. **Cost must be anchored in the SCP cost surface** (see §2.6). The 2012 surface included land price as one of its three components; this needs explicit handling.
8. **Classification error vs. real change.**
   - Native grassland × pasture and savanna × dirty pasture are confused in the Cerrado.
   - Collections reprocess the whole series, so collections must never be mixed.
   - Small changes in small areas may be below map error.
9. **Biome boundary.** The 2006 areas were drawn on the 2004 IBGE limit; MapBiomas uses the 2019 limit.
10. **Assessing polygons is not assessing function.** The areas exist to meet target goals. An area can keep 70% native vegetation and still have lost the rare target ecosystem.

## 2. Improved design

### 2.1 Questions
| # | Question | Type | Counterfactual? |
|---|---|---|---|
| Q1 | State and trajectory of priority areas at each milestone | descriptive | no |
| Q2 | Did they change differently from comparable non-priority areas? | effect (association) | **yes** |
| Q3 | Does the network still meet the target goals that justified it? | function | no (uses target GDB) |
| Q4 | Did the recommended actions happen? | implementation | partial |
| Q5 | How did the SCP cost surface vary inside/outside the areas, and would the areas still be selected? | cost / solution stability | no |
| Q6 | Did the 2012 revision respond to the state of the 2006 areas? | meta-assessment | no |

Q6 is cheap and informative: compare 2002–2011 trajectories of 2006 areas that **left** vs. **stayed** in 2012.

### 2.2 Milestones — [D1](decisions/D1_milestones.md)
Process the **full annual series** (1985 to the last year of the collection) and summarize by periods with breaks at:

| Milestone | Suggested year | Rationale |
|---|---|---|
| T0: baseline of 1st update | 2002 | data year used in 2006 (PROBIO) |
| T1: designation of 1st update | 2007 | Ordinance 9/2007 |
| T2: baseline of 2nd update | 2009 (and 2011) | MMA 2009 remnants; 2011 workshops |
| T3: designation of 2nd update | 2016 (and 2018) | Ordinances 223/2016 and 463/2018 |
| T4: current | last MapBiomas year | — |

State is measured at data years (T0, T2, T4). Attributable change is measured from act years (T1, T3), with 2012–2016 treated as "announced, not enacted".

### 2.3 Units of analysis — [D2](decisions/D2_universe.md)
- **AP2006.** 479 codes. Type "Protegida" is a separate stratum, since those areas were already protected areas or indigenous lands.
- **AP2012.** 294 areas + 54 `*CerraPa*` hybrids, with a hybrid flag and the post-harmonization class.
- **Transition strata** (overlay of both layers): *both*, *2006 only (left)*, *2012 only (entered)*, *neither*. These are the basis of Q2 and Q6.
- **Controls.** Grid cells (1 km² or H3) outside priority areas, protected areas and indigenous lands, matched on baseline covariates: % native vegetation, physiognomy, slope, agricultural suitability, distance to roads and towns, state, ecoregion, and neighbourhood conversion rate in the prior period. See [D5](decisions/D5_controls.md).
- Clip to the IBGE 2019 biome limit, and report the area of each priority area falling outside it.

### 2.4 Indicators
| Dimension | Indicator | Product / source | Caveat |
|---|---|---|---|
| State | % native by formation (forest, savanna, grassland, wetland) | MapBiomas LULC, Collection 11 | aggregate to classes with acceptable accuracy |
| State | native never converted since 1985 × secondary (age) | LULC trajectories; Secondary Vegetation | young secondary ≠ functional recovery |
| State | fragmentation: number of patches, core area, edge | Degradation module (edge, size, isolation) or own computation | check module coverage/period for the Cerrado [L] |
| State (Pantanal) | surface-water anomaly | MapBiomas Water | normalize by climatology/regional hydrology |
| Pressure | annual native-vegetation loss rate and destination (pasture, soy, sugarcane, silviculture) | LULC transitions; Alerta (2019+) | annualize; separate pressure types |
| Degradation | fire-regime departure: frequency above physiognomy threshold, late-dry-season fire, fire in forest/vereda | MapBiomas Fire (monthly scars) | thresholds per physiognomy, see [D3](decisions/D3_fire_rule.md) |
| Degradation | degradation vectors | Degradation module | new module; record version |
| Opportunity | low-vigour pasture in and around the area | MapBiomas Pasture (vigour/quality) | restoration-opportunity indicator, not native-vegetation state |
| Water/other pressure | irrigation (centre pivots), mining | Irrigation and Mining modules | — |
| Implementation | % area turned into protected area or indigenous land after the act, by recommended type | CNUC history, FUNAI | creation dates |
| Implementation | persistent secondary-vegetation gain (≥ X years) where the action was Restoration | Secondary Vegetation | [D] X |
| Implementation | reduction of degraded pasture where the action was CAR/good practices | Pasture + SICAR | weak attribution |
| Function (Q3) | % of each target's goal still achievable with current native vegetation, within network + protected areas | target GDB × LULC at T2/T4 | `SUM_NAT_2` meaning [H], see P3 |
| Cost (Q5) | SCP cost surface rebuilt per milestone (§2.6) | MapBiomas + road networks | same 0–10 rescaling and sum as 2012, see [D4](decisions/D4_cost.md) |

### 2.5 Analytical design
- **Q1.** Annual series by area, importance and priority class, recommended action, state and biome. Annualized rates per period, with map-error intervals.
- **Q2.** Matched difference-in-differences (or synthetic control by stratum), with the event at the act year. Test parallel pre-trends.
  - Honest expectation: effects are small, because priority-area designation is an indicative instrument.
  - A null result does not mean the designation is useless. Discuss anticipation and leakage.
- **Q3.** Recompute goal attainment per target at T2 and T4, and count the targets that became gaps again. This is the closest indicator to biodiversity outcomes available.
  - Caveat: the target set is **historical** (2011–2012 threat and endemism lists, revised several times since). Q3 therefore measures whether the network still serves *the targets it was designed for*, not current conservation needs. A cross-check against the current national threatened-species list is an optional extension.
- **Q4.** Only for actions with an observable proxy (protected-area creation, restoration, pasture); all other actions are explicitly left unassessed.
- **Q6.** Compare trajectories of the *left*, *stayed* and *entered* strata.

### 2.6 Cost as the SCP cost surface
**Adopted definition:** cost = the spatial characteristics that entered the systematic-conservation-planning cost surface (constraints and opportunities for conservation), not land price.

The 2012 surface [E, report pp. 21–22, 36] summed three themes, each rescaled 0–10, per planning unit (HydroSHEDS micro-basins of ~40,000 ha):
1. **Deforestation probability.** Land Change Modeler, 2002→2008 transition, regionalized by basin. Drivers: elevation, slope, roads, urban centres, mining, protected areas, indigenous lands.
2. **Infrastructure density.** Roads and railways; urban, agricultural and mining areas.
3. **Land price.** Mean value per planning unit.

Rebuild per milestone (T0, T2, T4):

| Component | How | Source | Fidelity |
|---|---|---|---|
| Deforestation pressure | **Observed** native-loss rate around each unit in the window preceding the milestone. Alternative: retrain an LCM-like transition model. | MapBiomas transitions | high; observed beats modelled |
| Infrastructure | Density of urban, agriculture and mining | MapBiomas | high for land uses; **historical road/railway series is a gap [L]** (OSM current only; DNIT/IBGE sparse versions) |
| Land price | (a) freeze at 2012; (b) omit, 2-component surface; (c) spatial proxy (suitability/agricultural rent) | — | see D4b; recommended (b) main + (a) sensitivity |

Caveats:
- The 2012 surface belongs to the 2nd update. Nothing in the available documents shows a formal cost surface in 2006 [L, P6]. Cost at T0 would therefore be retrospective: the 2012 yardstick applied to 2002.
- The 0–10 rescaling is relative to each year's distribution. **Fix the scale bounds at the reference year** (2009/2012); otherwise cost is always re-centred and the variation disappears (D4c).
- The 2012 planning-unit grid is unavailable [L]. Rebuild it from HydroSHEDS (same basin level, plus strict protected areas above 25–35 kha), or summarize directly per priority area and control cell.

Uses:
- Cost change inside vs. outside the areas, and by transition stratum.
- **Solution stability** (Phase 3, optional): re-run Marxan with the Annex V parameters, Annex II goals, current native vegetation and the updated cost, and measure how much of the 2012 network would be re-selected (selection frequency).

### 2.7 Quality control
- Fix **one** MapBiomas collection (Collection 11; confirm last year) and record every module version.
- Compute areas in an equal-area CRS (Albers). Transform the 2006 SAD69 layer with the official grid. Repair invalid geometries (2 + 12 + those of 2006).
- Report MapBiomas accuracy per class and biome; flag changes smaller than map error.
- Pantanal: treat flooded-grassland ↔ water swaps as natural dynamics.

### 2.8 Phases
1. **Phase 1 (Q1, Q6).** Annual zonal statistics in GEE, producing a long table `unit × year × class × area` (plus fire and water). Low risk, fast delivery.
2. **Phase 2 (Q3, Q4).** Cross with the target GDB, CNUC and SICAR.
3. **Phase 3 (Q2, Q5).** Counterfactual design and cost surface. Highest methodological risk; design after Phase 1.

### 2.9 Platform
- **GEE** (Python API) for every operation reading MapBiomas rasters. Rasterize unit IDs and use grouped reducers per year, rather than `reduceRegions` over complex polygons.
- **Python (Colab/Jupyter)** for tabular analysis, statistics, external joins (fact sheets, CNUC, SICAR, Annex II) and Marxan/prioritizr runs.
- Code lives in versioned `scripts/`; notebooks only orchestrate; the MapBiomas collection is a parameter.

## References
- [MapBiomas Collection 11 ATBD](https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/08/ATBD-General-Collection-11-versao-1.pdf)
- [Collection 11 legend codes](https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/08/CodigosDeLegenda_LegendCodes_MapBiomas_Brazil_Collection11_PDF.pdf)
- [MapBiomas Degradation factsheet (May 2026)](https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/08/Factsheet-Degradacao-13052026.pdf)
- WWF-Brasil/MMA (2015), cost surface pp. 21–22, 36
