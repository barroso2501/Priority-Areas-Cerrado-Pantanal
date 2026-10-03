# D6 — MapBiomas collection and period

**Status:** Accepted (2026-10-02, project lead)

- **Land use/cover:** MapBiomas Brazil **Collection 11**, annual series **1985–2025**, including the Degradation module.
- **Assets:** use the **integrated national** asset (all biomes in one image). Never use per-biome subsets for extraction (see D11).
- **Versions:** record the asset ID and version of every module used in `data/reference/assets.yml` (fire, water, pasture, secondary vegetation, degradation).
- **No mixing of collections.** If a module is only available for a different collection or a shorter period, document it as an exception in this file.

## Fire collection
- **Source:** MapBiomas Fire **Collection 5.1**, the latest published in the public Earth Engine folder (2026-10-03). It covers 1985–2025: the folder holds annual vector tables for every year 1985–2025.
- **Asset used:** `projects/mapbiomas-public/assets/brazil/fire/collection5_1/mapbiomas_fire_collection51_monthly_burned_v1` (monthly burned area, value = month).
- **Asset rejected:** the *accumulated* products (`accumulated_burned_*`). They record whether a pixel has ever burned up to a year, so they cannot give fire years, intervals or months.
- **Cross-check only, not used for D9:** the folder also has `interval_since_fire`, `time_after_fire`, `year_last_fire`, `fire_frequency` and `severity_class`. Their interval products ignore our stability and censoring rules (D9), so they serve only to sanity-check our intervals.

## To verify before extraction
- The fire collection's period and version: whether it reaches 2025 and how it aligns with Collection 11 (open issue P7).
- Pixel values of the Collection 11 legend (open issue P8).
