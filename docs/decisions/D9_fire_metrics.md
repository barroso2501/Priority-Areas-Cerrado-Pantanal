# D9 — Fire metrics: intervals by domain, with censoring

**Status:** Accepted in principle (2026-10-02, project lead; stability rule added the same day). Implementation details below are open.

## Decision (project lead)
1. **Separate domains.** Fire in **native vegetation** and fire in **land-use areas** are separate metrics. The domain is assigned from the land-cover class of the same year (D8 `fire_domain`).
2. **Intervals over frequency.** The primary metric is the fire-return **interval** per pixel, not counts.
3. **Include unburned areas.** Pixels with zero fire occurrences are kept.
4. **Censoring.** Intervals are kept with explicit censoring:
   - *left-censored*: time from series start (1985) to the first fire;
   - *right-censored*: time from the last fire to the series end (2025);
   - *never burned*: a pixel continuously in the same domain for the whole series, recorded as one interval right-censored at its full length.

5. **Stable areas only (project lead, 2026-10-02).** Interval and frequency analyses of the fire regime in vegetation use only pixels that remain **stable during the analysis period**. Pixels that transition (conversion, regrowth or any domain change) are **excluded** from the regime assessment. Fire in transitioning areas may be reported separately as a land-change process, never as regime.

This replaces the earlier proposal to censor intervals at domain change.

## Implications and proposals (to confirm)
- **Stability depends on the period.**
  - Stable over 1985–2025 gives the most consistent regime but a smaller and biased sample. Areas never converted tend to be remote, steep or protected, so the regime describes the "surviving" landscape (survivorship bias).
  - Stable per analysis period (between D1 milestones) gives larger samples, but each period's stable set differs.
  - Proposal: report both, with full-series stability as the reference.
- **Keep the choice open without re-extraction.** Extract with an extra dimension, `native_run_start`: the first year of the pixel's current continuous run in the native domain (1985 = native since the series start). Any stability window can then be selected afterwards, so D1 is not needed before extraction.
- **Level of stability.** Two possible levels:
  - (a) domain-stable: native throughout, with class swaps allowed, e.g. savanna ↔ grassland, which are often classification noise;
  - (b) class-stable: same native class every year.

  Proposal: (a) as the main analysis, with the physiognomy assigned as the pixel's modal class, and (b) as a sensitivity analysis. To confirm.
- **Censoring stays.** Within stable pixels, left-censoring (series or window start → first fire), right-censoring (last fire → window end) and never-burned pixels (one fully censored interval) are kept as decided.
- **Land-use domain.** Fire in stable land-use areas (e.g. pasture burning) is a separate metric of management pressure, not of vegetation regime.

## Extraction design (proposed)
- For each year *y* (1985–2025), per-pixel images of: burned in *y* (annual flag from the monthly scars); native run start year; modal native class; years since the last fire or the window start.
- Grouped reducer over: `zone_id × modal_class × native_run_start × interval_length × event_type`, where `event_type` ∈ {closed by fire, left-censored, right-censored, never burned}.
- Transitioning pixels are counted only in a separate "fire in transition" table: `zone_id × year × transition type × burned area`.

## Open details
- Annual flag definition: calendar year, or a fire year aligned to the dry season.
- Minimum patch or pixel rules for scars.
- Pantanal treatment (flood-driven fire regime).
