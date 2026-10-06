"""
product1_summary.py — Executive summary of Product 1 (D13) and of the fire section of
Product 2 (D15, descriptive only), in Portuguese, for the MMA
Biodiversity Directorate. One self-contained HTML page; every number is computed here from
the same tables as the fact sheets, so the summary and the sheets cannot disagree.

Inputs
  data/derived/product1/calibration_units.csv    categories, rates, flags per unit
  data/derived/product1/calibration_matrix.csv   same metrics for the matrix by biome
  data/interim/extract/p1_transitions.parquet    direct transitions 2012 -> 2025 (drivers)
  data/derived/zones_attributes.csv, data/interim/zones_upload.zip (unit geometry for the map)
  data/raw/biomas_2019/lm_bioma_250.shp, data/raw/uf/BR_UF_2025.shp (map context)
  data/reference/mapbiomas_col11_legend_groups.csv
  Fire section (Product 2, D15; descriptive only):
  data/derived/product2/units_fire.csv, units_fire_months.csv, matrix_regime.csv, matrix_fire.csv
  data/interim/extract/fire_regime_lat.parquet (optional: matrix reference standardized by
      latitude band; without it the reference is the single Cerrado + Pantanal matrix and the
      page says so)
Output
  data/derived/product1/sumario_executivo.html

Run from the repository root:   python scripts/analysis/product1_summary.py

Conventions
  - "Taxa agregada" (pooled rate) = sum of the units' Theil-Sen trends in hectares divided by
    the sum of their 2012 natural vegetation, per year. It weights large areas more than the
    median does; both are shown where they differ.
  - Interpretive sentences are tagged [E] (computed) or [H] (interpretation to be tested), as
    in the rest of the project. Proposals for the next cycle are marked as proposals.

What can break, and how you would notice:
  - Missing raw layers (biomes/UF): the map is drawn without context lines and a warning is
    printed.
  - Category or label names changing in calibration_units.csv: KeyError in CAT_PT / ACTION
    grouping. Re-run product1_calibration.py first.
"""
import base64
import html
import io
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "data/derived/product1"
EXT = ROOT / "data/interim/extract"
Y0, YS, Y1 = 2012, 2018, 2025
NY = Y1 - Y0
esc = html.escape

CATS = ["net gain", "stable", "turnover", "moderate loss", "intense loss", "very intense loss"]
CAT_PT = {"net gain": "Ganho líquido", "stable": "Estável", "turnover": "Rotatividade",
          "moderate loss": "Perda moderada", "intense loss": "Perda intensa", "very intense loss": "Perda muito intensa"}
# Ordinal colours: blue = gain, greys = no net change, oranges/reds = loss of increasing
# intensity. Every use is paired with a printed label or a table, never colour alone.
CAT_COL = {"net gain": "#2a78d6", "stable": "#b9b7af", "turnover": "#7d7c76",
           "moderate loss": "#f2a37f", "intense loss": "#e0533f", "very intense loss": "#8f1d1d"}
DRIVER_PT = {"pasture": "Pastagem", "soybean": "Soja", "other crops": "Outras lavouras",
             "mosaic of uses": "Mosaico de usos", "forest plantation": "Silvicultura", "mining": "Mineração",
             "urban": "Área urbana", "other non-vegetated": "Outras áreas não vegetadas",
             "aquaculture": "Aquicultura", "energy": "Energia"}
DRIVER = {15: "pasture", 39: "soybean", 20: "other crops", 40: "other crops", 41: "other crops",
          62: "other crops", 46: "other crops", 47: "other crops", 48: "other crops", 35: "other crops",
          21: "mosaic of uses", 9: "forest plantation", 30: "mining", 24: "urban",
          25: "other non-vegetated", 31: "aquaculture", 75: "energy", 91: "energy"}


def fnum(v, d=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    s = f"{v:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def fsig(v, d=2):
    return ("+" if v > 0 else "") + fnum(v, d)


def action_group(a):
    """Main action -> a small set of groups (MMA codes and hybrid free text differ)."""
    a = str(a).lower()
    if "uc" in a.split() or "criacao uc" in a or "criação de uc" in a or "criacao de uc" in a or "unidade de conserva" in a or a.startswith("criacao"):
        return "Criação ou ampliação de UC"
    for k, g in (("recupera", "Recuperação"), ("car", "CAR – boas práticas"), ("fomento", "Fomento ao uso sustentável"),
                 ("corredor", "Corredor / mosaico"), ("fiscaliza", "Fiscalização e controle"), ("ordenamento", "Ordenamento territorial")):
        if k in a:
            return g
    return "Outras"


# --- Data ------------------------------------------------------------------------------------
u = pd.read_csv(P1 / "calibration_units.csv", dtype={"unit": str}).set_index("unit")
mx = pd.read_csv(P1 / "calibration_matrix.csv").set_index("unit")
u["acao_grupo"] = u.Acao1.map(action_group)
u["uf_main"] = u.Estados.astype(str).str.split(",").str[0].str.strip()


def pooled(d, col="net_ha"):
    """Pooled rate, % per year of the 2012 natural vegetation."""
    return d[col].sum() / NY / d.nat_ha_2012.sum() * 100


def pooled_sub(d, col):
    return (d[col] * d.nat_ha_2012).sum() / d.nat_ha_2012.sum()


N = len(u)
nat12, nat25, land = u.nat_ha_2012.sum(), u.nat_ha_2025.sum(), u.land_ha_2012.sum()
rate_all = pooled(u)
r1, r2 = pooled_sub(u, "rate_2012_2018"), pooled_sub(u, "rate_2018_2025")
cat_n = u.category.value_counts().reindex(CATS).fillna(0).astype(int)
cat_nat = u.groupby("category").nat_ha_2012.sum().reindex(CATS).fillna(0)
n_loss = int(cat_n[["moderate loss", "intense loss", "very intense loss"]].sum())
n_acc = int(u.flag_acceleration.sum())
mcer = mx.loc["OUTSIDE|Cerrado"]

lg = pd.read_csv(ROOT / "data/reference/mapbiomas_col11_legend_groups.csv")
NAT = set(lg.loc[lg.level1_code.isin([1, 2]), "pixel_id"].astype(int))
ANT = set(lg.loc[lg.nature.isin(["anthropic", "ambiguous"]), "pixel_id"].astype(int))
z = pd.read_csv(ROOT / "data/derived/zones_attributes.csv")
z["unit"] = z.ap2012_code.where(z.ap2012_code != "none", z.hybrid_code).str.replace(".0", "", regex=False)
dt = pd.read_parquet(EXT / "p1_transitions.parquet").query("start == @Y0 and end == @Y1")
dt = dt.merge(z[["zone_id", "unit"]], on="zone_id")
dt = dt[dt.unit.isin(u.index) & dt.class_start.isin(NAT) & dt.class_end.isin(ANT)]
drivers = dt.assign(d=dt.class_end.map(DRIVER).fillna("other")).groupby("d").ha.sum().sort_values(ascending=False)


# --- Charts (inline SVG) ------------------------------------------------------------------------
def svg_stacked(groups, title):
    """100% stacked bars of categories (share of units) for each group, with counts on hover
    and the count table printed below."""
    W, l, r, rowh = 880, 250, 20, 34
    H = rowh * len(groups) + 10
    g = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="{esc(title)}">']
    for i, (lab, d) in enumerate(groups):
        y = 5 + i * rowh
        cnt = d.category.value_counts().reindex(CATS).fillna(0)
        tot = cnt.sum(); x = l
        g.append(f'<text x="{l - 10}" y="{y + 19}" class="tick" text-anchor="end">{esc(lab)} ({int(tot)})</text>')
        for c in CATS:
            w = (W - l - r) * cnt[c] / tot if tot else 0
            if w <= 0:
                continue
            g.append(f'<rect x="{x:.1f}" y="{y + 4}" width="{max(w - 2, 0.5):.1f}" height="22" fill="{CAT_COL[c]}">'
                     f'<title>{esc(lab)} · {CAT_PT[c]}: {int(cnt[c])} áreas ({fnum(cnt[c] / tot * 100, 0)}%)</title></rect>')
            if w > 34:
                txtcol = "#fff" if c in ("turnover", "intense loss", "very intense loss", "net gain") else "#1a1a19"
                g.append(f'<text x="{x + w / 2 - 1:.1f}" y="{y + 19}" text-anchor="middle" class="seg" fill="{txtcol}">{int(cnt[c])}</text>')
            x += w
    g.append("</svg>")
    return "".join(g)


def legend_cats():
    return '<ul class="leg">' + "".join(f'<li><span class="sw" style="background:{CAT_COL[c]}"></span>{CAT_PT[c]}</li>' for c in CATS) + "</ul>"


def svg_dumbbell(rows):
    """Pooled net rate 2012-2018 vs 2018-2025 per group: shows acceleration and the absence
    of a gradient by importance class in one view. Negative = loss."""
    W, l, r, rowh = 880, 230, 30, 30
    H = rowh * len(rows) + 40
    vals = [v for _, a, b, _ in rows for v in (a, b)]
    lo, hi = min(min(vals), -1.2) - 0.1, 0.1
    X = lambda v: l + (v - lo) / (hi - lo) * (W - l - r)
    g = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Taxa agregada por subperíodo">']
    for v in np.arange(np.ceil(lo * 4) / 4, hi + 1e-9, 0.25):
        g.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="6" y2="{H - 28}" class="{"zero" if abs(v) < 1e-9 else "grid"}"/>'
                 f'<text x="{X(v):.1f}" y="{H - 10}" class="tick" text-anchor="middle">{fnum(v, 2)}</text>')
    for i, (lab, a, b, sep) in enumerate(rows):
        y = 18 + i * rowh
        if sep:
            g.append(f'<line x1="10" x2="{W - r}" y1="{y - 15}" y2="{y - 15}" class="sep"/>')
        g.append(f'<text x="{l - 12}" y="{y + 4}" class="tick" text-anchor="end">{esc(lab)}</text>'
                 f'<line x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{y}" y2="{y}" class="db"/>'
                 f'<circle cx="{X(a):.1f}" cy="{y}" r="5.5" class="p1"><title>{esc(lab)} 2012–2018: {fnum(a, 2)}%/ano</title></circle>'
                 f'<circle cx="{X(b):.1f}" cy="{y}" r="5.5" class="p2"><title>{esc(lab)} 2018–2025: {fnum(b, 2)}%/ano</title></circle>')
    g.append("</svg>")
    return "".join(g)


