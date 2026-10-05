"""
build_site.py — Assemble the Product 1 web site (index + executive summary + fact sheets)
into one folder with flat, relative links, ready for a static host.

Layout of the output folder (default data/interim/site/, not versioned):
  index.html          table of all areas with a text filter (the entry page)
  sumario.html        executive summary
  ficha_<unit>.html   one page per area (maps embedded)
Every page links to index.html and sumario.html by relative path, so the folder works the
same on any static host (claude.ai artifact, GitHub Pages, an institutional server).

Run from the repository root, after product1_factsheets.py --units all and product1_summary.py:
  python scripts/analysis/build_site.py               # full HTML documents (any static host)
  python scripts/analysis/build_site.py --artifact    # entry page without <html>/<head>/<body>
                                                      # (claude.ai wraps it at publish time)

What can break, and how you would notice:
  - Missing inputs: the script stops and names the file to generate first.
  - A host that does not serve "index.html" as the folder's default page: open the site by
    the full path .../index.html.
"""
import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "data/derived/product1"
TITLE = "Áreas Prioritárias Cerrado-Pantanal"

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(ROOT / "data/interim/site"))
ap.add_argument("--artifact", action="store_true")
args = ap.parse_args()
out = Path(args.out)

src_index = P1 / "fichas/index.html"
src_sum = P1 / "sumario_executivo.html"
for f in (src_index, src_sum):
    if not f.exists():
        raise SystemExit(f"missing {f}: run product1_factsheets.py --units all and product1_summary.py first")

if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
shutil.copy(src_sum, out / "sumario.html")
n = 0
for f in sorted((P1 / "fichas").glob("ficha_*.html")):
    shutil.copy(f, out / f.name); n += 1

html = src_index.read_text(encoding="utf-8")
html = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", html, count=1)
if args.artifact:
    # Keep <title> and <style>, drop the document wrapper (the host adds its own skeleton)
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    head = re.sub(r"<meta[^>]*>", "", head)
    body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
    html = head + body
(out / "index.html").write_text(html, encoding="utf-8")
size = sum(p.stat().st_size for p in out.iterdir()) / 1e6
print(f"site: {n} fact sheets + index + summary in {out} ({size:.1f} MB)")
