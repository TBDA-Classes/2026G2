"""CeDInt Storey 1 — Energy forecast dashboard (Sprint 4, Task 3: UX).

Final model: Blend v1.3 (frozen in Sprint 3, confirmed in Sprint 4 Task 2).
Run from the repository root:   python Sprint4_Task3_UX_Dash/app.py   ->   http://127.0.0.1:8050
"""
from __future__ import annotations

import io
import sys

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update

from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent / "core"))   # settings, data_layer, anomalies, info_texts

import anomalies as AN  # noqa: E402
import info_texts as IT  # noqa: E402
import data_layer as D  # noqa: E402
import settings as S  # noqa: E402

C = S.COLORS
FONT = "Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
           suppress_callback_exceptions=True, title="CeDInt Energy Forecast")
server = app.server


# ==========================================================================================================
# Helpers
# ==========================================================================================================
def fig_base(height=360, **kw) -> go.Figure:
    f = go.Figure()
    layout = dict(template="plotly_white", height=height, margin=dict(l=56, r=16, t=16, b=40),
                  font=dict(family=FONT, size=12, color="#334155"), hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, font=dict(size=12)),
                  hoverlabel=dict(bgcolor="white", bordercolor="#d9dee7", font=dict(family=FONT, size=12,
                                                                                    color="#1f2933")),
                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", bargap=0.35)
    layout.update(kw)
    f.update_layout(**layout)
    f.update_xaxes(showgrid=False, showline=True, linecolor="#d9dee7", ticks="outside", tickcolor="#d9dee7",
                   tickfont=dict(color="#64748b"))
    f.update_yaxes(gridcolor="#eef1f5", griddash="dot", zeroline=False, showline=False,
                   tickfont=dict(color="#64748b"), title_font=dict(color="#64748b", size=12))
    return f


def empty_fig(msg: str, height=320) -> go.Figure:
    f = fig_base(height)
    f.add_annotation(text=msg, showarrow=False, font=dict(color=C["muted"], size=14), x=0.5, y=0.5,
                     xref="paper", yref="paper")
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    return f


import itertools as _it  # noqa: E402

_INFO_IDS = _it.count(1)


def info_icon(title: str, text: str | None = None):
    """Small (i) button that opens a pop-up explaining a chart, table or indicator (texts in info_texts.py)."""
    text = text or IT.info_for(title)
    if not text:
        return None
    uid = f"info-{next(_INFO_IDS)}"
    return html.Span([
        html.Button(html.I(className="bi bi-info-circle"), id=uid, className="info-dot", type="button",
                    title="What is this?"),
        dbc.Popover([dbc.PopoverHeader(title), dbc.PopoverBody(text)], target=uid, trigger="legacy",
                    placement="bottom-start", className="info-pop"),
    ], className="info-wrap")


def kpi(title: str, value: str, sub: str = "", icon: str = "", tip: str | None = None, id_: str | None = None,
        tone: str = "blue"):
    base = IT.info_for(title)
    text = " ".join(t for t in (base, tip if tip and tip != base else None) if t) or None
    body = [html.Div([html.Span(html.I(className=f"bi {icon}"), className=f"kpi-icon tone-{tone}") if icon else None,
                      html.Span(title), info_icon(title, text)], className="kpi-title"),
            html.Div(value, className="kpi-value"), html.Div(sub, className="kpi-sub")]
    return dbc.Card(dbc.CardBody(body), className="kpi-card h-100", id=id_ or f"kpi-{abs(hash(title)) % 10**8}")


def section(title: str, subtitle: str = "", *children, right=None):
    head = html.Div([html.Div([html.Div([html.H5(title, className="section-title mb-0"), info_icon(title)],
                                        className="d-flex align-items-center gap-1"),
                               html.Div(subtitle, className="section-sub") if subtitle else None]),
                     right], className="d-flex justify-content-between align-items-start mb-3 gap-3")
    return dbc.Card(dbc.CardBody([head, *children]), className="section-card mb-4")


def fmt(x, d=1, unit=""):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{d}f}{unit}"


def status_badge(level: str):
    icon, label, cls = {"critical": ("bi-exclamation-octagon-fill", "High impact", "badge-critical"),
                        "warning": ("bi-exclamation-triangle-fill", "Medium impact", "badge-warning"),
                        "info": ("bi-info-circle-fill", "Good to know", "badge-info")}[level]
    return html.Span([html.I(className=f"bi {icon} me-1"), label], className=f"status-badge {cls}")


ZONE_OPTS = [{"label": html.Span([html.Span(className="zone-dot", style={"background": S.ZONE_COLORS[z]}), z]),
              "value": z} for z in S.ZONES]


def zone_picker(id_, value):
    return dbc.Checklist(id=id_, options=ZONE_OPTS, value=value, inline=True, className="zone-picker",
                         inputClassName="btn-check", labelClassName="btn btn-sm zone-btn",
                         labelCheckedClassName="active")


def horizon_picker(id_, value):
    return dbc.RadioItems(id=id_, options=HZ_OPTS, value=value, inline=True, className="seg",
                          inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                          labelCheckedClassName="active")
LOAD_OPTS = [{"label": v, "value": v} for v in S.LOAD_TYPES.values()]
HZ_OPTS = [{"label": v, "value": k} for k, v in S.HORIZONS.items()]
TABLE_KW = dict(style_table={"overflowX": "auto", "borderRadius": "10px"},
                style_cell={"fontFamily": FONT, "fontSize": 13, "padding": "8px 12px", "textAlign": "left",
                            "border": "none", "color": "#1f2933"},
                style_header={"fontWeight": 600, "backgroundColor": "#f1f4f9", "color": "#475569",
                              "borderBottom": "1px solid #dbe2ec", "textTransform": "none"},
                style_data={"borderBottom": "1px solid #eef1f5"},
                style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafbfd"},
                                        {"if": {"column_type": "numeric"}, "textAlign": "right"}])
ZONE_OF = lambda circuit: circuit.split("|")[0]  # noqa: E731
SPLIT_OPTS = [{"label": "Test week", "value": "test"}, {"label": "Validation week", "value": "validation"}]


# ==========================================================================================================
# Shell: sidebar navigation + page container
# ==========================================================================================================
NAV = [("/", "bi-house", "Overview"), ("/live", "bi-broadcast", "Live forecast"),
       ("/anomalies", "bi-activity", "Anomalies"), ("/costs", "bi-cash-coin", "Energy & costs"),
       ("/forecast", "bi-play-circle", "Forecast replay"),
       ("/performance", "bi-speedometer2", "Performance"), ("/limitations", "bi-exclamation-diamond", "Known limitations"),
       ("/model", "bi-cpu", "The model")]

sidebar = html.Div([
    html.Div([html.I(className="bi bi-lightning-charge-fill brand-icon"),
              html.Div([html.Div("CeDInt Energy", className="brand-title"),
                        html.Div("Storey 1 · hourly forecast", className="brand-sub")])], className="brand"),
    dbc.Nav([dbc.NavLink([html.I(className=f"bi {i} me-2"), t,
                          html.Span(id="nav-badge", className="nav-badge") if h == "/anomalies" else None],
                         href=h, active="exact") for h, i, t in NAV],
            vertical=True, pills=True, className="side-nav"),
    html.Div([html.Div("Final model", className="side-label"),
              html.Div(S.MODEL_NAME, className="side-model"),
              html.Div("Frozen 29 Oct 2026 · rule D10", className="side-note"),
              html.Div("TBDA · Group 2 · UPM", className="side-note mt-3")], className="side-footer"),
], className="sidebar")

PAGE_TITLES = {h: t for h, _, t in NAV}


def _sw(kind, color, label, extra=None):
    """One legend row: a swatch drawn in CSS + its meaning."""
    style = {"line": {"height": "3px", "background": color, "borderRadius": "2px"},
             "dash": {"height": "0", "borderTop": f"3px dashed {color}"},
             "band": {"height": "12px", "background": color, "borderRadius": "3px"},
             "box": {"height": "12px", "background": color, "borderRadius": "3px"},
             "dot": {"height": "12px", "width": "12px", "background": color, "borderRadius": "50%"},
             "grad": {"height": "12px", "background": color, "borderRadius": "3px"}}[kind]
    return html.Div([html.Span(extra or "", className="lg-sw", style={"width": "30px", "display": "inline-block",
                                                                     **style}),
                     html.Span(label, className="lg-label")], className="lg-row")


def colour_legend():
    return [dbc.PopoverHeader("Colour legend (the same on every page)"), dbc.PopoverBody([
        html.Div("Lines and areas", className="lg-head"),
        _sw("line", C["actual"], "Measured energy (grey area underneath)"),
        _sw("line", C["forecast"], "Forecast (Blend v1.3)"),
        _sw("dash", C["forecast"], "Forecast for the hours after the last measurement"),
        _sw("band", C["band"], "Forecast interval (expected range)"),
        _sw("band", "rgba(42,120,214,0.10)", "The future (right of the NOW line)"),
        html.Div("Zones", className="lg-head"),
        *[_sw("dot", S.ZONE_COLORS[z], f"{z} — {S.ZONE_HELP[z]}") for z in S.ZONES],
        html.Div("Anomalies", className="lg-head"),
        html.Div([html.Span("▲", className="lg-sym"), "Spike: more than the forecast interval (extra cost)"],
                 className="lg-row"),
        html.Div([html.Span("▼", className="lg-sym"), "Drop: less than the forecast interval (possible fault)"],
                 className="lg-row"),
        _sw("dot", LEVEL_COLOR["Critical"], "Critical: ≥ 1 kWh or ≥ 6 h"),
        _sw("dot", LEVEL_COLOR["Moderate"], "Moderate: ≥ 0.25 kWh or ≥ 3 h"),
        _sw("dot", LEVEL_COLOR["Minor"], "Minor: small and short"),
        html.Div("Tariff periods", className="lg-head"),
        _sw("box", TARIFF_COLOR["P1"], "Peak: weekdays 10–14 h, 18–22 h"),
        _sw("box", TARIFF_COLOR["P2"], "Standard: weekdays 8–10, 14–18, 22–24 h"),
        _sw("box", TARIFF_COLOR["P3"], "Off-peak: nights, weekends, holidays"),
        html.Div("Heatmaps", className="lg-head"),
        _sw("grad", "linear-gradient(90deg,#1c5cab,#9ec5f4,#eef1f5,#fdba74,#c2410c)",
            "Deviation map: blue below · grey as forecast · orange above"),
        _sw("grad", "linear-gradient(90deg,#cde2fb,#3987e5,#0d366b)", "Errors / energy: light = low, dark = high"),
        html.Div("Badges", className="lg-head"),
        html.Div([html.Span("High impact", className="status-badge badge-critical me-1"),
                  html.Span("Medium", className="status-badge badge-warning me-1"),
                  html.Span("Good to know", className="status-badge badge-info me-1"),
                  html.Span("OK", className="status-badge badge-good")], className="lg-row flex-wrap gap-1"),
        html.Div("Click the (i) next to any title for an explanation of that chart or number.",
                 className="hint mt-2"),
    ])]


def topbar():
    try:
        if D.has_live():
            last = D.live_meta()["last_measured_hour_local"]
            pill = html.Span([html.Span(className="live-dot"), f"Data up to {last:%a %d %b %Y, %H:%M}"],
                             className="data-pill live")
        else:
            pill = html.Span([html.I(className="bi bi-clock-history me-1"), "Evaluation weeks · 22 Sep – 5 Oct 2025"],
                             className="data-pill")
    except Exception:  # noqa: BLE001
        pill = None
    return html.Div([html.Div(id="crumb", className="crumb"),
                     html.Div([pill, html.Span([html.I(className="bi bi-cpu me-1"), S.MODEL_NAME],
                                               className="data-pill model"),
                               html.Button([html.I(className="bi bi-palette me-1"), "Colours"], id="legend-btn",
                                           className="data-pill gear-btn", type="button"),
                               dbc.Popover(colour_legend(), target="legend-btn", trigger="legacy",
                                           placement="bottom-end", className="legend-pop"),
                               html.Button([html.I(className="bi bi-sliders me-1"), "Settings"],
                                           id={"type": "opset", "n": "top"}, className="data-pill gear-btn")],
                              className="d-flex gap-2 align-items-center")],
                    className="topbar")


CFG_DEFAULT = dict(AN.DEFAULTS)


def _slider(id_, lo, hi, step, val, marks):
    return dcc.Slider(id=id_, min=lo, max=hi, step=step, value=val, marks=marks, persistence=True,
                      persistence_type="session", tooltip={"placement": "bottom", "always_visible": True})


def settings_panel():
    live_ok = D.has_live()
    return dbc.Offcanvas(id="settings", placement="end", title="Analysis settings", is_open=False,
                         className="settings-canvas", children=[
        html.Div("Used by Overview, Anomalies, Energy & costs and the playback.", className="section-sub mb-3"),
        html.Label("Period", className="ctl-label"),
        dbc.RadioItems(id="set-period", value="eval", persistence=True, persistence_type="session",
                       options=[{"label": "Evaluation weeks", "value": "eval"},
                                {"label": "Latest data", "value": "live", "disabled": not live_ok}],
                       className="seg", inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                       labelCheckedClassName="active"),
        html.Div("" if live_ok else "“Latest data” needs the live forecast (Live forecast page).", className="hint"),
        html.Hr(),
        html.Label("Forecast interval", className="ctl-label"),
        dbc.RadioItems(id="set-level", value=0.90, persistence=True, persistence_type="session",
                       options=[{"label": "80%", "value": 0.80}, {"label": "90%", "value": 0.90},
                                {"label": "95%", "value": 0.95}], className="seg", inputClassName="btn-check",
                       labelClassName="btn btn-sm seg-btn", labelCheckedClassName="active"),
        html.Div("A wider interval flags fewer hours: only the clearest anomalies.", className="hint mb-3"),
        html.Label("Minimum deviation to flag (Wh in one hour)", className="ctl-label"),
        _slider("set-mindev", 0, 200, 5, 25, {0: "0", 25: "25", 100: "100", 200: "200"}),
        html.Div(id="set-info", className="info-box mt-3"),
        html.Hr(),
        html.Label("Electricity prices (€/kWh, assumed)", className="ctl-label"),
        html.Div([html.Span("Peak", className="tp-dot", style={"background": "#6250d6"}),
                  html.Span("weekdays 10–14 h and 18–22 h", className="hint")]),
        _slider("set-p1", 0, 0.5, 0.01, 0.24, {0.1: "0.10", 0.3: "0.30", 0.5: "0.50"}),
        html.Div([html.Span("Standard", className="tp-dot", style={"background": "#2a78d6"}),
                  html.Span("weekdays 8–10, 14–18 and 22–24 h", className="hint")]),
        _slider("set-p2", 0, 0.5, 0.01, 0.17, {0.1: "0.10", 0.3: "0.30", 0.5: "0.50"}),
        html.Div([html.Span("Off-peak", className="tp-dot", style={"background": "#9ec5f4"}),
                  html.Span("nights 0–8 h, weekends and holidays", className="hint")]),
        _slider("set-p3", 0, 0.5, 0.01, 0.12, {0.1: "0.10", 0.3: "0.30", 0.5: "0.50"}),
        html.Div("Periods follow the Spanish 2.0TD access tariff. The prices are placeholders until UPM's real "
                 "tariff is known.", className="hint mb-3"),
        html.Label("CO₂ per kWh (kg, assumed)", className="ctl-label"),
        _slider("set-co2", 0, 0.5, 0.01, 0.25, {0: "0", 0.25: "0.25", 0.5: "0.50"}),
        dbc.Alert("Every € and CO₂ number in the app is an estimate built from these values.", color="secondary",
                  className="small mt-3"),
    ])


def alert_panel():
    return dbc.Offcanvas(id="al-detail", placement="end", is_open=False, className="alert-canvas",
                         title="Anomaly details", children=[
        html.Div(id="al-body"),
        html.Div([dbc.Button([html.I(className="bi bi-chevron-left me-1"), "Previous"], id="al-prev", outline=True,
                             color="secondary", size="sm"),
                  dbc.Button(["Next ", html.I(className="bi bi-chevron-right ms-1")], id="al-next", outline=True,
                             color="secondary", size="sm"),
                  dbc.Button(id="al-review", color="primary", size="sm", className="ms-auto")],
                 className="d-flex gap-2 mt-3")])


def serve_layout():
    return html.Div([dcc.Location(id="url"), dcc.Store(id="run-stamp", data=0),
                     dcc.Store(id="cfg", data=CFG_DEFAULT), dcc.Store(id="reviewed", data=[], storage_type="session"),
                     dcc.Store(id="al-open"), dcc.Store(id="al-order", data=[]), sidebar,
                     html.Main([topbar(), html.Div(id="page")], className="content"),
                     settings_panel(), alert_panel()])


app.layout = serve_layout


# ==========================================================================================================
# Page 1 — Overview: who the dashboard is for and the headline numbers
# ==========================================================================================================
USERS = [
    ("bi-building-gear", "Building energy manager",
     "Plans and reports the building's consumption and looks for savings.",
     ["How much will each wing use tomorrow?", "Where and when are the largest loads?",
      "How far can I trust the numbers?"],
     "Live forecast (day-ahead, by zone) · Performance", "/live"),
    ("bi-tools", "Maintenance / facility technician",
     "Runs HVAC, lighting and the IT rack day to day and reacts to anomalies.",
     ["What should this circuit use in the next hours?", "Is the measured value far from the forecast?",
      "Which circuits behave unusually?"],
     "Live forecast (+1 h / +6 h, one load type) · Known limitations", "/live"),
    ("bi-mortarboard", "Researcher / project evaluator",
     "Checks how the model was built and how well it works before using the results.",
     ["Which model is used and how was it chosen?", "What are the error and its uncertainty?",
      "What are the known weaknesses?"],
     "Performance · The model · Known limitations", "/performance"),
]


