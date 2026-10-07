"""Build the static HTML calculator (docs/index.html) from the results CSV.

Usage:  python web/build.py [path/to/results.csv]

Reads the county results file and data/counties.csv, packs them into a compact
JSON blob and injects it into web/template.html. The output is one self-contained
index.html that runs anywhere (GitHub Pages, a local double-click, an LMS page).
"""
import base64
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CSV = Path(ARGS[0]) if ARGS else ROOT / "data" / "Detailed_Results_2026_ncsa_09142026.csv"
TEMPLATE = Path(__file__).parent / "template.html"
OUT = ROOT / "docs" / "index.html"  # GitHub Pages serves main:/docs
YEARS = [2020, 2021, 2022, 2023, 2024]
PRACTICES = ["All", "Nonirrigated", "Irrigated", "PLC only"]
UNITS = {"Corn": ["bu", 2], "Soybean": ["bu", 2], "Wheat": ["bu", 2], "Sorghum": ["bu", 2],
         "Seed Cotton": ["lb", 3], "Peanut": ["lb", 3], "Rice": ["lb", 3]}


def r(x, d=2):
    return None if pd.isna(x) else round(float(x), d)


def main():
    df = pd.read_csv(CSV)
    df["YieldType"] = df["YieldType"].fillna("PLC only")
    calc_year = int(df["calc_year"].iloc[0])

    # Crop-level (national) parameters: identical across counties
    crops = sorted(df["Commodity"].unique())
    crop_info = []
    for c in crops:
        g = df[df["Commodity"] == c].iloc[0]
        crop_info.append({
            "name": c, "unit": UNITS.get(c, ["unit", 2])[0], "dec": UNITS.get(c, ["unit", 2])[1],
            "mya": [r(g[f"{y} MYA Price"], 4) for y in YEARS],
            "erp": r(g["Avg. Eff.Ref.Price"], 4), "loan": r(g["Mkt Loan Rate"], 4),
            "bp": r(g["Avg. Benchmark Price"], 4), "ep": r(g["2026 Avg. Actual Price"], 4),
        })
    cidx = {c: i for i, c in enumerate(crops)}

    # PLC yield fallback: practice rows often lack it; borrow from the same county/crop
    plc_fb = df.dropna(subset=["PLC Yield"]).drop_duplicates(["fips", "Commodity"]).set_index(["fips", "Commodity"])["PLC Yield"]

    rows = []
    for g in df.to_dict("records"):
        py, borrowed = g["PLC Yield"], 0
        if pd.isna(py):
            py = plc_fb.get((g["fips"], g["Commodity"]))
            borrowed = int(py is not None and not pd.isna(py))
        rows.append([
            int(g["fips"]), cidx[g["Commodity"]], PRACTICES.index(g["YieldType"]),
            [r(g[f"{y} Yields"]) for y in YEARS], r(g["Avg. Benchmark Yield"]), r(py), borrowed,
            r(g["2026 Avg. Actual Yields"]), r(g["2026 Avg. ARC-CO Pmt"]), r(g["2026 Avg. PLC Pmt"]),
            r(g["2026 ARC-CO Pmt Likelihood"]), r(g["2026 PLC Pmt Likelihood"]),
        ])

    counties = pd.read_csv(ROOT / "data" / "counties.csv")
    st = counties.drop_duplicates("postal").assign(sf=lambda d: d.fips // 1000)
    states = {int(s.sf): [s.state, s.postal] for s in st.itertuples()}
    names = {int(c.fips): c.county for c in counties.itertuples()}
    used = sorted(df["fips"].unique())
    county_names = {str(f): names.get(int(f), f"FSA county {int(f):05d}") for f in used}

    data = {"year": calc_year, "histYears": YEARS, "practices": PRACTICES, "crops": crop_info,
            "states": {str(k): v for k, v in states.items()}, "counties": county_names, "rows": rows,
            "source": CSV.name}
    blob = json.dumps(data, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob)
    web = Path(__file__).parent
    b64 = lambda f: base64.b64encode(f.read_bytes()).decode()
    # Logo: web/logo.png (light theme) and optional web/logo-dark.png replace the text wordmark
    if (web / "logo.png").exists():
        dark = web / "logo-dark.png"
        imgs = f'<img class="logo-light" src="data:image/png;base64,{b64(web / "logo.png")}" alt="University of Minnesota Extension">'
        if dark.exists():
            imgs += f'<img class="logo-dark" src="data:image/png;base64,{b64(dark)}" alt="University of Minnesota Extension">'
        html = html.replace('<!--__LOGO__--><div class="wordmark">', imgs + '<div class="wordmark" hidden>', 1)
    # Fonts: embed every web/fonts/<family>-latin-<weight>-normal.woff2 so print/PDF never falls back
    faces = []
    for f in sorted((web / "fonts").glob("*-latin-*-normal.woff2")):
        fam, _, wt = f.stem.split("-")[:3]
        faces.append(f'@font-face{{font-family:"{fam.title()}";font-style:normal;font-weight:{wt};font-display:swap;'
                     f'src:url(data:font/woff2;base64,{b64(f)}) format("woff2")}}')
    html = html.replace("/*__FONTS__*/", "\n".join(faces), 1)
    # Standalone page needs its own document skeleton (the template is a body fragment)
    page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
            + html + "\n</body>\n</html>\n")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    if "--fragment" in sys.argv:  # body-only version, e.g. for embedding in another page
        OUT.with_name("fragment.html").write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(rows)} rows)")


if __name__ == "__main__":
    main()