def svg_hbars(items, unit="Mha", div=1e6, d=2):
    W, rowh, l, r = 880, 26, 190, 110
    H = rowh * len(items) + 6
    mx_ = max(v for _, v in items)
    g = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img">']
    for i, (k, v) in enumerate(items):
        y = 3 + i * rowh; w = max((W - l - r) * v / mx_, 2)
        g.append(f'<text x="{l - 8}" y="{y + 16}" class="tick" text-anchor="end">{esc(k)}</text>'
                 f'<rect x="{l}" y="{y + 4}" width="{w:.1f}" height="16" rx="3" class="bar"><title>{esc(k)}: {fnum(v / div, d)} {unit}</title></rect>'
                 f'<text x="{l + w + 6:.1f}" y="{y + 16}" class="val">{fnum(v / div, d)} {unit} · {fnum(v / sum(x for _, x in items) * 100, 0)}%</text>')
    g.append("</svg>")
    return "".join(g)


def map_svg(colour=None, tip_fn=None, label="Mapa interativo das áreas por categoria de dinâmica"):
    """Interactive map of the units coloured by dynamics category: every area is a link to its
    fact sheet (ficha_<unit>.html) with a hover tooltip, plus a scale bar. Inline SVG in the
    South America Albers Equal Area projection, so the scale bar is exact. Geometries are
    simplified (1.5 km for the areas, 3 km for context lines), which is invisible at page size."""
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, Polygon
    zz = gpd.read_file(ROOT / "data/interim/zones_upload.zip").merge(z[["zone_id", "unit"]], on="zone_id")
    zz = zz[zz.unit.isin(u.index)].dissolve("unit").to_crs("ESRI:102033")
    zz["geometry"] = zz.geometry.simplify(1500, preserve_topology=True)
    ctx = []
    try:
        bm = gpd.read_file(ROOT / "data/raw/biomas_2019/lm_bioma_250.shp").to_crs("ESRI:102033")
        bm = bm[bm.Bioma.isin(["Cerrado", "Pantanal"])]
        bm["geometry"] = bm.geometry.simplify(3000)
        uf = gpd.read_file(ROOT / "data/raw/uf/BR_UF_2025.shp").to_crs("ESRI:102033")
        uf["geometry"] = uf.geometry.simplify(3000)
        ctx = [(bm, "biome"), (uf, "uf")]
    except Exception as e:  # context layers are optional
        print("WARNING: map context not drawn:", e)
    xmin, ymin, xmax, ymax = zz.total_bounds
    pad = (xmax - xmin) * 0.03
    xmin, xmax, ymin, ymax = xmin - pad, xmax + pad, ymin - pad, ymax + pad
    W = 900.0
    k = W / (xmax - xmin)
    H = (ymax - ymin) * k

    def path(geom):
        if isinstance(geom, Polygon):
            polys = [geom]
        elif hasattr(geom, "geoms"):   # MultiPolygon or GeometryCollection: keep the polygon parts
            polys = [p for gg in geom.geoms for p in (gg.geoms if isinstance(gg, MultiPolygon) else [gg]) if isinstance(p, Polygon)]
        else:
            polys = []
        d = []
        for pg in polys:
            for ring in [pg.exterior, *pg.interiors]:
                pts = [f"{(x - xmin) * k:.1f},{(ymax - y) * k:.1f}" for x, y, *_ in ring.coords]
                if len(pts) > 2:
                    d.append("M" + "L".join(pts) + "Z")
        return "".join(d)

    g = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="catmap" role="img" aria-label="{esc(label)}">']
    for gdf, cls in ctx:
        for geom in gdf.geometry:
            if cls == "biome":
                g.append(f'<path class="ctx-biome" d="{path(geom)}"/>')
            else:
                g.append(f'<path class="ctx-uf" d="{path(geom)}"/>')
    for unit, row in zz.iterrows():
        m = u.loc[unit]
        name = "Área híbrida" if m.is_hybrid else str(m.NOME)
        tip = (tip_fn(unit, name) if tip_fn else
               f"{name} ({unit}) · {CAT_PT[m.category]} · {fnum(m.rate, 2)}%/ano · vegetação natural 2025: {fnum(m.nat_share_2025 * 100, 0)}%")
        fill = colour(unit) if colour else CAT_COL[m.category]
        g.append(f'<a href="ficha_{esc(unit)}.html" aria-label="{esc(tip)}"><path class="unit" fill="{fill}" '
                 f'fill-rule="evenodd" d="{path(row.geometry)}"><title>{esc(tip)}</title></path></a>')
    # Scale bar (Albers metres): 200 km
    L = 200000 * k
    x0, y0 = 24, H - 28
    g.append(f'<g class="scale"><rect x="{x0}" y="{y0}" width="{L / 2:.1f}" height="6" class="s1"/>'
             f'<rect x="{x0 + L / 2:.1f}" y="{y0}" width="{L / 2:.1f}" height="6" class="s2"/>'
             f'<text x="{x0}" y="{y0 - 6}" class="st">0</text><text x="{x0 + L / 2:.1f}" y="{y0 - 6}" class="st" text-anchor="middle">100</text>'
             f'<text x="{x0 + L:.1f}" y="{y0 - 6}" class="st" text-anchor="middle">200 km</text></g>')
    g.append("</svg>")
    return "".join(g)