def page_overview():
    m = D.official_metrics("test")
    allc = m[m["scope"] == "all circuits"].set_index("horizon")
    cards = []
    for hz in ["+1h", "+6h", "day-ahead"]:
        r = allc.loc[hz]
        cards.append(dbc.Col(kpi(f"Typical error · {S.HORIZONS[{'+1h': 1, '+6h': 6, 'day-ahead': 24}[hz]]}",
                                 f"{r.MAE_Wh:.1f} Wh", f"MAE per circuit-hour · 95% CI {r.MAE_lo:.1f}–{r.MAE_hi:.1f}",
                                 "bi-bullseye", id_=f"ov-{hz}", tone=["blue", "indigo", "green"][len(cards)]), md=4))
    users = []
    for icon, name, who, needs, pages, link in USERS:
        users.append(dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([html.Span(html.I(className=f"bi {icon}"), className="user-icon"),
                      html.H6(name, className="mb-0 ms-2")],
                     className="d-flex align-items-center mb-2"),
            html.P(who, className="small text-secondary mb-2"),
            html.Div("Needs to know", className="mini-label"),
            html.Ul([html.Li(n) for n in needs], className="small ps-3 mb-2"),
            html.Div("Best pages", className="mini-label"), html.Div(pages, className="small mb-3"),
            dbc.Button(["Open ", html.I(className="bi bi-arrow-right")], href=link, size="sm", outline=True,
                       color="primary")]), className="h-100 user-card"), md=4))
    return [
        html.Div([
            html.Div([html.Div("CeDInt · UPM · Storey 1", className="hero-kicker"),
                      html.H1("How much energy will the building use?", className="hero-title"),
                      html.P(["Hourly forecasts for the 16 circuits of the first floor, made by the team's final "
                              "model ", html.B(S.MODEL_NAME), ". Choose a zone, a horizon and, if you want, a type of "
                              "consumption."], className="hero-text"),
                      html.Div([dbc.Button([html.I(className="bi bi-broadcast me-2"), "Open the live forecast"],
                                           href="/live", className="hero-btn"),
                                dbc.Button([html.I(className="bi bi-speedometer2 me-2"), "How accurate is it?"],
                                           href="/performance", className="hero-btn ghost")],
                               className="d-flex gap-2 flex-wrap")], className="hero-body"),
            html.Div([html.Div([html.Div("16", className="hero-num"), html.Div("circuits", className="hero-numlab")]),
                      html.Div([html.Div("4", className="hero-num"), html.Div("zones", className="hero-numlab")]),
                      html.Div([html.Div("3", className="hero-num"), html.Div("horizons", className="hero-numlab")])],
                     className="hero-stats"),
        ], className="hero mb-4"),
        dcc.Loading(html.Div(id="ov-monitor"), type="dot"),
        html.H5("How accurate is the forecast?", className="mb-3 mt-2"),
        dbc.Row(cards, className="g-3 mb-4"),
        html.H5("Who this dashboard is for", className="mb-3 mt-2"),
        dbc.Row(users, className="g-3 mb-4"),
        section("How to read a forecast", "",
                dbc.Row([
                    dbc.Col([html.Div([html.I(className="bi bi-clock me-2"), html.B("Horizon")]),
                             html.P("How far ahead the forecast was made: +1 h and +6 h are rolling forecasts; "
                                    "day-ahead covers the next day and is issued at 00:00 Madrid time.",
                                    className="small")], md=4),
                    dbc.Col([html.Div([html.I(className="bi bi-lightning me-2"), html.B("Energy (Wh)")]),
                             html.P("Energy used in one hour by a circuit. 1,000 Wh = 1 kWh. All times are "
                                    "Madrid local time.", className="small")], md=4),
                    dbc.Col([html.Div([html.I(className="bi bi-rulers me-2"), html.B("Error (MAE)")]),
                             html.P("Mean absolute error: on average, how many Wh the forecast is away from the "
                                    "measured value. Lower is better.", className="small")], md=4),
                ])),
        dbc.Alert([html.I(className="bi bi-info-circle me-2"),
                   html.B("Live forecast"), " shows the latest measured data (up to 13 Oct 2025) and the model's "
                   "forecast for the next hours and the rest of the day. ", html.B("Forecast replay"),
                   " replays the model on the validation and test weeks used to evaluate it."],
                  color="light", className="small border"),
    ]


# ==========================================================================================================
# Page 2 — Forecasts
# ==========================================================================================================
def page_forecast():
    days = D.days("test")
    controls = dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([html.Label(["Zone (region) ", html.Span("(none = all)", className="text-secondary")],
                                className="ctl-label"),
                     zone_picker("f-zone", ["NW"])], lg=3, md=6),
            dbc.Col([html.Label("Time horizon", className="ctl-label"), horizon_picker("f-hz", 24)], lg=3, md=6),
            dbc.Col([html.Label(["Consumption type ", html.Span("(optional)", className="text-secondary")],
                                className="ctl-label"),
                     dcc.Dropdown(id="f-load", options=LOAD_OPTS, value=[], multi=True,
                                  placeholder="All types")], lg=3, md=6),
            dbc.Col([html.Label("Period", className="ctl-label"),
                     dcc.Dropdown(id="f-split", options=SPLIT_OPTS, value="test", clearable=False),
                     dcc.Dropdown(id="f-day", value="all", clearable=False, className="mt-2",
                                  options=[{"label": "Whole week", "value": "all"}] +
                                          [{"label": pd.Timestamp(d).strftime("%a %d %b"), "value": d} for d in days])],
                    lg=3, md=6),
        ], className="g-3"),
        html.Hr(className="my-3"),
        dbc.Row([
            dbc.Col(html.Div(id="f-hz-help", className="small text-secondary"), md=7),
            dbc.Col(html.Div([
                dbc.Switch(id="f-int", value=S.INTERVALS_VALIDATED, className="d-inline-block me-2",
                           label=f"Show {int(S.INTERVAL_LEVEL * 100)}% prediction interval"),
                html.Span("validated" if S.INTERVALS_VALIDATED else "experimental · pending Pole 1",
                          className="status-badge " + ("badge-good" if S.INTERVALS_VALIDATED else "badge-warning")),
            ], className="text-md-end"), md=5),
        ]),
    ]), className="controls-card mb-4")

    return [
        html.Div([html.H2("Forecast replay", className="mb-1"),
                  html.P("The model replayed on the two evaluation weeks: measured vs forecast energy for the circuits "
                         "you select. Several circuits are added up.",
                         className="lead-text")], className="page-head"),
        controls,
        html.Div(id="f-source-note"),
        dbc.Row(id="f-kpis", className="g-3 mb-4"),
        section("Measured vs forecast energy", "Hourly total of the selected circuits · Madrid time",
                dcc.Loading(dcc.Graph(id="f-chart", config={"displaylogo": False}), type="dot"),
                html.Div(id="f-chart-note", className="small text-secondary mt-2")),
        dbc.Row([
            dbc.Col(section("Forecast energy by circuit", "Total over the selected period, kWh",
                            dcc.Graph(id="f-bars", config={"displayModeBar": False})), lg=6),
            dbc.Col(section("Daily profile", "Average forecast and measured energy by hour of day, Wh",
                            dcc.Graph(id="f-profile", config={"displayModeBar": False})), lg=6),
        ]),
        replay_player(),
        section("Forecast table", "One row per circuit and hour",
                dash_table.DataTable(id="f-table", page_size=12, sort_action="native", filter_action="native",
                                     **TABLE_KW),
                right=dbc.Button([html.I(className="bi bi-download me-1"), "Download CSV"], id="f-dl-btn",
                                 size="sm", color="primary", outline=True)),
        dcc.Download(id="f-dl"),
    ]


@app.callback(Output("f-day", "options"), Output("f-day", "value"), Input("f-split", "value"), State("f-day", "value"))
def _days(split, cur):
    days = D.days(split)
    opts = [{"label": "Whole week", "value": "all"}] + [{"label": pd.Timestamp(d).strftime("%a %d %b"), "value": d}
                                                        for d in days]
    return opts, cur if cur in days else "all"


def _source(split):
    return "recomputed" if D.has_recomputed(split) else "stored"


@app.callback(
    Output("f-kpis", "children"), Output("f-chart", "figure"), Output("f-chart-note", "children"),
    Output("f-bars", "figure"), Output("f-profile", "figure"), Output("f-table", "data"), Output("f-table", "columns"),
    Output("f-hz-help", "children"), Output("f-source-note", "children"),
    Input("f-zone", "value"), Input("f-hz", "value"), Input("f-load", "value"), Input("f-split", "value"),
    Input("f-day", "value"), Input("f-int", "value"), Input("run-stamp", "data"))
def _forecast(zones, hz, loads, split, day, show_int, _stamp):
    src = _source(split)
    df = D.predictions(split, src)
    sel = D.select(df, hz, zones or None, loads or None, day)
    help_ = [html.I(className="bi bi-clock me-1"), html.B(S.HORIZONS[hz] + ": "), S.HORIZON_HELP[hz]]
    src_note = (dbc.Alert([html.I(className="bi bi-cpu me-2"), "Showing forecasts recomputed by this app from the "
                           "frozen model (page ", html.A("The model", href="/model"), ")."],
                          color="info", className="small py-2") if src == "recomputed" else None)
    if sel.empty:
        e = empty_fig("No circuit matches this selection — try another zone or consumption type.")
        return [], e, "", empty_fig("", 260), empty_fig("", 260), [], [], help_, src_note

    k = D.selection_kpis(sel)
    n_circ = sel["circuit"].nunique()
    kp = [
        dbc.Col(kpi("Forecast energy", f"{k['energy_kwh']:,.1f} kWh",
                    f"{n_circ} circuit{'s' if n_circ > 1 else ''} · {'whole week' if day == 'all' else pd.Timestamp(day).strftime('%a %d %b')}",
                    "bi-lightning-charge", id_="k-energy", tone="indigo"), md=3),
        dbc.Col(kpi("Peak forecast hour", f"{fmt(k['peak_wh'], 0)} Wh",
                    k["peak_time"].strftime("%a %d %b, %H:%M") if k["peak_time"] is not None else "",
                    "bi-graph-up-arrow", id_="k-peak", tone="amber"), md=3),
        dbc.Col(kpi("Error on this selection", f"{fmt(k['mae'])} Wh",
                    f"MAE per circuit-hour · {k['n_valid']} of {k['n_rows']} hours measured", "bi-bullseye",
                    tip="Mean absolute error over the circuit-hours of this selection that have a valid measurement. "
                        "Official scores are on the Performance page.", id_="k-mae", tone="green"), md=3),
        dbc.Col(kpi("Bias", f"{k['bias']:+.1f} Wh" if not np.isnan(k["bias"]) else "–",
                    "forecast too low" if k["bias"] < -1 else "forecast too high" if k["bias"] > 1 else "no clear bias",
                    "bi-arrow-down-up", tip="Mean of (forecast − measured). Negative = the model under-forecasts.",
                    id_="k-bias", tone="slate"), md=3),
    ]

    t = D.hourly_total(sel, bool(show_int))
    f = fig_base(380)
    if show_int:
        f.add_trace(go.Scatter(x=t["time"], y=t["hi"], line=dict(width=0), hoverinfo="skip", showlegend=False))
        f.add_trace(go.Scatter(x=t["time"], y=t["lo"], fill="tonexty", fillcolor=C["band"], line=dict(width=0),
                               name=f"{int(S.INTERVAL_LEVEL * 100)}% interval (experimental)",
                               customdata=np.c_[t["lo"], t["hi"]],
                               hovertemplate="Interval %{customdata[0]:,.0f} – %{customdata[1]:,.0f} Wh<extra></extra>"))
    f.add_trace(go.Scatter(x=t["time"], y=t["actual"], name="Measured", mode="lines",
                           line=dict(color=C["actual"], width=2.2, shape="spline", smoothing=0.4),
                           fill="tozeroy" if not show_int else None, fillcolor=C["actual_fill"],
                           hovertemplate="Measured %{y:,.0f} Wh<extra></extra>"))
    f.add_trace(go.Scatter(x=t["time"], y=t["pred"], name=f"Forecast ({S.HORIZONS[hz]})", mode="lines",
                           line=dict(color=C["forecast"], width=2.2, shape="spline", smoothing=0.4),
                           hovertemplate="Forecast %{y:,.0f} Wh<extra></extra>"))
    f.update_yaxes(title_text="Wh per hour", rangemode="tozero")
    if day == "all":
        f.update_xaxes(tickformat="%a %d %b", dtick=86400000)
    else:
        f.update_xaxes(tickformat="%H:%M")
    gaps = int(t["actual"].isna().sum())
    note = []
    if gaps:
        note.append(f"Gaps in the measured line: {gaps} hour(s) where at least one selected circuit has no valid "
                    f"measurement (data-quality rule v1.2). ")
    if show_int:
        note.append("Interval: Chronos-Bolt 10–90% band calibrated per circuit and horizon on the validation week "
                    "(conformal); for several circuits the distances to the limits are added (conservative). "
                    "Not yet validated by Pole 1.")
        if split == "validation":
            note.append(" On the validation week the interval is in-sample (it was calibrated on these hours).")
    if hz == 24:
        note.append(" Day-ahead: each day's 24 values come from the forecast issued at 00:00 of that day.")

    # breakdown by circuit
    b = sel.groupby(["circuit", "load_type"])["pred"].sum().div(1000).reset_index().sort_values("pred")
    fb = fig_base(max(220, 34 * len(b) + 60), hovermode="closest")
    fb.add_trace(go.Bar(y=b["circuit"], x=b["pred"], orientation="h",
                        marker=dict(color=[S.ZONE_COLORS[ZONE_OF(c)] for c in b["circuit"]], cornerradius=4),
                        hovertemplate="%{y}<br>%{x:,.2f} kWh<extra></extra>", width=0.6,
                        text=[f"{v:,.1f}" for v in b["pred"]], textposition="outside", cliponaxis=False,
                        textfont=dict(color="#52514e")))
    fb.update_layout(margin=dict(l=150, r=40, t=8, b=36), showlegend=False)
    fb.update_xaxes(title_text="kWh", showgrid=True, gridcolor=C["grid"])
    fb.update_yaxes(showgrid=False)

    # daily profile (sum over selected circuits, mean over days)
    p = t.assign(h=t["time"].dt.hour).groupby("h")[["pred", "actual"]].mean().reset_index()
    fp = fig_base(max(220, 34 * len(b) + 60))
    fp.add_trace(go.Scatter(x=p["h"], y=p["actual"], name="Measured",
                            line=dict(color=C["actual"], width=2.2, shape="spline", smoothing=0.5),
                            hovertemplate="Measured %{y:,.0f} Wh<extra></extra>"))
    fp.add_trace(go.Scatter(x=p["h"], y=p["pred"], name="Forecast",
                            line=dict(color=C["forecast"], width=2.2, shape="spline", smoothing=0.5),
                            hovertemplate="Forecast %{y:,.0f} Wh<extra></extra>"))
    fp.update_xaxes(title_text="Hour of day", dtick=3, range=[-0.5, 23.5])
    fp.update_yaxes(title_text="Wh per hour", rangemode="tozero")

    tab = sel.copy()
    if show_int:
        tab = D.add_intervals(tab)
    tab["Time (Madrid)"] = tab["target_local"].dt.strftime("%Y-%m-%d %H:%M")
    tab["Issued (Madrid)"] = tab["issue_utc"].dt.tz_convert(S.TZ_LOCAL).dt.strftime("%Y-%m-%d %H:%M")
    tab["Forecast (Wh)"] = tab["pred"].round(1)
    tab["Measured (Wh)"] = tab["actual"].round(1)
    tab["Error (Wh)"] = (tab["pred"] - tab["actual"]).round(1)
    cols = ["Time (Madrid)", "circuit", "zone", "load_type", "Issued (Madrid)", "Forecast (Wh)", "Measured (Wh)",
            "Error (Wh)"]
    if show_int:
        tab["Low (Wh)"], tab["High (Wh)"] = tab["lo"].round(1), tab["hi"].round(1)
        cols += ["Low (Wh)", "High (Wh)"]
    tab = tab.sort_values(["Time (Madrid)", "circuit"])[cols].rename(
        columns={"circuit": "Circuit", "zone": "Zone", "load_type": "Type"})
    tab = tab.astype(object).where(tab.notna(), None)          # NaN -> empty cell (valid JSON)
    return (kp, f, "".join(note), fb, fp, tab.to_dict("records"), [{"name": c, "id": c} for c in tab.columns],
            help_, src_note)


@app.callback(Output("f-dl", "data"), Input("f-dl-btn", "n_clicks"), State("f-table", "data"),
              State("f-hz", "value"), State("f-split", "value"), prevent_initial_call=True)
def _download(_, rows, hz, split):
    if not rows:
        return no_update
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return dict(content=buf.getvalue(), filename=f"blend_v1.3_{split}_{S.HORIZON_KEYS[hz]}_forecasts.csv")



