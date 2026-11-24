"""Building Energy Forecast — interactive dashboard for the TBDA Group 2 forecasting models.

Final model: Blend v1.3 (weighted average of Gradient Boosting v1.3, ChronosGBM v1.3 and Chronos-Bolt v1.3).
The app replays the frozen forecasts stored in the project folder; it does not run live models.

Run:   streamlit run ux_app/app.py
Data:  TBDA_DATA_DIR=/path/to/TBDA_v1.3_ChronosGBM_29-10  (default: ../TBDA_v1.3_ChronosGBM_29-10)
"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("TBDA_DATA_DIR", Path(__file__).resolve().parents[1] / "TBDA_v1.3_ChronosGBM_29-10"))
RES, MODELS_DIR = DATA_DIR / "results", DATA_DIR / "models"
KEYS = ["series_id", "horizon", "issue_time", "target_time", "lead"]

HORIZONS = {
    "+1 hour": "+1h",
    "+6 hours": "+6h",
    "Day-ahead (next 24 h)": "day-ahead",
}
HORIZON_HELP = {
    "+1h": "Forecast for the next hour, issued every hour.",
    "+6h": "Forecast for 6 hours ahead, issued every hour.",
    "day-ahead": "The 24 hours of the next day, issued once a day at 00:00 UTC.",
}
MODEL_INFO = {
    "blend": dict(label="Blend v1.3 (final model)", color="#F26B21", dash="solid", width=3.4),
    "gbm": dict(label="Gradient Boosting v1.3", color="#2E9E5B", dash="solid", width=2),
    "chronosgbm": dict(label="ChronosGBM v1.3", color="#7B4FD1", dash="solid", width=2),
    "chronos": dict(label="Chronos-Bolt v1.3", color="#0FA3B1", dash="solid", width=2),
    "b1": dict(label="Baseline A – same hour last week", color="#9CA3AF", dash="dot", width=1.8),
    "b2": dict(label="Baseline B – weekday × hour median", color="#4B5563", dash="dot", width=2),
    "b3": dict(label="Baseline C – persistence", color="#A0522D", dash="dot", width=1.8),
}
BASELINES = ["b2", "b1", "b3"]
ZONE_COLORS = {"NE": "#2563EB", "NW": "#F26B21", "SE": "#2E9E5B", "SW": "#7B4FD1"}
ACTUAL_COLOR = "#0B1F3A"

DATASETS = {
    "Validation week — 22–28 Sep 2025": "validation",
    "Test week — 29 Sep–5 Oct 2025": "test",
}
# Official results on the TEST week, all 16 circuits, MAE in Wh (source: RESULTS.md, Task 6).
OFFICIAL_TEST = [
    ("Blend v1.3 (final model)", 22.2, 34.7, 34.2),
    ("Chronos-Bolt v1.3", 21.5, 36.9, 36.2),
    ("ChronosGBM v1.3", 24.7, 34.2, 35.9),
    ("Gradient Boosting v1.3", 26.3, 37.1, 35.7),
    ("Random Forest", 27.7, 37.4, 37.4),
    ("Linear Regression", 25.1, 39.4, 39.7),
    ("Baseline C – persistence", 24.0, 57.8, 41.5),
    ("Baseline B – weekday × hour median", 43.7, 43.7, 43.7),
    ("Baseline A – same hour last week", 59.1, 59.1, 59.1),
]

st.set_page_config(page_title="Building Energy Forecast", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ----------------------------------------------------------------------------
# STYLE (HTML / CSS)
# ----------------------------------------------------------------------------
CSS = """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1500px;}
footer {visibility: hidden;}
.hero {background: linear-gradient(120deg,#0B1F3A 0%,#12365F 55%,#1D5C9E 100%); color:#fff; padding:26px 32px;
       border-radius:16px; margin-bottom:18px; box-shadow:0 6px 22px rgba(11,31,58,.25);}
.hero h1 {margin:0; font-size:2.0rem; font-weight:700; color:#fff; letter-spacing:-.5px;}
.hero p {margin:6px 0 14px 0; color:#CFE0F5; font-size:1.0rem;}
.pill {display:inline-block; padding:4px 12px; margin:0 8px 6px 0; border-radius:999px; font-size:.78rem; font-weight:600;
       background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.28); color:#fff;}
.pill.orange {background:#F26B21; border-color:#F26B21;}
.kpi-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:6px 0 18px 0;}
.kpi {background:#fff; border-radius:12px; padding:14px 16px 12px 16px; box-shadow:0 2px 10px rgba(11,31,58,.10);
      border:1px solid #E5EAF1;}
.kpi-t {font-size:.74rem; text-transform:uppercase; letter-spacing:.6px; color:#5B6B82; font-weight:700;}
.kpi-v {font-size:1.85rem; font-weight:700; color:#0B1F3A; line-height:1.25; margin-top:2px;}
.kpi-s {font-size:.82rem; color:#5B6B82; margin-top:2px; min-height:1.1em;}
.kpi-s .good {color:#15803D; font-weight:700;} .kpi-s .bad {color:#B91C1C; font-weight:700;}
.callout {background:#EEF5FF; border-left:5px solid #1D5C9E; color:#0B1F3A; padding:12px 16px; border-radius:8px;
          margin:8px 0 14px 0; font-size:.95rem; line-height:1.55;}
.callout.warn {background:#FFF6E5; border-left-color:#F59E0B;}
.callout.ok {background:#EAF8EF; border-left-color:#16A34A;}
.callout b {color:#0B1F3A;}
.section {font-size:1.15rem; font-weight:700; margin:18px 0 4px 0;}
.sub {color:#6B7A90; font-size:.9rem; margin-bottom:8px;}
.legend {margin:2px 0 8px 0;} .chip {display:inline-block; margin:0 14px 4px 0; font-size:.82rem;}
.chip i {display:inline-block; width:22px; height:0; border-top:3px solid; vertical-align:middle; margin-right:6px;}
.chip i.dot {border-top-style:dotted;} .chip i.dash {border-top-style:dashed;}
.small {font-size:.82rem; color:#6B7A90;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x))


def callout(text_html: str, kind: str = "") -> None:
    st.markdown(f'<div class="callout {kind}">{text_html}</div>', unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="section">{esc(title)}</div>' + (f'<div class="sub">{esc(sub)}</div>' if sub else ""),
                unsafe_allow_html=True)


def kpi_card(title: str, value: str, sub: str = "", accent: str = "#F26B21", tip: str = "") -> str:
    return (f'<div class="kpi" style="border-top:4px solid {accent}" title="{esc(tip)}">'
            f'<div class="kpi-t">{esc(title)}</div><div class="kpi-v">{esc(value)}</div><div class="kpi-s">{sub}</div></div>')


def legend_html(items: list[tuple[str, str, str]]) -> str:
    chips = "".join(f'<span class="chip"><i class="{d}" style="border-color:{c}"></i>{esc(l)}</span>' for l, c, d in items)
    return f'<div class="legend">{chips}</div>'


# ----------------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------------
def _read(name: str) -> pd.DataFrame:
    return pd.read_parquet(RES / f"{name}.parquet")


@st.cache_data(show_spinner="Loading forecasts…")
def load_wide(dataset: str) -> pd.DataFrame:
    """One row per circuit × horizon × target hour, one column per model."""
    if dataset == "validation":
        wide = _read("blend_validation_predictions_v1.3")[KEYS + ["y_true", "y_pred"]].rename(columns={"y_pred": "blend"})
        base = _read("task8_validation_predictions_v1.3")
        for model, col in {"ML_GBM": "gbm", "B1_last_week": "b1", "B2_weekday_hour_median": "b2", "B3_persistence": "b3"}.items():
            s = base.loc[base["model"] == model, KEYS + ["y_pred"]].drop_duplicates(KEYS).rename(columns={"y_pred": col})
            wide = wide.merge(s, on=KEYS, how="left")
        hyb = _read("hybrid_validation_predictions_v1.3")[KEYS + ["y_pred"]].drop_duplicates(KEYS)
        wide = wide.merge(hyb.rename(columns={"y_pred": "chronosgbm"}), on=KEYS, how="left")
        chr_ = _read("chronos_validation_predictions_v1.3")[KEYS + ["y_pred", "q10", "q90"]].drop_duplicates(KEYS)
        wide = wide.merge(chr_.rename(columns={"y_pred": "chronos"}), on=KEYS, how="left")
    else:
        wide = _read("chronos_test_predictions_v1.3")[KEYS + ["y_true", "y_pred", "q10", "q90"]].rename(columns={"y_pred": "chronos"})
    wide[["zone", "circuit"]] = wide["series_id"].str.split("|", n=1, expand=True)
    for c in wide.columns:
        if wide[c].dtype == "float32":
            wide[c] = wide[c].astype("float64")
    return wide.sort_values(["horizon", "target_time", "series_id"]).reset_index(drop=True)


@st.cache_data
def load_config() -> dict:
    return json.loads((MODELS_DIR / "blend_frozen_config_v1.3.json").read_text())


def model_cols(df: pd.DataFrame) -> list[str]:
    return [m for m in MODEL_INFO if m in df.columns]


def _localize(ts: pd.Series, tz: str) -> pd.Series:
    return ts.dt.tz_convert(tz).dt.tz_localize(None)


@st.cache_data
def aggregate(dataset: str, horizon: str, circuits: tuple, tz: str) -> pd.DataFrame:
    """Hourly total of the selected circuits (sum), one column per model."""
    w = load_wide(dataset)
    d = w[(w["horizon"] == horizon) & (w["series_id"].isin(circuits))]
    n = len(circuits)
    cols = ["y_true"] + model_cols(d)
    g = d.groupby("target_time")[cols].sum(min_count=n)  # a total needs every selected circuit to be valid
    if n == 1:
        g["q10"] = d.groupby("target_time")["q10"].first()
        g["q90"] = d.groupby("target_time")["q90"].first()
    g = g.reset_index()
    g["t"] = _localize(g["target_time"], tz)
    g["day"] = g["t"].dt.strftime("%Y-%m-%d")
    g["hour"] = g["t"].dt.hour
    return g


@st.cache_data
def per_circuit(dataset: str, horizon: str, circuits: tuple, tz: str) -> pd.DataFrame:
    w = load_wide(dataset)
    d = w[(w["horizon"] == horizon) & (w["series_id"].isin(circuits))].copy()
    d["t"] = _localize(d["target_time"], tz)
    d["day"] = d["t"].dt.strftime("%Y-%m-%d")
    return d


def metrics(g: pd.DataFrame, col: str) -> dict:
    m = g[[col, "y_true"]].dropna()
    if m.empty:
        return dict(mae=np.nan, rmse=np.nan, bias=np.nan, n=0, mean_actual=np.nan)
    e = m[col] - m["y_true"]
    return dict(mae=e.abs().mean(), rmse=float(np.sqrt((e ** 2).mean())), bias=e.mean(), n=len(m), mean_actual=m["y_true"].mean())


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def nice(c: str) -> str:
    return c.replace("|", " · ")


def fmt(v: float, scale: float, unit: str, sign: bool = False) -> str:
    if v is None or not np.isfinite(v):
        return "—"
    x = v / scale
    s = f"{x:+,.2f}" if (scale == 1000 and sign) else f"{x:,.2f}" if scale == 1000 else f"{x:+,.0f}" if sign else f"{x:,.0f}"
    return f"{s} {unit}"


def pct_delta_html(model_mae: float, ref_mae: float, ref_label: str) -> str:
    if not (np.isfinite(model_mae) and np.isfinite(ref_mae) and ref_mae > 0):
        return ""
    gain = (1 - model_mae / ref_mae) * 100
    cls, word = ("good", "lower") if gain >= 0 else ("bad", "higher")
    return f'<span class="{cls}">{abs(gain):.0f}% {word}</span> error than {esc(ref_label)}'


def base_layout(fig: go.Figure, height: int, ytitle: str) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", template="plotly_white",
                      paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#0B1F3A"),
                      yaxis_title=ytitle, legend=dict(orientation="h", y=1.1, x=0, font=dict(size=12)))
    fig.update_xaxes(showgrid=True, gridcolor="#EEF1F6")
    fig.update_yaxes(showgrid=True, gridcolor="#EEF1F6", zeroline=False)
    return fig


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
try:
    config = load_config()
    _ = load_wide("validation")
except FileNotFoundError as exc:
    st.error(f"Model files not found: `{exc.filename}`. Folder searched: `{DATA_DIR}`. "
             f"Set `TBDA_DATA_DIR` to the `TBDA_v1.3_ChronosGBM_29-10` folder.")
    st.stop()

sb = st.sidebar
sb.markdown("### ⚙️ Controls")

sb.markdown("**1 · Data period**")
dataset_label = sb.radio("Data period", list(DATASETS), key="dataset", label_visibility="collapsed")
dataset = DATASETS[dataset_label]
wide_all = load_wide(dataset)
available = model_cols(wide_all)

sb.markdown("**2 · Forecast horizon**")
horizon_label = sb.radio("Forecast horizon", list(HORIZONS), key="horizon", label_visibility="collapsed")
horizon = HORIZONS[horizon_label]
sb.caption(HORIZON_HELP[horizon])

sb.markdown("**3 · What to look at**")
all_circuits = sorted(wide_all["series_id"].unique())
all_zones = sorted(wide_all["zone"].unique())
scope_mode = sb.radio("Scope", ["Whole building", "Zones", "Circuits"], key="scope_mode", horizontal=True,
                      label_visibility="collapsed")
if scope_mode == "Zones":
    zsel = sb.multiselect("Zones", all_zones, default=["NW"], key="zones")
    circuits = tuple(c for c in all_circuits if c.split("|")[0] in zsel)
    scope_name = ("Zone " + " + ".join(zsel)) if zsel else ""
elif scope_mode == "Circuits":
    csel = sb.multiselect("Circuits", all_circuits, default=["NW|Plugs & Sockets"], format_func=nice, key="circuits")
    circuits = tuple(csel)
    scope_name = nice(csel[0]) if len(csel) == 1 else f"{len(csel)} circuits"
else:
    circuits, scope_name = tuple(all_circuits), "Whole building"
if not circuits:
    sb.warning("Nothing selected — showing the whole building.")
    circuits, scope_name = tuple(all_circuits), "Whole building"
if len(circuits) > 1:
    scope_name += f" ({len(circuits)} circuits)" if scope_mode != "Circuits" else ""

tz_label = sb.radio("Time zone", ["UTC", "Madrid"], key="tz", horizontal=True,
                    help="Day-ahead forecasts are issued at 00:00 UTC. In Madrid time a 'day' starts at 01:00/02:00.")
tz = "UTC" if tz_label == "UTC" else "Europe/Madrid"

g_all = aggregate(dataset, horizon, circuits, tz)
days = sorted(g_all["day"].unique())
day = sb.select_slider("Day to inspect", options=days, value=days[len(days) // 2], key="day")

sb.markdown("**4 · Models**")
default_primary = "blend" if "blend" in available else available[0]
primary = sb.selectbox("Forecast model", available, index=available.index(default_primary), key="primary",
                       format_func=lambda m: MODEL_INFO[m]["label"])
others = [m for m in available if m != primary]
compare = sb.multiselect("Compare with", others, default=[m for m in ["b2"] if m in others], key="compare",
                         format_func=lambda m: MODEL_INFO[m]["label"])
ref_options = [m for m in BASELINES if m in available]
ref = sb.selectbox("Reference for gains and alerts", ref_options if ref_options else [None], key="ref",
                   format_func=lambda m: MODEL_INFO[m]["label"] if m else "not available in this period",
                   help="Baselines are simple methods: a useful model must beat them.") if ref_options else None
single = len(circuits) == 1 and "q10" in g_all.columns
show_band = sb.checkbox("Show uncertainty band (Chronos-Bolt, 10–90%)", value=False, key="band",
                        disabled=not single or "chronos" not in available,
                        help="Only for a single circuit: the band comes from Chronos-Bolt, one component of the Blend.")

sb.markdown("**5 · Display**")
unit_choice = sb.radio("Units", ["Auto", "Wh", "kWh"], key="units", horizontal=True,
                       help="Energy per hour. 1 kWh = 1000 Wh.")
with sb.expander("🚨 Alert settings"):
    thr_pct = st.slider("Alert when forecast is above the reference by more than (%)", 5, 200, 30, 5, key="thr")
    min_pct = st.slider("…and the excess is at least (% of average load)", 0, 30, 5, 1, key="minpct",
                        help="Ignores tiny absolute differences when the reference is close to zero.")
if sb.button("🔄 Reload data", width="stretch"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# DERIVED VALUES
# ----------------------------------------------------------------------------
mean_load = g_all["y_true"].mean()
if not np.isfinite(mean_load):
    mean_load = g_all[primary].mean()
if unit_choice == "kWh" or (unit_choice == "Auto" and mean_load >= 1000):
    scale, unit = 1000.0, "kWh"
else:
    scale, unit = 1.0, "Wh"
ylab = f"Energy ({unit} per hour)"
yfmt = ".2f" if scale == 1000 else ",.0f"

g_all = g_all.copy()
if ref:
    g_all["pct_over"] = np.where(g_all[ref] > 0, (g_all[primary] - g_all[ref]) / g_all[ref] * 100, np.nan)
    g_all["alert"] = (g_all["pct_over"] > thr_pct) & ((g_all[primary] - g_all[ref]) >= min_pct / 100 * mean_load)
else:
    g_all["pct_over"], g_all["alert"] = np.nan, False

cur = g_all[g_all["day"] == day].copy()
prev_day = (pd.Timestamp(day) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
prev = g_all[g_all["day"] == prev_day]
P = MODEL_INFO[primary]["label"]
R = MODEL_INFO[ref]["label"] if ref else ""

# ----------------------------------------------------------------------------
# HERO
# ----------------------------------------------------------------------------
w = config["horizons"][horizon]
pills = (f'<span class="pill orange">Final model: Blend v1.3</span>'
         f'<span class="pill">{esc(dataset_label)}</span><span class="pill">Horizon: {esc(horizon_label)}</span>'
         f'<span class="pill">{esc(scope_name)}</span>')
st.markdown(f'<div class="hero"><h1>⚡ Building Energy Forecast</h1>'
            f'<p>How much electricity will the building use — and how far can we trust the forecast?</p>{pills}</div>',
            unsafe_allow_html=True)

if dataset == "test":
    callout("<b>Test week — Chronos-Bolt only.</b> The repository stores the test-week forecasts of one Blend component "
            "(Chronos-Bolt v1.3) but not of the Blend itself, nor of the baselines. Gains and alerts are therefore "
            "unavailable here. Official Blend results on the test week are in the <b>About</b> tab.", "warn")
else:
    callout("<b>Replay mode.</b> These are the frozen forecasts for the <b>validation week</b>, the week used to "
            "<i>choose</i> the final model. Errors here are usually a little lower than on the unseen test week "
            f"(official test MAE of the Blend: {OFFICIAL_TEST[0][1]} / {OFFICIAL_TEST[0][2]} / {OFFICIAL_TEST[0][3]} Wh "
            "at +1 h / +6 h / day-ahead). Times are in "
            f"{'UTC' if tz == 'UTC' else 'Madrid time'}; values are energy per hour.")

tab_over, tab_week, tab_models, tab_circ, tab_alert, tab_about = st.tabs(
    ["📈 Overview", "🗓️ Week view", "🏆 Model comparison", "🔌 Circuits", "🚨 Alerts", "ℹ️ About"])

# ============================================================================
# OVERVIEW
# ============================================================================
with tab_over:
    if cur.empty:
        st.warning("No data for this day and selection.")
    else:
        valid = cur.dropna(subset=["y_true", primary])
        mp = metrics(cur, primary)
        mr = metrics(cur, ref) if ref else None
        peak_f = cur.loc[cur[primary].idxmax()]
        act = cur["y_true"].dropna()
        peak_a = cur.loc[cur["y_true"].idxmax()] if len(act) else None
        n_alerts = int(cur["alert"].sum())

        cards = [
            kpi_card("Actual average load", fmt(act.mean(), scale, unit) if len(act) else "—",
                     f"{len(act)} valid hours of {len(cur)}", ACTUAL_COLOR, "Average measured energy per hour over the day."),
            kpi_card("Forecast average load", fmt(cur[primary].mean(), scale, unit),
                     (f"{(cur[primary].mean() / act.mean() - 1) * 100:+.0f}% vs actual" if len(act) and act.mean() > 0 else ""),
                     MODEL_INFO[primary]["color"], "Average of the selected model's forecasts."),
            kpi_card("Forecast peak", fmt(peak_f[primary], scale, unit), f"expected at {peak_f['t']:%H:%M}",
                     "#7B4FD1", "Highest forecast hour of the day."),
            kpi_card("Actual peak", fmt(peak_a["y_true"], scale, unit) if peak_a is not None else "—",
                     f"measured at {peak_a['t']:%H:%M}" if peak_a is not None else "", ACTUAL_COLOR,
                     "Highest measured hour of the day."),
            kpi_card("Average error (MAE)", fmt(mp["mae"], scale, unit),
                     pct_delta_html(mp["mae"], mr["mae"], R) if mr else "", "#16A34A",
                     "Mean Absolute Error: on average, how far the forecast is from the measurement, per hour. Lower is better."),
            kpi_card("Alert hours", f"{n_alerts} / {len(cur)}",
                     (f"forecast > reference +{thr_pct}%" if ref else "needs a baseline"), "#DC2626",
                     "Hours where the forecast exceeds the reference by more than the threshold set in Alert settings."),
        ]
        st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

        # plain-language summary
        lines = []
        if len(act) and act.mean() > 0:
            d = (cur[primary].mean() / act.mean() - 1) * 100
            lines.append(f"On <b>{esc(day)}</b>, <b>{esc(scope_name)}</b> used <b>{esc(fmt(act.mean(), scale, unit))}</b> per hour on "
                         f"average. {esc(P)} expected <b>{esc(fmt(cur[primary].mean(), scale, unit))}</b> "
                         f"({'close to' if abs(d) < 5 else 'above' if d > 0 else 'below'} the measurement, {d:+.0f}%).")
        if mr and np.isfinite(mp["mae"]) and np.isfinite(mr["mae"]):
            better = mp["mae"] < mr["mae"]
            lines.append(f"The average hourly error was <b>{esc(fmt(mp['mae'], scale, unit))}</b> against "
                         f"<b>{esc(fmt(mr['mae'], scale, unit))}</b> for {esc(R)} — the model was "
                         f"<b>{'more' if better else 'less'} accurate</b> than the reference on this day.")
        if ref:
            lines.append(f"<b>{n_alerts}</b> hour(s) are flagged: forecast more than {thr_pct}% above {esc(R)}." if n_alerts
                         else f"No hour is flagged: the forecast never exceeds {esc(R)} by more than {thr_pct}%.")
        callout("<br>".join(lines), "ok")

        # main chart
        section(f"{scope_name} — {day}", "Solid dark line = what was measured. Dashed colored line = what the model forecast.")
        fig = go.Figure()
        if not prev.empty and prev["y_true"].notna().any():
            fig.add_trace(go.Scatter(x=prev["t"], y=prev["y_true"] / scale, name="Actual (previous day)", mode="lines",
                                     line=dict(color=ACTUAL_COLOR, width=1.4), opacity=0.28, hovertemplate=f"%{{y:{yfmt}}}"))
        if show_band and single and "chronos" in available:
            fig.add_trace(go.Scatter(x=pd.concat([cur["t"], cur["t"][::-1]]),
                                     y=pd.concat([cur["q90"] / scale, (cur["q10"] / scale)[::-1]]),
                                     fill="toself", fillcolor="rgba(15,163,177,.16)", line=dict(width=0),
                                     name="Chronos-Bolt 10–90% range", hoverinfo="skip"))
        order = [m for m in compare if m != primary]
        for m in order:
            mi = MODEL_INFO[m]
            fig.add_trace(go.Scatter(x=cur["t"], y=cur[m] / scale, name=mi["label"], mode="lines",
                                     line=dict(color=mi["color"], width=mi["width"], dash=mi["dash"]),
                                     hovertemplate=f"%{{y:{yfmt}}}"))
        fig.add_trace(go.Scatter(x=cur["t"], y=cur["y_true"] / scale, name="Actual", mode="lines+markers",
                                 line=dict(color=ACTUAL_COLOR, width=3), marker=dict(size=6), connectgaps=False,
                                 hovertemplate=f"%{{y:{yfmt}}}"))
        pi = MODEL_INFO[primary]
        fig.add_trace(go.Scatter(x=cur["t"], y=cur[primary] / scale, name=pi["label"], mode="lines+markers",
                                 line=dict(color=pi["color"], width=3, dash="dash"), marker=dict(size=6),
                                 hovertemplate=f"%{{y:{yfmt}}}"))
        al = cur[cur["alert"]]
        if len(al):
            fig.add_trace(go.Scatter(x=al["t"], y=al[primary] / scale, mode="markers", name="Alert",
                                     marker=dict(color="#DC2626", size=14, symbol="triangle-up", line=dict(color="white", width=1.5)),
                                     hoverinfo="skip"))
        base_layout(fig, 470, ylab)
        fig.update_xaxes(title="Time of day", tickformat="%H:%M")
        st.plotly_chart(fig, width="stretch", theme=None)
        missing = int(cur["y_true"].isna().sum())
        if missing:
            st.caption(f"{missing} hour(s) have no valid sensor reading for this selection, so the actual line has gaps there.")
        if show_band and single:
            st.caption("The shaded range comes from Chronos-Bolt (one component of the Blend): about 8 actual values out of 10 should fall inside it.")

        with st.expander("🧭 How to read this page"):
            st.markdown(
                "- **Dark line** — the real consumption measured by the sensors.\n"
                "- **Orange dashed line** — the forecast of the selected model. The closer to the dark line, the better.\n"
                "- **Grey dotted line** — a simple reference method (a typical value for that weekday and hour). "
                "A useful model must be closer to the dark line than this one.\n"
                "- **Red triangles** — hours where the forecast is clearly above the reference: potential over-consumption to watch.\n"
                "- **MAE** — the average gap between forecast and measurement, in the same unit as the chart. Lower is better.")

        with st.expander("📋 Hour-by-hour table"):
            t = pd.DataFrame({"Time": cur["t"].dt.strftime("%H:%M"), f"Actual ({unit})": cur["y_true"] / scale,
                              f"Forecast ({unit})": cur[primary] / scale})
            if ref:
                t[f"Reference ({unit})"] = cur[ref] / scale
                t["Forecast vs reference"] = cur["pct_over"]
            t[f"Forecast error ({unit})"] = (cur[primary] - cur["y_true"]) / scale
            if ref:
                t["Alert"] = np.where(cur["alert"], "🚨", "")
            t = t.reset_index(drop=True)
            nd = 2 if scale == 1000 else 0
            fm = {c: f"{{:,.{nd}f}}" for c in t.columns if unit in c}
            fm.update({"Forecast vs reference": "{:+.0f}%"})
            sty = t.style.format(fm, na_rep="—")
            if ref:
                sty = sty.apply(lambda r: ["background-color:#FDE2E2;color:#7F1D1D" if r["Alert"] else "" for _ in r], axis=1)
            st.dataframe(sty, width="stretch", height=380, hide_index=True)
            st.download_button("⬇️ Download this day (CSV)", t.to_csv(index=False).encode("utf-8"),
                               file_name=f"forecast_{day}_{horizon}.csv", mime="text/csv")

# ============================================================================
# WEEK VIEW
# ============================================================================
with tab_week:
    section(f"Whole period — {scope_name}", "The full week at a glance. Zoom by dragging on the chart; double-click to reset.")
    fig = go.Figure()
    if ref:
        mi = MODEL_INFO[ref]
        fig.add_trace(go.Scatter(x=g_all["t"], y=g_all[ref] / scale, name=mi["label"], mode="lines",
                                 line=dict(color=mi["color"], width=1.6, dash="dot"), hovertemplate=f"%{{y:{yfmt}}}"))
    fig.add_trace(go.Scatter(x=g_all["t"], y=g_all["y_true"] / scale, name="Actual", mode="lines",
                             line=dict(color=ACTUAL_COLOR, width=2), connectgaps=False, hovertemplate=f"%{{y:{yfmt}}}"))
    fig.add_trace(go.Scatter(x=g_all["t"], y=g_all[primary] / scale, name=P, mode="lines",
                             line=dict(color=MODEL_INFO[primary]["color"], width=2, dash="dash"), hovertemplate=f"%{{y:{yfmt}}}"))
    fig.add_vrect(x0=pd.Timestamp(day), x1=pd.Timestamp(day) + pd.Timedelta(days=1), fillcolor="rgba(29,92,158,.08)", line_width=0,
                  annotation_text="selected day", annotation_position="top left")
    base_layout(fig, 400, ylab)
    st.plotly_chart(fig, width="stretch", theme=None)

    c1, c2 = st.columns(2)
    with c1:
        section("Where are the errors? Circuit × day", f"Average error of {P} ({unit} per hour). Darker = larger error.")
        pc = per_circuit(dataset, horizon, circuits, tz)
        pc["abs_err"] = (pc[primary] - pc["y_true"]).abs() / scale
        hm = pc.pivot_table(index="series_id", columns="day", values="abs_err", aggfunc="mean")
        if hm.empty:
            st.info("No scored hours.")
        else:
            hm = hm.loc[hm.mean(axis=1).sort_values().index]
            zf = ".2f" if scale == 1000 else ".0f"
            f2 = go.Figure(go.Heatmap(z=hm.values, x=[pd.Timestamp(c).strftime("%a %d") for c in hm.columns],
                                      y=[nice(i) for i in hm.index], colorscale="YlOrRd",
                                      colorbar=dict(title=unit), hovertemplate="%{y}<br>%{x}: %{z:" + zf + "} " + unit + "<extra></extra>"))
            base_layout(f2, max(260, 34 * len(hm) + 90), "")
            f2.update_layout(hovermode="closest", yaxis=dict(automargin=True))
            st.plotly_chart(f2, width="stretch", theme=None)
    with c2:
        section("When are the errors? Hour of day", f"Average error per hour of the day ({'UTC' if tz == 'UTC' else 'Madrid time'}).")
        gg = g_all.dropna(subset=["y_true", primary])
        if gg.empty:
            st.info("No scored hours.")
        else:
            prof = gg.assign(e=(gg[primary] - gg["y_true"]).abs() / scale).groupby("hour")["e"].mean()
            f3 = go.Figure(go.Bar(x=prof.index, y=prof.values, marker_color=MODEL_INFO[primary]["color"], name=P,
                                  hovertemplate=f"%{{x}}:00 → %{{y:{yfmt}}} {unit}<extra></extra>"))
            if ref:
                r = gg.assign(e=(gg[ref] - gg["y_true"]).abs() / scale).groupby("hour")["e"].mean()
                f3.add_trace(go.Scatter(x=r.index, y=r.values, mode="lines+markers", name=R,
                                        line=dict(color=MODEL_INFO[ref]["color"], dash="dot"), hovertemplate=f"%{{y:{yfmt}}}"))
            base_layout(f3, max(260, 34 * 16 + 90), f"Average error ({unit})")
            f3.update_xaxes(title="Hour of day", dtick=2)
            st.plotly_chart(f3, width="stretch", theme=None)

# ============================================================================
# MODEL COMPARISON
# ============================================================================
with tab_models:
    if len(available) < 2:
        callout("Only one model is stored for this period, so there is nothing to compare. "
                "Switch to the <b>validation week</b> to compare all seven models.", "warn")
    else:
        span = st.radio("Compare over", ["Whole period", f"Selected day ({day})"], horizontal=True, key="cmp_span")
        gsrc = g_all if span == "Whole period" else cur
        rows = []
        for m in available:
            mm = metrics(gsrc, m)
            rows.append(dict(key=m, Model=MODEL_INFO[m]["label"], MAE=mm["mae"], RMSE=mm["rmse"], Bias=mm["bias"], n=mm["n"],
                             rel=(mm["mae"] / mm["mean_actual"] * 100) if mm["mean_actual"] else np.nan))
        tb = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
        ref_mae = tb.loc[tb["key"] == ref, "MAE"].iloc[0] if ref else np.nan
        tb["gain"] = (1 - tb["MAE"] / ref_mae) * 100 if ref else np.nan
        tb.insert(0, "Rank", range(1, len(tb) + 1))
        best = tb.iloc[0]
        callout(f"Over this selection, the most accurate model is <b>{esc(best['Model'])}</b> "
                f"(average error {esc(fmt(best['MAE'], scale, unit))}). "
                + (f"The Blend ranks <b>#{int(tb.loc[tb['key'] == 'blend', 'Rank'].iloc[0])}</b> of {len(tb)}. " if "blend" in tb["key"].values else "")
                + "Differences between the top models can be small — on a single week several of them are statistically tied "
                  "(see the About tab).", "")
        f4 = go.Figure(go.Bar(y=tb["Model"][::-1], x=tb["MAE"][::-1] / scale, orientation="h",
                              marker_color=[MODEL_INFO[k]["color"] for k in tb["key"][::-1]],
                              text=[fmt(v, scale, unit) for v in tb["MAE"][::-1]], textposition="outside",
                              hovertemplate="%{y}: %{x:" + yfmt + "}<extra></extra>"))
        base_layout(f4, 420, "")
        f4.update_layout(hovermode="closest", xaxis_title=f"Average error, MAE ({unit} per hour) — lower is better",
                         yaxis=dict(automargin=True))
        st.plotly_chart(f4, width="stretch", theme=None)

        show = pd.DataFrame({
            "Rank": tb["Rank"], "Model": tb["Model"], f"MAE ({unit})": tb["MAE"] / scale, f"RMSE ({unit})": tb["RMSE"] / scale,
            f"Bias ({unit})": tb["Bias"] / scale, "Error vs average load (%)": tb["rel"],
            f"Gain vs {R} (%)" if ref else "Gain": tb["gain"], "Hours scored": tb["n"]})
        nd = 2 if scale == 1000 else 1
        st.dataframe(show.style.format({f"MAE ({unit})": f"{{:.{nd}f}}", f"RMSE ({unit})": f"{{:.{nd}f}}",
                                        f"Bias ({unit})": f"{{:+.{nd}f}}", "Error vs average load (%)": "{:.0f}%",
                                        (f"Gain vs {R} (%)" if ref else "Gain"): "{:+.0f}%"}, na_rep="—"),
                     width="stretch", hide_index=True)
        st.caption("MAE = average size of the error. RMSE = like MAE but penalises large misses more. "
                   "Bias = average (forecast − actual): positive means the model tends to over-forecast. "
                   "Errors are computed on the total of the selected circuits.")

        section("All horizons side by side", f"MAE of the total of the selected circuits, whole period ({unit} per hour).")
        mat = {}
        for hl, hk in HORIZONS.items():
            gh = aggregate(dataset, hk, circuits, tz)
            mat[hl] = {MODEL_INFO[m]["label"]: metrics(gh, m)["mae"] / scale for m in available}
        mat = pd.DataFrame(mat)
        mat = mat.loc[mat.mean(axis=1).sort_values().index]
        st.dataframe(mat.style.format("{:.2f}" if scale == 1000 else "{:.1f}").background_gradient(cmap="YlOrRd", axis=None),
                     width="stretch")

# ============================================================================
# CIRCUITS
# ============================================================================
with tab_circ:
    span_c = st.radio("Period", ["Whole period", f"Selected day ({day})"], horizontal=True, key="circ_span")
    pc = per_circuit(dataset, horizon, circuits, tz)
    if span_c != "Whole period":
        pc = pc[pc["day"] == day]
    rows = []
    for sid, d in pc.groupby("series_id"):
        d = d.dropna(subset=["y_true", primary])
        if d.empty:
            continue
        e = d[primary] - d["y_true"]
        r = dict(Circuit=nice(sid), Zone=sid.split("|")[0], mean=d["y_true"].mean(), mae=e.abs().mean(), bias=e.mean(), n=len(d))
        r["rel"] = r["mae"] / r["mean"] * 100 if r["mean"] > 0 else np.nan
        if ref:
            rm = (d[ref] - d["y_true"]).abs().mean()
            r["gain"] = (1 - r["mae"] / rm) * 100 if rm > 0 else np.nan
        rows.append(r)
    ct = pd.DataFrame(rows)
    if ct.empty:
        st.info("No scored hours for this selection.")
    else:
        ct = ct.sort_values("mae", ascending=False).reset_index(drop=True)
        section(f"Forecast error by circuit — {P}", f"Average error per hour ({unit}). Bars are colored by zone.")
        f5 = go.Figure(go.Bar(y=ct["Circuit"][::-1], x=ct["mae"][::-1] / scale, orientation="h",
                              marker_color=[ZONE_COLORS[z] for z in ct["Zone"][::-1]],
                              hovertemplate="%{y}: %{x:" + yfmt + "}<extra></extra>"))
        base_layout(f5, max(300, 30 * len(ct) + 90), "")
        f5.update_layout(hovermode="closest", xaxis_title=f"MAE ({unit} per hour)", yaxis=dict(automargin=True))
        st.markdown(legend_html([(f"Zone {z}", c, "") for z, c in ZONE_COLORS.items()]), unsafe_allow_html=True)
        st.plotly_chart(f5, width="stretch", theme=None)
        nd = 2 if scale == 1000 else 1
        out = pd.DataFrame({"Circuit": ct["Circuit"], f"Average load ({unit})": ct["mean"] / scale,
                            f"MAE ({unit})": ct["mae"] / scale, "Error vs average load (%)": ct["rel"],
                            f"Bias ({unit})": ct["bias"] / scale, "Hours scored": ct["n"]})
        fm = {f"Average load ({unit})": f"{{:.{nd}f}}", f"MAE ({unit})": f"{{:.{nd}f}}",
              f"Bias ({unit})": f"{{:+.{nd}f}}", "Error vs average load (%)": "{:.0f}%"}
        if ref:
            out[f"Gain vs {R} (%)"] = ct["gain"]
            fm[f"Gain vs {R} (%)"] = "{:+.0f}%"
        st.dataframe(out.style.format(fm, na_rep="—"), width="stretch", hide_index=True)
        st.caption("A small circuit can have a small MAE but a large relative error: read the two columns together. "
                   "SE and SW circuits are barely present in the training data, so treat their forecasts with more caution.")

# ============================================================================
# ALERTS
# ============================================================================
with tab_alert:
    if not ref:
        callout("Alerts compare the forecast with a baseline, and no baseline is stored for this period. "
                "Switch to the <b>validation week</b> to use alerts.", "warn")
    else:
        al = g_all[g_all["alert"]].copy()
        callout(f"An hour is flagged when {esc(P)} forecasts more than <b>{thr_pct}%</b> above {esc(R)} "
                f"<i>and</i> the excess is at least <b>{min_pct}%</b> of the average load. Change these in the sidebar.", "")
        hits = al.dropna(subset=["y_true"])
        confirmed = ((hits["y_true"] - hits[ref]) / hits[ref].where(hits[ref] > 0) * 100 > thr_pct).sum() if len(hits) else 0
        cards = [kpi_card("Flagged hours", f"{len(al)}", f"out of {len(g_all)} hours", "#DC2626"),
                 kpi_card("With a measurement", f"{len(hits)}", "alerts we can check", "#1D5C9E"),
                 kpi_card("Confirmed", f"{confirmed}" + (f" ({confirmed / len(hits) * 100:.0f}%)" if len(hits) else ""),
                          f"actual also > reference +{thr_pct}%", "#16A34A",
                          "Share of alerts where the measured consumption also exceeded the reference by the same threshold.")]
        st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
        if al.empty:
            st.success("No alert on this period with the current settings. Lower the threshold in the sidebar to see more.")
        else:
            per_day = al.groupby("day").size().reindex(days, fill_value=0)
            f6 = go.Figure(go.Bar(x=[pd.Timestamp(d).strftime("%a %d %b") for d in per_day.index], y=per_day.values,
                                  marker_color="#DC2626", hovertemplate="%{x}: %{y} hour(s)<extra></extra>"))
            base_layout(f6, 280, "Alert hours")
            f6.update_layout(hovermode="closest")
            st.plotly_chart(f6, width="stretch", theme=None)
            tb = pd.DataFrame({"Date": al["t"].dt.strftime("%a %d %b"), "Time": al["t"].dt.strftime("%H:%M"),
                               f"Forecast ({unit})": al[primary] / scale, f"Reference ({unit})": al[ref] / scale,
                               "Above reference": al["pct_over"], f"Actual ({unit})": al["y_true"] / scale})
            tb["Confirmed by measurement"] = np.where(al["y_true"].isna(), "n/a",
                                                      np.where((al["y_true"] - al[ref]) / al[ref].where(al[ref] > 0) * 100 > thr_pct, "✅ yes", "❌ no"))
            nd = 2 if scale == 1000 else 0
            st.dataframe(tb.reset_index(drop=True).style.format({f"Forecast ({unit})": f"{{:,.{nd}f}}", f"Reference ({unit})": f"{{:,.{nd}f}}",
                                                                 f"Actual ({unit})": f"{{:,.{nd}f}}", "Above reference": "{:+.0f}%"}, na_rep="—"),
                         width="stretch", hide_index=True, height=420)
            st.download_button("⬇️ Download alerts (CSV)", tb.to_csv(index=False).encode("utf-8"),
                               file_name=f"alerts_{horizon}.csv", mime="text/csv")

# ============================================================================
# ABOUT
# ============================================================================
with tab_about:
    section("The final model: Blend v1.3", "Chosen on the validation week with rule D10 (29 Oct 2025).")
    st.markdown(
        "The **Blend** averages three forecasts, each already frozen before the test week:\n"
        "- **Gradient Boosting v1.3** — a tree-based model using calendar and recent-load features.\n"
        "- **ChronosGBM v1.3** — the same kind of model, fed with Chronos forecasts as extra inputs.\n"
        "- **Chronos-Bolt v1.3** — a pre-trained time-series foundation model, used without re-training.\n\n"
        "One pooled model per horizon covers the 16 circuits. Weights are tuned per horizon:")
    wt = pd.DataFrame([{"Horizon": hl, "Gradient Boosting": config["horizons"][hk]["w_gbm"],
                        "ChronosGBM": config["horizons"][hk]["w_hybrid"], "Chronos-Bolt": config["horizons"][hk]["w_chronos"]}
                       for hl, hk in HORIZONS.items()])
    st.dataframe(wt.style.format({c: "{:.2f}" for c in wt.columns[1:]}), width="stretch", hide_index=True)

    section("Official results on the unseen test week", "29 Sep – 5 Oct 2025, all 16 circuits, MAE in Wh per hour (lower is better). Source: RESULTS.md, Task 6.")
    ot = pd.DataFrame(OFFICIAL_TEST, columns=["Model", "+1 hour", "+6 hours", "Day-ahead"])
    st.dataframe(ot.style.format({c: "{:.1f}" for c in ot.columns[1:]}).background_gradient(cmap="YlOrRd", subset=ot.columns[1:], axis=None),
                 width="stretch", hide_index=True)
    callout("The Blend is the best model, or tied with the best, at every horizon, and beats Baseline B everywhere "
            "(−49% at +1 h, −21% at +6 h, −22% day-ahead). It beats simple persistence significantly only at +6 h.", "ok")

    section("Glossary")
    st.markdown(
        "- **Wh / kWh per hour** — energy used during one hour (1 kWh = 1000 Wh).\n"
        "- **Horizon** — how far ahead the forecast looks.\n"
        "- **Baseline** — a simple method (last week, typical weekday-and-hour, or last value). It sets the bar a model must clear.\n"
        "- **Validation vs test** — validation data is used to choose the model; the test week is kept aside and used once for the final score.\n"
        "- **MAE / RMSE / bias** — average error size / error penalising big misses / average direction of the error.\n"
        "- **Alert** — an hour where the forecast is well above the reference.")

    section("Good to know")
    st.markdown(
        "- The app **replays stored forecasts**; it is not connected to live sensors.\n"
        "- On this dashboard the Blend is shown on the validation week only; its test-week forecasts are not stored in the repository.\n"
        "- Errors concentrate on a few circuits (NW Plugs & Sockets, NW Lighting, SE Lighting), mostly at night.\n"
        "- SE/SW circuits are barely in the training data; power (W) and current (I) are not modelled.\n"
        "- Some hours have no valid sensor reading; they are left out of every error figure.")
    st.caption(f"Data folder: `{DATA_DIR}` · files: blend / task8 / hybrid / chronos validation predictions v1.3, chronos test predictions v1.3, blend_frozen_config_v1.3.json")
