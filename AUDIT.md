# Auditing the ARC-CO / PLC Calculator

This guide covers every number the calculator shows: where it comes from, how it is calculated, and how to check it.

**Short version:** open `data/app_inputs_audit.csv` in Excel. It has one row per county / crop / practice in the app. Each column header names its source (for example `PLC yield [Main!AA]`). Then read `data/build_report.txt` for anything that didn't match.

---

## 1. Files involved

| File | Role |
|---|---|
| `data/FSAInputData_YYYYMMDD.xlsx` | **Main source.** FSA ARC/PLC program data. The build uses the newest file with this name pattern. |
| `data/Detailed_Results_*.csv` | Your simulation results. Used **only** for the "Our estimations" section (corn, soybeans, wheat). |
| `data/FSA_yields_*.feather` | FSA actual county yields, 2009–2025. Used **only** for the History chart. |
| `data/counties.csv` | State FIPS → two-letter state abbreviation (display only). |
| `web/build.py` | Reads the files above, checks them, and writes the page. Python. |
| `web/template.html` | The page itself, including the payment formulas (JavaScript). |
| `arcplc.py` | The same formulas in Python. The build uses them to fill the audit table. |
| `docs/index.html` | The published page (output of the build; never edit by hand). |
| `data/app_inputs_audit.csv` | **Audit table** (output of the build). |
| `data/build_report.txt` | **Build report**: cross-checks, merge results, mismatches (output of the build). |
| `data/yield_conflicts.csv` | Yields-file records where the same county / crop / practice / year has two different values (output of the build). |
| `tools/check_formulas.js` | Optional check that the page's JavaScript gives the same payments as the Python. Needs Node.js. |

---

## 2. Where every input comes from

The program year is read from the Main tab title ("… FOR PROGRAM YEAR 2026"). It sets the year on the page and chart labels, and fills in the year inside the expected headers below, so a 2027 file works without code changes.

The build finds columns **by their header text** (row 4 of the Main tab), not by letter. If a column moves, the build still finds it and notes the new letter in the build report. If a header is renamed or deleted, the build **stops with an error** instead of reading the wrong column. The expected headers are listed in `web/build.py` under `MAIN_COLS` and `RATE_COLS`.

### FSA workbook, tab **Main** (one row per county × sub-county × crop × practice)

| Shown in the app as | Column | Header in the file |
|---|---|---|
| County FIPS (shown in the heading; key for matching the results file) | A | `ST_Cty` |
| **State** dropdown | B | `State Name` |
| **County** dropdown (name) | C | `County Name` |
| County suffix, e.g. "Chouteau (A)" | D | `Sub County` |
| **Crop** dropdown (FSA name; display name comes from the `lookups` tab) | E | `Crop Name` |
| Link to the PLC rates tab | F | `name pmts` |
| Units (bu or lb) | I | `Unit` |
| **Practice** dropdown | J | `ARC-CO Yield Designation` |
| *Audit table only* (the History chart uses the yields file) | K–O | `2020 … 2024 trend adjusted (county yield or 80% of T)` |
| Benchmark yield (also the dashed line in History) | Q | `2026 Bench Mark (2020-24 olympic avg)` |
| Benchmark price | R | `2026 Bench Mark Price (2020-24 olympic avg)` |
| **Default county yield** (input box, "Reset to defaults") | V | `2026 Actual Yield` (placeholder default for now; labeled only as "Default" in the app) |
| **Default MYA price** (input box, "Reset to defaults") | W | `2026 National Price` |
| PLC yield | AA | `PLC Yields` |
| *Cross-check only, not displayed* | S, T, U | Benchmark revenue, guarantee, max payment rate |

### FSA workbook, tab **PLC rates** (one row per commodity)

Matched to Main using Main column F (`name pmts`) = PLC rates column B (`key`).

| Shown in the app as | Column | Header |
|---|---|---|
| Effective reference price | F | `2026 Effective Reference Price` |
| National loan rate | I | `2026 National Loan Rate` |
| *Cross-check only*: projected MYA price | G | `Projected (P) or Final (F) 2026/27 MYA Price` |

The date printed on the page's data line (e.g. "September 11, 2026") is read from the top of this tab.

### Yields file (`FSA_yields_*.feather`): History chart only

| Shown in the app as | Field |
|---|---|
| History line, 2009–2025 | `ActYield`, by `Year` |

**Match:** county FIPS (`ST_Cty`) + crop (`Crop Name`, same names as Main column E) + practice (`ARC-CO Yield Designation`).