# ==========================================================================================================
# Page — Live forecast: latest measured data + forecast ahead (computed on this computer by live_engine.py)
# ==========================================================================================================
def live_setup_box(extra=None):
    return section("Compute the live forecast", "Runs the frozen Blend v1.3 on the latest data", html.Div([
        html.P(["The live forecast needs Chronos-Bolt, one of the three parts of the final model, so it is computed "
                "on this computer (the first run downloads the Chronos-Bolt weights, about 250 MB, and takes a few "
                "minutes; later runs take less than a minute). Requirements: Python 3.11 or newer and"],
               className="small mb-1"),
        html.Pre("pip install -r Sprint4_Task3_UX_Dash/requirements-live.txt", className="code-box"),
        dbc.Button([html.I(className="bi bi-arrow-repeat me-1"), "Compute / update live forecast"], id="l-run",
                   color="primary", className="mt-2"),
        dcc.Loading(html.Div(id="l-run-out", children=extra, className="mt-3"), type="dot"),
    ]))


def page_live():
    if not D.has_live():
        return [html.Div([html.H2("Live forecast", className="mb-1"),
                          html.P("The latest measured data and the model's forecast for the next hours.",
                                 className="lead-text")], className="page-head"),
                dbc.Alert([html.I(className="bi bi-hourglass-split me-2"),
                           "No live forecast on this computer yet. Click the button below to compute it."],
                          color="warning"),
                live_setup_box()]
    m = D.live_meta()
    last, issued = m["last_measured_hour_local"], m["issued_at_local"]
    end_of_last = last + pd.Timedelta(hours=1)
    controls = dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([html.Label(["Zone (region) ", html.Span("(none = all)", className="text-secondary")],
                            className="ctl-label"),
                 zone_picker("l-zone", ["NW"])], lg=3, md=6),
        dbc.Col([html.Label("Time horizon", className="ctl-label"), horizon_picker("l-hz", 24)], lg=3, md=6),
        dbc.Col([html.Label(["Consumption type ", html.Span("(optional)", className="text-secondary")],
                            className="ctl-label"),
                 dcc.Dropdown(id="l-load", options=LOAD_OPTS, value=[], multi=True, placeholder="All types")],
                lg=3, md=6),
        dbc.Col([html.Label("Show", className="ctl-label"),
                 dcc.Dropdown(id="l-span", clearable=False, value=2,
                              options=[{"label": "Today", "value": 1}, {"label": "Last 2 days", "value": 2},
                                       {"label": "All latest days (8)", "value": 8}]),
                 dbc.Switch(id="l-int", value=S.INTERVALS_VALIDATED, className="mt-2",
                            label=f"{int(S.INTERVAL_LEVEL * 100)}% interval (experimental)")], lg=3, md=6),
    ], className="g-3")), className="controls-card mb-4")
    tiles = zone_tiles()
    return [
        html.Div([html.H2("Live forecast", className="mb-1"),
                  html.P(["Latest measurement: ", html.B(f"{last:%a %d %b %Y}, {last:%H:%M}–{end_of_last:%H:%M}"),
                          " (Madrid). Forecasts issued at ", html.B(f"{issued:%H:%M}"),
                          " with the data known at that moment. Everything to the right of the ", html.I("now"),
                          " line is a forecast."], className="lead-text")], className="page-head"),
        tiles,
        controls,
        html.Div(id="l-summary", className="summary-card mb-4"),
        dbc.Row(id="l-kpis", className="g-3 mb-4"),
        section("Latest data and forecast", "Hourly total of the selected circuits · Madrid time",
                dcc.Loading(dcc.Graph(id="l-chart", config={"displaylogo": False}), type="dot"),
                html.Div(id="l-note", className="small text-secondary mt-2")),
        section("Upcoming hours", "Forecasts after the last measurement, per circuit",
                dash_table.DataTable(id="l-table", page_size=12, sort_action="native", **TABLE_KW)),
        live_setup_box(html.Div(f"Current live forecast computed on {m['created_local']:%d %b %Y %H:%M} "
                                f"({m['rows']:,} forecasts, {m['future_rows']:,} of them ahead of the data).",
                                className="small text-secondary")),
    ]

def zone_tiles():
    """Floor plan of Storey 1 as four clickable zone tiles (NW | NE on top, SW | SE below): rest of today."""
    df = D.live_predictions()
    da = df[df["horizon_h"] == 24]
    last = D.live_meta()["last_measured_hour_local"]
    cells = {}
    for z in S.ZONES:
        d = da[da["zone"] == z]
        rest = d.loc[d["is_future"], "pred"].sum() / 1000
        lasth = d[d["target_local"] == last]
        meas = lasth["actual"].sum() if lasth["actual"].notna().all() and len(lasth) else np.nan
        cells[z] = html.Button([
            html.Div([html.Span(className="zone-dot lg", style={"background": S.ZONE_COLORS[z]}),
                      html.Span(z, className="tile-zone"), html.Span(S.ZONE_HELP[z], className="tile-help")],
                     className="tile-head"),
            html.Div([html.Div([html.Div(f"{rest:,.1f}", className="tile-value"),
                                html.Div("kWh rest of today", className="tile-label")]),
                      html.Div([html.Div(fmt(meas, 0), className="tile-value small-v"),
                                html.Div("Wh last hour", className="tile-label")], className="text-end")],
                     className="d-flex justify-content-between align-items-end"),
        ], id={"type": "ztile", "zone": z}, n_clicks=0, className="zone-tile",
            style={"--zc": S.ZONE_COLORS[z]})
    return html.Div([
        html.Div([html.Span([html.Span("Storey 1 at a glance", className="mini-label mb-0"),
                             info_icon("Storey 1 at a glance")], className="d-flex align-items-center gap-1"),
                  html.Span("click a zone to select it", className="tile-hint")],
                 className="d-flex justify-content-between align-items-center mb-2"),
        html.Div([cells["NW"], cells["NE"], cells["SW"], cells["SE"]], className="tile-grid"),
    ], className="mb-4")


@app.callback(Output("l-zone", "value"), Input({"type": "ztile", "zone": ALL}, "n_clicks"), prevent_initial_call=True)
def _tile_click(clicks):
    if not ctx.triggered_id or not any(clicks):
        return no_update
    return [ctx.triggered_id["zone"]]


@app.callback(Output("l-kpis", "children"), Output("l-chart", "figure"), Output("l-note", "children"),
              Output("l-summary", "children"),
              Output("l-table", "data"), Output("l-table", "columns"),
              Input("l-zone", "value"), Input("l-hz", "value"), Input("l-load", "value"), Input("l-span", "value"),
              Input("l-int", "value"), Input("cfg", "data"))
def _live(zones, hz, loads, span, show_int, cfg):
    m = D.live_meta()
    last = m["last_measured_hour_local"]
    df = D.live_predictions()
    sel = D.select(df, hz, zones or None, loads or None)
    if sel.empty:
        return ([], empty_fig("No circuit matches this selection — try another zone or consumption type."), "",
                None, [], [])
    day0 = (last.normalize() - pd.Timedelta(days=span - 1))
    sel_w = sel[sel["target_local"] >= day0]
    past, fut = sel[~sel["is_future"]], sel[sel["is_future"]]
    t = D.hourly_total(sel_w, bool(show_int))
    t_past = t[t["target_local"] <= last]
    t_fut = t[t["target_local"] >= last]          # starts at the last measured hour so the lines join

    n_circ = sel["circuit"].nunique()
    fut_tot = D.hourly_total(fut, False) if len(fut) else None
    ok = past.dropna(subset=["actual", "pred"])
    mae = float((ok["pred"] - ok["actual"]).abs().mean()) if len(ok) else np.nan
    if hz == 1:
        nxt = fut_tot.iloc[0] if fut_tot is not None and len(fut_tot) else None
        k2 = kpi("Next hour", f"{fmt(nxt['pred'] if nxt is not None else np.nan, 0)} Wh",
                 f"{nxt['target_local']:%H:%M}–{nxt['target_local'] + pd.Timedelta(hours=1):%H:%M}" if nxt is not None else "",
                 "bi-skip-forward", id_="lk-next", tone="indigo")
    else:
        lab = "Next 6 hours" if hz == 6 else "Rest of today"
        span_txt = (f"{fut_tot['target_local'].min():%H:%M}–{fut_tot['target_local'].max() + pd.Timedelta(hours=1):%H:%M}"
                    if fut_tot is not None and len(fut_tot) else "")
        k2 = kpi(lab, f"{fut_tot['pred'].sum() / 1000 if fut_tot is not None else 0:,.2f} kWh", span_txt,
                 "bi-skip-forward", id_="lk-next", tone="indigo")
    peak = fut_tot.loc[fut_tot["pred"].idxmax()] if fut_tot is not None and len(fut_tot) else None
    lastrow = t_past.dropna(subset=["actual"]).tail(1)
    kp = [
        dbc.Col(kpi("Last measured hour", f"{fmt(lastrow['actual'].iloc[0], 0) if len(lastrow) else '–'} Wh",
                    f"{last:%a %d %b, %H:%M} · {n_circ} circuit{'s' if n_circ > 1 else ''}", "bi-activity",
                    id_="lk-last", tone="slate"), md=3),
        dbc.Col(k2, md=3),
        dbc.Col(kpi("Highest upcoming hour", f"{fmt(peak['pred'] if peak is not None else np.nan, 0)} Wh",
                    f"{peak['target_local']:%H:%M}" if peak is not None else "", "bi-graph-up-arrow",
                    id_="lk-peak", tone="amber"), md=3),
        dbc.Col(kpi("Error on the latest days", f"{fmt(mae)} Wh",
                    f"MAE per circuit-hour, {S.HORIZONS[hz]} · data never used to build the model", "bi-bullseye",
                    tip="Mean absolute error of this horizon on the latest days of data (after the test week).",
                    id_="lk-mae", tone="green"), md=3),
    ]

    # one plain-language sentence for the selection
    what = (", ".join(zones) if zones else "the whole floor") + (f" · {', '.join(loads)}" if loads else "")
    last_val = lastrow["actual"].iloc[0] if len(lastrow) else np.nan
    if fut_tot is not None and len(fut_tot):
        if hz == 1:
            ahead = [html.B(f"{fut_tot['pred'].iloc[0]:,.0f} Wh"), " in the next hour (",
                     f"{fut_tot['target_local'].iloc[0]:%H:%M}", ")"]
        else:
            ahead = [html.B(f"{fut_tot['pred'].sum() / 1000:,.1f} kWh"),
                     " over the next 6 hours" if hz == 6 else " for the rest of today",
                     ", highest at ", html.B(f"{peak['target_local']:%H:%M}"), f" ({peak['pred']:,.0f} Wh)"]
        trend = ""
        if not np.isnan(last_val) and last_val > 0:
            ch = (fut_tot["pred"].iloc[0] - last_val) / last_val * 100
            trend = (" — consumption is expected to rise" if ch > 10 else
                     " — consumption is expected to fall" if ch < -10 else " — consumption is expected to stay stable")
        summary = [html.I(className="bi bi-chat-square-text summary-icon"), html.Div([
            html.B(what), f" ({n_circ} circuit{'s' if n_circ > 1 else ''}) used ",
            html.B(f"{fmt(last_val, 0)} Wh"), f" in the last measured hour ({last:%H:%M}). The model expects ",
            *ahead, trend + "."])]
    else:
        summary = [html.I(className="bi bi-chat-square-text summary-icon"),
                   html.Div("No forecast ahead for this selection.")]

    f = fig_base(420)
    now_x = (last + pd.Timedelta(hours=1)).tz_localize(None)
    x_end = t["time"].max() + pd.Timedelta(minutes=30)
    f.add_vrect(x0=now_x, x1=x_end, fillcolor=C["future"], line_width=0, layer="below")
    if show_int:
        f.add_trace(go.Scatter(x=t["time"], y=t["hi"], line=dict(width=0), hoverinfo="skip", showlegend=False))
        f.add_trace(go.Scatter(x=t["time"], y=t["lo"], fill="tonexty", fillcolor=C["band"], line=dict(width=0),
                               name=f"{int(S.INTERVAL_LEVEL * 100)}% interval (experimental)",
                               customdata=np.c_[t["lo"], t["hi"]],
                               hovertemplate="Interval %{customdata[0]:,.0f} – %{customdata[1]:,.0f} Wh<extra></extra>"))
    f.add_trace(go.Scatter(x=t_past["time"], y=t_past["actual"], name="Measured", mode="lines",
                           line=dict(color=C["actual"], width=2.2, shape="spline", smoothing=0.4),
                           fill="tozeroy" if not show_int else None, fillcolor=C["actual_fill"],
                           hovertemplate="Measured %{y:,.0f} Wh<extra></extra>"))
    f.add_trace(go.Scatter(x=t_past["time"], y=t_past["pred"], name=f"Forecast made at the time ({S.HORIZONS[hz]})",
                           mode="lines", line=dict(color=C["forecast"], width=1.8, shape="spline", smoothing=0.4),
                           hovertemplate="Forecast %{y:,.0f} Wh<extra></extra>"))
    if len(t_fut) > 1 or (len(t_fut) == 1 and hz == 1):
        f.add_trace(go.Scatter(x=t_fut["time"], y=t_fut["pred"], name="Forecast ahead", mode="lines+markers",
                               line=dict(color=C["forecast"], width=3, dash="dash"),
                               marker=dict(size=9, color="white", line=dict(color=C["forecast"], width=2.5)),
                               hovertemplate="Forecast ahead %{y:,.0f} Wh<extra></extra>"))
    n_live = 0
    if hz == 24 and D.has_live():                       # anomalies of the latest data (spikes ▲, drops ▼)
        c_ = {**AN.DEFAULTS, **(cfg or {})}
        lf, lh, la = _anom_cached("live", round(c_["level"], 2), float(c_["min_dev"]), c_["p1"], c_["p2"], c_["p3"],
                                  D.LIVE_CSV.stat().st_mtime)
        la = in_scope(la, zones, loads)
        la = la[la["start"] >= day0.tz_localize(None)]
        n_live = len(la)
        tp = t.set_index("time")["actual"]
        for k in ("Spike", "Drop"):
            r = la[la["kind"] == k]
            if len(r):
                f.add_trace(go.Scatter(x=r["start"], y=tp.reindex(r["start"]).to_numpy(), mode="markers",
                                       name=f"{k}s", customdata=np.c_[r["id"], r["load_type"], r["dev_kwh"], r["level"]],
                                       marker=dict(symbol=KIND_SYMBOL[k], size=14,
                                                   color=[LEVEL_COLOR[l] for l in r["level"]],
                                                   line=dict(color="white", width=1.5)),
                                       hovertemplate="%{customdata[0]} · %{customdata[1]} · %{customdata[3]}<br>"
                                                     "%{customdata[2]:+.2f} kWh vs forecast<extra></extra>"))
    f.add_vline(x=now_x, line=dict(color="#334155", dash="dot", width=1.5))
    f.add_annotation(x=now_x, y=1, yref="paper", text="NOW", showarrow=False, xanchor="left", yanchor="top",
                     font=dict(size=11, color="white"), bgcolor="#334155", borderpad=3, xshift=6)
    f.add_annotation(x=now_x, y=0.9, yref="paper", text="forecast →", showarrow=False, xanchor="left",
                     font=dict(size=11, color=C["forecast"]), xshift=6)
    f.update_yaxes(title_text="Wh per hour", rangemode="tozero")
    f.update_xaxes(tickformat="%a %d %b\n%H:%M" if span > 1 else "%H:%M")

    note = []
    if hz == 6:
        note.append("+6 h: each point ahead was forecast 6 hours before that hour, so the forecasts reach 6 hours past "
                    "the last measurement. ")
    if hz == 24:
        note.append("Day-ahead: today's 24 values were all forecast at 00:00; the dashed part is the rest of today. "
                    "Tomorrow's day-ahead forecast is issued at midnight, when today's data are complete. ")
    if hz == 24 and n_live:
        note.append(f"▲/▼ = {n_live} anomaly(ies) in this view: measured energy outside the forecast interval "
                    "(details on the Anomalies page, period “Latest data” in Settings). ")
    n_missing = int(sel_w["pred"].isna().sum())
    if n_missing:
        note.append(f"{n_missing} circuit-hours have no forecast: the circuit had no valid data in the hours the model "
                    "reads (SE/SW measurement gaps). ")
    if t_past["actual"].isna().any():
        note.append("Gaps in the measured line = hours where a selected circuit has no valid measurement. ")

    tab = fut.copy()
    if show_int and len(tab):
        tab = D.add_intervals(tab)
    tab["Time (Madrid)"] = tab["target_local"].dt.strftime("%a %d %b %H:%M")
    tab["Issued (Madrid)"] = tab["issue_utc"].dt.tz_convert(S.TZ_LOCAL).dt.strftime("%a %d %b %H:%M")
    tab["Forecast (Wh)"] = tab["pred"].round(1)
    cols = ["Time (Madrid)", "circuit", "zone", "load_type", "Issued (Madrid)", "Forecast (Wh)"]
    if show_int and len(tab):
        tab["Low (Wh)"], tab["High (Wh)"] = tab["lo"].round(1), tab["hi"].round(1)
        cols += ["Low (Wh)", "High (Wh)"]
    tab = tab.sort_values(["target_local", "circuit"])[cols].rename(
        columns={"circuit": "Circuit", "zone": "Zone", "load_type": "Type"})
    tab = tab.astype(object).where(tab.notna(), None)
    return (kp, f, "".join(note), summary, tab.to_dict("records"),
            [{"name": c, "id": c, "type": "numeric" if "(Wh)" in c else "text"} for c in tab.columns])


