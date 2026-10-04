"""
31_export_maps.py — One change map per priority area (Product 1 fact sheets, D13).

Map classes, comparing MapBiomas level-1 groups in 2012 and 2025 (endpoint comparison, the
same basis as the "where did it go" chart of the fact sheet):
  1 natural vegetation stable     natural 2012 -> natural 2025
  2 natural vegetation lost       natural 2012 -> anthropic 2025
  3 natural vegetation gained     anthropic 2012 -> natural 2025
  4 anthropic stable              anthropic 2012 -> anthropic 2025
  5 water / sand stable           water or sand in both years
  6 exchange with water / sand    any other change involving water or sand
                                  (hydrological dynamics, D13 §5; includes possible reservoirs)
Natural = level 1 classes 1-2; anthropic = legend nature anthropic/ambiguous; water/sand =
classes 33 and 23. The area itself is drawn in full colour with a dark outline; the
surroundings inside the image frame are drawn faded, as context.

Output: one PNG per unit (<unit>.png, about 900 px wide) in --out, plus maps_index.csv with
the bounds of each image. The maps are illustrations: thumbnails are computed by Earth Engine
from image pyramids, so small patches may be generalized. All AREAS in the fact sheets come
from the tables, never from these images.

Run (Colab, after the authentication cell):
  %run scripts/gee/31_export_maps.py --units 29 252 244       # test
  %run scripts/gee/31_export_maps.py                          # all 348 units (~20-40 min)
Existing PNGs are skipped, so an interrupted run can simply be started again.

What can break, and how you would notice:
  - "Computation timed out" / HTTP 400 on very large areas: the unit is listed as failed at
    the end; run again with --dims 600 for those units.
  - A blank (all white) image means the unit has no MapBiomas pixels (coverage gap).
  - If the legend table changes, the class lists change at the next run (read at run time).
"""
import argparse
import csv
import importlib
import time
from pathlib import Path

import ee
import pandas as pd
import requests

import gee_common as gc

gc = importlib.reload(gc)

PALETTE = ["1f6f3a",   # 1 natural stable
           "eb6834",   # 2 natural lost
           "4a3aa7",   # 3 natural gained
           "d8d2c4",   # 4 anthropic stable (recessive by design)
           "2a78d6",   # 5 water / sand stable
           "56b4e9"]   # 6 exchange with water / sand
# Palette checked with the dataviz validator (all-pairs CVD separation >= 9.0 for the five
# saturated classes; class 4 is a neutral background tone).

ap = argparse.ArgumentParser()
ap.add_argument("--units", nargs="+", default=None, help="unit codes; default all")
ap.add_argument("--out", default=str(gc.ROOT / "data/interim/maps"))
ap.add_argument("--dims", type=int, default=900, help="image width/height limit in pixels")
ap.add_argument("--y0", type=int, default=2012)
ap.add_argument("--y1", type=int, default=2025)
args = ap.parse_args()
out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

gc.init()
gc.check_verified()

# --- Units from the zone markers (same rule as the analysis scripts) ---------------------
z = pd.read_csv(gc.ROOT / "data/derived/zones_attributes.csv")
z["unit"] = z.ap2012_code.where(z.ap2012_code != "none", z.hybrid_code).str.replace(".0", "", regex=False)
z = z[z.unit != "none"]
unit_codes = sorted(z.unit.unique(), key=lambda s: (not s.isdigit(), int(s) if s.isdigit() else 0, s))
sel = args.units or unit_codes

# --- Change classes, computed once for the whole extent ------------------------------------
NAT = ee.List(gc.natural_vegetation_classes())
ANT = ee.List(gc.anthropic_classes())
NNV = ee.List([23, 33])


def flag(img, classes):
    return img.remap(classes, ee.List.repeat(1, classes.size()), 0)


c0, c1 = gc.lulc(args.y0), gc.lulc(args.y1)
n0, n1 = flag(c0, NAT), flag(c1, NAT)
a0, a1 = flag(c0, ANT), flag(c1, ANT)
w0, w1 = flag(c0, NNV), flag(c1, NNV)
cls = (ee.Image(6)                                   # default: exchange involving water/sand
       .where(n0.And(n1), 1).where(n0.And(a1), 2).where(a0.And(n1), 3)
       .where(a0.And(a1), 4).where(w0.And(w1), 5)
       .updateMask(c0.mask().And(c1.mask())).rename("cls"))
vis = cls.visualize(min=1, max=6, palette=PALETTE)
faded = vis.multiply(0.35).add(255 * 0.65).uint8()   # 65% towards white
white = ee.Image.constant([255, 255, 255]).uint8().rename(["vis-red", "vis-green", "vis-blue"])
zones_fc = ee.FeatureCollection(gc.CFG["zones_asset"])
bounds = pd.read_csv(gc.ROOT / "data/derived/product1/units_bounds.csv", dtype={"unit": str}).set_index("unit")

failed, index = [], []
for u in sel:
    f = out / f"{u}.png"
    if f.exists():
        continue
    ids = z.loc[z.unit == u, "zone_id"].astype(int).tolist()
    if not ids:
        print("unknown unit", u); failed.append(u); continue
    # Bounds precomputed locally (data/derived/product1/units_bounds.csv, EPSG:4674): avoids
    # one server round-trip per unit and the edge limit of a full dissolve.
    xmin, ymin, xmax, ymax = bounds.loc[u, ["minx", "miny", "maxx", "maxy"]].astype(float)
    fc = zones_fc.filter(ee.Filter.inList("zone_id", ids))
    px, py = (xmax - xmin) * 0.06, (ymax - ymin) * 0.06
    region = ee.Geometry.Rectangle([xmin - px, ymin - py, xmax + px, ymax + py], proj="EPSG:4674", geodesic=False)
    scale = max(xmax - xmin, ymax - ymin) * 111000 / args.dims          # metres per output pixel
    geom = fc.union(maxError=scale).geometry()
    inside = ee.Image.constant(1).clip(geom).mask().gt(0)
    outline = ee.Image().byte().paint(ee.FeatureCollection([ee.Feature(geom)]), 1, 2).visualize(palette=["222222"])
    img = ee.ImageCollection([white, faded, vis.updateMask(inside), outline]).mosaic()
    for attempt in range(3):
        try:
            url = img.getThumbURL({"region": region, "dimensions": args.dims, "format": "png"})
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            f.write_bytes(r.content)
            index.append({"unit": u, "xmin": xmin - px, "ymin": ymin - py, "xmax": xmax + px, "ymax": ymax + py})
            print("ok", u)
            break
        except Exception as e:  # network hiccup or EE timeout: retry, then report
            if attempt == 2:
                print("FAILED", u, str(e)[:200]); failed.append(u)
            time.sleep(5)

if index:
    idx = out / "maps_index.csv"
    new = not idx.exists()
    with open(idx, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["unit", "xmin", "ymin", "xmax", "ymax"])
        if new:
            w.writeheader()
        w.writerows(index)
print(f"done: {len(index)} new maps in {out}; failed: {failed or 'none'}")
