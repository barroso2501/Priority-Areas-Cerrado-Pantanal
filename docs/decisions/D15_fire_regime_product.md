# D15 — Product 2: fire regime in stable natural vegetation of the priority areas

**Status:** Accepted 2026-10-06 (project lead); categories simplified the same day (§4, project lead); earlier revisions the same day (§4 absence over the full series, prolonged exclusion; §5 critical window by latitude band, north of 12°S confirmed; indicator renamed "sem ignição natural"). Thresholds are parameters, to be calibrated (§7; calibration extraction defined 2026-10-06, project lead: calibration before the presentation). Supersedes the open parts of D3 for this product and implements D9.
**Raised:** 2026-10-05

## 1. Question
What is the state of the fire regime in the natural vegetation that remained natural over the whole series, in each 2nd-update priority area, and how did it change between 2012–2018 and 2019–2025?

## 2. Universe (scope, not limitation)
- **Stable natural vegetation:** pixels in MapBiomas level-1 natural vegetation classes (D13 §3) in **every year 1985–2025** (domain-level stability, D9 option a). Regenerated and converted pixels are excluded by design: their age and history add noise unrelated to the regime. The product therefore describes the regime of the vegetation that persisted, which is the intended object.
- **Vegetation types**, by the pixel's modal class over 1985–2025:
  - forest: classes 3, 6;
  - savanna: class 4;
  - grassland: class 12;
  - wetland / floodable: classes 11, 7 — **reported only**, without an expected regime (flood-driven, Pantanal and veredas);
  - other natural classes (29, 32, 50, 77, 84): excluded.
- Units: the 348 units of D13 (294 MMA areas + 54 hybrids); the matrix outside them as context.

## 3. Fire year
Fire year *y* = April of *y* to March of *y+1*. The boundary falls in the wet season: January–April hold 1.3% of the burned area in stable vegetation [E], so a December/January scar pair is not counted as two consecutive years. Fire year 2025 ends in December 2025 (January–March 2026 not yet mapped; about 1% of the annual fire). Sensitivity: calendar year.

## 4. Pixel category (revised 2026-10-06, project lead)
**Purpose.** An assessment of the state of stable natural vegetation in relation to fire as a disturbance, which harms communities both in excess and in absence. The **extremes are the most important and the most robust** part of the assessment; what lies between them may or may not be adequate and needs a finer analysis (at fragment level, not at priority-area level), outside this product.

All categories are judged over the **full series of fire years 1985–2025**, the same 41 years over which the vegetation is stable.

| Forest (stable) | Savanna and grassland (stable); expected interval **3–20 years** |
|---|---|
| 1 **not affected by fire** — no fire in 1985–2025 | 1 **above expected** — repeated annual or biennial fire: at least **2 intervals shorter than 3 years** |
| 2 **affected by fire** — at least one fire | 2 **as expected** — all other cases |
| | 3 **below expected** — **no fire in the last 20 fire years** (2006–2025), never-burned pixels included |

- "Below expected" is assigned first: it describes the current state, even for a pixel that burned too often in the past.
- One isolated short interval is not excess (a re-burn of unburnt fuel the following year can happen in a natural mosaic); the excess signal is **repetition**.
- The upper bound of 20 years matches the prolonged-exclusion threshold set by the project lead; 3 years is the lower bound of the expected interval.
- Wetlands: the same rule is computed and reported, without interpretation (flood-driven regime).
- Parameters in `config.yml`: `expected_min` = 3, `expected_max` = 20, `excess_short_intervals` = 2.

[E] Order of magnitude from the existing interval tables (calendar year, priority areas): stable savanna + grassland never burned in 41 years 31.3%, burned but not in the last 20 years 15.6% → **below expected ≈ 47%**; stable forest with at least one fire in 1985–2025 ≈ 29%.

**"Below expected" as a result.** The project lead considers it an important result, consistent with his independent analysis of fire intervals in the stable vegetation of the whole Cerrado (draft *Cerrado Fire Intervals*, 1985–2024: about half of the stable natural vegetation never burned). Caveat for the record: both analyses use the MapBiomas fire product, so the agreement confirms the computation and the reading, not the detection itself (omission, §6).

Earlier proposals superseded: pixel classes infrequent/compatible/frequent/consecutive on 2012–2025, and a unit-level "compatibility" from the interval distribution. The interval distribution (mosaic) stays as a descriptive table for the finer, fragment-level analysis.

## 5. Indicators per unit
- **Regime composition:** share of stable forest and of stable savanna + grassland in each class (§4). Wetlands reported with the same counts, no class reading.
- **Change 2012–2018 → 2019–2025** (fire years), per type:
  - annual burned fraction of the stable area;
  - share of the stable area with at least one pair of consecutive fire years within the sub-period;
  - **critical-window ratio** = burned area in the critical window of the pixel's latitude band / total burned area (calendar months of the sub-period's years);
  - **no-natural-ignition ratio** (*sem ignição natural*) = burned area in July–August / total burned area. Natural ignition in the Cerrado comes from lightning, which does not occur in these months, so this fraction is certainly human-caused.
