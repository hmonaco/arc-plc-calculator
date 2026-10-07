"""ARC-CO / PLC payment calculator — Streamlit MVP.

Run locally:   streamlit run app.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from arcplc import arc_co_payment, plc_payment, sensitivity

DATA_DIR = Path(__file__).parent / "data"
RESULTS_FILE = DATA_DIR / "Detailed_Results_2026_ncsa_09142026.csv"
COUNTY_FILE = DATA_DIR / "counties.csv"
CROP_YEAR = 2026
HIST_YEARS = [2020, 2021, 2022, 2023, 2024]

UNITS = {  # crop: (yield unit, price unit, price decimals)
    "Corn": ("bu", "$/bu", 2), "Soybean": ("bu", "$/bu", 2),
    "Wheat": ("bu", "$/bu", 2), "Sorghum": ("bu", "$/bu", 2),
    "Seed Cotton": ("lb", "$/lb", 3), "Peanut": ("lb", "$/lb", 3),
    "Rice": ("lb", "$/lb", 3),
}
PRACTICE_LABELS = {"All": "All", "Irrigated": "Irrigated",
                   "Nonirrigated": "Non-irrigated", "PLC only": "PLC yield only (no ARC benchmark)"}
ARC_COLOR, PLC_COLOR = "#13294B", "#E84A27"

st.set_page_config(page_title="ARC-CO / PLC Calculator", page_icon="🌽", layout="wide")


# ---------------------------------------------------------------- data
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_FILE)
    df["YieldType"] = df["YieldType"].fillna("PLC only")
    counties = pd.read_csv(COUNTY_FILE)
    states = counties.drop_duplicates("postal").assign(sfips=lambda d: d.fips // 1000)
    df = df.merge(counties, on="fips", how="left")
    # FSA administrative counties without a Census match: fall back to the FIPS code
    miss = df["county"].isna()
    sf = states.set_index("sfips")
    df.loc[miss, "state"] = (df.loc[miss, "fips"] // 1000).map(sf["state"])
    df.loc[miss, "postal"] = (df.loc[miss, "fips"] // 1000).map(sf["postal"])
    df.loc[miss, "county"] = "FSA county " + df.loc[miss, "fips"].astype(str)
    return df


df = load_data()

# ---------------------------------------------------------------- sidebar: selection
st.sidebar.title("Select")
states = sorted(df["state"].dropna().unique())
state = st.sidebar.selectbox("State", states,
                             index=states.index("Minnesota") if "Minnesota" in states else 0)
sdf = df[df["state"] == state]
counties = sorted(sdf["county"].unique())
county = st.sidebar.selectbox("County", counties)
cdf = sdf[sdf["county"] == county]
crop = st.sidebar.selectbox("Crop", sorted(cdf["Commodity"].unique()))
pdf_ = cdf[cdf["Commodity"] == crop]
practices = [p for p in ["All", "Nonirrigated", "Irrigated", "PLC only"] if p in set(pdf_["YieldType"])]
practice = st.sidebar.selectbox("Practice", practices, format_func=PRACTICE_LABELS.get)
row = pdf_[pdf_["YieldType"] == practice].iloc[0]

y_unit, p_unit, pdec = UNITS.get(crop, ("unit", "$/unit", 2))
has_arc = pd.notna(row["Avg. Benchmark Yield"])
loan = float(row["Mkt Loan Rate"])
erp = float(row["Avg. Eff.Ref.Price"])
plc_yield = row["PLC Yield"]
plc_note = ""
if pd.isna(plc_yield):  # practice rows often carry no PLC yield: fall back to another row of the same county/crop
    alt = pdf_["PLC Yield"].dropna()
    plc_yield = alt.iloc[0] if len(alt) else np.nan
    if len(alt):
        plc_note = "PLC yield not reported for this practice; using the county's PLC yield for the crop."
plc_yield = float(plc_yield)
has_plc = not np.isnan(plc_yield)
by = float(row["Avg. Benchmark Yield"]) if has_arc else np.nan
bp = float(row["Avg. Benchmark Price"])
br = by * bp if has_arc else np.nan

st.sidebar.caption(f"FIPS {int(row['fips']):05d}")

# ---------------------------------------------------------------- header
st.title(f"{CROP_YEAR} ARC-CO / PLC payment calculator")
st.markdown(f"**{county}, {row['postal']}** · {crop} · {PRACTICE_LABELS[practice]}")

c = st.columns(6)
c[0].metric("Benchmark yield", f"{by:,.1f} {y_unit}" if has_arc else "—")
c[1].metric("Benchmark price", f"${bp:,.{pdec}f}")
c[2].metric("Benchmark revenue", f"${br:,.0f}/ac" if has_arc else "—")
c[3].metric("ARC guarantee (90%)", f"${0.9 * br:,.0f}/ac" if has_arc else "—")
c[4].metric("Effective ref. price", f"${erp:,.{pdec}f}")
c[5].metric("PLC yield", f"{plc_yield:,.1f} {y_unit}" if has_plc else "—", help=plc_note or None)
if plc_note:
    st.caption("ℹ️ " + plc_note)

st.divider()

# ---------------------------------------------------------------- inputs
st.subheader("Your inputs")
i1, i2, _ = st.columns([1, 1, 2])
default_y = float(row["2026 Avg. Actual Yields"]) if pd.notna(row["2026 Avg. Actual Yields"]) else (by if has_arc else 0.0)
default_p = float(row["2026 Avg. Actual Price"])
key = f"{row['fips']}-{crop}-{practice}"  # reset inputs when the selection changes
act_y = i1.number_input(f"{CROP_YEAR} county yield ({y_unit}/ac)", min_value=0.0,
                        value=round(default_y, 1), step=1.0, key="y" + key, disabled=not has_arc,
                        help="FSA county yield used for ARC-CO. Defaults to the model's expected yield.")
mya = i2.number_input(f"{CROP_YEAR} MYA price ({p_unit})", min_value=0.0,
                      value=round(default_p, pdec), step=0.05 if pdec == 2 else 0.005,
                      format=f"%.{pdec}f", key="p" + key,
                      help="Marketing-year average price. Defaults to the model's expected price.")

arc_pay = float(arc_co_payment(act_y, mya, by, bp, loan)) if has_arc else np.nan
plc_pay = float(plc_payment(mya, erp, loan, plc_yield)) if has_plc else np.nan

# ---------------------------------------------------------------- results
st.subheader("Estimated payments ($ per base acre)")
r = st.columns(4)
r[0].metric("ARC-CO", f"${arc_pay:,.2f}" if has_arc else "n/a")
r[1].metric("PLC", f"${plc_pay:,.2f}" if has_plc else "n/a")
if has_arc and has_plc:
    diff = arc_pay - plc_pay
    better = "ARC-CO" if diff > 0 else "PLC" if diff < 0 else "Tie"
    r[2].metric("Higher payment", better, f"${abs(diff):,.2f}/ac", delta_color="off")
r[3].metric("Actual revenue", f"${act_y * max(mya, loan):,.0f}/ac" if has_arc else "—")

with st.expander("Model expectations from the stochastic simulation (not affected by your inputs)"):
    e = st.columns(4)
    e[0].metric("Expected ARC-CO", f"${row['2026 Avg. ARC-CO Pmt']:,.2f}" if has_arc else "n/a")
    e[1].metric("Expected PLC", f"${row['2026 Avg. PLC Pmt']:,.2f}" if pd.notna(row['2026 Avg. PLC Pmt']) else "n/a")
    e[2].metric("P(ARC-CO pays)", f"{row['2026 ARC-CO Pmt Likelihood']:.0%}" if has_arc else "n/a")
    e[3].metric("P(PLC pays)", f"{row['2026 PLC Pmt Likelihood']:.0%}" if pd.notna(row['2026 PLC Pmt Likelihood']) else "n/a")
    st.caption("Averages over simulated yield and price outcomes. They differ from the payment at the "
               "average yield and price because they include the uncertainty in markets and yields.")

st.divider()

# ---------------------------------------------------------------- sensitivity + charts
tab_sens, tab_charts, tab_hist = st.tabs(["Sensitivity table", "Charts", "History"])

with tab_sens:
    s1, s2, _ = st.columns([1, 1, 2])
    y_step = s1.select_slider("Yield step (% of benchmark)", [2.5, 5.0, 10.0], value=5.0)
    p_step = s2.select_slider("Price step (% of your MYA)", [2.5, 5.0, 10.0], value=5.0)
    p_grid = mya * (1 + p_step / 100 * np.arange(-4, 5))
    if has_arc:
        y_grid = by * (1 + y_step / 100 * np.arange(-6, 5))
        arc_g, plc_r = sensitivity(by, bp, erp, loan, plc_yield, y_grid, p_grid)
        cols = [f"${p:,.{pdec}f}" for p in p_grid]
        idx = [f"{y:,.1f} ({y / by:.0%})" for y in y_grid]
        tbl = pd.DataFrame(arc_g, index=idx, columns=cols)
        tbl.index.name = f"County yield ({y_unit})"
        if has_plc:
            tbl.loc["PLC payment"] = plc_r
        st.markdown(f"**ARC-CO payment ($/base acre)** by county yield (rows) and MYA price (columns); "
                    f"last row is PLC.")
        sty = tbl.style.format("{:,.2f}").background_gradient(
            cmap="Blues", axis=None, subset=pd.IndexSlice[[i for i in tbl.index if i != "PLC payment"], :])
        if has_plc:
            sty = sty.background_gradient(cmap="Oranges", axis=None, subset=pd.IndexSlice[["PLC payment"], :])
        st.dataframe(sty, width="stretch")
        st.download_button("Download table (CSV)", tbl.to_csv().encode(),
                           f"arcplc_sensitivity_{int(row['fips']):05d}_{crop}_{practice}.csv")
    else:
        plc_r = plc_payment(p_grid, erp, loan, plc_yield)
        st.dataframe(pd.DataFrame({"MYA price": p_grid, "PLC payment": plc_r}).style.format(
            {"MYA price": f"${{:,.{pdec}f}}", "PLC payment": "${:,.2f}"}), hide_index=True)

with tab_charts:
    ch1, ch2 = st.columns(2)
    # Chart 1: payment vs MYA price at the entered yield
    lo = min(loan, mya) * 0.95
    hi = max(erp, bp, mya) * 1.3
    px = np.linspace(lo, hi, 200)
    fig = go.Figure()
    if has_arc:
        fig.add_scatter(x=px, y=arc_co_payment(act_y, px, by, bp, loan), name=f"ARC-CO (yield {act_y:,.1f})",
                        line=dict(color=ARC_COLOR, width=3))
    if has_plc:
        fig.add_scatter(x=px, y=plc_payment(px, erp, loan, plc_yield), name="PLC",
                        line=dict(color=PLC_COLOR, width=3))
    fig.add_vline(x=mya, line_dash="dot", annotation_text="your MYA", annotation_position="top")
    fig.add_vline(x=erp, line_dash="dash", line_color="gray", annotation_text="eff. ref. price",
                  annotation_position="bottom right")
    fig.update_layout(title="Payment vs. MYA price", xaxis_title=f"MYA price ({p_unit})",
                      yaxis_title="$ per base acre", legend=dict(orientation="h", y=-0.2),
                      margin=dict(t=50, b=10), height=420)
    ch1.plotly_chart(fig, width="stretch")

    # Chart 2: where does ARC beat PLC? (ARC - PLC over yield x price)
    if has_arc and has_plc:
        yy = np.linspace(by * 0.6, by * 1.2, 61)
        pp = np.linspace(lo, hi, 61)
        a, p = sensitivity(by, bp, erp, loan, plc_yield, yy, pp)
        d = a - p[None, :]
        m = np.abs(d).max() or 1
        hm = go.Figure(go.Heatmap(x=pp, y=yy, z=d, zmin=-m, zmax=m, colorscale=[[0, PLC_COLOR], [0.5, "#f7f7f7"], [1, ARC_COLOR]],
                                  colorbar=dict(title="ARC − PLC<br>$/ac"),
                                  hovertemplate="price %{x:.3f}<br>yield %{y:.1f}<br>ARC−PLC $%{z:.2f}<extra></extra>"))
        hm.add_scatter(x=[mya], y=[act_y], mode="markers", marker=dict(size=12, color="black", symbol="x"),
                       name="your inputs", showlegend=False)
        hm.update_layout(title="ARC-CO minus PLC (blue = ARC higher, orange = PLC higher)",
                         xaxis_title=f"MYA price ({p_unit})", yaxis_title=f"County yield ({y_unit}/ac)",
                         margin=dict(t=50, b=10), height=420)
        ch2.plotly_chart(hm, width="stretch")

with tab_hist:
    hy = [row.get(f"{y} Yields") for y in HIST_YEARS]
    hp = [row.get(f"{y} MYA Price") for y in HIST_YEARS]
    h1, h2 = st.columns(2)
    if has_arc:
        f1 = go.Figure(go.Bar(x=HIST_YEARS, y=hy, marker_color=ARC_COLOR, name="County yield"))
        f1.add_hline(y=by, line_dash="dash", annotation_text=f"benchmark {by:,.1f}")
        f1.update_layout(title="County yields used in the benchmark", yaxis_title=f"{y_unit}/ac", height=380)
        h1.plotly_chart(f1, width="stretch")
    f2 = go.Figure(go.Bar(x=HIST_YEARS, y=hp, marker_color=PLC_COLOR, name="MYA price"))
    f2.add_hline(y=bp, line_dash="dash", annotation_text=f"benchmark {bp:,.{pdec}f}")
    f2.add_hline(y=erp, line_dash="dot", line_color="gray", annotation_text=f"eff. ref. {erp:,.{pdec}f}",
                 annotation_position="bottom right")
    f2.update_layout(title="National MYA prices", yaxis_title=p_unit, height=380)
    h2.plotly_chart(f2, width="stretch")
    st.caption("Benchmark yield and price are Olympic averages of the 2020–2024 values "
               "(yields include any plug/T-yield substitution).")

st.divider()
st.caption("Payments are per base acre and include the 85% payment-acre factor. ARC-CO: 90% guarantee, "
           "12% maximum payment rate. Before sequestration and payment limits. For educational purposes only.")
