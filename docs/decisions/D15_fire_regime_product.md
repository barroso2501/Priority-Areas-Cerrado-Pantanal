# D15 — Product 2: fire regime in stable natural vegetation of the priority areas

**Status:** Accepted 2026-10-06 (project lead); revised the same day (§4 absence over the full series, prolonged exclusion; §5 critical window by latitude band, north of 12°S confirmed; indicator renamed "sem ignição natural"). Thresholds are parameters, to be calibrated (§7). Supersedes the open parts of D3 for this product and implements D9.
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

## 4. Pixel regime class
Absence and prolonged exclusion are judged over the **full series** (fire years 1985–2025): the universe is stable over 41 years, and an ecologically significant exclusion signal must be long (project lead). Frequency classes describe the **current** regime on fire years 2012–2025 (14 years); 7-year sub-periods are too short to resolve 3–5-year intervals and are used only for change (§5). Over 41 years almost every pixel that burns would show at least one consecutive pair somewhere, so frequency classes on the full series would not discriminate [H].

| Forest (expected: no fire or rare, spaced events; window 2012–2025) | Savanna and grassland (expected: return interval 3–5 years) |
|---|---|
| F0 no fire | O0 **absence** — no fire in 1985–2025 (41 fire years). Regime alteration, whatever the cause (without fire, population and ecological processes are biased) |
| F1 one event | O5 **prolonged exclusion** — burned before, but no fire in the last 20 fire years (2006–2025). Separate class |
| F2 recurrent — two or more events, none consecutive | O4 consecutive — at least one pair of consecutive fire years in 2012–2025 |
| F3 recurrent with consecutive years | O3 frequent — shortest interval in 2012–2025 = 2 years |
| | O2 **compatible** — in 2012–2025, at least two fires, every interval 3–5 years and no run of more than 4 fire-free years at the window edges |
| | O1 infrequent — all other cases, including no fire in 2012–2025 with a last fire 6–19 years before 2025 |

Assignment order: O0 → O5 → O4 → O3 → O2 → O1 (and F3 → F2 → F1 → F0). Thresholds (consecutive = 1, frequent = 2, compatible = 3–5, exclusion = 20 years) are parameters in `config.yml`.

[E] For reference (savanna + grassland stable in the priority areas, existing interval tables): 31% never burned in 1985–2025; among the burned pixels, 48% had no fire in the last 10 years and 40% in the last 14.

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
- **The 3–5-year interval is a working expectation** [H] for open physiognomies; fine fuels in grasslands can recover in 1–2 years. Hence parameters and sensitivity (§7).
- Integrated fire management (MIF) does not justify high frequency; no exception is made for it (project lead).

## 7. Calibration and sensitivity (before publication)
- Thresholds of §4 varied (compatible 2–5 and 3–6; frequent = 2).
- Calendar year instead of fire year.
- Class-stable universe instead of domain-stable.
- Critical windows shifted by one month (earlier and later) in each band.
- Prolonged exclusion at 15 and 25 years.

## 8. Extraction
`scripts/gee/22_extract_fire_regime.py`: per zone × vegetation type × regime class, the stable area and, per sub-period, burned fraction, consecutive-pair area and August–October / total burned area. Decoded and checked by `90_collect_exports.py` (sum over classes = stable area of the type, against `fire_intervals`).

## 9. Not in this product
Fire in land-use areas; fire in transitioning pixels; fire severity; degradation (D3 option 3 cross-check with the MapBiomas degradation module remains open).