- **Duplicates:** 3,103 county / crop / practice / year keys appear more than once, and 1,730 of them have different values (mostly 2014–2018, many seed cotton). The build uses the **first value in file order** and lists every conflict in `data/yield_conflicts.csv`.
- **No history:** sub-county rows (Chouteau, Umatilla) have none, since the file has no sub-county field. One other row has none: Vermilion, LA medium/short-grain rice.

### FSA workbook, tab **lookups**

Used only to turn FSA crop names into readable ones (column C → column A, with footnote marks like "2/" removed), e.g. `Rice_Long Grain` → "Rice (long grain)".

### Results file (`Detailed_Results_*.csv`): "Our estimations" section only

| Shown in the app as | Column |
|---|---|
| Expected ARC-CO | `2026 Avg. ARC-CO Pmt` |
| Expected PLC | `2026 Avg. PLC Pmt` |
| Chance ARC-CO pays | `2026 ARC-CO Pmt Likelihood` |
| Chance PLC pays | `2026 PLC Pmt Likelihood` |
| Used only for the mismatch note | `Avg. Benchmark Yield` |

**Merge rule** (`web/build.py`, section `detailed results (estimations)`):

- **Key:** county FIPS + crop + practice. Results crop names are mapped `Corn → Corn`, `Soybean → Soybeans`, `Wheat → Wheat`. Practices must match exactly (`All`, `Irrigated`, `Nonirrigated`).
- **Crops:** only corn, soybeans and wheat. For every other crop the whole section is hidden.
- **Sub-counties:** rows with a value in Main column D (e.g. Chouteau A/B, Umatilla A/B) get no estimates, because the results file has no sub-county.
- **Missing values:** if a matched results row has no value for a field (common for PLC on irrigated / non-irrigated rows), the app shows "not estimated".
- **Benchmark mismatch:** if the results file's benchmark yield differs from FSA column Q by more than 0.05, the section shows a note with both numbers. Every case is also listed in the build report.

### Fixed program parameters (not from any file)

`web/template.html` (`const PAF =` line) and `arcplc.py`:

| Parameter | Value |
|---|---|
| Payment acres | 85% of base acres |
| ARC-CO guarantee | 90% of benchmark revenue |
| ARC-CO maximum payment | 12% of benchmark revenue |

---

## 3. The formulas

The page calculates payments in the visitor's browser with two one-line functions in `web/template.html` (search for `function arcPay`):

```js
function arcPay(y, p, by, bp, loan){ const br = by*bp; const s = GUAR*br - y*Math.max(p, loan); return Math.min(Math.max(s,0), CAP*br)*PAF; }
function plcPay(p, erp, loan, py){ return Math.max(erp - Math.max(p, loan), 0)*py*PAF; }
```

In words, with y = county yield, p = MYA price, BY / BP = benchmark yield / price (Q, R), LR = loan rate, ERP = effective reference price, PY = PLC yield (AA):

- **ARC-CO** ($/base acre) = min( max( 0.90 × BY × BP − y × max(p, LR), 0 ), 0.12 × BY × BP ) × 0.85
- **PLC** ($/base acre) = max( ERP − max(p, LR), 0 ) × PY × 0.85

The same two formulas are in `arcplc.py` (`arc_co_payment`, `plc_payment`). Everything else on the page reuses these two functions:

| Display | How it's computed | Find it in `web/template.html` (search for) |
|---|---|---|
| ARC-CO and PLC boxes | `arcPay` / `plcPay` at your yield and price | `const a = k.hasArc` and `const q = k.hasPlc` |
| Benchmark revenue | BY × BP | `"Benchmark revenue"` |
| ARC guarantee (90%) | 0.90 × BY × BP | `"ARC guarantee (90%)"` |
| Your actual revenue | y × max(p, LR) | `const rev =` |
| Sensitivity table rows | BY × 120%, 115% … 70% (step selectable) | `const pcts =` |
| Sensitivity table columns | your price × (1 ± 4 steps) | `const prices =` |
| Sensitivity PLC row | `plcPay` at each column price | `function renderTable` |
| "ARC-CO − PLC" view | ARC-CO cell minus PLC at the same price | `function renderTable` |
| Charts | `arcPay` / `plcPay` over a grid of prices and yields | `function renderCharts` |

The default county is set on the `const DEFAULT =` line (currently `{ fips:27127, crop:"Corn" }`).

---

## 4. How to audit, step by step

