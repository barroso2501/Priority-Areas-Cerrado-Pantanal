# D6 — MapBiomas collection and period

**Status:** Accepted (2026-10-02, project lead)

- **Land use/cover:** MapBiomas Brazil **Collection 11**, annual series **1985–2025**, including the Degradation module.
- **Assets:** use the **integrated national** asset (all biomes in one image). Never use per-biome subsets for extraction (see D11).
- **Versions:** record the asset ID and version of every module used in `data/reference/assets.yml` (fire, water, pasture, secondary vegetation, degradation).
- **No mixing of collections.** If a module is only available for a different collection or a shorter period, document it as an exception in this file.

## Fire collection
MapBiomas Fire **Collection 5** (1985–2025) is the fire source; its period matches LULC Collection 11.

## To verify before extraction
- The fire collection's period and version: whether it reaches 2025 and how it aligns with Collection 11 (open issue P7).
- Pixel values of the Collection 11 legend (open issue P8).