@app.callback(Output("l-run-out", "children"), Input("l-run", "n_clicks"), prevent_initial_call=True)
def _live_run(_):
    try:
        r = D.run_live()
    except Exception as e:  # noqa: BLE001
        r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if not r["ok"]:
        return dbc.Alert([html.B("The live forecast could not be computed. "),
                          "Check that the packages in requirements-live.txt are installed (Python 3.11+).",
                          html.Pre(r["error"], className="small mt-2 mb-0")], color="danger")
    w = r.get("chronos_weights_match_frozen", {})
    wtxt = ("Chronos-Bolt weights identical to the frozen ones." if w and all(w.values())
            else "Note: the Chronos-Bolt weights differ from the checksum recorded when the model was frozen.")
    return dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"),
                      f"Live forecast computed in {r['seconds']} s: {r['rows']:,} forecasts, {r['future_rows']:,} "
                      f"ahead of the data. {wtxt} ", html.A("Reload the page", href="/live"), " to see it."],
                     color="success")


# ==========================================================================================================
# Page 3 — Performance indicators (official Task 6 scores of the final model)
# ==========================================================================================================
def page_performance():
    return [
        html.Div([html.H2("Performance", className="mb-1"),
                  html.P("How accurate the final model is. These are the official scores of the Sprint 3 model "
                         "comparison (Task 6): same hours for every model, 95% confidence intervals from a 24-hour "
                         "block bootstrap.", className="lead-text")], className="page-head"),
        dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([html.Label("Period", className="ctl-label"),
                     dbc.RadioItems(id="p-split", options=SPLIT_OPTS, value="test", inline=True, className="seg",
                                    inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                                    labelCheckedClassName="active")], md=6),
            dbc.Col([html.Label("Time horizon (charts)", className="ctl-label"),
                     horizon_picker("p-hz", 24)], md=6)])),
            className="controls-card mb-4"),
        dbc.Row(id="p-kpis", className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(section("Error by zone", "MAE with 95% CI, Wh per circuit-hour",
                            dcc.Graph(id="p-zone", config={"displayModeBar": False})), lg=5),
            dbc.Col(section("Error by circuit and horizon", "MAE, Wh per circuit-hour",
                            dcc.Graph(id="p-heat", config={"displayModeBar": False})), lg=7),
        ]),
        section("Error by hour of day", "MAE, Wh per circuit-hour · Madrid time",
                dcc.Graph(id="p-hour", config={"displayModeBar": False}),
                html.Div("Night hours are the hardest: almost all of that error comes from NW | Plugs & Sockets "
                         "(see Known limitations).", className="small text-secondary")),
        section("Forecast interval at each level", "The interval that defines the anomalies: at level X% about X% "
                "of the measured hours should fall inside it", html.Div(id="p-band")),
        section("Prediction interval check", "Experimental · calibrated on the validation week, checked on the test week",
                html.Div(id="p-int")),
        detection_test_block(),
    ]


@app.callback(Output("p-kpis", "children"), Output("p-zone", "figure"), Output("p-heat", "figure"),
              Output("p-hour", "figure"), Output("p-int", "children"), Input("p-split", "value"), Input("p-hz", "value"))
def _performance(split, hz):
    m = D.official_metrics(split)
    allc = m[m["scope"] == "all circuits"].set_index("horizon")
    kp = []
    for h in [1, 6, 24]:
        r = allc.loc[S.HORIZON_KEYS[h]]
        kp.append(dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([html.Span(S.HORIZONS[h]), info_icon(f"{S.HORIZONS[h]} · scores", IT.INFO["Score cards"])],
                     className="kpi-title"),
            html.Div([html.Span(f"{r.MAE_Wh:.1f}", className="kpi-value"), html.Span(" Wh MAE", className="kpi-unit")]),
            html.Div(f"95% CI {r.MAE_lo:.1f} – {r.MAE_hi:.1f} Wh", className="kpi-sub"),
            html.Hr(className="my-2"),
            html.Div([html.Span("RMSE ", className="text-secondary"), f"{r.RMSE_Wh:.1f} Wh",
                      html.Span(" · scaled MAE ", className="text-secondary"), f"{r.scaled_MAE:.3f}",
                      html.Span(" · WAPE ", className="text-secondary"), f"{r['WAPE_%']:.1f}%"], className="small"),
            html.Div(f"{int(r.n):,} circuit-hours scored", className="small text-secondary"),
        ]), className="kpi-card h-100"), md=4))

    hk = S.HORIZON_KEYS[hz]
    z = m[(m["horizon"] == hk) & m["scope"].str.startswith("zone")].copy()
    z["zone"] = z["scope"].str.replace("zone ", "")
    n_circ_rows = D.official_per_circuit(split)["circuit"].nunique()
    fz = fig_base(max(320, 26 * n_circ_rows + 60), hovermode="closest")
    fz.add_trace(go.Bar(x=z["zone"], y=z["MAE_Wh"], width=0.55,
                        marker=dict(color=[S.ZONE_COLORS[v] for v in z["zone"]], cornerradius=6),
                        error_y=dict(type="data", symmetric=False, array=z["MAE_hi"] - z["MAE_Wh"],
                                     arrayminus=z["MAE_Wh"] - z["MAE_lo"], color="#52514e", thickness=1.2, width=5),
                        customdata=np.c_[z["MAE_lo"], z["MAE_hi"], z["n"]],
                        hovertemplate="Zone %{x}<br>MAE %{y:.1f} Wh<br>95% CI %{customdata[0]:.1f}–%{customdata[1]:.1f}"
                                      "<br>%{customdata[2]} circuit-hours<extra></extra>"))
    fz.update_yaxes(title_text="Wh", rangemode="tozero")

    pc = D.official_per_circuit(split)
    piv = pc.pivot_table(index="circuit", columns="horizon_h", values="MAE_Wh").reindex(columns=[1, 6, 24])
    piv = piv.loc[piv[24].sort_values().index]
    fh = fig_base(max(320, 26 * len(piv) + 60), hovermode="closest")
    fh.add_trace(go.Heatmap(z=piv.values, x=[S.HORIZONS[c] for c in piv.columns], y=piv.index,
                            colorscale=[[i / 6, c] for i, c in enumerate(C["seq"])], xgap=2, ygap=2,
                            text=[[f"{v:.1f}" for v in row] for row in piv.values], texttemplate="%{text}",
                            hovertemplate="%{y} · %{x}<br>MAE %{z:.1f} Wh<extra></extra>",
                            colorbar=dict(title="Wh", thickness=10)))
    fh.update_layout(margin=dict(l=150, r=16, t=8, b=36))
    fh.update_yaxes(showgrid=False)

    bh = D.official_by_hour(split)
    bh = bh[bh["horizon"] == hk]
    fhour = fig_base(300, hovermode="closest")
    fhour.add_vrect(x0=-0.5, x1=8.5, fillcolor="#f1f0eb", line_width=0, layer="below",
                    annotation_text="night / early morning", annotation_position="top left",
                    annotation_font=dict(size=11, color="#52514e"))
    fhour.add_trace(go.Bar(x=bh["hour_local"], y=bh["MAE_Wh"], width=0.7,
                           marker=dict(color=[C["seq"][5] if h_ <= 8 else C["seq"][2] for h_ in bh["hour_local"]],
                                       cornerradius=4),
                           customdata=bh["n"], hovertemplate="%{x}:00 · MAE %{y:.1f} Wh<br>%{customdata} circuit-hours"
                                                             "<extra></extra>"))
    fhour.update_xaxes(title_text="Hour of day", dtick=2, range=[-0.6, 23.6])
    fhour.update_yaxes(title_text="Wh", rangemode="tozero")

    cov = D.interval_coverage("test")
    rows = [html.Tr([html.Td(S.HORIZONS[int(r.horizon_h)]), html.Td(f"{r.coverage * 100:.1f}%"),
                     html.Td(f"{int(S.INTERVAL_LEVEL * 100)}%"), html.Td(f"{r.mean_width_Wh:,.0f} Wh"),
                     html.Td(f"{int(r.n):,}")]) for r in cov.itertuples()]
    int_box = html.Div([
        dbc.Table([html.Thead(html.Tr([html.Th("Horizon"), html.Th("Test hours inside"), html.Th("Target"),
                                       html.Th("Mean width"), html.Th("Hours")])), html.Tbody(rows)],
                  bordered=False, hover=True, size="sm", className="mb-2"),
        html.Div([status_badge("warning"), html.Span(
            " Intervals stay hidden by default until Pole 1 validates them. Coverage close to the target on the test "
            "week supports the method; much lower coverage means the intervals are too narrow.",
            className="small text-secondary ms-1")]),
    ])
    return kp, fz, fh, fhour, int_box


# ==========================================================================================================
# Page 4 — Known limitations
# ==========================================================================================================
LIMITS = [
    ("critical", "Night-time error on NW | Plugs & Sockets",
     "The circuit's night consumption rose from 514 Wh/h (training) to 980 Wh/h (validation) and 1,043 Wh/h (test), "
     "1,924 Wh/h on the night of 30 Sep. The model, trained on the lower level, under-forecasts it. It explains 79% "
     "of the night error (00–09 h) of the test week and, with SE | Lighting, about 76% of all validation error "
     "(Sprint 4 Task 1). Cause to be confirmed with the data owner.",
     "Treat night forecasts for this circuit as a lower bound."),
    ("warning", "Few measured hours in the SE and SW zones",
     "SE/SW circuits had little or no valid data in training, and some have many invalid hours in the test week "
     "(e.g. SE | Plugs & Sockets: 63 of 168 hours scored). Scores for these circuits are less reliable.",
     "Check the coverage chart below before trusting a circuit's score."),
    ("warning", "Only one test week",
     "All scores come from 29 Sep – 5 Oct 2025 (168 hours). Many differences are within the confidence intervals, "
     "and the model has not seen other seasons (training: 19 Aug – 22 Sep 2025).",
     "Expect larger errors in winter or in holiday periods."),
    ("warning", "Unusual events are not predictable",
     "On 3 Oct NE | HVAC used 690 / 686 / 266 Wh in three hours against a normal ~3 Wh. Such events are not in the "
     "data the model learns from. They change MAE little but double the scaled error.",
     "Large measured-vs-forecast gaps can signal an anomaly worth checking."),
    ("info", "Outdoor temperature is not used",
     "Sprint 4 Task 2 tested two temperature inputs: they made +1 h and +6 h worse and did not change day-ahead, "
     "because the training period has almost no temperature variety. The decision is to retest with data that "
     "include cool and warm periods.", "HVAC forecasts may react late to sudden weather changes."),
    ("info", "Prediction intervals not yet validated",
     "The intervals shown in the dashboard are experimental (Chronos-Bolt band calibrated on one validation week) "
     "until Pole 1 validates them.", "Use them as a rough range only."),
    ("info", "Energy only",
     "Power (W) and current (A) are not forecast, only hourly energy (Wh).", "Peak power is not covered."),
]


def page_limitations():
    cards = []
    for lvl, title, text, advice in LIMITS:
        cards.append(dbc.Col(dbc.Card(dbc.CardBody([
            html.Div(status_badge(lvl), className="mb-2"), html.H6(title), html.P(text, className="small mb-2"),
            html.Div([html.I(className="bi bi-lightbulb me-1"), html.B("What it means for you: "), advice],
                     className="small advice")]), className=f"h-100 limit-card limit-{lvl}"), lg=6))

    cov = D.data_coverage("test")
    fc = fig_base(max(320, 26 * len(cov) + 60), hovermode="closest")
    fc.add_trace(go.Bar(y=cov["circuit"], x=cov["coverage"] * 100, orientation="h", width=0.6,
                        marker=dict(color=[C["critical"] if v < 0.6 else C["warning"] if v < 0.9 else C["forecast"]
                                           for v in cov["coverage"]]),
                        customdata=cov["valid_h"], hovertemplate="%{y}<br>%{customdata} of 168 hours measured"
                                                                  "<extra></extra>"))
    fc.add_vline(x=90, line=dict(color="#52514e", dash="dot", width=1), annotation_text="90%",
                 annotation_font=dict(size=11, color="#52514e"))
    fc.update_layout(margin=dict(l=150, r=16, t=8, b=36), showlegend=False)
    fc.update_xaxes(title_text="% of hours with a valid measurement (test week)", range=[0, 103], showgrid=True,
                    gridcolor=C["grid"])

    fn = fig_base(max(320, 26 * len(cov) + 60), hovermode="closest")
    fn.add_trace(go.Bar(x=["Training<br>19 Aug – 21 Sep", "Validation<br>22 – 28 Sep", "Test<br>29 Sep – 5 Oct"],
                        y=[514, 980, 1043], marker=dict(color=[C["seq"][2], C["seq"][4], C["seq"][6]]), width=0.5,
                        text=["514", "980", "1,043"], textposition="outside", cliponaxis=False,
                        hovertemplate="%{x}<br>%{y:,} Wh/h<extra></extra>"))
    fn.update_yaxes(title_text="Mean night consumption, Wh/h", rangemode="tozero", range=[0, 1250])

    return [
        html.Div([html.H2("Known limitations", className="mb-1"),
                  html.P("Where the forecasts are weaker and why. Read this before acting on a forecast.",
                         className="lead-text")], className="page-head"),
        dbc.Row(cards, className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(section("NW | Plugs & Sockets: night consumption keeps rising", "Mean consumption 00–09 h",
                            dcc.Graph(figure=fn, config={"displayModeBar": False})), lg=5),
            dbc.Col(section("Measured hours per circuit", "Test week · red < 60%, amber < 90%",
                            dcc.Graph(figure=fc, config={"displayModeBar": False})), lg=7),
        ]),
    ]


# ==========================================================================================================
# Page 5 — The model (how it works + run the frozen model)
# ==========================================================================================================
def page_model():
    bc = D.blend_config()
    hz = [("+1h", 1), ("+6h", 6), ("day-ahead", 24)]
    parts = [("w_gbm", "Gradient boosting v1.3", C["seq"][6]), ("w_hybrid", "ChronosGBM v1.3", C["seq"][4]),
             ("w_chronos", "Chronos-Bolt v1.3", C["seq"][2])]
    fw = fig_base(220, hovermode="closest", barmode="stack")
    for key, name, col in parts:
        vals = [bc["horizons"][k][key] for k, _ in hz]
        fw.add_trace(go.Bar(y=[S.HORIZONS[h] for _, h in hz], x=vals, name=name, orientation="h",
                            marker=dict(color=col, line=dict(color="white", width=2)),
                            text=[f"{v:.2f}" for v in vals], textposition="inside", insidetextanchor="middle",
                            textfont=dict(color="white" if col != C["seq"][2] else "#0d366b"),
                            hovertemplate=name + " · %{y}: weight %{x:.2f}<extra></extra>"))
    fw.update_layout(margin=dict(l=80, r=16, t=30, b=30))
    fw.update_xaxes(range=[0, 1], title_text="Weight in the blend", showgrid=True, gridcolor=C["grid"])
    fw.update_yaxes(autorange="reversed")

    comp = [("Gradient boosting v1.3", "Learns from the recent history of each circuit, the hour, weekday and "
                                       "holidays. Trained on 15 circuits, forecasts all 16."),
            ("Chronos-Bolt v1.3", "Pre-trained time-series foundation model (Amazon). Used zero-shot: it reads the "
                                  "last days of a circuit and continues the pattern."),
            ("ChronosGBM v1.3", "Gradient boosting that also receives Chronos-Bolt's forecast range (10th, 50th, "
                                "90th percentile) as inputs.")]
    has = {s: D.has_recomputed(s) for s in ("test", "validation")}
    return [
        html.Div([html.H2("The model", className="mb-1"),
                  html.P(["The final model is ", html.B(S.MODEL_NAME), ": a weighted average of three forecasters. "
                          "Weights were chosen per horizon on the validation week (rule D10) and frozen on 29 Oct "
                          "2026; Sprint 4 Task 2 kept it unchanged (temperature did not help)."],
                         className="lead-text")], className="page-head"),
        dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.H6(n), html.P(t, className="small mb-0")]), className="h-100"),
                         md=4) for n, t in comp], className="g-3 mb-4"),
        section("Blend weights by horizon", "Share of each forecaster in the final forecast",
                dcc.Graph(figure=fw, config={"displayModeBar": False})),
        section("Run the frozen model", "Recompute the forecasts from the saved model files, inside this app", html.Div([
            html.P(["This runs the two frozen gradient-boosting parts (", html.Code(".joblib"), " files in ",
                    html.Code("TBDA_v1.3_ChronosGBM_29-10/models"), ") on dataset v1.2, adds the frozen Chronos-Bolt "
                    "forecasts from their cache and blends them with the frozen weights. Nothing is retrained. When it "
                    "finishes, the Forecast replay page uses the recomputed values."], className="small"),
            dbc.Row([
                dbc.Col(dcc.Dropdown(id="m-split", options=SPLIT_OPTS, value="test", clearable=False), md=4),
                dbc.Col(dbc.Button([html.I(className="bi bi-play-fill me-1"), "Run model"], id="m-run",
                                   color="primary"), md="auto"),
            ], className="g-2 align-items-center mb-3"),
            dcc.Loading(html.Div(id="m-out", children=html.Div(
                ["Recomputed forecasts available: ",
                 ", ".join(s for s, v in has.items() if v) or "none yet (the app shows the stored Task 6 forecasts)."],
                className="small text-secondary")), type="dot"),
        ])),
        section("Add new measurements", "The model stays frozen; the data can grow. Point to the newest export of "
                "the cleaned data and the app rebuilds the hourly dataset with the team's v1.2 rules, then forecasts "
                "from the new last measurement.", html.Div([
                    html.P(["Accepted: the zip or folder of the cleaned data (", html.Code("NE/ NW/ SE/ SW/"),
                            " with ", html.Code("clean_Storey1_<zone>_CLEAN_DATA.csv"), ", like ",
                            html.Code("CLEAN DATA all zones.zip"), "), or one CSV for all zones. Paths are relative to "
                            "the repository folder."], className="small"),
                    dbc.InputGroup([dbc.Input(id="u-path", placeholder="CLEAN DATA all zones.zip", type="text"),
                                    dbc.Button([html.I(className="bi bi-cloud-arrow-up me-1"), "Update data & forecast"],
                                               id="u-run", color="primary")], className="mb-2"),
                    dcc.Loading(html.Div(id="u-out", children=html.Div(
                        f"Dataset in use: {S.current_derived().relative_to(S.REPO)}", className="hint")), type="dot")])),
        section("Data and evaluation", "", html.Ul([
            html.Li("Data: hourly energy of 16 circuits, CeDInt Storey 1, dataset v1.2 (gap rule + energy/power check)."),
            html.Li("Training 19 Aug – 21 Sep 2025 · validation 22 – 28 Sep · test 29 Sep – 5 Oct (UTC)."),
            html.Li("Horizons: +1 h, +6 h, and day-ahead issued at 00:00 Madrid time (leads 1–24 h)."),
            html.Li("Main metric MAE (Wh); model choice by scaled MAE (MAE ÷ circuit training mean). The test week "
                    "was used once, with the frozen model."),
        ], className="small mb-0")),
    ]


