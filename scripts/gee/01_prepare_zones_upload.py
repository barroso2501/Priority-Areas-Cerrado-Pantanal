"""
01_prepare_zones_upload.py — Package the extraction zones (D7) for upload to Earth Engine.

Input : data/interim/zones.gpkg (layer zones_albers), produced by scripts/build_zones.py
Output: data/interim/zones_upload.zip  -> zipped shapefile with a single field `zone_id`,
        EPSG:4674, to be uploaded as a GEE table asset (Assets > New > Table upload).

Run from the repository root:   python scripts/gee/01_prepare_zones_upload.py

Why simplify: the partition keeps 1 cm precision (3.9 M vertices). MapBiomas pixels are
30 m, so a topology-preserving simplification at 10 m changes nothing at pixel scale and
makes ingestion lighter. Coordinates are then snapped to 1e-6 degrees (~0.1 m) so the
zip stays below 30 MB. `coverage_simplify` simplifies shared edges once, so zones stay
gap-free and non-overlapping (independent per-feature simplification would not).

What can break, and how you would notice:
  - shapely < 2.1 has no coverage_simplify -> AttributeError; upgrade shapely.
  - The script prints the total area before/after; the relative change should be
    < 0.01%. A larger change means the tolerance is too coarse for small zones.
  - A few sub-pixel sliver zones collapse when snapped (about 80 zones, < 0.1 ha in total
    with the current partition); they are dropped and reported. Their zone_id simply
    never appears in the exports.
  - GEE ingestion errors about vertex counts: lower nothing here; instead split the
    upload (rare: the largest zone has ~0.2 M vertices before simplification).
"""
import zipfile
from pathlib import Path

import geopandas as gpd
import shapely

ROOT = Path(__file__).resolve().parents[2]
INT = ROOT / "data/interim"
TOL_M = 10.0  # simplification tolerance in metres (Albers); 1/3 of a MapBiomas pixel
PREC_DEG = 1e-6  # coordinate snapping in degrees (~0.1 m); shrinks the zip below 30 MB

z = gpd.read_file(INT / "zones.gpkg", layer="zones_albers", columns=["zone_id"])
before_area, before_v = z.area.sum(), int(z.geometry.count_coordinates().sum())

# Topology-preserving simplification of the whole coverage at once
z["geometry"] = shapely.coverage_simplify(z.geometry.values, TOL_M)
z["geometry"] = shapely.make_valid(z.geometry.values)
after_area, after_v = z.area.sum(), int(z.geometry.count_coordinates().sum())
print(f"vertices {before_v:,} -> {after_v:,}; area change {abs(after_area/before_area-1):.2e}")

out_dir = INT / "zones_upload"
out_dir.mkdir(parents=True, exist_ok=True)
zs = z.to_crs(4674)[["zone_id", "geometry"]]
zs["geometry"] = shapely.make_valid(zs.geometry.values)  # reprojection can leave invalid rings
zs["geometry"] = shapely.make_valid(shapely.set_precision(zs.geometry.values, PREC_DEG))
empty = zs.geometry.is_empty | zs.geometry.isna()
# Slivers far below one pixel collapse when snapped; they cannot be rasterized at 30 m anyway
print(f"dropped {int(empty.sum())} sliver zones that collapsed at {PREC_DEG} deg precision")
zs[~empty].to_file(out_dir / "zones.shp")
with zipfile.ZipFile(INT / "zones_upload.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for f in out_dir.glob("zones.*"):
        zf.write(f, f.name)
print(f"written {INT / 'zones_upload.zip'} ({(INT / 'zones_upload.zip').stat().st_size/1e6:.1f} MB)")
