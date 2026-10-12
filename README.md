# ARC-CO / PLC Payment Calculator

University of Minnesota Extension calculator for 2026 ARC-CO and PLC payments by county, crop and practice.
Live page: `docs/index.html`, published with GitHub Pages (**Settings → Pages → main / /docs**).

**Auditing:** see [AUDIT.md](AUDIT.md). It lists every input with its source file, tab and column, the formulas and their exact lines, and a step-by-step check.

## How it fits together

```
data/FSAInputData_YYYYMMDD.xlsx  ─┐
data/Detailed_Results_*.csv      ─┼─>  python web/build.py  ─>  docs/index.html            (the page)
web/template.html (page + JS)    ─┘                         ─>  data/app_inputs_audit.csv  (what the page uses, labeled by source)
                                                            ─>  data/build_report.txt      (cross-checks and merge results)
```

- **FSA workbook (Main tab):** dropdowns, benchmark yield and price, default county yield (col V), default price (col W), PLC yield (col AA), 2020–24 yields.
- **FSA workbook (PLC rates tab):** effective reference price and loan rate.
- **Results CSV:** the "Our estimations" section, for corn, soybeans and wheat only.
- **Yields feather:** FSA actual county yields for the History chart.

## Updating

1. Put the new file(s) in `data/` (FSA: `FSAInputData_YYYYMMDD.xlsx`; the newest is used).
2. `pip install -r requirements.txt` (once), then `python web/build.py`.
3. Read `data/build_report.txt`, then upload `docs/index.html`.

Wording, layout or the default county: edit `web/template.html` (default county is the `DEFAULT` line near the top of the script), rebuild, and upload.

## Files

| File | What it is |
|---|---|
| `web/template.html` | Page source: layout, styling, formulas (JavaScript) |
| `web/build.py` | Reads and checks the data, writes the page and the audit outputs (Python) |
| `arcplc.py` | Same formulas in Python, used for the audit table |
| `tools/check_formulas.js` | Optional: confirms the page's JavaScript matches the Python on every row (Node.js) |
| `web/logo*.png`, `web/fonts/` | UMN Extension logo, Raleway font (SIL OFL), embedded at build time |
| `data/counties.csv` | State FIPS → two-letter abbreviation |

For educational purposes only. Contact: Henrique Monaco, hmonaco@umn.edu