@app.callback(Output("m-out", "children"), Output("run-stamp", "data"), Input("m-run", "n_clicks"),
              State("m-split", "value"), State("run-stamp", "data"), prevent_initial_call=True)
def _run(_, split, stamp):
    try:
        r = D.run_model(split)
    except Exception as e:  # noqa: BLE001  (shown to the user, the app keeps the stored forecasts)
        r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if not r["ok"]:
        return dbc.Alert([html.B("The model could not run. "), "The app keeps showing the stored forecasts.",
                          html.Pre(r["error"], className="small mt-2 mb-0")], color="danger"), no_update
    same = r["max_abs_diff_Wh"] < 0.01
    return dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"),
                      f"{r['rows']:,} forecasts computed for the {split} week in {r['seconds']} s. ",
                      f"Largest difference from the stored Task 6 forecasts: {r['max_abs_diff_Wh']:.4f} Wh "
                      f"({'identical' if same else 'check the model files'})."],
                     color="success" if same else "warning"), stamp + 1


# ==========================================================================================================
# Anomalies, data quality, energy & costs — shared helpers
# ==========================================================================================================
from functools import lru_cache as _lru  # noqa: E402

LEVEL_COLOR = {"Critical": "#c2410c", "Moderate": "#f59e0b", "Minor": "#94a3b8"}
KIND_SYMBOL = {"Spike": "triangle-up", "Drop": "triangle-down"}
TARIFF_COLOR = {"P1": "#6250d6", "P2": "#2a78d6", "P3": "#9ec5f4"}


@_lru(maxsize=16)
def _anom_cached(period, level, min_dev, p1, p2, p3, stamp):
    f = AN.frame(period, level)
    hrs, an = AN.detect(f, min_dev, {"p1": p1, "p2": p2, "p3": p3})
    return f, hrs, an


def anom(cfg):
    """(period used, hourly frame, anomaly hours, anomalies) for the current settings."""
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    period = cfg["period"]
    if period == "live" and AN.frame("live", cfg["level"]) is None:
        period = "eval"
    stamp = D.LIVE_CSV.stat().st_mtime if period == "live" else 0.0
    f, h, a = _anom_cached(period, round(cfg["level"], 2), float(cfg["min_dev"]), cfg["p1"], cfg["p2"], cfg["p3"], stamp)
    return period, f, h, a


def period_label(period):
    if period == "live" and D.has_live():
        m = D.live_meta()
        return f"{m['live_start_local']:%d %b} – {m['last_measured_hour_local']:%d %b %Y} (latest data)"
    return AN.PERIODS["eval"]


def in_scope(df, zones=None, loads=None):
    k = pd.Series(True, index=df.index)
    if zones:
        k &= df["zone"].isin(zones)
    if loads:
        k &= df["load_type"].isin(loads)
    return df[k]


def level_chip(level, kind=None):
    icon = {"Critical": "bi-lightning-fill", "Moderate": "bi-circle-half", "Minor": "bi-circle"}[level]
    k = ""
    if kind:
        k = " · ▲ spike" if kind == "Spike" else " · ▼ drop"
    return html.Span([html.I(className=f"bi {icon} me-1"), level + k], className=f"lvl-chip lvl-{level}")


def when_label(e):
    same = e.start.date() == (e.end - pd.Timedelta(minutes=1)).date()
    return f"{e.start:%a %d %b %H:%M}–{e.end:%H:%M}" if same else f"{e.start:%a %d %b %H:%M} → {e.end:%a %d %b %H:%M}"


def energy_cost(f, cfg):
    v = f.dropna(subset=["actual"])
    return float((v["actual"] / 1000 * AN.price_of(v["tariff"], {**AN.DEFAULTS, **cfg})).sum())


@app.callback(Output("settings", "is_open"), Input({"type": "opset", "n": ALL}, "n_clicks"),
              State("settings", "is_open"), prevent_initial_call=True)
def _open_settings(clicks, is_open):
    if not ctx.triggered or not ctx.triggered[0].get("value"):
        return no_update
    return not is_open


@app.callback(Output("cfg", "data"), Output("set-info", "children"),
              Input("set-period", "value"), Input("set-level", "value"), Input("set-mindev", "value"),
              Input("set-p1", "value"), Input("set-p2", "value"), Input("set-p3", "value"), Input("set-co2", "value"))
def _settings(period, level, mindev, p1, p2, p3, co2):
    cfg = {"period": period or "eval", "level": float(level or 0.9), "min_dev": float(mindev or 0),
           "p1": float(p1 or 0), "p2": float(p2 or 0), "p3": float(p3 or 0), "co2": float(co2 or 0)}
    per, f, h, a = anom(cfg)
    days = max(f["time"].dt.normalize().nunique(), 1)
    info = [html.B(f"{len(a)} anomalies"), f" in {days} days ({len(a) / days:.1f} a day): "
            f"{int((a['kind'] == 'Spike').sum())} spikes and {int((a['kind'] == 'Drop').sum())} drops. "
            f"The interval holds {AN.coverage(f) * 100:.0f}% of the measured hours (nominal {cfg['level'] * 100:.0f}%)."]
    return cfg, info


@app.callback(Output("nav-badge", "children"), Input("cfg", "data"))
def _badge(cfg):
    _, _, _, a = anom(cfg)
    n = int((a["level"] == "Critical").sum())
    return str(n) if n else None


# ==========================================================================================================
# Overview — forecast health and the period at a glance
# ==========================================================================================================
@app.callback(Output("ov-monitor", "children"), Input("cfg", "data"))
def _ov_monitor(cfg):
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    period, f, hrs, a = anom(cfg)
    cov = AN.coverage(f)
    valid = f["actual"].notna()
    used = f.loc[valid, "actual"].sum() / 1000
    cost = energy_cost(f, cfg)
    sp = a[a["kind"] == "Spike"]
    extra, extra_eur = sp["dev_kwh"].sum(), sp["cost_eur"].sum()
    g = go.Figure(go.Indicator(
        mode="gauge+number", value=cov * 100, number={"suffix": "%", "font": {"size": 40, "color": "#0f172a"}},
        title={"text": f"of measured hours inside the {cfg['level'] * 100:.0f}% forecast interval",
               "font": {"size": 13, "color": "#64748b"}},
        gauge={"axis": {"range": [0, 100], "tickcolor": "#cbd5e1", "tickfont": {"color": "#64748b"}},
               "bar": {"color": C["forecast"], "thickness": 0.28},
               "steps": [{"range": [0, cfg["level"] * 100 - 10], "color": "#fde8df"},
                         {"range": [cfg["level"] * 100 - 10, cfg["level"] * 100 - 3], "color": "#fef3c7"},
                         {"range": [cfg["level"] * 100 - 3, 100], "color": "#dcfce7"}],
               "threshold": {"line": {"color": "#0f172a", "width": 3}, "thickness": 0.8, "value": cfg["level"] * 100}}))
    g.update_layout(height=230, margin=dict(l=20, r=20, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family=FONT))
    verdict = ("The model behaves as expected in this period." if cov >= cfg["level"] - 0.03 else
               "More hours than expected fall outside the interval: look at the anomalies.")
    counts = a["level"].value_counts()
    health = section("Forecast health", period_label(period), dcc.Graph(figure=g, config={"displayModeBar": False}),
                     html.Div(verdict, className="hint text-center"),
                     html.Div([html.Div([html.Div(f"{int(counts.get(l, 0))}", className="mini-num"), level_chip(l)],
                                        className="text-center") for l in AN.LEVELS],
                              className="d-flex justify-content-around mt-2"))
    kp = dbc.Row([
        dbc.Col(kpi("Measured energy", f"{used:,.0f} kWh", f"{valid.mean() * 100:.0f}% of circuit-hours measured",
                    "bi-lightning-charge", id_="ovk-used", tone="slate"), md=6),
        dbc.Col(kpi("Energy cost (est.)", f"{cost:,.0f} €", "peak / standard / off-peak prices from Settings",
                    "bi-receipt", id_="ovk-cost", tone="indigo"), md=6),
        dbc.Col(kpi("Extra energy in spikes", f"{extra:,.1f} kWh", f"{extra_eur:,.2f} € · {extra * cfg['co2']:,.1f} kg CO₂ (est.)",
                    "bi-arrow-up-right", id_="ovk-extra", tone="amber"), md=6),
        dbc.Col(kpi("Drops below forecast", f"{int((a['kind'] == 'Drop').sum())}",
                    "possible outages or equipment switched off", "bi-arrow-down-right", id_="ovk-drop",
                    tone="blue"), md=6),
    ], className="g-3")
    # daily energy by tariff period + daily forecast
    v = f[valid].assign(day=f["time"].dt.normalize())
    full = f.assign(day=f["time"].dt.normalize()).groupby("day")["time"].nunique()
    v = v[v["day"].isin(full[full >= 20].index)]                     # drop the partial first/last day
    pt = v.pivot_table(index="day", columns="tariff", values="actual", aggfunc="sum").fillna(0) / 1000
    fc = v.groupby("day")["forecast"].sum() / 1000
    crit = a[a["level"] == "Critical"].assign(day=lambda x: x["start"].dt.normalize()).groupby("day").size()
    fd = fig_base(400, barmode="stack", hovermode="x unified", bargap=0.3)
    for tp in ("P3", "P2", "P1"):
        if tp in pt:
            fd.add_trace(go.Bar(x=pt.index, y=pt[tp], name=AN.TARIFF[tp], marker=dict(color=TARIFF_COLOR[tp]),
                                hovertemplate="%{y:,.0f} kWh<extra>" + AN.TARIFF[tp] + "</extra>"))
    fd.add_trace(go.Scatter(x=fc.index, y=fc.values, name="Forecast", mode="lines+markers",
                            line=dict(color="#0f172a", width=2, dash="dot"), marker=dict(size=6),
                            hovertemplate="Forecast %{y:,.0f} kWh<extra></extra>"))
    if len(crit):
        tot = pt.sum(axis=1)
        fd.add_trace(go.Scatter(x=crit.index, y=tot.reindex(crit.index).to_numpy() * 1.06, mode="text",
                                text=["⚡" * min(int(n), 3) for n in crit.values], name="Critical anomalies",
                                textfont=dict(size=14), hovertemplate="%{text} critical<extra></extra>"))
    fd.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000, tickangle=0, tickfont=dict(size=10))
    fd.update_yaxes(title_text="kWh per day")
    top = a.assign(s=a["dev_kwh"].abs()).sort_values("s", ascending=False).head(3)
    cards = [dcc.Link([
        html.Div([level_chip(r.level, r.kind), html.Span(r.zone, className="tag ms-2")], className="d-flex gap-1"),
        html.Div([html.B(r.load_type), f" · {when_label(r)}"], className="small mt-1"),
        html.Div(f"{r.dev_kwh:+,.2f} kWh vs forecast" + (f" · {r.cost_eur:,.2f} €" if r.kind == "Spike" else ""),
                 className="hint")], href=f"/anomalies#{r.id}", className=f"feed-item lvl-{r.level}")
        for r in top.itertuples()] or [html.Div("No anomalies in this period.", className="section-sub")]
    return [dbc.Row([dbc.Col(health, lg=4), dbc.Col(html.Div(kp, className="kpi-fill"), lg=8)], className="g-3 mb-4"),
            dbc.Row([
                dbc.Col(section("Energy per day by tariff period", "Measured energy split into peak, standard and "
                                "off-peak hours; the dotted line is what the model forecast",
                                dcc.Graph(figure=fd, config={"displayModeBar": False})), lg=8),
                dbc.Col(section("Biggest anomalies", "Largest deviations from the forecast", html.Div(cards),
                                dbc.Button(["Open the anomalies ", html.I(className="bi bi-arrow-right")],
                                           href="/anomalies", color="primary", outline=True, size="sm",
                                           className="w-100 mt-2")), lg=4)])]


# ==========================================================================================================
# Page — Anomalies
# ==========================================================================================================
def page_anomalies():
    return [
        html.Div([html.H2("Anomalies", className="mb-1"),
                  html.P("Hours where the measured energy left the model's forecast interval: spikes above it (extra "
                         "energy and cost) and drops below it (possible faults or outages). Click the map or a row.",
                         className="lead-text")], className="page-head"),
        dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([html.Label(["Zone ", html.Span("(none = all)", className="text-secondary")], className="ctl-label"),
                     zone_picker("a-zone", [])], lg=3, md=6),
            dbc.Col([html.Label("Consumption type", className="ctl-label"),
                     dcc.Dropdown(id="a-load", options=LOAD_OPTS, value=[], multi=True, placeholder="All types")],
                    lg=3, md=6),
            dbc.Col([html.Label("Direction", className="ctl-label"),
                     dbc.RadioItems(id="a-kind", value="ALL", options=[{"label": "Both", "value": "ALL"},
                                                                      {"label": "▲ Spikes", "value": "Spike"},
                                                                      {"label": "▼ Drops", "value": "Drop"}],
                                    className="seg", inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                                    labelCheckedClassName="active")], lg=3, md=6),
            dbc.Col([html.Label("Level", className="ctl-label"),
                     dbc.Checklist(id="a-level", value=list(AN.LEVELS), inline=True,
                                   options=[{"label": l, "value": l} for l in AN.LEVELS], className="zone-picker",
                                   inputClassName="btn-check", labelClassName="btn btn-sm zone-btn",
                                   labelCheckedClassName="active")], lg=3, md=6),
        ], className="g-3")), className="controls-card mb-3"),
        html.Div(id="a-summary", className="summary-card mb-3"),
        dbc.Tabs(id="a-tab", active_tab="anom", className="mb-3", children=[
            dbc.Tab(label="Anomalies", tab_id="anom"), dbc.Tab(label="Data quality", tab_id="quality")]),
        html.Div(id="a-anom-view", children=[
            section("Deviation map", "Every circuit, every hour: orange = above the forecast, blue = below, grey = as "
                    "expected (deviation in interval widths). Outlined cells are anomalies; blank = no valid reading.",
                    dcc.Graph(id="a-map", config={"displayModeBar": False})),
            section("Anomaly list", "Click a row for the full story", dash_table.DataTable(
                id="a-table", page_size=15, sort_action="native", **TABLE_KW),
                right=dbc.Button([html.I(className="bi bi-download me-1"), "CSV"], id="a-dl-btn", size="sm",
                                 color="primary", outline=True)),
            dcc.Download(id="a-dl")]),
        html.Div(id="a-quality-view", style={"display": "none"}),
    ]


def _filter_anom(a, zones, loads, kind, levels):
    a = in_scope(a, zones, loads)
    if kind in ("Spike", "Drop"):
        a = a[a["kind"] == kind]
    return a[a["level"].isin(levels or [])]


@app.callback(Output("a-summary", "children"), Output("a-map", "figure"), Output("a-table", "data"),
              Output("a-table", "columns"), Output("al-order", "data"), Output("a-quality-view", "children"),
              Output("a-anom-view", "style"), Output("a-quality-view", "style"),
              Input("cfg", "data"), Input("a-zone", "value"), Input("a-load", "value"), Input("a-kind", "value"),
              Input("a-level", "value"), Input("a-tab", "active_tab"), Input("reviewed", "data"))