- **Critical window by latitude band** (project lead, revised 2026-10-06). In 12–18°S the herbaceous layer enters water stress in July, August is the most critical month (higher temperature, shallow soil water exhausted), September continues it with occasional small rains, and rains return in October–November; the season shifts later northwards.
  - South of 12°S (12–18°S and south of 18°S): **July–September**.
  - North of 12°S: **August–October** (northward shift; confirmed by the project lead 2026-10-06).

  The fire product is monthly, so windows are whole months.
- [E] Share of fire in the window, 2012–2025, stable open vegetation in the priority areas: south of 18°S 58% (July–September); 18–12°S 56% (July–September; 34% falls in October, outside the window); 12–8°S 79% and north of 8°S 80% (August–October). July–August: 34%, 15%, 22% and 35%.
- **Reading of the ratios:** relative, each unit against the stable matrix of the same latitude band (south of 18°S, 18–12°S, 12–8°S, north of 8°S), and change between sub-periods within the unit. No absolute threshold.
- **Minimum fire for the ratios:** computed only when the burned area in the sub-period is at least max(1,000 ha, 1% of the stable open vegetation of the unit); otherwise "insufficient fire to assess the season".
- Fire in forest is never interpreted through season: any recurrence is already a departure.

## 6. Critical test before recording (points a reviewer would raise)
- **Forest class may contain cerradão and transition forest** [H]: 35% of closed intervals in "forest" are 1–2 years [E]. Sensitivity: repeat with class-stable pixels (same class every year, D9 option b).
- **Omission and commission of the fire product.** Understorey fire in forest is under-detected [H], so F0 means "no fire detectable". Spurious scars inflate O3/O4; sensitivity with a minimum scar size is planned.
- **Latitude.** Handled by a critical window per latitude band (§5) and by comparing each unit with the matrix of the same band. A three-month window per band is coarse for a gradual shift; finer bands are possible later if needed.
- **The 3–20-year expected interval** is deliberately broad: the assessment targets the extremes. The middle class is not a statement of adequacy.
- Integrated fire management (MIF) does not justify high frequency; no exception is made for it (project lead).
- **No judgement of merit or cause** (project lead, 2026-10-06). The product presents the data. It does not attribute "above expected" to traditional or indigenous fire use, to MIF, or to any other agent, and it does not judge whether a given use is legitimate. Units around indigenous lands appear among the highest "above" shares [E]; this is reported as a fact of location, without causal reading.
- **Biome transitions** (savanna or forest classes in Cerrado–Amazon or Cerrado–Atlantic Forest contact zones, whose expected regime may differ) are not treated now; see §10.

## 7. Calibration and sensitivity (before publication)
- Thresholds of §4 varied: expected maximum 10, 15 and 25 years; excess with 1 and 3 short intervals; short interval = 1 year only (annual fire), with 1 and 2 repetitions.
- Calendar year instead of fire year.
- Class-stable universe instead of domain-stable.
- Critical windows shifted by one month (earlier and later) in each band.

**How (2026-10-06).** One extraction (`scripts/gee/23_extract_fire_calibration.py`, notebook step 11) exports, per zone × type, the stable area by a pixel *signature* — number of intervals < 3 years and of 1-year intervals (each capped at 3), band of the last fire year (2016–2025, 2011–2015, 2006–2010, 2001–2005, ≤ 2000, never), class-stable flag — once on fire years and once on calendar years, plus burned area by month × latitude band × sub-period. Every variant above is rebuilt offline (`scripts/analysis/product2_calibration.py`): category shares inside and outside the units, and how many units change flag (below > 50%, above > 20%, above > 50%, forest affected > 50%) relative to the product setting. The offline test checks the signature rules against direct per-pixel rules for all 24 combinations of N, k and short-interval definition; the decoding QC checks that the product setting rebuilt from the signature equals `fire_regime`.

**Reading criterion (proposed, to confirm with the results).** A threshold is retained when the extremes are robust to it: the global shares move little, and the units flagged at the extremes are largely the same. Where a choice moves many units across a flag, the presentation reports the flag as threshold-dependent instead of choosing the threshold that looks best.

## 8. Extraction
`scripts/gee/22_extract_fire_regime.py`: per zone × vegetation type × category (§4), the stable area and, per sub-period, burned fraction, consecutive-pair area and August–October / total burned area. Decoded and checked by `90_collect_exports.py` (sum over classes = stable area of the type, against `fire_intervals`). Calibration: `23_extract_fire_calibration.py` (§7), decoded into `fire_calib.parquet` and `fire_calib_month.parquet`.

## 9. Not in this product
Fire in land-use areas; fire in transitioning pixels; fire severity; degradation (D3 option 3 cross-check with the MapBiomas degradation module remains open).

## 10. Next steps outside this product
- **Biome transitions:** qualify the categories with the IBGE vegetation map (phytophysiognomies and ecotones), so that savanna or forest in contact zones is read against the regime of its own formation (project lead, 2026-10-06; not considered now).
- Fragment-level analysis of the "as expected" class: interval distribution and time-since-fire mosaic per fragment of stable open vegetation (mode at 4–6 years, few at 3, long tail from 7, per the project lead), to separate adequate from merely non-extreme regimes.
