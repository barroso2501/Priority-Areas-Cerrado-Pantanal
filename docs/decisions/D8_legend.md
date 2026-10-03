# D8 — Legend handling

**Status:** Accepted (2026-10-02, project lead)

## Decision
- **Extraction.** Extract at the **most detailed** Collection 11 class (pixel value), with no aggregation in GEE.
- **Aggregation.** Aggregate afterwards through `data/reference/mapbiomas_col11_legend_groups.csv`. The table carries the four MapBiomas hierarchical levels plus two project groupings:
  - `nature`: natural / anthropic / ambiguous;
  - `fire_domain`: native / use / non_burnable, used by D9.
- **Pixel values.** Values in the table are carried over from Collection 10 and flagged `col10_verify`. Four classes new in Collection 11 have no value yet (`new_in_col11`). All must be checked against the Collection 11 asset metadata before use (open issue P8).

## Judgement calls to review
- "Other non-vegetated areas" is marked `ambiguous`: it mixes natural bare ground and degraded or anthropic soil.
- "Rocky outcrop" sits under level 1 *Herbaceous/Shrubby Vegetation* in Collection 11 and is treated as native (burnable fringe).

## Verification (2026-10-03, closes P8)
- **Values present in the zones** (`00_discover_assets.py`, 1985 and 2025): 3, 4, 5, 6, 7, 9, 11, 12, 15, 20, 21, 23, 24, 25, 29, 30, 31, 32, 33, 39, 40, 41, 46, 47, 48, 50, 62, 75, 91.
- **New Collection 11 classes** (ATBD): 7 Flooded Savanna (beta), 77 Herbaceous and Shrub Formation, 84 Salt Marsh (beta), 91 Wind farm (beta). The ATBD reports no recoding of existing classes; only the definition of Rocky Outcrop (29) was broadened.
- **Native set used for fire stability (D9):** 3, 4, 5, 6, 7, 11, 12, 29, 32, 49, 50, 77, 84. It now includes class 7, Flooded Savanna, which is present in the extent. The provisional list would have treated class 7 as land use.
