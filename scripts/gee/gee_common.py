"""
gee_common.py — Shared helpers for the Earth Engine extraction scripts.

Key encodings (all integers, decoded by 90_collect_exports.py):
  LULC area         key = zone_id * 1000 + class
  LULC transitions  key = zone_id * 10000 + class_from * 100 + class_to      (classes < 100)
  Fire monthly      key = ((zone_id * 2 + stable) * 100 + class) * 13 + month
  Fire intervals    key = zone_id * 100 + modal_class
Class values must be < 100; 00_discover_assets.py checks this.
"""
from pathlib import Path

import ee
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load(open(Path(__file__).with_name("config.yml"), encoding="utf-8"))
LEGEND = ROOT / "data/reference/mapbiomas_col11_legend_groups.csv"


def init():
    """Authenticate (first run opens a browser) and initialize with the project."""
    try:
        ee.Initialize(project=CFG["gee_project"])
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=CFG["gee_project"])


def years():
    y = CFG["years"]
    return list(range(y["first"], y["last"] + 1))


def check_verified():
    """Refuse to run extractions while asset IDs are still placeholders."""
    m = CFG["mapbiomas"]
    bad = [k for k in ("lulc_asset", "fire_monthly_asset") if m[k] == "VERIFY"]
    if bad or "YOUR-CLOUD-PROJECT-ID" in CFG["gee_project"] or "YOUR-CLOUD-PROJECT-ID" in CFG["zones_asset"]:
        raise SystemExit(f"Fill config.yml first (placeholders: {bad or 'gee_project'}). "
                         "Run 00_discover_assets.py to find the asset IDs.")


def legend() -> pd.DataFrame:
    """Legend grouping table (D8). Rows without a verified pixel value are dropped."""
    lg = pd.read_csv(LEGEND)
    if (lg.pixel_id_status != "verified").any():
        print("WARNING: legend pixel values not all verified (open issue P8).")
    return lg.dropna(subset=["pixel_id"]).astype({"pixel_id": int})


def native_classes() -> list[int]:
    lg = legend()
    return lg.loc[lg.fire_domain == "native", "pixel_id"].tolist()


def lulc(year: int) -> ee.Image:
    m = CFG["mapbiomas"]
    return ee.Image(m["lulc_asset"]).select(m["lulc_band_pattern"].format(year=year)).rename("cls")


def fire_month(year: int) -> ee.Image:
    """Month of burn (1-12); masked where not burned."""
    m = CFG["mapbiomas"]
    img = ee.Image(m["fire_monthly_asset"]).select(m["fire_monthly_band_pattern"].format(year=year))
    return img.selfMask().rename("month")


def zones_image() -> tuple[ee.Image, ee.Geometry]:
    """Rasterize zones in the MapBiomas grid; return (zone_id image, extent rectangle)."""
    fc = ee.FeatureCollection(CFG["zones_asset"])
    img = ee.Image().int32().paint(fc, "zone_id").rename("zone")
    # Region = precomputed bounding box. fc.geometry() would union all zones and fails
    # ("Geometry has too many edges"). Pixels outside zones are masked by `img` anyway.
    region = ee.Geometry.Rectangle(CFG["zones_bbox"], proj="EPSG:4674", geodesic=False)
    return img, region


def grid():
    """CRS and transform of the LULC asset, so every reduction uses its native grid."""
    p = ee.Image(CFG["mapbiomas"]["lulc_asset"]).projection().getInfo()
    return p["crs"], p["transform"]


def grouped_sum(img_key_first: ee.Image, n_values: int, region: ee.Geometry) -> ee.List:
    """Sum `n_values` bands grouped by an integer key.

    Callers pass the key as the FIRST band, followed by the value bands. Earth Engine
    requires the group band to come AFTER the reduced inputs, so the bands are reordered
    here to [values..., key] and the group field is the last band (index n_values).
    """
    crs, tr = grid()
    key = img_key_first.select([0])
    values = img_key_first.select(list(range(1, n_values + 1)))
    img = values.addBands(key)
    base = ee.Reducer.sum().repeat(n_values) if n_values > 1 else ee.Reducer.sum()
    reducer = base.group(groupField=n_values, groupName="key")
    out = img.reduceRegion(reducer=reducer, geometry=region, crs=crs, crsTransform=tr,
                           maxPixels=1e13, tileScale=CFG["export"]["tile_scale"])
    return ee.List(out.get("groups"))


def export_groups(groups: ee.List, description: str, extra: dict):
    """Turn reducer groups into a table and export it to Drive as CSV."""
    def to_feat(g):
        g = ee.Dictionary(g)
        return ee.Feature(None, g.combine(ee.Dictionary(extra)))
    fc = ee.FeatureCollection(groups.map(to_feat))
    task = ee.batch.Export.table.toDrive(collection=fc, description=description,
                                         folder=CFG["export"]["drive_folder"], fileFormat="CSV")
    task.start()
    print("started", description)
    return task
