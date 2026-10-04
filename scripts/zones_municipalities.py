"""
zones_municipalities.py — Area of each extraction zone in each IBGE municipality
(Product 1, D13 section 7, item 3: municipality filter of the fact sheets).

Runs without Earth Engine. It needs internet access only to download the IBGE municipal
boundaries, so run it in Colab (this sandbox and some networks block the IBGE server), or
pass a local copy with --mun.

Inputs
  --zones  zone polygons with field zone_id. Default: data/interim/zones_upload.zip
           (the same file uploaded to Earth Engine; its 10 m simplification is irrelevant
           at municipal scale). data/interim/zones.gpkg also works.
  --mun    IBGE municipal boundaries (zip or shapefile). Default: download
           BR_Municipios_2025.zip from IBGE (same year as the UF layer used in the zones).
Output
  data/derived/zones_municipalities.csv
     zone_id, cd_mun, nm_mun, uf, ha, share_of_zone
  One row per zone x municipality with at least 0.01 ha in common. share_of_zone sums to
  ~1 per zone for zones inside Brazil; zones beyond the border or offshore sum to less
  (they also lack MapBiomas pixels, findings.md section 9).

Run from the repository root:
  python scripts/zones_municipalities.py
  python scripts/zones_municipalities.py --mun /path/BR_Municipios_2025.zip   # offline

Method
  Both layers are reprojected to South America Albers Equal Area (the project CRS for area
  computations) and intersected. Only municipalities touching the bounding box of the zones
  are kept before the overlay, to save time.

What can break, and how you would notice:
  - IBGE changes the URL or the field names: download fails (HTTP error) or a KeyError on
    CD_MUN / NM_MUN / SIGLA_UF. Fix with --url, or with --fields CODE NAME UF.
  - Invalid geometries raise a GEOS error in the overlay; they are repaired with
    make_valid() first, so this should not happen. If it does, the error names the layer.
  - QC printed at the end: zones whose shares sum to < 0.99 should be only the border or
    offshore zones (about 86 kha, findings.md section 9). Many more means a CRS problem.
"""
import argparse
import tempfile
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = ("https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
       "malhas_municipais/municipio_2025/Brasil/BR_Municipios_2025.zip")
ALBERS = "ESRI:102033"  # South America Albers Equal Area Conic

ap = argparse.ArgumentParser()
ap.add_argument("--zones", default=str(ROOT / "data/interim/zones_upload.zip"))
ap.add_argument("--mun", default=None, help="local IBGE municipal file; downloads if omitted")
ap.add_argument("--url", default=URL)
ap.add_argument("--fields", nargs=3, default=["CD_MUN", "NM_MUN", "SIGLA_UF"],
                metavar=("CODE", "NAME", "UF"), help="field names in the municipal layer")
ap.add_argument("--out", default=str(ROOT / "data/derived/zones_municipalities.csv"))
args = ap.parse_args()

# --- 1. Read zones -------------------------------------------------------------------------
zones = gpd.read_file(args.zones)[["zone_id", "geometry"]]
print(f"zones: {len(zones)} features, CRS {zones.crs}")

# --- 2. Read (or download) municipalities -------------------------------------------------
mun_path = args.mun
if mun_path is None:
    tmp = Path(tempfile.gettempdir()) / Path(args.url).name
    if not tmp.exists():
        print("downloading", args.url)
        urllib.request.urlretrieve(args.url, tmp)
    mun_path = str(tmp)
code, name, uf = args.fields
# bbox filter at read time: only municipalities touching the zone extent are loaded
bbox = tuple(zones.to_crs("EPSG:4674").total_bounds)
mun = gpd.read_file(mun_path, bbox=bbox)
mun = mun[[code, name, uf, "geometry"]].rename(columns={code: "cd_mun", name: "nm_mun", uf: "uf"})
print(f"municipalities in the zone extent: {len(mun)}")

# --- 3. Overlay in an equal-area projection -------------------------------------------------
zones = zones.to_crs(ALBERS)
mun = mun.to_crs(ALBERS)
zones["geometry"] = zones.geometry.make_valid()
mun["geometry"] = mun.geometry.make_valid()
zones["zone_ha"] = zones.area / 1e4

inter = gpd.overlay(zones, mun, how="intersection", keep_geom_type=True)
inter["ha"] = inter.area / 1e4
inter = inter[inter.ha >= 0.01]
inter["share_of_zone"] = inter.ha / inter.zone_ha
out = (inter[["zone_id", "cd_mun", "nm_mun", "uf", "ha", "share_of_zone"]]
       .sort_values(["zone_id", "ha"], ascending=[True, False]))
out.to_csv(args.out, index=False, float_format="%.4f")

# --- 4. QC -------------------------------------------------------------------------------
s = out.groupby("zone_id").share_of_zone.sum().reindex(zones.zone_id).fillna(0)
low = s[s < 0.99]
lost_ha = ((1 - low) * zones.set_index("zone_id").zone_ha.reindex(low.index)).sum()
print(f"rows: {len(out)}; zones: {out.zone_id.nunique()} of {len(zones)}; "
      f"municipalities: {out.cd_mun.nunique()}")
print(f"zones with shares summing to < 0.99: {len(low)} (uncovered area {lost_ha:,.0f} ha; "
      f"expected: border/offshore zones only, ~86 kha)")
print("written", args.out)