# --- Tables ---------------------------------------------------------------------------------------
def group_table(col, order=None, label=""):
    rows = []
    keys = order or u[col].value_counts().index.tolist()
    for k in keys:
        d = u[u[col] == k]
        if not len(d):
            continue
        cnt = d.category.value_counts()
        rows.append(f"<tr><td>{esc(str(k))}</td><td>{len(d)}</td><td>{fnum(d.nat_ha_2012.sum() / 1e6, 2)}</td>"
                    f"<td>{fnum(d.nat_ha_2025.sum() / d.land_ha_2012.sum() * 100, 0)}%</td>"
                    f"<td>{fnum(pooled(d), 2)}</td><td>{fnum(d.rate.median(), 2)}</td>"
                    f"<td>{int(cnt.get('intense loss', 0) + cnt.get('very intense loss', 0))}</td>"
                    f"<td>{int(d.flag_acceleration.sum())}</td></tr>")
    return (f'<table class="num"><thead><tr><th>{esc(label)}</th><th>Áreas</th><th>Vegetação natural 2012 (Mha)</th>'
            '<th>Vegetação natural 2025</th><th>Taxa agregada (%/ano)</th><th>Mediana (%/ano)</th>'
            '<th>Perda intensa ou muito intensa</th><th>Com aceleração</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


hl = u[u.category.isin(["very intense loss", "intense loss"])].sort_values("rate").head(20)
hl_rows = "".join(
    f'<tr><td><a href="ficha_{esc(k)}.html">{esc(k)}</a></td><td><a href="ficha_{esc(k)}.html">{esc("Área híbrida" if m.is_hybrid else str(m.NOME))}</a></td><td>{esc(str(m.Estados))}</td>'
    f'<td>{esc(str(m.Import_bio))}</td><td>{fnum(m.nat_share_2012 * 100, 0)}% → {fnum(m.nat_share_2025 * 100, 0)}%</td>'
    f'<td>{fnum(m.rate, 2)}</td><td>{"sim" if m.flag_acceleration else ""}</td><td>{esc(DRIVER_PT.get(m.driver, str(m.driver)))}</td></tr>'
    for k, m in hl.iterrows())
big_stable = u[(u.category == "stable") & (u.nat_share_2025 >= 0.8)].sort_values("nat_ha_2025", ascending=False)
frontier = u[(u.nat_share_2025 >= 0.5) & u.category.isin(["intense loss", "very intense loss"])]

imp_order = ["Extremamente Alta", "Muito Alta", "Alta"]
dumb = ([("Todas as áreas (348)", r1, r2, False)]
        + [(f"Importância {k.lower()}", pooled_sub(u[u.Import_bio == k], "rate_2012_2018"), pooled_sub(u[u.Import_bio == k], "rate_2018_2025"), i == 0) for i, k in enumerate(imp_order)]
        + [(f"Prioridade {k.lower()}", pooled_sub(u[u.Prior_acao == k], "rate_2012_2018"), pooled_sub(u[u.Prior_acao == k], "rate_2018_2025"), i == 0) for i, k in enumerate(imp_order)]
        + [("Áreas MMA (294)", pooled_sub(u[~u.is_hybrid], "rate_2012_2018"), pooled_sub(u[~u.is_hybrid], "rate_2018_2025"), True),
           ("Áreas híbridas (54)", pooled_sub(u[u.is_hybrid], "rate_2012_2018"), pooled_sub(u[u.is_hybrid], "rate_2018_2025"), False),
           ("Matriz fora das APs, Cerrado", mcer.rate_2012_2018, mcer.rate_2018_2025, True)])

soy = drivers.get("soybean", 0) / drivers.sum() * 100
past = drivers.get("pasture", 0) / drivers.sum() * 100
mos = drivers.get("mosaic of uses", 0) / drivers.sum() * 100
imp = u.groupby("Import_bio").apply(pooled)
MATOPIBA = {"MA", "TO", "PI", "BA"}
n_front_matopiba = int((frontier.uf_main.isin(MATOPIBA) & ~frontier.is_hybrid).sum())   # MMA areas only; hybrids counted apart
n_front_hyb_amz = int(frontier.index.str.startswith("AMZ").sum())
vi = u[u.category == "very intense loss"]
n_vi_hyb = int(vi.is_hybrid.sum())
vi_mma = vi[~vi.is_hybrid]
n_vi_mma_soy = int((vi_mma.driver == "soybean").sum())

# --- Fire (Product 2, D15): descriptive only ------------------------------------------------------
P2 = ROOT / "data/derived/product2"
F = pd.read_csv(P2 / "units_fire.csv", dtype={"unit": str}).set_index("unit")
for c_ in ("flag_below", "flag_above", "flag_forest"):
    F[c_] = F[c_].fillna("none")
F = F.join(u[["category", "uf_main"]])
FMON = pd.read_csv(P2 / "units_fire_months.csv", dtype={"unit": str})
MREG = pd.read_csv(P2 / "matrix_regime.csv").set_index(["type", "cls"])
MFIRE = pd.read_csv(P2 / "matrix_fire.csv").set_index(["latband", "subperiod"])
BAND_PT = {0: "ao sul de 18°S", 1: "18°S a 12°S", 2: "12°S a 8°S", 3: "ao norte de 8°S"}
# Category colours as in the fact sheets: warm = above expected / forest affected, cool = below.
FC_ABOVE, FC_MID, FC_BELOW = "#c4561d", "#c9c6bd", "#3b6fb6"

# Matrix reference standardized by latitude band (D15; summary): for a group of units, the
# matrix share of each class in each latitude band, weighted by the group's own stable area
# in that band, so that a northern group is compared with the northern matrix.
FLAT = None
_flp = EXT / "fire_regime_lat.parquet"
if _flp.exists():
    FLAT = pd.read_parquet(_flp)
    _zb = z[["zone_id", "unit", "biome_2019"]].copy()
    FLAT = FLAT.merge(_zb, on="zone_id")
    FLAT["inside"] = FLAT.unit.isin(u.index)
    _mat = FLAT[~FLAT.inside & FLAT.biome_2019.isin(["Cerrado", "Pantanal"])]
    MBAND = (_mat.groupby(["latband", "type", "cls"]).stable_ha.sum()
             / _mat.groupby(["latband", "type"]).stable_ha.sum())          # matrix share per band
    ABAND = FLAT[FLAT.inside].groupby(["unit", "latband", "type"]).stable_ha.sum()


def ref_share(units_, types, cls):
    """Matrix share of class `cls` (types pooled) as reference for a group of units."""
    if FLAT is None:
        num = sum(MREG.loc[(t, cls)].ha for t in types if (t, cls) in MREG.index)
        den = sum(MREG.loc[t].ha.sum() for t in types)
        return num / den
    a = ABAND[ABAND.index.get_level_values("unit").isin(units_)]
    a = a[a.index.get_level_values("type").isin(types)].groupby(level=["latband", "type"]).sum()
    if a.sum() <= 0:
        return np.nan
    w = [(v, MBAND.get((lb, t, cls), 0.0)) for (lb, t), v in a.items()]
    return sum(v * m for v, m in w) / sum(v for v, _ in w)


def fgroup(d):
    """Area-weighted fire composition of a group of units."""
    oh, fh = d.open_ha.fillna(0), d.forest_ha.fillna(0)
    return {"n": len(d), "open_mha": oh.sum() / 1e6,
            "above": (d.open_above.fillna(0) * oh).sum() / oh.sum() if oh.sum() else np.nan,
            "below": (d.open_below.fillna(0) * oh).sum() / oh.sum() if oh.sum() else np.nan,
            "forest": (d.forest_affected.fillna(0) * fh).sum() / fh.sum() if fh.sum() else np.nan,
            "ref_above": ref_share(d.index, (2, 3), 1), "ref_below": ref_share(d.index, (2, 3), 3),
            "ref_forest": ref_share(d.index, (1,), 2),
            "nb": int(d.flag_below.isin(["robust", "threshold"]).sum()), "nbr": int((d.flag_below == "robust").sum()),
            "na": int(d.flag_above.isin(["robust", "threshold"]).sum()), "nar": int((d.flag_above == "robust").sum()),
            "nf": int(d.flag_forest.isin(["robust", "threshold"]).sum()), "nfr": int((d.flag_forest == "robust").sum())}


def svg_fire_groups(groups):
    """100% stacked bars (area-weighted) of above / as expected / below for stable savanna +
    grassland, each group followed by its matrix reference (lighter)."""
    W, l, r, rowh = 880, 250, 10, 26
    rows = []
    for lab, d in groups:
        g_ = fgroup(d)
        rows.append((f"{lab} ({g_['n']})", (g_["above"], 1 - g_["above"] - g_["below"], g_["below"]), False))
        rows.append(("matriz de referência", (g_["ref_above"], 1 - g_["ref_above"] - g_["ref_below"], g_["ref_below"]), True))
    H = rowh * len(rows) + 6
    g = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Regime de fogo por grupo">']
    for i, (lab, sh, muted) in enumerate(rows):
        y = 3 + i * rowh + (4 if muted else 0)
        h = 14 if muted else 20
        g.append(f'<text x="{l - 10}" y="{y + h - 4}" class="tick{" mut" if muted else ""}" text-anchor="end">{esc(lab)}</text>')
        x = l
        for v, col, nm in zip(sh, (FC_ABOVE, FC_MID, FC_BELOW), ("acima do esperado", "de acordo", "abaixo do esperado")):
            w = (W - l - r) * (0 if np.isnan(v) else v)
            if w <= 0:
                continue
            g.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 1, .5):.1f}" height="{h}" fill="{col}"{" opacity=.5" if muted else ""}>'
                     f'<title>{esc(lab)} · {nm}: {fnum(v * 100, 1)}%</title></rect>')
            if w > 34 and not muted:
                g.append(f'<text x="{x + w / 2:.1f}" y="{y + 15}" class="seg" text-anchor="middle" fill="{"#fff" if col != FC_MID else "#1a1a19"}">{fnum(v * 100, 0)}%</text>')
            x += w
    g.append("</svg>")
    return "".join(g)


