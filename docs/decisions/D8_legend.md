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
