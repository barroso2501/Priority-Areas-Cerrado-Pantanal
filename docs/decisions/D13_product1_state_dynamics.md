# D13 — Product 1: state and dynamics of natural vegetation in the 2012 priority areas

**Status:** Accepted (2026-10-04, project lead), including the §5 amendment and the calibrated thresholds of §4/§6.
**Raised:** 2026-10-04

## 1. Context
The first product goes to the **MMA Biodiversity Directorate**, which prepares and revises the priority areas. It supports planning of the next revision cycle.

It describes the **state and dynamics of natural vegetation** in the 2nd-update areas from 2012 to 2025.

It does **not** assess the efficiency or effectiveness of the areas as public policy. That is Q2/Q4, and needs counterfactual controls (D5).

**No fire metrics** are included.

## 2. Components
1. **Executive summary.** Simplified method; results consolidated by biological importance, action priority, main action type and state (UF); a map of categories; the matrix outside the priority areas as context.
2. **One fact sheet per area.** Tables and charts comparing the state and dynamics of natural vegetation and land use between 2012 and 2025. Format approved 2026-10-04 (prototype: areas 29, 252, 244). Includes a change map 2012 → 2025 with six classes: natural stable, natural lost, natural gained, anthropic stable, water/sand stable, exchange with water/sand (the project lead proposed the first, second, fourth and fifth; the other two are needed so that every pixel has a class). A simplified mobile view is planned for a later stage. Map rules accepted 2026-10-04 by the project lead: stability compares only 2012 and 2025 (endpoint comparison of level-1 groups; turnover between those years is measured by persistence and the category, not by the map); colour palette as validated in `scripts/gee/31_export_maps.py`.
3. **Categorical assessment** of each area, on two axes plus flags (§4).
4. **Queryable data package.** Fact sheets are generated from tables, so the tables are the primary product (see `findings.md` §1 for the 2012 precedent): one row per area with attributes, categories and flags; long tables of area × year × class and area × transition; a GeoPackage; a data dictionary with version. An online query tool can be built on these tables.

## 3. Accepted choices
| Item | Decision |
|---|---|
| Period | 2012–2025, with two sub-periods **2012–2018** and **2018–2025** used to detect acceleration. The split is not a before/after designation contrast (designation 2016/2018). |
| Natural vegetation | MapBiomas **level 1** classes *Forest* (1) and *Herbaceous/Shrubby Vegetation* (2): pixel values 3, 4, 5, 6, 7, 49, 11, 12, 29, 32, 50, 77, 84. This equals the `native` set of D8, so Phase 1 numbers stay comparable. |
| Thresholds | **Fixed** and interpretable; the same across biomes. Quantile thresholds are rejected because they change with each cycle and each biome. |
| Regional reference | The rate in the matrix outside the 2012 areas is reported **as context only**, labelled as such. It is not an effect comparison. |
| Hybrids | Included in the same product (D2 option a), with a `hybrid` flag in every table, fact sheet and filter. |
| Matrix outside the priority areas | Included in the executive summary as context, by biome (2019 limit) and UF. |

## 4. Categories (thresholds calibrated in §6, accepted 2026-10-04)
**Rate metric.** Robust trend (Theil–Sen slope) of the annual **non-anthropic area** (§5), expressed as % per year of the natural vegetation area in 2012. Negative = loss. The same metric is computed for each sub-period. Endpoint differences are reported but not used for classification, because the last year of a collection is the least stable [H]. Each trend carries a standard error from the residuals around the line, inflated for lag-1 autocorrelation.

**Axis A — state in 2025:** natural vegetation share of land area: ≥80%, 50–80%, 20–50%, <20%. The fact sheet also gives the remaining hectares.

**Axis B — dynamics 2012–2025:**

| Category | Rule |
|---|---|
| Net gain | trend > +0.2%/yr **and** net gain ≥ 0.5 percentage points of land area **and** ≥ 100 ha |
| Stable | \|trend\| ≤ 0.2%/yr (or positive below the gain minima) **and** gross conversion ≤ 0.5%/yr |
| Turnover | \|trend\| ≤ 0.2%/yr **and** gross conversion > 0.5%/yr |
| Moderate loss | −1 ≤ trend < −0.2%/yr |
| Intense loss | −2 ≤ trend < −1%/yr |
| Very intense loss | trend < −2%/yr |