def fire_table(groups, label):
    rows = []
    for lab, d in groups:
        g_ = fgroup(d)
        rows.append(f"<tr><td>{esc(lab)}</td><td>{g_['n']}</td><td>{fnum(g_['open_mha'], 2)}</td>"
                    f"<td>{fnum(g_['above'] * 100, 0)}%&nbsp;<span class='ref'>({fnum(g_['ref_above'] * 100, 0)}%)</span></td>"
                    f"<td>{fnum(g_['below'] * 100, 0)}%&nbsp;<span class='ref'>({fnum(g_['ref_below'] * 100, 0)}%)</span></td>"
                    f"<td>{fnum(g_['forest'] * 100, 0)}%&nbsp;<span class='ref'>({fnum(g_['ref_forest'] * 100, 0)}%)</span></td>"
                    f"<td>{g_['nbr']} + {g_['nb'] - g_['nbr']}</td><td>{g_['nar']} + {g_['na'] - g_['nar']}</td><td>{g_['nfr']} + {g_['nf'] - g_['nfr']}</td></tr>")
    return (f'<table class="num"><thead><tr><th>{esc(label)}</th><th>Áreas</th><th>Savana e campo estáveis (Mha)</th>'
            '<th>Acima do esperado</th><th>Abaixo do esperado</th><th>Floresta afetada</th>'
            '<th>Áreas &gt; 50% abaixo</th><th>Áreas &gt; 20% acima</th><th>Áreas &gt; 50% floresta afetada</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


FALL = fgroup(F)
UFG = {k: fgroup(F[F.uf_main == k]) for k in ("MA", "TO", "MG")}
F_ok = F[F.open_ha >= 1000]
bf1 = (F_ok.sp1_burned_frac_yr * F_ok.open_ha).sum() / F_ok.open_ha.sum()
bf2 = (F_ok.sp2_burned_frac_yr * F_ok.open_ha).sum() / F_ok.open_ha.sum()
n_up = int(((F_ok.sp2_burned_frac_yr > 1.5 * F_ok.sp1_burned_frac_yr) & (F_ok.sp2_burned_frac_yr > 0.02)).sum())
n_dn = int(((F_ok.sp2_burned_frac_yr < F_ok.sp1_burned_frac_yr / 1.5) & (F_ok.sp1_burned_frac_yr > 0.02)).sum())
_j = F_ok.dropna(subset=["sp1_julaug", "sp2_julaug"])
band_rows = []
for lb in range(4):
    d = _j[_j.latband == lb]
    dd = d.sp2_julaug - d.sp1_julaug
    band_rows.append(f"<tr><td>{BAND_PT[lb]}</td><td>{len(d)}</td><td>{fnum(d.sp1_julaug.median() * 100, 0)}%</td><td>{fnum(d.sp2_julaug.median() * 100, 0)}%</td>"
                     f"<td>{int((dd > .10).sum())}</td><td>{int((dd < -.10).sum())}</td>"
                     f"<td>{fnum(MFIRE.loc[(lb, 'sp1')].julaug * 100, 0)}% → {fnum(MFIRE.loc[(lb, 'sp2')].julaug * 100, 0)}%</td></tr>")
n_j_up = int(((_j.sp2_julaug - _j.sp1_julaug) > .10).sum()); n_j_dn = int(((_j.sp2_julaug - _j.sp1_julaug) < -.10).sum())

# Fire flags x dynamics category (Product 1), counts
def _lvl(f):
    return {"robust": "robusto", "threshold": "depende do limiar"}.get(f, "")
xt_rows = []
for c in CATS:
    d = F[F.category == c]
    xt_rows.append(f"<tr><td>{CAT_PT[c]}</td><td>{len(d)}</td><td>{int((d.flag_below == 'robust').sum())}</td><td>{int((d.flag_below == 'threshold').sum())}</td>"
                   f"<td>{int((d.flag_above == 'robust').sum())}</td><td>{int((d.flag_above == 'threshold').sum())}</td><td>{int(d.flag_forest.isin(['robust', 'threshold']).sum())}</td></tr>")
ab_r = F[F.flag_above == "robust"]
n_ab_r_loss = int(ab_r.category.isin(["intense loss", "very intense loss"]).sum())


def fname(k):
    m = u.loc[k]
    return "Área híbrida" if m.is_hybrid else str(m.NOME)


def list_rows(d, cols):
    out = []
    for k, f in d.iterrows():
        cells = "".join(c_(f) for c_ in cols)
        out.append(f'<tr><td><a href="ficha_{esc(k)}.html">{esc(k)}</a></td><td><a href="ficha_{esc(k)}.html">{esc(fname(k))}</a></td>'
                   f'<td>{esc(str(u.loc[k].Estados))}</td>{cells}</tr>')
    return "".join(out)


ab_list = list_rows(ab_r.sort_values("open_above", ascending=False),
                    [lambda f: f"<td>{fnum(f.open_ha / 1e3, 1)}</td>", lambda f: f"<td>{fnum(f.open_above * 100, 0)}%</td>",
                     lambda f: f"<td>{fnum(f.open_above_annual_only * 100, 0)}%</td>", lambda f: f"<td>{CAT_PT.get(f.category, '')}</td>"])
be_r = F[F.flag_below == "robust"].sort_values("open_ha", ascending=False).head(20)
be_list = list_rows(be_r, [lambda f: f"<td>{fnum(f.open_ha / 1e3, 1)}</td>", lambda f: f"<td>{fnum(f.open_below * 100, 0)}%</td>",
                           lambda f: f"<td>{fnum(f.open_below_n25 * 100, 0)}%</td>", lambda f: f"<td>{CAT_PT.get(f.category, '')}</td>"])
fo = F[F.flag_forest.isin(["robust", "threshold"])].sort_values("forest_affected", ascending=False)
fo_list = list_rows(fo, [lambda f: f"<td>{fnum(f.forest_ha / 1e3, 1)}</td>", lambda f: f"<td>{fnum(f.forest_affected * 100, 0)}%</td>",
                         lambda f: f"<td>{_lvl(f.flag_forest)}</td>"])

FIRE_MAP_COL = {"above_r": FC_ABOVE, "above_t": "#eba67e", "below_r": FC_BELOW, "below_t": "#9fbbe2",
                "none": "#c6c1b3", "small": "#ffffff"}
FIRE_MAP_PT = {"above_r": "Acima do esperado > 20%, robusto", "above_t": "Acima do esperado > 20%, depende do limiar",
               "below_r": "Abaixo do esperado > 50%, robusto", "below_t": "Abaixo do esperado > 50%, depende do limiar",
               "none": "Sem sinalização nos extremos", "small": "Savana e campo estáveis < 1.000 ha"}


def fire_class(k):
    f = F.loc[k]
    if f.flag_above in ("robust", "threshold"):          # 2 units carry both flags: shown as above, both in the tooltip
        return "above_r" if f.flag_above == "robust" else "above_t"
    if f.flag_below in ("robust", "threshold"):
        return "below_r" if f.flag_below == "robust" else "below_t"
    return "small" if f.flag_below == "small" else "none"


def fire_tip(k, name):
    f = F.loc[k]
    t = (f"{name} ({k}) · savana e campo estáveis {fnum(f.open_ha)} ha: acima {fnum(f.open_above * 100, 0)}%, "
         f"abaixo {fnum(f.open_below * 100, 0)}%")
    if not np.isnan(f.forest_affected):
        t += f" · floresta afetada {fnum(f.forest_affected * 100, 0)}%"
    return t


fire_cls_n = pd.Series({k: fire_class(k) for k in F.index}).value_counts()
REF_NOTE = ("Entre parênteses, a matriz de referência: vegetação estável do Cerrado e do Pantanal fora das áreas prioritárias, "
            "<b>ponderada pela faixa de latitude</b> de cada grupo (ao sul de 18°S, 18–12°S, 12–8°S, ao norte de 8°S), para que um grupo do norte "
            "seja comparado com a matriz do norte." if FLAT is not None else
            "Entre parênteses, a matriz de referência: vegetação estável do Cerrado e do Pantanal fora das áreas prioritárias, "
            "<b>sem ponderação por latitude</b> (versão provisória).")

# --- Page ------------------------------------------------------------------------------------------
CSS = '''
:root{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6b6a66;--rule:#e4e2dc;--grid:#ecebe7;--card:#f4f3ef;
--main:#2a78d6;--p1:#9ec5f4;--p2:#184f95;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#a3a29a;
--rule:#383835;--grid:#2a2a28;--card:#242422;--main:#3987e5;--p1:#5598e7;--p2:#cde2fb;color-scheme:dark}}
:root[data-theme="dark"]{--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#a3a29a;--rule:#383835;--grid:#2a2a28;--card:#242422;
--main:#3987e5;--p1:#5598e7;--p2:#cde2fb;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:940px;margin:0 auto;padding:28px 16px 72px}
.eyebrow{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:0}
h1{font-size:28px;line-height:1.2;margin:6px 0 8px}h2{font-size:20px;margin:40px 0 6px;padding-top:12px;border-top:1px solid var(--rule)}
h3{font-size:16px;margin:22px 0 4px}p{margin:6px 0 10px}.muted{color:var(--muted);font-size:13px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border-radius:8px;padding:12px 14px}.kpi b{display:block;font-size:28px;line-height:1.1;margin:4px 0}
.kpi span{font-size:12px;color:var(--muted)}.kpi small{font-size:13px;color:var(--ink2)}
.keys{background:var(--card);border-radius:8px;padding:6px 20px 6px 32px}.keys li{margin:8px 0}
.box{border-left:4px solid var(--rule);padding:4px 14px;margin:12px 0;color:var(--ink2);font-size:14px}
table.num{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}
table.num th,table.num td{padding:5px 8px;border-bottom:1px solid var(--rule);text-align:right;vertical-align:top}
table.num th:first-child,table.num td:first-child,table.num.l td,table.num.l th{text-align:left}
table.num thead th{font-weight:600;color:var(--ink2);font-size:12px}
.wrap{overflow-x:auto}
.chart{width:100%;height:auto;display:block}.chart .tick{fill:var(--muted);font-size:12px}.chart .val{fill:var(--ink2);font-size:12px}
.chart .seg{font-size:12px;font-weight:600}.chart .grid{stroke:var(--grid)}.chart .zero{stroke:var(--muted)}
.chart .sep{stroke:var(--rule);stroke-dasharray:2 3}.chart .db{stroke:var(--muted);stroke-width:2}
.chart .p1{fill:var(--p1);stroke:var(--surface);stroke-width:2}.chart .p2{fill:var(--p2);stroke:var(--surface);stroke-width:2}
.chart .bar{fill:var(--main)}
.leg{list-style:none;display:flex;flex-wrap:wrap;gap:6px 16px;padding:0;margin:6px 0;font-size:13px}
.leg .sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.leg .dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}
img.map{width:100%;max-width:720px;display:block;margin:0 auto;border-radius:6px}
table.hl td:nth-child(-n+4),table.hl th:nth-child(-n+4),table.hl td:nth-child(8),table.hl th:nth-child(8){text-align:left}
nav.topnav{font-size:13px;margin-bottom:12px}nav.topnav a{color:var(--main);margin-right:16px}
.mapframe{border:1px solid var(--rule);border-radius:6px;background:#fff;padding:4px;max-width:760px;margin:0 auto}
.catmap{width:100%;height:auto;display:block}.catmap .ctx-biome{fill:#f1efe9;stroke:#9a988f;stroke-width:.8}
.catmap .ctx-uf{fill:none;stroke:#c9c6bd;stroke-width:.5}.catmap .unit{stroke:#fff;stroke-width:.4;cursor:pointer}
.catmap a:hover .unit,.catmap a:focus .unit{stroke:#111;stroke-width:1.6}.catmap a:focus{outline:none}
.catmap .s1{fill:#222}.catmap .s2{fill:#fff;stroke:#222;stroke-width:1}.catmap .st{font-size:11px;fill:#222}
table.hl a,p a,table.hl2 a,.box a{color:var(--main)}
table.hl2 td:nth-child(-n+3),table.hl2 th:nth-child(-n+3),table.hl2 td:last-child,table.hl2 th:last-child{text-align:left}
.ref{color:var(--muted);font-size:12px;white-space:nowrap}.chart .tick.mut{font-style:italic;font-size:11px}
details{margin:10px 0}summary{cursor:pointer}
footer{border-top:1px solid var(--rule);margin-top:40px;font-size:12px;color:var(--muted)}
'''

body = f'''
<nav class="topnav"><a href="index.html">Índice das fichas</a></nav>
<p class="eyebrow">Subsídio ao novo ciclo de revisão das Áreas Prioritárias para a Conservação</p>
<h1>Áreas Prioritárias do Cerrado e Pantanal: estado e dinâmica da vegetação natural (2012–2025) e fogo (1985–2025)</h1>
<p class="muted">Sumário executivo · 2ª atualização (Portarias MMA 223/2016 e 463/2018) · {N} áreas: 294 da camada MMA e 54 áreas híbridas · MapBiomas Coleção 11</p>

<div class="box"><b>O que este diagnóstico é e o que não é.</b> Descreve o estado da vegetação natural nas áreas prioritárias e como ela mudou desde 2012, ano em que as áreas foram desenhadas. <b>Não avalia a eficácia</b> das áreas como política pública: para isso seria preciso comparar com áreas equivalentes não designadas. O fogo na vegetação natural estável é apresentado <a href="#fogo">em seção própria</a>, de forma descritiva. Degradação não está incluída nesta versão.</div>

<section class="kpis">
  <div class="kpi"><span>Vegetação natural nas áreas</span><b>{fnum(nat12 / land * 100, 0)}% → {fnum(nat25 / land * 100, 0)}%</b><small>{fnum(nat12 / 1e6, 1)} → {fnum(nat25 / 1e6, 1)} Mha, 2012 → 2025</small></div>
  <div class="kpi"><span>Taxa agregada 2012–2025</span><b>{fnum(rate_all, 2)}%/ano</b><small>da vegetação natural de 2012</small></div>
  <div class="kpi"><span>Aceleração</span><b>{fnum(r1, 2)} → {fnum(r2, 2)}</b><small>%/ano, 2012–2018 → 2018–2025</small></div>
  <div class="kpi"><span>Áreas em perda</span><b>{n_loss} de {N}</b><small>{cat_n["stable"]} estáveis · {cat_n["net gain"]} com ganho líquido</small></div>
</section>

<h2>Principais resultados</h2>
<ol class="keys">
  <li><b>A vegetação natural diminuiu na grande maioria das áreas.</b> {n_loss} das {N} áreas ({fnum(n_loss / N * 100, 0)}%) estão em uma das categorias de perda; {cat_n["stable"]} são estáveis, {cat_n["turnover"]} têm rotatividade (perda e regeneração se compensam) e só {cat_n["net gain"]} tiveram ganho líquido. [E]</li>
  <li><b>A perda acelerou.</b> A taxa agregada passou de {fnum(r1, 2)}%/ano em 2012–2018 para {fnum(r2, 2)}%/ano em 2018–2025; {n_acc} áreas têm aceleração acima do ruído da série. A matriz fora das áreas, no Cerrado, acelerou na mesma direção ({fnum(mcer.rate_2012_2018, 2)} → {fnum(mcer.rate_2018_2025, 2)}%/ano). [E]</li>
  <li><b>A perda é concentrada.</b> {cat_n["intense loss"] + cat_n["very intense loss"]} áreas com perda intensa ou muito intensa (acima de 1%/ano) respondem por {fnum((u[u.category.isin(["intense loss", "very intense loss"])].net_ha.sum()) / u.net_ha.sum() * 100, 0)}% da perda líquida total, com {fnum(cat_nat["intense loss"] / nat12 * 100 + cat_nat["very intense loss"] / nat12 * 100, 0)}% da vegetação natural de 2012. [E]</li>
  <li><b>A classe de importância biológica não indica a intensidade da perda.</b> As áreas de importância extremamente alta perdem tanto quanto as de importância alta ({fnum(imp.get("Extremamente Alta"), 2)} e {fnum(imp.get("Alta"), 2)}%/ano). A prioridade de ação acompanha melhor a perda, o que é coerente com prioridade refletindo ameaça. [E]</li>
  <li><b>As áreas ainda bem conservadas na fronteira agrícola são o caso mais urgente.</b> {len(frontier)} áreas com 50% ou mais de vegetação natural em 2025 têm perda intensa ou muito intensa: {n_front_matopiba} são áreas MMA do Matopiba (MA, TO, PI, BA) e {n_front_hyb_amz} são híbridas com a Amazônia. [E] [H] São as áreas em que a janela para ação ainda está aberta e se fecha mais rápido.</li>
  <li><b>Pastagem é o principal destino da vegetação convertida ({fnum(past, 0)}%), seguida de mosaico de usos ({fnum(mos, 0)}%) e soja ({fnum(soy, 0)}%).</b> A soja pesa mais onde a perda é mais rápida: é o principal destino em {n_vi_mma_soy} das {len(vi_mma)} áreas MMA com perda muito intensa. [E] [H] A comparação direta 2012 → 2025 registra o uso final; parte da pastagem e do mosaico pode ser etapa anterior à agricultura.</li>
  <li><b>As áreas híbridas perdem mais rápido</b> que as áreas da camada MMA ({fnum(pooled(u[u.is_hybrid]), 2)} contra {fnum(pooled(u[~u.is_hybrid]), 2)}%/ano); {n_vi_hyb} das {len(vi)} áreas com perda muito intensa são híbridas com a Amazônia. [E]</li>
</ol>

<h2>Como ler as categorias</h2>
<p>Cada área recebe uma <b>categoria de dinâmica</b> pela tendência anual da área não convertida (vegetação natural mais água e areia) entre 2012 e 2025, em % ao ano da vegetação natural de 2012. Perda e ganho contam só trocas entre vegetação natural e uso antrópico; cheias e variações de água não contam como perda.</p>
<table class="num l"><thead><tr><th>Categoria</th><th>Regra</th><th>Áreas</th></tr></thead><tbody>
<tr><td>Ganho líquido</td><td>tendência &gt; +0,2%/ano, com ganho mínimo de 0,5 p.p. da área e 100 ha</td><td>{cat_n["net gain"]}</td></tr>
<tr><td>Estável</td><td>tendência entre −0,2 e +0,2%/ano e conversão bruta ≤ 0,5%/ano</td><td>{cat_n["stable"]}</td></tr>
<tr><td>Rotatividade</td><td>tendência entre −0,2 e +0,2%/ano, conversão bruta &gt; 0,5%/ano</td><td>{cat_n["turnover"]}</td></tr>
<tr><td>Perda moderada</td><td>−1 a −0,2%/ano (metade da vegetação some em 70 a 350 anos)</td><td>{cat_n["moderate loss"]}</td></tr>
<tr><td>Perda intensa</td><td>−2 a −1%/ano (metade em 35 a 70 anos)</td><td>{cat_n["intense loss"]}</td></tr>
<tr><td>Perda muito intensa</td><td>abaixo de −2%/ano (metade em menos de 35 anos)</td><td>{cat_n["very intense loss"]}</td></tr>
</tbody></table>
<p class="muted">Alertas independentes da categoria: aceleração, baixa confiança (tendência perto de um limite), dinâmica hidrológica, possível reservatório, área pequena e área híbrida. {int(u.low_confidence.sum())} áreas têm o alerta de baixa confiança: a categoria delas deve ser lida junto com a taxa contínua, mostrada em cada ficha.</p>

<h2>Mapa das categorias</h2>
{legend_cats()}
<div class="mapframe">{map_svg()}</div>
<p class="muted">Clique em uma área para abrir a ficha; passe o cursor para ver nome, categoria e taxa. Fundo: Cerrado e Pantanal (IBGE 2019) e limites estaduais. Áreas híbridas incluídas. Projeção cônica equivalente de Albers (América do Sul).</p>

<h2>Categorias por importância, prioridade e tipo de área</h2>
<p class="muted">Número de áreas em cada categoria. Passe o cursor sobre os segmentos para ver contagens e percentuais.</p>
{legend_cats()}
{svg_stacked([(f"Importância {k.lower()}", u[u.Import_bio == k]) for k in imp_order] + [(f"Prioridade {k.lower()}", u[u.Prior_acao == k]) for k in imp_order] + [("Áreas MMA", u[~u.is_hybrid]), ("Áreas híbridas", u[u.is_hybrid])], "Categorias por grupo")}
<div class="wrap">{group_table("Import_bio", imp_order, "Importância biológica")}</div>
<div class="wrap">{group_table("Prior_acao", imp_order, "Prioridade de ação")}</div>

<h3>A perda acelerou em todos os grupos</h3>
<ul class="leg"><li><span class="dot" style="background:var(--p1)"></span>2012–2018</li><li><span class="dot" style="background:var(--p2)"></span>2018–2025</li></ul>
{svg_dumbbell(dumb)}
<p class="muted">Taxa líquida agregada, % ao ano da vegetação natural de 2012. Valores negativos são perda. A matriz fora das áreas prioritárias é contexto, não grupo de comparação.</p>

<h2>Por ação principal recomendada e por UF</h2>
<div class="wrap">{group_table("acao_grupo", None, "Ação principal")}</div>
<p class="muted">[H] As áreas cuja ação principal é criar unidade de conservação continuam perdendo vegetação. Verificar quais UCs foram de fato criadas é uma etapa posterior (avaliação de implementação).</p>
<div class="wrap">{group_table("uf_main", None, "UF principal")}</div>

<h2>Para onde foi a vegetação convertida</h2>
<p class="muted">Vegetação natural de 2012 que era uso antrópico em 2025, somada nas {N} áreas.</p>
{svg_hbars([(DRIVER_PT.get(k, k), v) for k, v in drivers.items() if v >= 1000])}

<h2>Áreas em destaque</h2>
<h3>As 20 áreas com perda mais rápida</h3>
<div class="wrap"><table class="num hl"><thead><tr><th>Código</th><th>Nome</th><th>UF</th><th>Importância</th><th>Vegetação natural 2012 → 2025</th><th>%/ano</th><th>Aceleração</th><th>Vetor</th></tr></thead><tbody>{hl_rows}</tbody></table></div>
<h3>Grandes áreas estáveis e bem conservadas</h3>
<p>{len(big_stable)} áreas estáveis mantêm 80% ou mais de vegetação natural, somando {fnum(big_stable.nat_ha_2025.sum() / 1e6, 1)} Mha; as maiores são {", ".join(f'<a href="ficha_{esc(k)}.html">{esc(str(n))}</a>' for k, n in big_stable.NOME.head(6).items())}. Várias estão no Pantanal, onde a vegetação oscila com as cheias, mas a área convertida em uso pouco mudou. [E]</p>

<h2>Contexto: a matriz fora das áreas prioritárias</h2>
<div class="wrap"><table class="num"><thead><tr><th>Bioma (IBGE 2019)</th><th>Vegetação natural 2012</th><th>2025</th><th>Taxa 2012–2025 (%/ano)</th><th>2012–2018</th><th>2018–2025</th></tr></thead><tbody>
{"".join(f"<tr><td>{esc(k.split('|')[1])}</td><td>{fnum(r.nat_share_2012 * 100, 0)}%</td><td>{fnum(r.nat_share_2025 * 100, 0)}%</td><td>{fnum(r.rate, 2)}</td><td>{fnum(r.rate_2012_2018, 2)}</td><td>{fnum(r.rate_2018_2025, 2)}</td></tr>" for k, r in mx.iterrows() if k.split("|")[1] in ("Cerrado", "Pantanal", "Caatinga", "Amazônia", "Mata Atlântica"))}
</tbody></table></div>
<p class="muted">Matriz = toda a área do recorte de análise fora das áreas prioritárias de 2012 e das híbridas, separada pelo bioma de 2019. [H] A taxa agregada das áreas prioritárias ({fnum(rate_all, 2)}%/ano) é próxima da taxa da matriz no Cerrado ({fnum(mcer.rate, 2)}%/ano). Isso <b>não</b> mede efeito: as áreas foram escolhidas justamente onde havia mais vegetação, e as pressões diferem.</p>

<h2 id="fogo">Fogo na vegetação natural estável, 1985–2025</h2>
<div class="box">Esta seção é <b>descritiva</b>: apresenta o regime de fogo observado, sem juízo de mérito e sem atribuir causa (uso tradicional, manejo, acidentes ou outros). Universo: vegetação que permaneceu natural em todos os anos de 1985 a 2025, pelo MapBiomas Coleção 11 e pelo MapBiomas Fogo. Método: decisão D15 do projeto.</div>

<section class="kpis">
  <div class="kpi"><span>Savana e campo estáveis nas áreas</span><b>{fnum(FALL["open_mha"], 1)} Mha</b><small>{fnum(FALL["above"] * 100, 0)}% acima e {fnum(FALL["below"] * 100, 0)}% abaixo do esperado</small></div>
  <div class="kpi"><span>Floresta estável afetada por fogo</span><b>{fnum(FALL["forest"] * 100, 0)}%</b><small>ao menos um fogo em 1985–2025</small></div>
  <div class="kpi"><span>Áreas com &gt; 50% abaixo do esperado</span><b>{FALL["nb"]}</b><small>{FALL["nbr"]} robustas · {FALL["nb"] - FALL["nbr"]} dependem do limiar</small></div>
  <div class="kpi"><span>Áreas com &gt; 20% acima do esperado</span><b>{FALL["na"]}</b><small>{FALL["nar"]} robustas · {FALL["na"] - FALL["nar"]} dependem do limiar</small></div>
</section>

<h3>Principais resultados do fogo</h3>
<ol class="keys">
  <li><b>A ausência prolongada de fogo é o padrão mais comum.</b> {fnum(FALL["below"] * 100, 0)}% da savana e do campo estáveis das áreas não queimam há pelo menos 20 anos ou nunca queimaram desde 1985; em {FALL["nb"]} áreas isso vale para mais da metade da vegetação aberta estável, e em {FALL["nbr"]} delas o resultado se mantém mesmo com limiar de 25 anos. [E]</li>
  <li><b>O fogo acima do esperado é mais concentrado.</b> {fnum(FALL["above"] * 100, 0)}% da savana e do campo estáveis tiveram fogo repetido com intervalos menores que 3 anos. {FALL["na"]} áreas passam de 20%, mas só {FALL["nar"]} se mantêm quando se conta apenas fogo em anos seguidos; nas demais, o sinal vem sobretudo do retorno a cada dois anos. [E]</li>
  <li><b>{fnum(FALL["forest"] * 100, 0)}% da floresta estável foi afetada por fogo</b> ao menos uma vez desde 1985, mais que na matriz da mesma latitude ({fnum(FALL["ref_forest"] * 100, 0)}%); {FALL["nf"]} áreas têm mais da metade da floresta estável afetada. [E]</li>
  <li><b>Há um gradiente norte–sul, que persiste na comparação dentro da mesma faixa de latitude.</b> O fogo acima do esperado concentra-se no MA e no TO; a ausência prolongada, em MG e no MS. A matriz também tem mais fogo ao norte, mas, comparadas com a matriz da mesma faixa de latitude, as áreas do MA ({fnum(UFG["MA"]["above"] * 100, 0)}% acima do esperado, contra {fnum(UFG["MA"]["ref_above"] * 100, 0)}%) e do TO ({fnum(UFG["TO"]["above"] * 100, 0)}% contra {fnum(UFG["TO"]["ref_above"] * 100, 0)}%) seguem acima da referência, e as de MG têm mais ausência prolongada ({fnum(UFG["MG"]["below"] * 100, 0)}% contra {fnum(UFG["MG"]["ref_below"] * 100, 0)}%). [E] [H] O intervalo esperado (3 a 20 anos) é o mesmo em todo o bioma; como as faixas são largas (4 a 6 graus), parte da diferença entre norte e sul ainda pode refletir o clima.</li>
  <li><b>A área queimada por ano mudou pouco no conjunto</b> ({fnum(bf1 * 100, 1)}% em 2012–2018 e {fnum(bf2 * 100, 1)}% em 2019–2025), mas {n_up} áreas tiveram aumento de mais de 50% e {n_dn} tiveram redução equivalente. [E]</li>
  <li><b>Das {len(ab_r)} áreas com fogo acima do esperado em nível robusto, {n_ab_r_loss} estão também em perda intensa ou muito intensa de vegetação natural</b> (produto de estado e dinâmica). A coincidência é descrita, não interpretada como causa. [E]</li>
</ol>

<h3>Como ler</h3>
<table class="num l"><thead><tr><th>Vegetação estável</th><th>Categoria</th><th>Regra (1985–2025)</th></tr></thead><tbody>
<tr><td rowspan="3">Savana e campo</td><td>Acima do esperado</td><td>ao menos dois intervalos entre fogos menores que 3 anos (fogo repetido anual ou a cada dois anos)</td></tr>
<tr><td>De acordo</td><td>os demais casos; <b>não</b> é afirmação de que o regime seja adequado, que exige análise por fragmento</td></tr>
<tr><td>Abaixo do esperado</td><td>nenhum fogo nos últimos 20 anos (2006–2025), incluindo o que nunca queimou</td></tr>
<tr><td>Floresta</td><td>Afetada por fogo</td><td>ao menos um fogo</td></tr>
</tbody></table>
<p class="muted"><b>Robustez das sinalizações por área.</b> Robusta: o resultado se mantém nos testes de sensibilidade (abaixo: limiar de 25 anos; acima: contando só fogo em anos seguidos; floresta: só pixels com a mesma classe em todos os anos). Depende do limiar: o resultado muda com essas escolhas. Os testes usam o mesmo produto de fogo, então a robustez não corrige erros de detecção. Áreas com menos de 1.000 ha de savana e campo estáveis não recebem sinalização ({int(fire_cls_n.get("small", 0))} áreas). Áreas úmidas (campo e savana alagáveis) não são classificadas, porque o regime depende da inundação.</p>

<h3>Mapa das sinalizações de fogo</h3>
<ul class="leg">{"".join(f'<li><span class="sw" style="background:{FIRE_MAP_COL[k]};border:1px solid #bbb"></span>{FIRE_MAP_PT[k]} ({int(fire_cls_n.get(k, 0))})</li>' for k in FIRE_MAP_COL)}</ul>
<div class="mapframe">{map_svg(lambda k: FIRE_MAP_COL[fire_class(k)], fire_tip, "Mapa interativo das sinalizações de fogo")}</div>
<p class="muted">Clique em uma área para abrir a ficha. Duas áreas têm as duas sinalizações (acima em parte da vegetação e abaixo em outra parte); aparecem como "acima", e a dica mostra os dois valores.</p>

<h3>Por importância, prioridade e tipo de área</h3>
<ul class="leg"><li><span class="sw" style="background:{FC_ABOVE}"></span>Acima do esperado</li><li><span class="sw" style="background:{FC_MID}"></span>De acordo</li><li><span class="sw" style="background:{FC_BELOW}"></span>Abaixo do esperado</li><li class="muted">barra fina: matriz de referência</li></ul>
{svg_fire_groups([("Todas as áreas", F)] + [(f"Importância {k.lower()}", F[u.Import_bio.reindex(F.index) == k]) for k in imp_order] + [(f"Prioridade {k.lower()}", F[u.Prior_acao.reindex(F.index) == k]) for k in imp_order] + [("Áreas MMA", F[~u.is_hybrid.reindex(F.index).astype(bool)]), ("Áreas híbridas", F[u.is_hybrid.reindex(F.index).astype(bool)])])}
<p class="muted">Participação na área de savana e campo estáveis do grupo (ponderada pela área). {REF_NOTE}</p>
<div class="wrap">{fire_table([("Todas as áreas", F)] + [(f"Importância {k.lower()}", F[u.Import_bio.reindex(F.index) == k]) for k in imp_order] + [(f"Prioridade {k.lower()}", F[u.Prior_acao.reindex(F.index) == k]) for k in imp_order] + [("Áreas MMA", F[~u.is_hybrid.reindex(F.index).astype(bool)]), ("Áreas híbridas", F[u.is_hybrid.reindex(F.index).astype(bool)])], "Grupo")}</div>
<h3>Por UF principal</h3>
<div class="wrap">{fire_table([(k, F[F.uf_main == k]) for k in F.groupby("uf_main").open_ha.sum().sort_values(ascending=False).index], "UF principal")}</div>
<p class="muted">Nas colunas de contagem, "a + b" = a áreas robustas + b áreas que dependem do limiar.</p>

<h3>Mudança entre 2012–2018 e 2019–2025</h3>
<p>Na savana e no campo estáveis, a área queimada por ano foi de {fnum(bf1 * 100, 1)}% para {fnum(bf2 * 100, 1)}% no conjunto das áreas. A parte do fogo que ocorre em <b>julho e agosto</b>, meses sem raios no Cerrado (o fogo é iniciado por pessoas), subiu mais de 10 pontos em {n_j_up} áreas e caiu mais de 10 pontos em {n_j_dn}, entre as {len(_j)} com fogo suficiente nos dois períodos. [E]</p>
<div class="wrap"><table class="num"><thead><tr><th>Faixa de latitude</th><th>Áreas</th><th>Julho–agosto, mediana 2012–2018</th><th>2019–2025</th><th>Áreas com alta &gt; 10 p.p.</th><th>Áreas com queda &gt; 10 p.p.</th><th>Matriz da faixa</th></tr></thead><tbody>{"".join(band_rows)}</tbody></table></div>
<p class="muted">Percentual da área queimada que ocorreu em julho–agosto. Só áreas com ao menos 1.000 ha (e 1% da vegetação aberta estável) queimados em cada subperíodo.</p>

<h3>Relação com a dinâmica da vegetação natural</h3>
<div class="wrap"><table class="num"><thead><tr><th>Categoria de dinâmica 2012–2025</th><th>Áreas</th><th>Abaixo, robusto</th><th>Abaixo, depende do limiar</th><th>Acima, robusto</th><th>Acima, depende do limiar</th><th>Floresta &gt; 50% afetada</th></tr></thead><tbody>{"".join(xt_rows)}</tbody></table></div>
<p class="muted">Número de áreas. Tabela descritiva: as duas avaliações usam universos diferentes (o fogo, só a vegetação estável desde 1985).</p>

<h3>Áreas em destaque</h3>
<details open><summary><b>Fogo acima do esperado, robusto ({len(ab_r)} áreas)</b></summary>
<div class="wrap"><table class="num hl2"><thead><tr><th>Código</th><th>Nome</th><th>UF</th><th>Savana e campo estáveis (mil ha)</th><th>Acima do esperado</th><th>Só fogo em anos seguidos</th><th>Dinâmica 2012–2025</th></tr></thead><tbody>{ab_list}</tbody></table></div></details>
<details><summary><b>Ausência prolongada de fogo, robusta: as 20 maiores áreas</b></summary>
<div class="wrap"><table class="num hl2"><thead><tr><th>Código</th><th>Nome</th><th>UF</th><th>Savana e campo estáveis (mil ha)</th><th>Abaixo do esperado</th><th>Com limiar de 25 anos</th><th>Dinâmica 2012–2025</th></tr></thead><tbody>{be_list}</tbody></table></div></details>
<details><summary><b>Floresta estável com mais de 50% afetada por fogo ({len(fo)} áreas)</b></summary>
<div class="wrap"><table class="num hl2"><thead><tr><th>Código</th><th>Nome</th><th>UF</th><th>Floresta estável (mil ha)</th><th>Afetada</th><th>Robustez</th></tr></thead><tbody>{fo_list}</tbody></table></div></details>

<h2>Subsídios para o próximo ciclo (propostas)</h2>
<ol>
  <li><b>Usar a dinâmica, não só o estado.</b> Áreas com muita vegetação e perda intensa ({len(frontier)} áreas) pedem ação mais urgente do que o estado sozinho sugere.</li>
  <li><b>Rever o papel da classe de importância.</b> Ela não diferencia a pressão sofrida desde 2012. A combinação entre importância e dinâmica pode orientar a priorização de ações.</li>
  <li><b>Tratar a fronteira agrícola como contexto próprio.</b> As maiores perdas estão no Matopiba e na transição com a Amazônia, onde a conversão para soja e pastagem segue rápida.</li>
  <li><b>Melhorar a governança dos dados</b> do ciclo: vocabulário controlado para classes e ações (a camada atual tem grafias inconsistentes), identificador estável das áreas entre ciclos, origem das áreas híbridas e publicação das entradas da priorização.</li>
  <li><b>Próximas camadas de diagnóstico:</b> posse da terra e folga legal de conversão; degradação; regime de fogo por fragmento (para separar o regime adequado do apenas não extremo) e qualificação pelas fitofisionomias do mapa de vegetação do IBGE; efeito comparado com áreas equivalentes não designadas.</li>
</ol>

<h2>Limitações</h2>
<ul>
  <li>Erros de classificação do MapBiomas, sobretudo a confusão entre formações campestres e pastagem, afetam perda e ganho brutos. A categoria usa a tendência de 14 anos, que é mais robusta; {int(u.low_confidence.sum())} áreas estão perto de um limite.</li>
  <li>Vegetação secundária conta como natural. A persistência desde 1985 é mostrada em cada ficha.</li>
  <li>Reservatórios não são separados de rios e lagos no MapBiomas; um alerta indica possíveis casos, ainda não conferidos com a lista oficial de barragens.</li>
  <li>Cerca de 86 mil ha das áreas estão fora da cobertura do MapBiomas Brasil (fronteira e mar) e não foram avaliados.</li>
  <li>As áreas híbridas não têm nome nem vínculo com as áreas de origem na camada oficial.</li>
  <li><b>Fogo:</b> o produto de fogo subdetecta queimadas de sub-bosque em floresta e pode registrar cicatrizes espúrias; a robustez das sinalizações não corrige erros de detecção.</li>
  <li><b>Fogo:</b> o intervalo esperado (3 a 20 anos) é o mesmo para todo o bioma; zonas de transição com a Amazônia e a Mata Atlântica e o cerradão mapeado como floresta podem ter regime próprio e ainda não foram qualificados.</li>
  <li><b>Fogo:</b> só a vegetação estável desde 1985 entra na avaliação; vegetação regenerada e áreas convertidas ficam fora.</li>
</ul>

<footer><p>Autoria: Mario Barroso Ramos Neto e Claude (Anthropic). Fontes: MapBiomas Coleção 11 e MapBiomas Fogo (1985–2025); Áreas Prioritárias para a Conservação, 2ª atualização, MMA; limites de biomas e UFs, IBGE. Método completo: decisões D13 (estado e dinâmica) e D15 (fogo) e scripts do repositório do projeto. Tags: [E] resultado calculado; [H] interpretação a testar. Documento gerado em {date.today():%d/%m/%Y}; versão preliminar para discussão.</p></footer>
'''

out = P1 / "sumario_executivo.html"
out.write_text('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>Sumário executivo — Áreas Prioritárias Cerrado e Pantanal</title><style>{CSS}</style></head><body><main>{body}</main></body></html>',
               encoding="utf-8")
print("written", out)