def _anomalies(cfg, zones, loads, kind, levels, tab, acked):
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    period, f, hrs, a_all = anom(cfg)
    a = _filter_anom(a_all, zones, loads, kind, levels).sort_values("start")
    acked = set(acked or [])
    keyf = lambda i: f"{period}:{cfg['level']}:{cfg['min_dev']}:{i}"  # noqa: E731
    sp = a[a["kind"] == "Spike"]
    summ = [html.I(className="bi bi-activity summary-icon"), html.Div([
        html.B(f"{len(a)} anomalies"), f" in {period_label(period)}: ",
        html.B(f"{len(sp)} spikes"), f" adding {sp['dev_kwh'].sum():,.1f} kWh (≈ {sp['cost_eur'].sum():,.2f} €) and ",
        html.B(f"{int((a['kind'] == 'Drop').sum())} drops"), " below the forecast. ",
        f"{int((a['level'] == 'Critical').sum())} are critical; "
        f"{sum(1 for i in a['id'] if keyf(i) in acked)} acknowledged."])]

    # deviation map (diverging: blue below, grey as expected, orange above)
    ff = in_scope(f, zones, loads)
    z = ((ff["actual"] - ff["forecast"]) / ff["q_Wh"].clip(lower=1)).clip(-3, 3)
    piv = ff.assign(z=z).pivot_table(index="circuit", columns="time", values="z", aggfunc="first")
    order = sorted(piv.index, key=lambda c: (S.ZONES.index(c.split("|")[0]), c))[::-1]
    piv = piv.reindex(order)
    m = fig_base(max(300, 24 * len(order) + 80), hovermode="closest")
    m.add_trace(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, zmin=-3, zmax=3, zmid=0, ygap=1,
                           colorscale=[[0, "#1c5cab"], [0.33, "#9ec5f4"], [0.5, "#eef1f5"], [0.67, "#fdba74"],
                                       [1, "#c2410c"]],
                           colorbar=dict(title="σ", thickness=10, tickvals=[-3, -1, 0, 1, 3],
                                         ticktext=["−3 below", "−1", "0", "+1", "+3 above"]),
                           hovertemplate="%{y}<br>%{x|%a %d %b %H:%M}<br>deviation %{z:.1f} interval widths"
                                         "<extra></extra>", hoverongaps=False))
    ah = in_scope(hrs, zones, loads)
    ah = ah[ah["aid"].isin(a["id"])]
    if len(ah):
        m.add_trace(go.Scatter(x=ah["time"], y=ah["circuit"], mode="markers", name="anomaly hour",
                               customdata=np.c_[ah["aid"], ah["kind"]],
                               marker=dict(symbol="square-open", size=9, color="#0f172a", line=dict(width=1.4)),
                               hovertemplate="%{customdata[0]} · %{customdata[1]}<br>%{y}<br>%{x|%a %d %b %H:%M}"
                                             "<extra>click for details</extra>"))
    m.update_layout(margin=dict(l=150, r=20, t=10, b=40), showlegend=False)
    m.update_xaxes(tickformat="%a %d", dtick=86400000, showgrid=False)
    m.update_yaxes(showgrid=False)

    rows = []
    for r in a.assign(s=a["dev_kwh"].abs()).sort_values(["level", "s"], key=lambda c: c.map(
            {l: i for i, l in enumerate(AN.LEVELS)}) if c.name == "level" else -c).itertuples():
        rows.append({"id": r.id, "ID": r.id, "Level": r.level, "Type": "▲ Spike" if r.kind == "Spike" else "▼ Drop",
                     "When (Madrid)": when_label(r), "Zone": r.zone, "Circuit": r.load_type, "Hours": int(r.n),
                     "Deviation (kWh)": round(r.dev_kwh, 2), "Extra cost (€)": round(r.cost_eur, 2),
                     "Night/weekend": f"{r.night_share * 100:.0f}%", "Ack.": "✓" if keyf(r.id) in acked else ""})
    numc = ("Hours", "Deviation (kWh)", "Extra cost (€)")
    cols = [{"name": c, "id": c, "type": "numeric" if c in numc else "text"} for c in (rows[0] if rows else {}) if c != "id"]

    # data quality
    q = in_scope(AN.quality_table(f), zones, loads)
    by = q.groupby("reason")["hours"].sum().sort_values()
    fq = fig_base(max(260, 24 * f["circuit"].nunique() + 60), hovermode="closest")
    fq.add_trace(go.Bar(y=by.index, x=by.values, orientation="h", width=0.55, marker=dict(color="#64748b", cornerradius=4),
                        text=[f"{v:,} h" for v in by.values], textposition="outside", cliponaxis=False,
                        hovertemplate="%{y}: %{x:,} circuit-hours<extra></extra>"))
    fq.update_layout(margin=dict(l=230, r=50, t=8, b=30))
    measured = in_scope(f, zones, loads).groupby("circuit")["actual"].apply(lambda s: s.notna().mean()).sort_values()
    fm = fig_base(max(260, 24 * len(measured) + 60), hovermode="closest")
    fm.add_trace(go.Bar(y=measured.index, x=measured.values * 100, orientation="h", width=0.6,
                        marker=dict(color=[S.ZONE_COLORS[c.split("|")[0]] for c in measured.index], cornerradius=4),
                        text=[f"{v * 100:.0f}%" for v in measured.values], textposition="outside", cliponaxis=False,
                        hovertemplate="%{y}: %{x:.0f}% of hours with a valid reading<extra></extra>"))
    fm.update_layout(margin=dict(l=150, r=40, t=8, b=30))
    fm.update_xaxes(range=[0, 105], title_text="% of hours with a valid reading")
    quality = [dbc.Alert([html.I(className="bi bi-info-circle me-2"),
                          "Hours with a meter or data problem are left out of every calculation in this app — they are "
                          "never anomalies and never counted as zero. The rules are the team's dataset v1.2 checks."],
                         color="light", className="small border"),
               dbc.Row([dbc.Col(section("Why hours were excluded", f"{int(q['hours'].sum()) if len(q) else 0} "
                                        "circuit-hours", dcc.Graph(figure=fq, config={"displayModeBar": False})), lg=6),
                        dbc.Col(section("Measured hours per circuit", "Share of hours with a valid reading",
                                        dcc.Graph(figure=fm, config={"displayModeBar": False})), lg=6)]),
               section("Excluded periods", "", dash_table.DataTable(
                   data=[{"From": f"{r.start:%a %d %b %H:%M}", "To": f"{r.end:%a %d %b %H:%M}", "Zone": r.zone,
                          "Circuit": r.load_type, "Hours": int(r.hours), "Reason": r.reason} for r in q.itertuples()],
                   columns=[{"name": c, "id": c} for c in ("From", "To", "Zone", "Circuit", "Hours", "Reason")],
                   page_size=12, sort_action="native", **TABLE_KW))]
    show, hide = {}, {"display": "none"}
    return (summ, m, rows, cols, [r["id"] for r in rows], quality,
            show if tab == "anom" else hide, show if tab == "quality" else hide)


@app.callback(Output("al-open", "data"),
              Input("a-table", "active_cell"), Input("a-map", "clickData"), Input("url", "hash"),
              Input("al-prev", "n_clicks"), Input("al-next", "n_clicks"),
              State("al-open", "data"), State("al-order", "data"), prevent_initial_call=True)
def _pick(cell, click, hash_, _p, _n, cur, order):
    t, cur = ctx.triggered_id, (cur or {})
    k = cur.get("k", 0) + 1
    if t == "a-table" and cell and cell.get("row_id"):
        return {"id": cell["row_id"], "k": k}
    if t == "a-map" and click:
        cd = click["points"][0].get("customdata")
        return {"id": cd[0], "k": k} if cd else no_update
    if t == "url" and hash_ and len(hash_) > 2 and hash_[1] in "SD":
        return {"id": hash_[1:], "k": k}
    if t in ("al-prev", "al-next") and cur.get("id") in (order or []):
        i = order.index(cur["id"]) + (1 if t == "al-next" else -1)
        return {"id": order[max(0, min(len(order) - 1, i))], "k": k}
    return no_update


@app.callback(Output("al-detail", "is_open"), Output("al-body", "children"), Output("al-review", "children"),
              Input("al-open", "data"), Input("reviewed", "data"), State("cfg", "data"), prevent_initial_call=True)
def _detail(sel, acked, cfg):
    aid = (sel or {}).get("id")
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    period, f, hrs, a = anom(cfg)
    hit = a[a["id"] == aid] if aid else a.iloc[0:0]
    if hit.empty:
        return no_update, no_update, no_update
    e = next(hit.itertuples())
    done = f"{period}:{cfg['level']}:{cfg['min_dev']}:{aid}" in set(acked or [])
    g = f[(f["circuit"] == e.circuit) & (f["time"] >= e.start - pd.Timedelta(hours=24)) &
          (f["time"] < e.end + pd.Timedelta(hours=24))]
    fig = fig_base(250, margin=dict(l=48, r=10, t=10, b=34))
    fig.add_vrect(x0=e.start, x1=e.end, fillcolor=LEVEL_COLOR[e.level], opacity=0.15, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=g["time"], y=g["hi"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=g["time"], y=g["lo"], fill="tonexty", fillcolor=C["band"], line=dict(width=0),
                             name=f"{cfg['level'] * 100:.0f}% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g["time"], y=g["forecast"], name="Forecast",
                             line=dict(color=C["forecast"], width=2, shape="spline", smoothing=0.4),
                             hovertemplate="Forecast %{y:,.0f} Wh<extra></extra>"))
    fig.add_trace(go.Scatter(x=g["time"], y=g["actual"], name="Measured", line=dict(color=C["actual"], width=2.2),
                             hovertemplate="Measured %{y:,.0f} Wh<extra></extra>"))
    fig.update_yaxes(title_text="Wh per hour", rangemode="tozero")
    fig.update_xaxes(tickformat="%a %H:%M")
    hh = hrs[hrs["aid"] == aid]
    tariff_split = hh.groupby("tariff")["dev"].sum() / 1000
    same = a[(a["circuit"] == e.circuit) & (a["kind"] == e.kind)]
    reason = ("Critical: at least 1 kWh away from the forecast or 6 hours or longer." if e.level == "Critical" else
              "Moderate: at least 0.25 kWh or 3 hours, but below the critical thresholds." if e.level == "Moderate"
              else "Minor: short and small; worth a look only if it repeats.")
    body = [
        html.Div(f"Anomaly {aid}", className="mini-label"),
        html.H4(f"{e.load_type} · zone {e.zone}", className="mb-2"),
        html.Div([level_chip(e.level, e.kind), html.Span(when_label(e), className="tag ms-2")], className="mb-3"),
        html.Div([html.P(e.story, className="mb-1"), html.Div(reason, className="hint")], className="panel-box mb-3"),
        html.Div([
            html.Div([html.B(f"{e.dev_kwh:+,.2f} kWh"), html.Span(f"{e.measured_kwh:,.2f} measured · "
                                                                f"{e.forecast_kwh:,.2f} forecast")], className="fact"),
            html.Div([html.B(f"{e.n} h"), html.Span(f"largest hourly gap {e.peak_dev_wh:,.0f} Wh")], className="fact"),
            html.Div([html.B(f"{e.cost_eur:,.2f} €" if e.kind == "Spike" else "—"),
                      html.Span("extra cost · " + ", ".join(f"{AN.TARIFF[k].lower()} {v:,.2f} kWh"
                                                           for k, v in tariff_split.items()) if e.kind == "Spike"
                                else "no extra cost (less energy than forecast)")], className="fact"),
            html.Div([html.B(f"{len(same)}×"), html.Span(f"{e.kind.lower()}s on this circuit in the period")],
                     className="fact"),
        ], className="facts"),
        html.Div([html.Div("Measured vs forecast, one day either side", className="mini-label mb-1"),
                  dcc.Graph(figure=fig, config={"displayModeBar": False})], className="panel-box mb-3"),
        html.Div([html.Div("Where to start", className="mini-label"),
                  html.Ul([html.Li(t) for t in (AN.GUIDE.get(e.load_type, []) if e.kind == "Spike" else AN.DROP_GUIDE)],
                          className="small mb-0")], className="panel-box"),
    ]
    return True, body, ("Acknowledged ✓" if done else "Acknowledge")


@app.callback(Output("reviewed", "data"), Input("al-review", "n_clicks"), State("al-open", "data"),
              State("reviewed", "data"), State("cfg", "data"), prevent_initial_call=True)
def _ack(_, sel, acked, cfg):
    aid = (sel or {}).get("id")
    if not aid:
        return no_update
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    period, *_ = anom(cfg)
    s = set(acked or [])
    s.symmetric_difference_update({f"{period}:{cfg['level']}:{cfg['min_dev']}:{aid}"})
    return sorted(s)


@app.callback(Output("a-dl", "data"), Input("a-dl-btn", "n_clicks"), State("a-table", "data"),
              prevent_initial_call=True)
def _anom_csv(_, rows):
    if not rows:
        return no_update
    return dict(content=pd.DataFrame(rows).drop(columns=["id"]).to_csv(index=False), filename="cedint_anomalies.csv")


# ==========================================================================================================
# Page — Energy & costs
# ==========================================================================================================
def page_costs():
    return [
        html.Div([html.H2("Energy & costs", className="mb-1"),
                  html.P("Where the energy goes, what it costs by tariff period, the weekly rhythm of each zone and "
                         "the base load that never switches off — with a what-if calculator.", className="lead-text")],
                 className="page-head"),
        dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([html.Label(["Zone ", html.Span("(none = all)", className="text-secondary")], className="ctl-label"),
                     zone_picker("w-zone", [])], lg=4, md=6),
            dbc.Col([html.Label("Consumption type", className="ctl-label"),
                     dcc.Dropdown(id="w-load", options=LOAD_OPTS, value=[], multi=True, placeholder="All types")],
                    lg=4, md=6),
            dbc.Col([html.Label("Prices used", className="ctl-label"),
                     html.Div([html.Span(id="w-assump", className="me-2"),
                               dbc.Button([html.I(className="bi bi-sliders me-1"), "Edit"],
                                          id={"type": "opset", "n": "cost"}, size="sm", color="primary", outline=True)],
                              className="d-flex align-items-center flex-wrap gap-1")], lg=4),
        ], className="g-3")), className="controls-card mb-3"),
        html.Div(id="w-focus", className="mb-3"),
        dbc.Row(id="w-kpis", className="g-3 mb-3"),
        dbc.Row([
            dbc.Col(section("Where the energy goes", "Click a zone or a circuit: the whole page and the filters focus "
                            "on it. Click “Storey 1” at the top to see everything again",
                            dcc.Graph(id="w-tree", config={"displayModeBar": False})), lg=5),
            dbc.Col(section("Cost per day by tariff period", "Estimated € per day; peak hours cost the most",
                            dcc.Graph(id="w-days", config={"displayModeBar": False})), lg=7),
        ]),
        section("Weekly rhythm", "Average energy per hour for each weekday (Madrid time). Switch to see where the "
                "spikes above the forecast concentrate.",
                dbc.RadioItems(id="w-rhythm", value="use", options=[{"label": "Average use", "value": "use"},
                                                                    {"label": "Extra in spikes", "value": "extra"}],
                               className="seg mb-2", inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                               labelCheckedClassName="active"),
                dcc.Graph(id="w-heat", config={"displayModeBar": False})),
        dbc.Row([
            dbc.Col(section("Base load vs average use", "Base load = the 10th percentile of hourly use: the floor the "
                            "circuit never goes below (19 Aug – 13 Oct 2025)",
                            dcc.Graph(id="w-base", config={"displayModeBar": False})), lg=7),
            dbc.Col(section("What if the base load were lower?", "Move the slider: estimated yearly savings if the base "
                            "load of this selection were cut, priced at the off-peak/standard average",
                            dcc.Slider(id="w-cut", min=0, max=50, step=5, value=20,
                                       marks={i: f"{i}%" for i in range(0, 51, 10)}),
                            html.Div(id="w-whatif", className="mt-3"),
                            dcc.Graph(id="w-whatif-chart", config={"displayModeBar": False})), lg=5),
        ]),
    ]


@app.callback(Output("w-assump", "children"), Output("w-kpis", "children"), Output("w-tree", "figure"),
              Output("w-days", "figure"), Output("w-heat", "figure"), Output("w-base", "figure"),
              Output("w-whatif", "children"), Output("w-focus", "children"), Output("w-whatif-chart", "figure"),
              Input("cfg", "data"), Input("w-zone", "value"), Input("w-load", "value"), Input("w-rhythm", "value"),
              Input("w-cut", "value"))
