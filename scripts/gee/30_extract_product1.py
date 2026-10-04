"""
30_extract_product1.py — Extra Earth Engine extractions for Product 1 (D13, section 7).

Two kinds of export, all per zone, settings in config.yml -> product1:

1. Direct transitions between two years (not the sum of annual transitions):
     product1_trans_<start>_<end>.csv     columns: key, sum (ha), start, end
     key = zone_id * 10000 + class_start * 100 + class_end
   Used for "where did the natural vegetation go" in each fact sheet, for the whole
   period 2012-2025 and for each sub-period (2012-2018, 2018-2025).

2. Persistence of natural vegetation present in the start year of a window:
     product1_persist_<window>.csv        columns: key, sum (list of 4 ha values), window, start, end, k_water
     key = zone_id * 1000 + class_start
     sum = [nat_start_ha, strict_ha, never_anthropic_ha, water_persistent_ha]
       nat_start_ha        natural vegetation in the start year (the denominator)
       strict_ha           ... and natural vegetation in EVERY year of the window
       never_anthropic_ha  ... and never in an anthropic class in any year of the window
                           (exchanges with water or sand are allowed: D13 section 5)
       water_persistent_ha ... and water in EVERY one of the last k_water years
                           (flag "possible reservoir", D13 section 5)
   Natural vegetation = MapBiomas level 1 classes 1 and 2 (D13 section 3).
   Anthropic = legend `nature` anthropic or ambiguous (D13 section 5).

Run from the repository root (or from the Colab notebook):
  python scripts/gee/30_extract_product1.py            # all exports (3 + 2 tasks)
  python scripts/gee/30_extract_product1.py --only trans
  python scripts/gee/30_extract_product1.py --only persist
Then download the Drive folder and run 90_collect_exports.py, which decodes these files.

What can break, and how you would notice:
  - The 1985-2025 persistence window stacks 41 years, like the fire-interval task. If it
    fails with "User memory limit exceeded" or "Computation timed out", raise
    export.tile_scale in config.yml (4 -> 8 -> 16) and run again with --only persist.
  - QC in 90_collect_exports.py: (a) direct-transition total per zone equals the LULC area
    of the start year; (b) nat_start_ha equals the natural-vegetation area of the start year
    in lulc_area; (c) strict <= never_anthropic <= nat_start, and
    water_persistent <= nat_start - strict (a pixel that became water is no longer
    natural vegetation in every year). A failure points to a mask or legend error.
  - If the legend table changes (new classes), re-run this script: the class lists are read
    from data/reference/mapbiomas_col11_legend_groups.csv at run time.
"""
import argparse
import importlib

import ee

import gee_common as gc

gc = importlib.reload(gc)  # re-read config.yml if it was edited in the same Colab session

ap = argparse.ArgumentParser()
ap.add_argument("--only", choices=["trans", "persist"], help="run only one kind of export")
args = ap.parse_args()

gc.init()
gc.check_verified()
zone, region = gc.zones_image()
area = ee.Image.pixelArea().divide(1e4).rename("ha")
P = gc.CFG["product1"]

# Class lists -> 0/1 images. remap() leaves unlisted values masked unless a default is given;
# default 0 keeps every mapped pixel in the computation.
NAT = ee.List(gc.natural_vegetation_classes())
ANT = ee.List(gc.anthropic_classes())


def is_in(img, classes):
    """1 where the class is in `classes`, else 0. Cast to Int8 so that every image put in an
    ImageCollection has the same type (EE error 'Expected a homogeneous image collection')."""
    return img.remap(classes, ee.List.repeat(1, classes.size()), 0).toInt8()


# --- 1. Direct transitions ------------------------------------------------------------------
if args.only in (None, "trans"):
    for a, b in P["transition_pairs"]:
        key = zone.multiply(10000).add(gc.lulc(a).multiply(100)).add(gc.lulc(b)).rename("key").int()
        g = gc.grouped_sum(key.addBands(area), 1, region)
        gc.export_groups(g, f"product1_trans_{a}_{b}", {"start": a, "end": b})

# --- 2. Persistence of natural vegetation -------------------------------------------------
if args.only in (None, "persist"):
    k = int(P["water_final_years"])
    water = int(P["water_class"])
    for w in P["persistence_windows"]:
        a, b = int(w["start"]), int(w["end"])
        ys = list(range(a, b + 1))
        start_cls = gc.lulc(a)
        nat_start = is_in(start_cls, NAT)

        # Natural vegetation in every year: minimum of the yearly 0/1 flags
        strict = ee.ImageCollection([is_in(gc.lulc(y), NAT) for y in ys]).min()
        # Never anthropic: maximum of the yearly anthropic flags must be 0
        ever_ant = ee.ImageCollection([is_in(gc.lulc(y), ANT) for y in ys]).max()
        # Water in every one of the last k years of the window
        last = ys[-k:] if k <= len(ys) else ys
        water_all = ee.ImageCollection([gc.lulc(y).eq(water).toInt8() for y in last]).min()

        bands = [
            nat_start.multiply(area).rename("nat_start_ha"),
            nat_start.And(strict).multiply(area).rename("strict_ha"),
            nat_start.And(ever_ant.Not()).multiply(area).rename("never_anthropic_ha"),
            nat_start.And(water_all).multiply(area).rename("water_persistent_ha"),
        ]
        key = zone.multiply(1000).add(start_cls).rename("key").int()
        # Only pixels that were natural vegetation in the start year matter; masking the key
        # keeps the exported table small (other start classes would only add zero rows).
        key = key.updateMask(nat_start)
        g = gc.grouped_sum(key.addBands(ee.Image.cat(bands)), len(bands), region)
        gc.export_groups(g, f"product1_persist_{w['name']}",
                         {"window": w["name"], "start": a, "end": b, "k_water": len(last)})
