# D13 — Product 1: state and dynamics of natural vegetation in the 2012 priority areas

**Status:** Accepted (2026-10-04, project lead), except §5 (proposed amendment, pending) and the threshold values in §4 (provisional until the calibration in §6).
**Raised:** 2026-10-04

## 1. Context
The first product goes to the **MMA Biodiversity Directorate**, which prepares and revises the priority areas. It supports planning of the next revision cycle.

It describes the **state and dynamics of natural vegetation** in the 2nd-update areas from 2012 to 2025.

It does **not** assess the efficiency or effectiveness of the areas as public policy. That is Q2/Q4, and needs counterfactual controls (D5).

**No fire metrics** are included.

## 2. Components
1. **Executive summary.** Simplified method; results consolidated by biological importance, action priority, main action type and state (UF); a map of categories; the matrix outside the priority areas as context.
2. **One fact sheet per area.** Tables and charts comparing the state and dynamics of natural vegetation and land use between 2012 and 2025.
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

## 4. Categories (values provisional, see §6)
**Rate metric.** Robust trend (Theil–Sen slope) of the annual series, expressed as % per year of the natural vegetation area in 2012. The same metric is computed for each sub-period. Endpoint differences are reported but not used for classification, because the last year of a collection is the least stable [H].

**Axis A — state in 2025:** natural vegetation share of land area: ≥80%, 50–80%, 20–50%, <20%. The fact sheet also gives the remaining hectares.

**Axis B — dynamics 2012–2025:**

| Category | Rule (provisional) |
|---|---|
| Net gain | trend > +0.1%/yr **and** gain ≥ minimum absolute change |
| Stable | \|trend\| ≤ 0.1%/yr **and** gross conversion ≤ 0.5%/yr |
| Turnover | \|trend\| ≤ 0.1%/yr **and** gross conversion > 0.5%/yr |
| Moderate loss | −1 ≤ trend < −0.1%/yr |
| Intense loss | −2 ≤ trend < −1%/yr |
| Very intense loss | trend < −2%/yr |

At −1%/yr, half of the 2012 natural vegetation is gone in about 70 years; at −2%/yr, in about 35.

**Flags,** independent of the category:
- acceleration: the 2018–2025 trend is lower than the 2012–2018 trend by more than 0.5 percentage points per year;
- dominant conversion driver (pasture, soybean or other crops, forest plantation, mining, urban);
- small area (< 5 kha; unstable rates);
- coverage gap (`findings.md` §9);
- hybrid;
- hydrological dynamics (§5).

**Minimum absolute change.** The relative rate inflates small changes in areas with little natural vegetation left. Exploratory 2012–2025 run [E]: 6 of the 9 areas with net gain had less than 30% natural vegetation in 2012. Gain therefore also requires a minimum change in percentage points of area and in hectares, to be set in §6.

## 5. Proposed amendment (pending): conversion is natural → anthropic only
**Evidence** [E] (annual transitions 2012–2025, `lulc_transitions`): in the Pantanal (2019 limit), **88%** of the gross transitions out of natural vegetation go to water or sand (classes 33, 23), and almost the same amount comes back (5.38 vs. 5.31 Mha summed over the years). In the Cerrado this share is 2%. In 36 of the 348 units, more than 20% of the gross "loss" is this kind of exchange, mostly Pantanal areas (e.g. 182, 224, 243, 252: 94–99%).

**Problem.** If loss means "natural vegetation → anything else", the Pantanal areas would be classified as "turnover" or loss because of flooding cycles, not conversion.

**Proposal.**
- Loss = natural vegetation → **anthropic** classes (`nature` = anthropic or ambiguous).
- Gain = anthropic → natural vegetation.
- Exchanges between natural vegetation and natural non-vegetated classes (water 33, beach/dune/sand 23) are **hydrological or natural dynamics**. They are reported separately, are neutral for the category and raise the `hydrological dynamics` flag.
- The trend is computed on the anthropic area (or, equivalently, on the non-anthropic area). The flood-driven annual fluctuation of the vegetation stock therefore does not enter the category.
- Axis A (state) stays on natural vegetation as defined in §3.

**Known gap** [L]: MapBiomas class 33 includes reservoirs. A dam flooding natural vegetation between 2012 and 2025 would be counted as natural dynamics. Reservoirs built in the period must be checked against an external list before this is final.

## 6. Calibration before the thresholds are fixed
- Estimate classification noise from the year-to-year residual around the trend, using the anthropic-area series of §5. The stability band (±0.1%/yr) must be larger than the trend uncertainty that this noise implies over 14 years.
- Set the minimum absolute change for gain.
- Report the number of areas per category under ±50% variations of each threshold (sensitivity), so the Directorate sees how robust each assignment is.
- Thresholds become final only after the project lead approves the calibration.

## 7. New extraction needed
1. Direct transition 2012 → 2025 per zone. The sum of annual transitions is not the same thing.
2. Natural vegetation stable 2012–2025 per zone (the share never converted in the period), to measure turnover properly.
3. Intersection of zones with IBGE municipalities, for the municipality filter.

Protected areas and indigenous lands are left out of Product 1, because they pull the reading towards effectiveness. They may enter later as a filter only.

## 8. Evidence from the exploratory run (2012–2025, endpoints; superseded by §4–6 when implemented)
- [E] Median net change −0.66%/yr in the 348 units; −0.79%/yr in the matrix outside them.
- [E] Only 17 units had net gain. With net-rate classes alone, about 65% of the units fall into a single "moderate loss" class. Hence the two axes and the flags.
- [E] Gross loss (median 1.37%/yr) is more than twice the net loss; gross regrowth is 0.56%/yr; the two are correlated (ρ = 0.67).
- [E] 135 units lost faster in 2018–2025 than in 2012–2018 by more than 0.5 percentage points per year.