At −0.2%/yr, half of the 2012 natural vegetation would be gone in about 350 years (stable at the planning horizon); at −1%/yr, in about 70; at −2%/yr, in about 35. Gross conversion = sum of annual natural → anthropic transitions, % of the 2012 natural vegetation per year.

**Flags,** independent of the category:
- acceleration: the 2018–2025 trend is lower than the 2012–2018 trend by more than 0.5 percentage points per year **and** by more than 2 standard errors of the difference;
- low confidence: the trend lies within one standard error of a category boundary;
- dominant conversion driver: anthropic class in 2025 that received most of the converted 2012 natural vegetation (direct transition 2012 → 2025);
- small area (< 5 kha; unstable rates);
- coverage gap (`findings.md` §9);
- hybrid;
- hydrological dynamics (§5): exchanges with water or sand > 20% of all gross exchanges of natural vegetation;
- possible reservoir (§5): persistent water ≥ 100 ha **and** ≥ 0.5% of the 2012 natural vegetation.

The fact sheet and the executive summary show the continuous rate next to the category, because the moderate/intense boundary is the most influential choice (§6).

**Minimum absolute change.** The relative rate inflates small changes in areas with little natural vegetation left. Exploratory 2012–2025 run [E]: 6 of the 9 areas with net gain had less than 30% natural vegetation in 2012. Gain therefore also requires a minimum change in percentage points of area and in hectares (0.5 pp and 100 ha, §6).

## 5. Amendment (accepted 2026-10-04): conversion is natural → anthropic only
**Evidence** [E] (annual transitions 2012–2025, `lulc_transitions`): in the Pantanal (2019 limit), **88%** of the gross transitions out of natural vegetation go to water or sand (classes 33, 23), and almost the same amount comes back (5.38 vs. 5.31 Mha summed over the years). In the Cerrado this share is 2%. In 36 of the 348 units, more than 20% of the gross "loss" is this kind of exchange, mostly Pantanal areas (e.g. 182, 224, 243, 252: 94–99%).

**Problem.** If loss means "natural vegetation → anything else", the Pantanal areas would be classified as "turnover" or loss because of flooding cycles, not conversion.

**Rule.**
- Loss = natural vegetation → **anthropic** classes (`nature` = anthropic or ambiguous).
- Gain = anthropic → natural vegetation.
- Exchanges between natural vegetation and natural non-vegetated classes (water 33, beach/dune/sand 23) are **hydrological or natural dynamics**. They are reported separately in the fact sheet, are neutral for the category and raise the `hydrological dynamics` flag.
- The trend is computed on the anthropic area (or, equivalently, on the non-anthropic area). The flood-driven annual fluctuation of the vegetation stock therefore does not enter the category.
- Axis A (state) stays on natural vegetation as defined in §3.

**Reservoirs (decision of the project lead).** MapBiomas class 33 does not separate reservoirs from rivers and lakes. Natural vegetation flooded by a reservoir is therefore treated as **hydrological dynamics**: it stays out of the natural-vegetation accounting and out of the category.

*Point raised before recording (critical test).* A reservoir is an anthropic conversion with permanent loss of habitat. Under this rule, an area partly flooded by a dam between 2012 and 2025 can be classified as "stable". Mitigation adopted so that the loss is reported, not hidden:
- flag `possible reservoir` when natural vegetation of 2012 became water and **stayed water in every year of the final stretch** of the series (persistence, extraction item 4 in §7). Seasonal and interannual flooding returns; a reservoir does not;
- the fact sheet shows the hectares under this flag next to the category;
- [L] confirmation against an external list of dams built in 2012–2025 (ANA/ANEEL) is not yet done. Without it the flag stays "possible": long Pantanal flood pulses or river migration can also look persistent.

[E] Order of magnitude: net natural → water over 2012–2025 exceeds 1% of the 2012 natural vegetation in 12 units, almost all in the Pantanal (largest: unit 182, 8.7%). Net values at the endpoints depend on the flood state of each year, so they do not identify reservoirs by themselves.