**Step 1 – Read the build report** (`data/build_report.txt`). Check that:
- the FSA file and results file named at the top are the ones you expect;
- the four **cross-checks** show 0 rows over tolerance. They confirm, within the FSA file itself, that S = Q × R, T = 90% × S, U = 12% × S, and that the national price in column W equals the PLC rates tab's projected MYA price;
- there are no unexpected **NOTE** lines about columns that moved;
- the **estimations merge** counts look right, and you've reviewed the listed benchmark mismatches.

**Step 2 – Spot-check inputs against the FSA workbook.** Pick a few counties. Find each row in `data/app_inputs_audit.csv` and compare its columns with the same row of the Main tab; the column letters are in the headers. Then open the app for the same county / crop / practice and compare:
- Benchmark yield, benchmark price, PLC yield and effective reference price (the strip under the payment boxes);
- the default yield and price in the input boxes;
- the History bars.

**Step 3 – Check the payment math.** With the app at its defaults ("Reset to defaults"), the ARC-CO and PLC boxes must equal the audit table columns `ARC-CO at defaults` and `PLC at defaults`. Those are computed in Python by `arcplc.py`, independently of the page.

Worked example, **Redwood County, MN · Oats · All** (FSA 20261012):

| Item | Value | Source |
|---|---|---|
| Benchmark yield | 88.52 bu | Main!Q |
| Benchmark price | $3.94 | Main!R |
| Default yield | 93.08 bu | Main!V |
| Default price | $3.35 | Main!W |
| Loan rate / ERP | $2.20 / $3.05 | PLC rates!I / F |
| Benchmark revenue | 88.52 × 3.94 = $348.77 | |
| Guarantee (90%) | $313.89 | |
| Actual revenue | 93.08 × max(3.35, 2.20) = $311.82 | |
| Shortfall | $2.07 (below the 12% cap of $41.85) | |
| **ARC-CO** | 2.07 × 0.85 = **$1.76** per base acre | matches the app |
| **PLC** | max(3.05 − 3.35, 0) × 71.32 × 0.85 = **$0.00** | matches the app |

**Step 4 (optional) – Check the page's JavaScript against Python on every row.** With Node.js installed:

```bash
node tools/check_formulas.js docs/index.html data/app_inputs_audit.csv
```

It recomputes all rows with the page's own formula lines and compares them with the Python results. At the 20261012 build: 18,850 rows, 0 mismatches. The largest difference was 0.5 cents, from rounding in the CSV.

**Step 5 – Check the estimations.** For a corn, soybean or wheat county, the four numbers in "Our estimations" must equal the `Est.` / `Chance` columns in the audit table. Those come straight from the results file; the app does not recalculate them.

---

## 5. Known data notes (build of 2026-10-12)

- **Rice (temperate japonica)** has no benchmark price in Main column R (16 rows). The app shows ARC-CO as n/a with a note; PLC is calculated normally.
- **Sub-counties:** Chouteau, MT and Umatilla, OR appear as separate "(A)" / "(B)" entries, as in the FSA file, and get no estimations.
- **17 rows** where the results file's benchmark yield differs from FSA column Q (up to about 22 bu). These are listed in the build report, and the app shows a note on those pages. The estimates there were simulated with the results file's benchmark.
- **149 results-file rows** have no matching FSA row (county / crop / practice not in the FSA file), so they never appear in the app. They are listed in the build report.
- The results file has **no PLC estimate** for many irrigated / non-irrigated rows; the app shows "not estimated".
- **Yields file conflicts:** 1,730 county / crop / practice / years have two different actual yields; the first is used (see `data/yield_conflicts.csv`).

---

## 6. Updating the data

1. Save the new FSA workbook in `data/` as `FSAInputData_YYYYMMDD.xlsx`. The build always uses the newest name. Keep the same tab names (`Main`, `PLC rates`, `lookups`) and header texts. Column positions can change.
2. For new simulation results, save the CSV in `data/` as `Detailed_Results_….csv`. For new actual yields, save `FSA_yields_….feather`. In both cases the name that sorts last is used.
3. Run `python web/build.py`. You need Python with pandas, numpy, openpyxl and pyarrow (`pip install -r requirements.txt`).
4. Read `data/build_report.txt`, then upload `docs/index.html` (plus the data files and the two audit outputs, if you keep them in the repo).

To use specific files instead of the newest:

```bash
python web/build.py --fsa data/FSAInputData_20261012.xlsx --results data/Detailed_Results_2026_ncsa_09142026.csv --yields data/FSA_yields_2009-2025_0807.feather
```
