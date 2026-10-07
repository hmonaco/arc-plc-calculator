# ARC-CO / PLC Payment Calculator (MVP)

Two versions of the same tool live here:

- **`docs/index.html`**: static HTML/JavaScript page. No server; host it on GitHub Pages.
- **`app.py`**: Streamlit (Python) version.

## HTML version (GitHub Pages)

`docs/index.html` is self-contained (data, Raleway font and logo embedded, ~1.5 MB). To publish:

1. Push the repo to GitHub.
2. Repo **Settings → Pages → Source: Deploy from a branch → `main` / `/docs`** → Save.
3. The site appears at `https://<user>.github.io/<repo>/` in a minute or two.

To refresh the data after rerunning your models:

```bash
python web/build.py path/to/new_results.csv   # rewrites docs/index.html
```

Edit the page itself in `web/template.html` (the formulas are near the top of its script and mirror `arcplc.py`).
You can also just double-click `docs/index.html` to open it locally.

## Streamlit version

A small Streamlit app: pick **state → county → crop → practice**, enter a county
yield and MYA price, and get 2026 ARC-CO and PLC payments per base acre, a
yield × price sensitivity table, and two charts.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy from GitHub (free)

1. Push this folder to a GitHub repo.
2. Go to <https://share.streamlit.io>, sign in with GitHub, **New app**.
3. Pick the repo, branch `main`, main file `app.py` → Deploy.

You get a public URL; every push to `main` redeploys.

## Files

| File | What it is |
|---|---|
| `web/template.html`, `web/build.py` | HTML page source and the script that embeds the data → `docs/index.html` |
| `app.py` | Streamlit UI: selectors, inputs, results, sensitivity table, charts, history tab |
| `arcplc.py` | Payment formulas (pure functions — swap in your own module here) |
| `data/Detailed_Results_2026_ncsa_09142026.csv` | County parameters and simulated expectations |
| `data/counties.csv` | FIPS → county/state names (Census 2020) |

## Payment rules (2026, OBBBA)

- **ARC-CO** = min(max(0.90 × BY × BP − Y × max(MYA, LR), 0), 0.12 × BY × BP) × 0.85
- **PLC** = max(ERP − max(MYA, LR), 0) × PLC yield × 0.85

BY/BP = benchmark yield/price, ERP = effective reference price, LR = loan rate.
Payments are $ per base acre, before sequestration and payment limits.

## Data notes

- Rows with no practice and no ARC benchmark are shown as "PLC yield only".
- Irrigated/non-irrigated rows often carry no PLC yield; the app then uses the
  PLC yield from another row of the same county/crop and says so.
- FSA administrative counties with no Census FIPS match show as "FSA county #####".
- Prices in the CSV are rounded to 2 decimals, which is coarse for $/lb crops
  (seed cotton, peanuts, rice). Export more decimals for those.

## Ideas for v2

- Historical tab driven by a longer yield/price series file
- Farm-level inputs (base acres, own PLC yield) → total $ for the farm
- Distribution of simulated payments rather than only the mean

## Branding

- Colors: UMN Extension theme (maroon `#7A0019`, gold `#FFCC33`, lime `#C1D72E`, orange `#F8981D`), set as CSS tokens at the top of `web/template.html`.
- Font: Raleway (SIL Open Font License), embedded from `web/fonts/` so printouts never fall back.
- Logo: `web/logo.png` (light) and `web/logo-dark.png` (dark theme), embedded at build time.