## 6. Calibration (run 2026-10-04, `scripts/analysis/product1_calibration.py`)
Outputs in `data/derived/product1/` (`calibration_report.txt`, `calibration_units.csv`, `calibration_sensitivity.csv`). Tags [E] unless stated.

- **Trend noise.** Median standard error of the 2012–2025 trend: 0.10%/yr (90th percentile 0.27). With the provisional band ±0.1%/yr, 2 × SE exceeded the band in 260 of 348 units. **Band widened to ±0.2%/yr** (169 units still exceed it; they carry the low-confidence flag when near a boundary). A noise-adaptive band per unit was rejected because it breaks the fixed-threshold rule (§3).
- [H] The standard error is partly inflated by real curvature of the series (median lag-1 autocorrelation of residuals 0.64), so it is conservative.
- **Moderate/intense boundary (−1%/yr)** is the most influential: at −0.5 it would move 103 units, at −1.5 it would move 41. Kept at −1 as a value judgement (half-life ≈ 70 years), with the continuous rate always shown.
- **Acceleration.** Magnitude rule alone: 109 units; with the noise test: 103. At 0.25 or 0.75 pp/yr: 141 or 68 units.
- **Gain minima** are robust: halving or doubling them changes 1–2 units.
- **Result with the accepted thresholds** (348 units): moderate loss 201, intense loss 68, stable 38, turnover 22, very intense loss 12, net gain 7; low confidence 115. Very intense loss: six MMA areas (Matopiba and Rio Apa; soybean is the driver in three) and six Amazon–Cerrado hybrids (pasture).
- **Matrix outside the units (context):** Cerrado −0.77%/yr; Pantanal −0.36%/yr.
- **Source labels.** The MMA layers spell classes inconsistently ("Muita Alta" in areas 203 and 30, "Muito alta", "Extremamente alta" in hybrids). They are normalized in the script (see `data_governance.md`).

## 7. New extraction needed
1. Direct transition 2012 → 2025 per zone. The sum of annual transitions is not the same thing.
2. Natural vegetation stable 2012–2025 per zone (the share never converted in the period), to measure turnover properly.
3. Intersection of zones with IBGE municipalities, for the municipality filter.
4. Natural vegetation in 2012 that is water in every year of the final stretch of the series (e.g. 2020–2025), per zone, for the `possible reservoir` flag (§5).

Protected areas and indigenous lands are left out of Product 1, because they pull the reading towards effectiveness. They may enter later as a filter only.

## 8. Evidence from the exploratory run (2012–2025, endpoints; superseded by §4–6 when implemented)
- [E] Median net change −0.66%/yr in the 348 units; −0.79%/yr in the matrix outside them.
- [E] Only 17 units had net gain. With net-rate classes alone, about 65% of the units fall into a single "moderate loss" class. Hence the two axes and the flags.
- [E] Gross loss (median 1.37%/yr) is more than twice the net loss; gross regrowth is 0.56%/yr; the two are correlated (ρ = 0.67).
- [E] 135 units lost faster in 2018–2025 than in 2012–2018 by more than 0.5 percentage points per year.

## 9. Next layer, outside Product 1 v1: land tenure
The project lead will add land tenure later (private land, public land, protected areas, indigenous territories, other). Tenure sets the legal ceiling of conversion, so the same rate means different things: what matters is the rate relative to the **legally convertible remainder**. Candidate metric: legal headroom = natural vegetation − legally required minimum, and years to exhaust it at the current rate. Points to resolve before using it:
- [E] Legal reserve rules differ inside the Cerrado (20% outside the Legal Amazon, 35% for Cerrado inside it) and are set per property, not per priority area; Permanent Preservation Areas add to it.
- [H] Off-site compensation of legal reserve deficits and the consolidated-area rules of the 2012 Forest Code mean the area-level ceiling is not strictly binding.
- Protected-area categories differ: Environmental Protection Areas (APA) allow private use and behave like private land for this purpose.
- Tenure data (CAR/SICAR, SIGEF/SNCI, CNUC, FUNAI, land-tenure meshes) have overlaps and changed over 2012–2025; the reference year must be fixed.
- This layer reads as vulnerability, not effectiveness, and keeps Product 1 within its scope only if framed that way.