def _costs(cfg, zones, loads, rhythm, cut):
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    period, f, hrs, a = anom(cfg)
    f = in_scope(f, zones, loads)
    hrs, a = in_scope(hrs, zones, loads), in_scope(a, zones, loads)
    v = f.dropna(subset=["actual"]).copy()
    v["eur"] = v["actual"] / 1000 * AN.price_of(v["tariff"], cfg)
    days = max(f["time"].dt.normalize().nunique(), 1)
    used, cost = v["actual"].sum() / 1000, v["eur"].sum()
    sp = a[a["kind"] == "Spike"]
    peak_share = v.loc[v["tariff"] == "P1", "eur"].sum() / max(cost, 1e-9)
    assump = [html.Span(f"peak {cfg['p1']:.2f}", className="tag"), html.Span(f"standard {cfg['p2']:.2f}", className="tag ms-1"),
              html.Span(f"off-peak {cfg['p3']:.2f} €/kWh", className="tag ms-1"),
              html.Span(f"{cfg['co2']:.2f} kg CO₂/kWh", className="tag ms-1")]
    kp = [dbc.Col(kpi("Energy", f"{used:,.0f} kWh", f"{days} days · {used / days:,.0f} kWh a day", "bi-lightning-charge",
                      id_="wk-1", tone="slate"), md=6, lg=3),
          dbc.Col(kpi("Estimated cost", f"{cost:,.0f} €", f"{peak_share * 100:.0f}% of it in peak hours", "bi-receipt",
                      id_="wk-2", tone="indigo"), md=6, lg=3),
          dbc.Col(kpi("Extra cost of spikes", f"{sp['cost_eur'].sum():,.2f} €",
                      f"{sp['cost_eur'].sum() / max(cost, 1e-9) * 100:.1f}% of the cost · {sp['dev_kwh'].sum():,.1f} kWh",
                      "bi-arrow-up-right", id_="wk-3", tone="amber"), md=6, lg=3),
          dbc.Col(kpi("Monthly bill, projected", f"{cost / days * 30:,.0f} €",
                      f"{used / days * 30 * cfg['co2']:,.0f} kg CO₂ a month (est.)", "bi-calendar3", id_="wk-4",
                      tone="green"), md=6, lg=3)]
    # treemap zone -> circuit
    e = v.groupby(["zone", "circuit", "load_type"])["actual"].sum().reset_index()
    ids = ["Storey 1"] + [f"Zone {z}" for z in e["zone"].unique()] + list(e["circuit"])
    parents = [""] + ["Storey 1"] * e["zone"].nunique() + [f"Zone {z}" for z in e["zone"]]
    vals = [e["actual"].sum() / 1000] + [e.loc[e["zone"] == z, "actual"].sum() / 1000 for z in e["zone"].unique()] + \
           list(e["actual"] / 1000)
    labels = ["Storey 1"] + [f"Zone {z}" for z in e["zone"].unique()] + list(e["load_type"])
    colors = ["#e2e8f0"] + [S.ZONE_COLORS[z] for z in e["zone"].unique()] + [S.ZONE_COLORS[z] for z in e["zone"]]
    tr = go.Figure(go.Treemap(ids=ids, parents=parents, values=vals, labels=labels, branchvalues="total",
                              marker=dict(colors=colors, line=dict(color="white", width=2)),
                              texttemplate="<b>%{label}</b><br>%{value:,.0f} kWh<br>%{percentRoot:.0%}",
                              hovertemplate="<b>%{label}</b><br>%{value:,.1f} kWh · %{percentRoot:.1%} of the floor"
                                            "<extra></extra>", maxdepth=2, pathbar=dict(visible=True)))
    tr.update_layout(height=380, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor="rgba(0,0,0,0)",
                     font=dict(family=FONT, size=13))
    # cost per day by tariff
    full = f.assign(day=f["time"].dt.normalize()).groupby("day")["time"].nunique()
    vd = v.assign(day=v["time"].dt.normalize())
    vd = vd[vd["day"].isin(full[full >= 20].index)]
    pt = vd.pivot_table(index="day", columns="tariff", values="eur", aggfunc="sum").fillna(0)
    fd = fig_base(380, barmode="stack", bargap=0.3)
    for tp in ("P3", "P2", "P1"):
        if tp in pt:
            fd.add_trace(go.Bar(x=pt.index, y=pt[tp], name=AN.TARIFF[tp], marker=dict(color=TARIFF_COLOR[tp]),
                                hovertemplate="%{y:,.2f} €<extra>" + AN.TARIFF[tp] + "</extra>"))
    fd.update_xaxes(tickformat="%a<br>%d %b", dtick=86400000, tickangle=0, tickfont=dict(size=10))
    fd.update_yaxes(title_text="€ per day (est.)")
    # weekly rhythm heatmap
    wd = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if rhythm == "extra":
        src = hrs[hrs["kind"] == "Spike"].assign(val=lambda x: x["dev"])
        hm = src.assign(d=src["time"].dt.weekday, h=src["time"].dt.hour).pivot_table(
            index="d", columns="h", values="val", aggfunc="sum") / 1000
        scale, unit = [[0, "#fff7ed"], [0.5, "#fb923c"], [1, "#9a3412"]], "kWh extra (total)"
    else:
        tot = v.groupby("time")["actual"].sum().reset_index()
        hm = tot.assign(d=tot["time"].dt.weekday, h=tot["time"].dt.hour).pivot_table(
            index="d", columns="h", values="actual", aggfunc="mean") / 1000
        scale, unit = [[i / 6, c] for i, c in enumerate(C["seq"])], "kWh per hour (average)"
    hm = hm.reindex(index=range(7), columns=range(24))
    fh = fig_base(300, hovermode="closest")
    fh.add_trace(go.Heatmap(z=hm.values, x=list(range(24)), y=wd, colorscale=scale, xgap=2, ygap=2, zmin=0,
                            colorbar=dict(title="kWh", thickness=10), hoverongaps=False,
                            hovertemplate="%{y} %{x}:00<br>%{z:.2f} " + unit + "<extra></extra>"))
    fh.update_yaxes(autorange="reversed", showgrid=False)
    fh.update_xaxes(dtick=1, title_text="Hour of day", showgrid=False)
    fh.update_layout(margin=dict(l=50, r=16, t=8, b=40))
    # base load dumbbell
    b = in_scope(AN.base_load(), zones, loads).sort_values("mean_wh")
    fb = fig_base(max(280, 26 * len(b) + 60), hovermode="closest")
    for _, r in b.iterrows():
        fb.add_shape(type="line", x0=r["base_wh"], x1=r["mean_wh"], y0=r["circuit"], y1=r["circuit"],
                     line=dict(color="#cbd5e1", width=3), layer="below")
    fb.add_trace(go.Scatter(x=b["mean_wh"], y=b["circuit"], mode="markers", name="Average use",
                            marker=dict(size=11, color=C["forecast"]),
                            hovertemplate="%{y}<br>average %{x:,.0f} Wh/h<extra></extra>"))
    fb.add_trace(go.Scatter(x=b["base_wh"], y=b["circuit"], mode="markers", name="Base load",
                            marker=dict(size=11, color="#0f172a", symbol="diamond"),
                            customdata=np.c_[b["base_share"] * 100, b["night_weekend_share"] * 100],
                            hovertemplate="%{y}<br>base %{x:,.0f} Wh/h = %{customdata[0]:.0f}% of the average<br>"
                                          "%{customdata[1]:.0f}% of its energy at night/weekends<extra></extra>"))
    fb.update_xaxes(type="log", title_text="Wh per hour (log scale)", showgrid=True, gridcolor="#eef1f5")
    fb.update_layout(margin=dict(l=150, r=16, t=30, b=40))
    # what-if
    base_total = b["base_wh"].sum()
    avg_off = (cfg["p2"] + cfg["p3"]) / 2
    kwh_y = base_total * (cut or 0) / 100 * 8760 / 1000
    whatif = html.Div([
        html.Div([html.Div("Base load of this selection", className="mini-label"),
                  html.Div(f"{base_total:,.0f} Wh every hour", className="kpi-value")], className="mb-3"),
        html.Div([html.Div(f"Cutting it by {cut or 0}% saves about", className="mini-label"),
                  html.Div(f"{kwh_y:,.0f} kWh a year", className="kpi-value"),
                  html.Div(f"≈ {kwh_y * avg_off:,.0f} € and {kwh_y * cfg['co2']:,.0f} kg CO₂ a year (estimates)",
                           className="kpi-sub")]),
        html.Div("Racks, emergency lighting and refrigeration cannot be switched off: start with plugs & sockets.",
                 className="hint mt-3")])
    if zones or loads:
        what = " · ".join(filter(None, [("Zone " + ", ".join(zones)) if zones else "All zones",
                                        ", ".join(loads) if loads else None]))
        focus = html.Div([html.I(className="bi bi-bullseye me-2"), html.Span("Focused on: ", className="me-1"),
                          html.B(what),
                          dbc.Button([html.I(className="bi bi-x-lg me-1"), "Show the whole floor"], id="w-clear",
                                     size="sm", color="secondary", outline=True, className="ms-auto")],
                         className="focus-bar")
    else:
        focus = html.Div([html.I(className="bi bi-grid-3x3-gap me-2"), "Showing the whole floor · click a zone or a "
                          "circuit in “Where the energy goes” to focus on it",
                          dbc.Button(id="w-clear", style={"display": "none"})], className="focus-bar muted")
    # savings by circuit for the chosen cut, as tall as the base-load chart minus the text above it
    sv = b.assign(eur=b["base_wh"] * (cut or 0) / 100 * 8760 / 1000 * avg_off).sort_values("eur").tail(8)
    fs = fig_base(max(200, 26 * len(b) + 60 - 230), hovermode="closest")
    fs.add_trace(go.Bar(y=sv["circuit"], x=sv["eur"], orientation="h", width=0.6,
                        marker=dict(color=[S.ZONE_COLORS[z] for z in sv["zone"]], cornerradius=4),
                        text=[f"{v:,.0f} €" for v in sv["eur"]], textposition="outside", cliponaxis=False,
                        hovertemplate="%{y}<br>%{x:,.0f} € a year<extra></extra>"))
    fs.update_layout(margin=dict(l=150, r=50, t=26, b=30),
                     title=dict(text="Yearly savings by circuit (est.)", font=dict(size=12, color="#64748b"), x=0))
    fs.update_xaxes(title_text="€ per year", showgrid=True, gridcolor="#eef1f5")
    return assump, kp, tr, fd, fh, fb, whatif, focus, fs


@app.callback(Output("w-zone", "value"), Output("w-load", "value"),
              Input("w-tree", "clickData"), Input("w-clear", "n_clicks"),
              State("w-zone", "value"), State("w-load", "value"), prevent_initial_call=True)
def _tree_focus(click, clear, zones, loads):
    """Click on the treemap = focus the whole page (and its filters) on that zone or circuit."""
    if ctx.triggered_id == "w-clear":
        return ([], []) if clear else (no_update, no_update)
    if not click or not click.get("points"):
        return no_update, no_update
    pid = str(click["points"][0].get("id") or "")
    if pid == "Storey 1":
        return [], []
    if pid.startswith("Zone "):
        return [pid.replace("Zone ", "")], []
    if "|" in pid:
        z, raw = pid.split("|", 1)
        return [z], [S.LOAD_TYPES.get(raw, raw)]
    return no_update, no_update


# ==========================================================================================================
# Forecast replay — hour-by-hour playback
# ==========================================================================================================
def replay_player():
    return section("Hour-by-hour playback", "Watch the week unfold: measured energy appears hour by hour against the "
                   "day-ahead forecast and its interval; ▲ spikes and ▼ drops are flagged as they happen.",
                   html.Div([
                       dbc.Button([html.I(className="bi bi-play-fill me-1"), "Play"], id="rp-play", color="primary",
                                  size="sm"),
                       dbc.Button([html.I(className="bi bi-skip-backward-fill me-1"), "Start"], id="rp-restart",
                                  outline=True, color="secondary", size="sm"),
                       dbc.RadioItems(id="rp-speed", value=3, options=[{"label": "1×", "value": 1},
                                                                      {"label": "3×", "value": 3},
                                                                      {"label": "8×", "value": 8}],
                                      className="seg", inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                                      labelCheckedClassName="active"),
                       html.Span(id="rp-clock", className="rp-clock ms-auto"),
                   ], className="d-flex gap-2 align-items-center flex-wrap mb-2"),
                   dcc.Slider(id="rp-slider", min=0, max=167, step=1, value=0, marks=None),
                   dcc.Interval(id="rp-int", interval=450, disabled=True),
                   dcc.Graph(id="rp-chart", config={"displayModeBar": False}),
                   dbc.Row([dbc.Col(html.Div(id="rp-facts", className="facts"), lg=6),
                            dbc.Col([html.Div("Flagged so far", className="mini-label mb-1"),
                                     html.Div(id="rp-feed", className="feed")], lg=6)], className="g-3 mt-1"))


@app.callback(Output("rp-int", "disabled"), Output("rp-play", "children"), Input("rp-play", "n_clicks"),
              State("rp-int", "disabled"), prevent_initial_call=True)
def _rp_play(_, disabled):
    playing = disabled
    return (not playing, [html.I(className=f"bi {'bi-pause-fill' if playing else 'bi-play-fill'} me-1"),
                          "Pause" if playing else "Play"])


@app.callback(Output("rp-slider", "value"), Input("rp-int", "n_intervals"), Input("rp-restart", "n_clicks"),
              Input("f-split", "value"), State("rp-slider", "value"), State("rp-speed", "value"),
              prevent_initial_call=True)
def _rp_tick(_, __, ___, i, speed):
    if ctx.triggered_id in ("rp-restart", "f-split"):
        return 0
    return min(167, (i or 0) + int(speed or 3))


@app.callback(Output("rp-chart", "figure"), Output("rp-clock", "children"), Output("rp-facts", "children"),
              Output("rp-feed", "children"),
              Input("rp-slider", "value"), Input("f-zone", "value"), Input("f-load", "value"), Input("f-split", "value"),
              Input("cfg", "data"))
def _rp_draw(i, zones, loads, split, cfg):
    cfg = {**AN.DEFAULTS, **(cfg or {})}
    f, hrs, a = _anom_cached("eval", round(cfg["level"], 2), float(cfg["min_dev"]), cfg["p1"], cfg["p2"], cfg["p3"], 0.0)
    wk0 = pd.Timestamp("2025-09-22 02:00") if split == "validation" else pd.Timestamp("2025-09-29 02:00")
    ff = in_scope(f, zones, loads)
    ff = ff[(ff["time"] >= wk0) & (ff["time"] < wk0 + pd.Timedelta(hours=168))].dropna(subset=["actual"])
    i = int(i or 0)
    now = wk0 + pd.Timedelta(hours=i)
    t = ff.groupby("time").agg(a=("actual", "sum"), e=("forecast", "sum"), lo=("lo", "sum"), hi=("hi", "sum"))
    t = t.reindex(pd.date_range(wk0, periods=168, freq="h"))
    so = t[t.index <= now]
    fig = fig_base(340)
    fig.add_vrect(x0=now, x1=t.index.max(), fillcolor=C["future"], line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=t.index, y=t["hi"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=t.index, y=t["lo"], fill="tonexty", fillcolor=C["band"], line=dict(width=0),
                             name=f"{cfg['level'] * 100:.0f}% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=t.index, y=t["e"], name="Day-ahead forecast",
                             line=dict(color=C["forecast"], width=2, shape="spline", smoothing=0.4),
                             hovertemplate="Forecast %{y:,.0f} Wh<extra></extra>"))
    fig.add_trace(go.Scatter(x=so.index, y=so["a"], name="Measured so far", line=dict(color=C["actual"], width=2.4),
                             hovertemplate="Measured %{y:,.0f} Wh<extra></extra>"))
    aa = in_scope(a, zones, loads)
    seen = aa[(aa["start"] >= wk0) & (aa["start"] <= now)]
    for k in ("Spike", "Drop"):
        r = seen[seen["kind"] == k]
        if len(r):
            fig.add_trace(go.Scatter(x=r["start"], y=t["a"].reindex(r["start"]).to_numpy(), mode="markers", name=k + "s",
                                     marker=dict(symbol=KIND_SYMBOL[k], size=13,
                                                 color=[LEVEL_COLOR[l] for l in r["level"]],
                                                 line=dict(color="white", width=1.5)),
                                     customdata=np.c_[r["id"], r["load_type"], r["zone"], r["level"]],
                                     hovertemplate="%{customdata[0]} · %{customdata[1]} %{customdata[2]} · "
                                                   "%{customdata[3]}<extra></extra>"))
    fig.add_vline(x=now, line=dict(color="#334155", width=1.5))
    fig.update_xaxes(range=[wk0, wk0 + pd.Timedelta(hours=167)], tickformat="%a %d", dtick=86400000)
    fig.update_yaxes(title_text="Wh per hour", rangemode="tozero")
    inside = ((so["a"] >= so["lo"]) & (so["a"] <= so["hi"])).mean() if so["a"].notna().any() else float("nan")
    sp = seen[seen["kind"] == "Spike"]
    facts = [html.Div([html.B(f"{so['a'].sum() / 1000:,.0f} kWh"), html.Span("measured so far")], className="fact"),
             html.Div([html.B(f"{inside * 100:.0f}%" if inside == inside else "–"),
                       html.Span("hours inside the interval")], className="fact"),
             html.Div([html.B(f"{len(sp)} ▲ · {len(seen) - len(sp)} ▼"), html.Span("spikes · drops")],
                      className="fact"),
             html.Div([html.B(f"{sp['cost_eur'].sum():,.2f} €"), html.Span("extra cost so far")], className="fact")]
    feed = [dcc.Link([level_chip(r.level, r.kind), html.B(f" {r.load_type}", className="ms-1"),
                      html.Span(r.zone, className="tag ms-2"),
                      html.Div(f"{r.start:%a %d %b %H:%M} · {r.dev_kwh:+,.2f} kWh · {r.n} h", className="hint")],
                     href=f"/anomalies#{r.id}", className=f"feed-item lvl-{r.level}")
            for r in seen.sort_values("start", ascending=False).itertuples()] or \
           [html.Div("Nothing flagged yet.", className="section-sub")]
    return fig, f"{now:%a %d %b %Y · %H:%M}", facts, feed


@app.callback(Output("p-band", "children"), Input("p-split", "value"))
def _p_band(split):
    rows = []
    for lvl in (0.80, 0.90, 0.95):
        f = AN.frame("eval", lvl)
        t = f[f["time"] >= pd.Timestamp("2025-09-29 02:00")] if split == "test" else \
            f[f["time"] < pd.Timestamp("2025-09-29 02:00")]
        c = AN.coverage(t)
        ok = abs(c - lvl) <= 0.03
        rows.append(html.Tr([html.Td(f"{lvl * 100:.0f}%"), html.Td(f"{c * 100:.1f}%"),
                             html.Td(html.Span("✓ close to nominal" if ok else "✗ off nominal",
                                               className="status-badge " + ("badge-good" if ok else "badge-warning"))),
                             html.Td(f"{(t['hi'] - t['lo']).mean():,.0f} Wh")]))
    note = ("Validation week: in-sample (the interval was calibrated on these hours)." if split == "validation" else
            "Test week: never used to calibrate, so this is the honest check.")
    return [dbc.Table([html.Thead(html.Tr([html.Th(c) for c in ("Nominal level", "Measured hours inside",
                                                               "Verdict", "Mean width")])), html.Tbody(rows)],
                      hover=True, size="sm", className="mb-1"), html.Div(note, className="hint")]


@app.callback(Output("u-out", "children"), Input("u-run", "n_clicks"), State("u-path", "value"),
              prevent_initial_call=True)
def _update_data(_, path):
    if not path:
        return dbc.Alert("Write the path of the new export first.", color="warning", className="small")
    try:
        r = D.update_data(path.strip().strip('"'))
    except Exception as e:  # noqa: BLE001
        r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if not r["ok"]:
        return dbc.Alert([html.B("The update did not finish. "), html.Pre(r.get("error") or "", className="small mb-0")],
                         color="danger")
    last = pd.Timestamp(r["data"]["last_measured_hour_utc"]).tz_convert(S.TZ_LOCAL)
    return dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"),
                      f"Dataset rebuilt ({r['data']['rows']:,} hourly rows, last measurement {last:%a %d %b %Y %H:%M}) "
                      f"and live forecast refreshed. ", html.A("Reload the app", href="/live"), " to see it."],
                     color="success")


# ==========================================================================================================
# Performance — detection test (injected anomalies, analysis/ folder made by engines/injection_test.py)
# ==========================================================================================================
VAL_DIR = S.VAL_DIR
DT_SETTINGS = [("0.9|25.0", "90% interval · 25 Wh (default)"), ("0.8|25.0", "80% interval · 25 Wh"),
               ("0.95|25.0", "95% interval · 25 Wh"), ("0.9|10.0", "90% interval · 10 Wh"),
               ("0.9|50.0", "90% interval · 50 Wh")]


def _dt(name):
    p = VAL_DIR / name
    return pd.read_csv(p) if p.exists() else None


def detection_test_block():
    if _dt("injection_detection_by_magnitude_duration_dash.csv") is None:
        return section("Detection test (injected anomalies)", "Not run yet",
                       html.P(["Run ", html.Code("python engines/injection_test.py"),
                               " to create it (about 10 seconds)."], className="small"))
    return html.Div([
        html.Div([html.H4("Detection test (injected anomalies)", className="mb-1"),
                  html.P("Only one real event is confirmed in the data, so the detector is tested by adding artificial "
                         "spikes and drops to the real measurements and checking whether the dashboard finds them: "
                         "every circuit, every possible start hour, +25% to +200% extra use or −50% / −100% (switched "
                         "off), for 1, 3 or 6 hours.", className="lead-text mb-3")], className="mt-4"),
        dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([html.Label("Detector setting", className="ctl-label"),
                     dcc.Dropdown(id="dt-set", options=[{"label": l, "value": v} for v, l in DT_SETTINGS],
                                  value="0.9|25.0", clearable=False)], md=5),
            dbc.Col([html.Label("Injected anomaly", className="ctl-label"),
                     dbc.RadioItems(id="dt-kind", value="Spike", options=[{"label": "▲ Spikes", "value": "Spike"},
                                                                         {"label": "▼ Drops", "value": "Drop"}],
                                    className="seg", inputClassName="btn-check", labelClassName="btn btn-sm seg-btn",
                                    labelCheckedClassName="active")], md=4),
            dbc.Col([html.Label("Re-run", className="ctl-label"),
                     dbc.Button([html.I(className="bi bi-arrow-repeat me-1"), "Run the test again"], id="dt-run",
                                size="sm", color="primary", outline=True)], md=3),
        ], className="g-3")), className="controls-card mb-3"),
        dcc.Loading(html.Div(id="dt-run-out"), type="dot"),
        dbc.Row(id="dt-kpis", className="g-3 mb-3"),
        dbc.Row([
            dbc.Col(section("Detection rate by size and duration", "Share of injected cases found, all circuits pooled",
                            dcc.Graph(id="dt-heat", config={"displayModeBar": False})), lg=6),
            dbc.Col(section("Alerts vs detection: the trade-off", "Each dot is a detector setting: anomalies per day on "
                            "the real data vs share of +100%, 6-hour spikes found. Click a dot to select it",
                            dcc.Graph(id="dt-trade", config={"displayModeBar": False})), lg=6),
        ]),
        dbc.Row([
            dbc.Col(section("Detection rate by circuit", "Injected cases found per circuit, at the chosen size",
                            dbc.RadioItems(id="dt-mag", value=1.0, className="seg mb-2", inputClassName="btn-check",
                                           labelClassName="btn btn-sm seg-btn", labelCheckedClassName="active",
                                           options=[{"label": "+25%", "value": 0.25}, {"label": "+50%", "value": 0.5},
                                                    {"label": "+100%", "value": 1.0},
                                                    {"label": "+200%", "value": 2.0}]),
                            dcc.Graph(id="dt-circ", config={"displayModeBar": False})), lg=6),
            dbc.Col(section("Smallest extra use the dashboard can see", "Median extra Wh in one hour needed to raise a "
                            "spike, per circuit; label = what limits it",
                            dcc.Graph(id="dt-min", config={"displayModeBar": False})), lg=6),
        ]),
    ])


@app.callback(Output("dt-mag", "options"), Output("dt-mag", "value"), Input("dt-kind", "value"),
              State("dt-mag", "value"))
def _dt_mags(kind, cur):
    if kind == "Drop":
        opts = [{"label": "−50%", "value": 0.5}, {"label": "−100% (off)", "value": 1.0}]
        return opts, cur if cur in (0.5, 1.0) else 1.0
    return ([{"label": f"+{int(m * 100)}%", "value": m} for m in (0.25, 0.5, 1.0, 2.0)], cur or 1.0)


@app.callback(Output("dt-set", "value"), Input("dt-trade", "clickData"), prevent_initial_call=True)
def _dt_pick(click):
    if not click:
        return no_update
    return click["points"][0]["customdata"][0]


@app.callback(Output("dt-run-out", "children"), Input("dt-run", "n_clicks"), prevent_initial_call=True)
def _dt_rerun(_):
    import subprocess
    proc = subprocess.run([sys.executable, str(S.ENGINES_DIR / "injection_test.py")], capture_output=True, text=True,
                          cwd=str(S.APP_DIR), timeout=600)
    if proc.returncode != 0:
        return dbc.Alert(html.Pre((proc.stderr or proc.stdout)[-1500:], className="small mb-0"), color="danger")
    return dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"), "Test re-run. ",
                      html.A("Reload the page", href="/performance"), " to see the new numbers."], color="success",
                     className="small")


@app.callback(Output("dt-kpis", "children"), Output("dt-heat", "figure"), Output("dt-trade", "figure"),
              Output("dt-circ", "figure"), Output("dt-min", "figure"),
              Input("dt-set", "value"), Input("dt-kind", "value"), Input("dt-mag", "value"))
def _dt_show(setting, kind, mag):
    lvl, md = (float(x) for x in setting.split("|"))
    mdur, circ, mins = (_dt(n) for n in ("injection_detection_by_magnitude_duration_dash.csv",
                                          "injection_detection_by_circuit_magnitude_dash.csv",
                                          "injection_minimum_detectable_surplus_dash.csv"))
    quiet, known = _dt("injection_quiet_data_alerts_dash.csv"), _dt("injection_known_event_check_dash.csv")
    sel = lambda d: d[np.isclose(d["level"], lvl) & np.isclose(d["min_dev_Wh"], md)]  # noqa: E731
    q = sel(quiet).iloc[0]
    ke = known[np.isclose(known["level"], lvl)] if np.isclose(md, 25.0) else known.iloc[0:0]
    m = sel(mdur)
    m = m[m["kind"] == kind]
    big = m[(m["magnitude"] == 1.0) & (m["hours"] == 6)]
    big_pct = float(big["detected_pct"].iloc[0]) if len(big) else float("nan")
    cases = int(sel(mdur)["cases"].sum())
    kp = [
        dbc.Col(kpi("Anomalies per day (real data)", f"{q['alerts_per_day']:.1f}",
                    f"{int(q['alerts_14_days'])} in {int(q['days'])} days · {int(q['spikes'])} spikes, {int(q['drops'])} drops",
                    "bi-bell", id_="dtk-1", tone="slate",
                    tip="The alert load a user would see on the unmodified data with this setting."), md=6, lg=3),
        dbc.Col(kpi("Found: " + ("+100% for 6 h" if kind == "Spike" else "switched off for 6 h"), f"{big_pct:.0f}%",
                    "share of injected cases detected, all circuits", "bi-bullseye", id_="dtk-2", tone="green",
                    tip="Pooled over all 16 circuits; the tiny circuits (hand dryers, emergency lights) pull it down "
                        "because their whole use is smaller than the minimum deviation."), md=6, lg=3),
        dbc.Col(kpi("Known real event", "Found ✓" if len(ke) and bool(ke["detected"].iloc[0]) else "—",
                    (ke["anomaly"].iloc[0] if len(ke) and bool(ke["detected"].iloc[0]) else "checked at 25 Wh only"),
                    "bi-patch-check", id_="dtk-3", tone="indigo",
                    tip="NE|HVAC left on, 3 Oct 2025 11:00–14:00 (Task 6 event list)."), md=6, lg=3),
        dbc.Col(kpi("Cases tested", f"{cases:,}", f"interval {lvl * 100:.0f}% · minimum deviation {md:.0f} Wh",
                    "bi-clipboard-data", id_="dtk-4", tone="amber",
                    tip="Every circuit × every start hour with valid data and no real anomaly × size × duration × "
                        "timing (spikes and drops)."), md=6, lg=3),
    ]
    piv = m.pivot_table(index="magnitude", columns="hours", values="detected_pct").sort_index(ascending=False)
    ylab = [("+" if kind == "Spike" else "−") + f"{int(v * 100)}%" for v in piv.index]
    fh = fig_base(320, hovermode="closest")
    fh.add_trace(go.Heatmap(z=piv.values, x=[f"{h} h" for h in piv.columns], y=ylab, zmin=0, zmax=100,
                            colorscale=[[i / 6, c] for i, c in enumerate(C["seq"])], xgap=3, ygap=3,
                            text=[[f"{v:.0f}%" for v in r] for r in piv.values], texttemplate="%{text}",
                            textfont=dict(size=14), colorbar=dict(title="% found", thickness=10),
                            hovertemplate="%{y} for %{x}: %{z:.1f}% found<extra></extra>"))
    fh.update_xaxes(title_text="Duration", showgrid=False)
    fh.update_yaxes(title_text="Size (% of the circuit's mean use)", showgrid=False)
    # trade-off scatter
    t = quiet.copy()
    t["key"] = t["level"].round(2).astype(str) + "|" + t["min_dev_Wh"].round(1).astype(str)
    det = mdur[(mdur["kind"] == kind) & (mdur["magnitude"] == 1.0) & (mdur["hours"] == 6)].copy()
    det["key"] = det["level"].round(2).astype(str) + "|" + det["min_dev_Wh"].round(1).astype(str)
    t = t.merge(det[["key", "detected_pct"]], on="key")
    lab = dict(DT_SETTINGS)
    t["label"] = t["key"].map(lambda k: lab.get(k, k).replace(" (default)", ""))
    cur = t["key"] == f"{lvl}|{md}"
    ft = fig_base(320, hovermode="closest")
    ft.add_trace(go.Scatter(x=t["alerts_per_day"], y=t["detected_pct"], mode="markers+text", text=t["label"],
                            textposition="top center", customdata=np.c_[t["key"]],
                            marker=dict(size=np.where(cur, 20, 13), color=np.where(cur, C["forecast"], "#94a3b8"),
                                        line=dict(color="white", width=2)),
                            hovertemplate="%{text}<br>%{x:.1f} anomalies/day · %{y:.0f}% found<extra></extra>"))
    ft.update_xaxes(title_text="Anomalies per day on the real data (fewer = quieter)", showgrid=True,
                    gridcolor="#eef1f5")
    ft.update_yaxes(title_text="% found (" + ("+100%" if kind == "Spike" else "off") + ", 6 h)")
    ft.update_layout(margin=dict(l=56, r=30, t=30, b=46))
    # by circuit
    cc = sel(circ)
    cc = cc[(cc["kind"] == kind) & (cc["magnitude"] == mag)].sort_values("detected_pct")
    fc = fig_base(max(320, 24 * len(cc) + 60), hovermode="closest")
    fc.add_trace(go.Bar(y=cc["circuit"], x=cc["detected_pct"], orientation="h", width=0.6,
                        marker=dict(color=[S.ZONE_COLORS[c.split("|")[0]] for c in cc["circuit"]], cornerradius=4),
                        text=[f"{v:.0f}%" for v in cc["detected_pct"]], textposition="outside", cliponaxis=False,
                        customdata=np.c_[cc["cases"], cc["critical_pct"]],
                        hovertemplate="%{y}<br>%{x:.1f}% found (%{customdata[1]:.0f}% as Critical)<br>"
                                      "%{customdata[0]} cases<extra></extra>"))
    fc.update_xaxes(range=[0, 112], title_text="% of injected cases found")
    fc.update_layout(margin=dict(l=150, r=30, t=8, b=40))
    # minimum detectable surplus
    mn = sel(mins).sort_values("median_min_surplus_Wh")
    fm = fig_base(max(320, 24 * len(mn) + 60), hovermode="closest")
    fm.add_trace(go.Bar(y=mn["circuit"], x=mn["median_min_surplus_Wh"], orientation="h", width=0.6,
                        marker=dict(color=[C["forecast"] if b == "forecast interval" else "#94a3b8"
                                           for b in mn["binding"]], cornerradius=4),
                        text=[f"{v:,.0f} Wh · {p:,.0f}% of mean" for v, p in
                              zip(mn["median_min_surplus_Wh"], mn["median_min_surplus_pct_of_mean"])],
                        textposition="outside", cliponaxis=False, customdata=np.c_[mn["binding"], mn["mean_load_Wh"]],
                        hovertemplate="%{y}<br>needs ≥ %{x:,.0f} Wh extra in one hour<br>mean use %{customdata[1]:,.0f}"
                                      " Wh/h · limited by the %{customdata[0]}<extra></extra>"))
    fm.update_xaxes(type="log", title_text="Extra Wh in one hour (log scale) · blue = limited by the forecast "
                                           "interval, grey = by the minimum deviation")
    fm.update_layout(margin=dict(l=150, r=150, t=8, b=46))
    return kp, fh, ft, fc, fm


# ==========================================================================================================
# Router
# ==========================================================================================================
PAGES = {"/": page_overview, "/live": page_live, "/anomalies": page_anomalies, "/costs": page_costs,
         "/forecast": page_forecast, "/performance": page_performance,
         "/limitations": page_limitations, "/model": page_model}


def setup_problem(missing):
    return [html.H2("The dashboard cannot find the project files", className="mb-3"),
            dbc.Alert([html.P(["The folder ", html.Code("Sprint4_Task3_UX_Dash"), " must be INSIDE the repository folder ",
                               html.Code("2026G2"), " (next to ", html.Code("Task6_rev0_03-11"), " and ",
                               html.Code("TBDA_v1.3_ChronosGBM_29-10"), ")."]),
                       html.P(["Repository folder used now: ", html.Code(str(S.REPO))]),
                       html.Div("Missing files:"), html.Ul([html.Li(html.Code(p)) for p in missing])],
                      color="danger")]


@app.callback(Output("crumb", "children"), Input("url", "pathname"))
def _crumb(path):
    return [html.Span("CeDInt Storey 1", className="crumb-root"), html.I(className="bi bi-chevron-right mx-2"),
            html.Span(PAGE_TITLES.get(path or "/", "Overview"), className="crumb-page")]


@app.callback(Output("page", "children"), Input("url", "pathname"))
def _route(path):
    missing = D.check_repository()
    if missing:
        return setup_problem(missing)
    page = PAGES.get(path or "/")
    if page is None:
        return [html.H3("Page not found"), dcc.Link("Back to overview", href="/")]
    try:
        return page()
    except Exception as e:  # noqa: BLE001  (show the problem instead of silently keeping the old page)
        import traceback
        return [html.H3("This page could not be built", className="mb-3"),
                dbc.Alert([html.P("Send this message to the developer:"),
                           html.Pre(traceback.format_exc()[-3000:], className="small mb-0")], color="danger")]


if __name__ == "__main__":
    import sys
    _missing = D.check_repository()
    print(f"Repository folder: {S.REPO}")
    if _missing:
        print("WARNING - files not found (put Sprint4_Task3_UX_Dash inside the 2026G2 folder):")
        for p in _missing:
            print("   ", p)
    print("Live forecast available:", D.has_live())
    app.run(debug="--debug" in sys.argv, host="127.0.0.1", port=8050)
