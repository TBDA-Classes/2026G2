"""Tableau de bord UX — prévision de consommation électrique (Blend v1.3).

Mode « relecture » : l'app rejoue les prévisions gelées du modèle final (Blend v1.3)
sur la semaine de validation (22-28 sept. 2025) et les compare au réel et à la
référence « médiane par jour de semaine × heure » (Baseline B / B2).

Lancer :  streamlit run ux_app/app.py
Autre dossier de données :  TBDA_DATA_DIR=/chemin/vers/TBDA_v1.3_ChronosGBM_29-10
"""
from __future__ import annotations

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
DATA_DIR = Path(
    os.environ.get(
        "TBDA_DATA_DIR",
        Path(__file__).resolve().parents[1] / "TBDA_v1.3_ChronosGBM_29-10",
    )
)
RES = DATA_DIR / "results"
MODELS = DATA_DIR / "models"

HORIZONS = {  # libellé affiché -> clé dans les fichiers de prévision
    "+1 h": "+1h",
    "+6 h": "+6h",
    "Lendemain (J+1, 24 h)": "day-ahead",
}
HORIZON_HELP = {
    "+1h": "Prévision de l'heure suivante, émise chaque heure.",
    "+6h": "Prévision à 6 heures, émise chaque heure.",
    "day-ahead": "24 heures du lendemain, émises une fois par jour à 00:00 UTC.",
}
# Résultats officiels de la semaine de TEST (RESULTS.md, Task 6), 16 circuits, MAE en Wh.
TEST_MAE = {"+1h": 22.2, "+6h": 34.7, "day-ahead": 34.2}
TEST_MAE_B2 = {"+1h": 43.7, "+6h": 43.7, "day-ahead": 43.7}

C_REAL, C_PRED, C_REF, C_ALERT = "#1f77b4", "#ff7f0e", "#8c8c8c", "#d62728"

st.set_page_config(
    page_title="Prévision énergétique — Blend v1.3",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------------------------------------------------------------
# DONNÉES (chargées une seule fois, puis servies depuis le cache)
# ----------------------------------------------------------------------------
KEYS = ["series_id", "horizon", "issue_time", "target_time", "lead"]


@st.cache_data(show_spinner="Chargement des prévisions…")
def load_forecasts() -> pd.DataFrame:
    blend = pd.read_parquet(RES / "blend_validation_predictions_v1.3.parquet")
    base = pd.read_parquet(RES / "task8_validation_predictions_v1.3.parquet")
    ref = (
        base.loc[base["model"] == "B2_weekday_hour_median", KEYS + ["y_pred"]]
        .rename(columns={"y_pred": "ref"})
        .drop_duplicates(KEYS)
    )
    df = blend[KEYS + ["y_true", "y_pred"]].merge(ref, on=KEYS, how="left")
    df[["zone", "circuit"]] = df["series_id"].str.split("|", n=1, expand=True)
    df["day"] = df["target_time"].dt.strftime("%Y-%m-%d")
    for c in ("series_id", "horizon", "zone", "circuit"):
        df[c] = df[c].astype("category")
    return df.sort_values(["horizon", "target_time", "series_id"]).reset_index(drop=True)


@st.cache_data
def load_model_config() -> dict:
    return json.loads((MODELS / "blend_frozen_config_v1.3.json").read_text())


@st.cache_data
def aggregate(horizon: str, day: str, scope_kind: str, scope_value: str) -> pd.DataFrame:
    """Série horaire (somme des circuits du périmètre) pour le jour choisi + la veille (réel)."""
    df = load_forecasts()
    d = df[df["horizon"] == horizon]
    if scope_kind == "zone":
        d = d[d["zone"] == scope_value]
    elif scope_kind == "circuit":
        d = d[d["series_id"] == scope_value]
    n = d["series_id"].nunique()
    prev = (pd.Timestamp(day) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    d = d[d["day"].isin([prev, day])]
    # min_count=n : une heure où un circuit n'a pas de réel valide n'a pas de total réel
    g = d.groupby(["target_time", "day"], observed=True)[["y_true", "y_pred", "ref"]].sum(min_count=n)
    g = g.reset_index().sort_values("target_time")
    g["is_day"] = g["day"] == day
    return g


@st.cache_data
def accuracy_by_circuit(horizon: str) -> pd.DataFrame:
    df = load_forecasts()
    d = df[(df["horizon"] == horizon) & df["y_true"].notna()].copy()
    d["err_model"] = (d["y_pred"] - d["y_true"]).abs()
    d["err_ref"] = (d["ref"] - d["y_true"]).abs()
    t = (
        d.groupby("series_id", observed=True)
        .agg(MAE_modele=("err_model", "mean"), MAE_ref=("err_ref", "mean"), heures=("y_true", "size"),
             conso_moy=("y_true", "mean"))
        .reset_index()
    )
    t["gain_vs_ref_%"] = (1 - t["MAE_modele"] / t["MAE_ref"]) * 100
    return t.sort_values("MAE_modele", ascending=False).reset_index(drop=True)


def fmt_energy(wh: float | None) -> str:
    if wh is None or not np.isfinite(wh):
        return "—"
    return f"{wh / 1000:.2f} kWh" if abs(wh) >= 1000 else f"{wh:.0f} Wh"


# ----------------------------------------------------------------------------
# BARRE LATÉRALE
# ----------------------------------------------------------------------------
try:
    forecasts = load_forecasts()
    config = load_model_config()
except FileNotFoundError as exc:
    st.error(
        f"Fichiers du modèle introuvables : `{exc.filename}`.\n\n"
        f"Dossier cherché : `{DATA_DIR}`. Définir `TBDA_DATA_DIR` vers `TBDA_v1.3_ChronosGBM_29-10`."
    )
    st.stop()

st.sidebar.title("⚙️ Paramètres")

horizon_label = st.sidebar.radio("Horizon de prévision", list(HORIZONS), help="Les 3 horizons du modèle final.")
horizon = HORIZONS[horizon_label]
st.sidebar.caption(HORIZON_HELP[horizon])

zones = sorted(forecasts["zone"].unique())
scope = st.sidebar.selectbox("Périmètre", ["Bâtiment entier (16 circuits)"] + [f"Zone {z}" for z in zones]
                             + ["Un circuit…"])
if scope.startswith("Bâtiment"):
    scope_kind, scope_value, scope_name = "all", "", "Bâtiment entier"
elif scope.startswith("Zone"):
    scope_kind, scope_value = "zone", scope.split()[1]
    scope_name = scope
else:
    circuits = sorted(forecasts["series_id"].unique())
    scope_value = st.sidebar.selectbox("Circuit", circuits)
    scope_kind, scope_name = "circuit", scope_value.replace("|", " · ")

days = sorted(forecasts.loc[forecasts["horizon"] == horizon, "day"].unique())
day = st.sidebar.select_slider("Jour rejoué (UTC)", options=days, value=days[min(2, len(days) - 1)])

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Alerte de surconsommation")
thr_pct = st.sidebar.slider("Seuil (% au-dessus de la référence)", 5, 100, 25, 5,
                            help="Heure en alerte si la prévision dépasse la référence de plus de ce pourcentage…")
thr_abs = st.sidebar.number_input("…et d'au moins (Wh)", min_value=0, value=20, step=10,
                                  help="Évite les fausses alertes quand la référence est proche de 0.")
if st.sidebar.button("🔄 Recharger les données", width="stretch"):
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------------------------------
# EN-TÊTE
# ----------------------------------------------------------------------------
st.title("⚡ Prévision de consommation — Blend v1.3")
st.info(
    f"**Mode relecture** — prévisions gelées du modèle final rejouées sur la semaine de validation "
    f"({days[0]} → {days[-1]}). Pas de flux temps réel. Horaires en **UTC**, énergie en **Wh par heure**."
)

w = config["horizons"][{"+1h": "+1h", "+6h": "+6h", "day-ahead": "day-ahead"}[horizon]]
c1, c2 = st.columns([3, 2])
c1.markdown(
    f"**Modèle actif ({horizon_label}) :** Blend v1.3 = "
    f"{w['w_gbm']:.2f} × GBM + {w['w_hybrid']:.2f} × ChronosGBM + {w['w_chronos']:.2f} × Chronos-Bolt"
)
c2.markdown(
    f"**MAE test (16 circuits) :** {TEST_MAE[horizon]} Wh — référence {TEST_MAE_B2[horizon]} Wh "
    f"(**−{(1 - TEST_MAE[horizon] / TEST_MAE_B2[horizon]) * 100:.0f} %**)"
)

tab_fc, tab_acc, tab_model = st.tabs(["📈 Prévision", "🎯 Précision par circuit", "🤖 À propos du modèle"])

# ----------------------------------------------------------------------------
# ONGLET 1 — PRÉVISION
# ----------------------------------------------------------------------------
with tab_fc:
    g = aggregate(horizon, day, scope_kind, scope_value)
    cur = g[g["is_day"]].copy()
    if cur.empty:
        st.warning("Aucune donnée pour ce jour et ce périmètre.")
    else:
        cur["ecart_ref_pct"] = np.where(cur["ref"] > 0, (cur["y_pred"] - cur["ref"]) / cur["ref"] * 100, np.nan)
        cur["alerte"] = (cur["ecart_ref_pct"] > thr_pct) & ((cur["y_pred"] - cur["ref"]) >= thr_abs)
        valid = cur.dropna(subset=["y_true"])
        mae_m = (valid["y_pred"] - valid["y_true"]).abs().mean() if len(valid) else np.nan
        mae_r = (valid["ref"] - valid["y_true"]).abs().mean() if len(valid) else np.nan
        peak = cur.loc[cur["y_pred"].idxmax()]

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Conso réelle moyenne", fmt_energy(valid["y_true"].mean()) if len(valid) else "—")
        k2.metric("Prévision moyenne", fmt_energy(cur["y_pred"].mean()))
        k3.metric("Pic prévu", fmt_energy(peak["y_pred"]), f"à {peak['target_time']:%H:%M} UTC", delta_color="off")
        k4.metric("Erreur moyenne (MAE)", fmt_energy(mae_m),
                  (f"{(mae_m / mae_r - 1) * 100:+.0f} % vs référence" if np.isfinite(mae_r) and mae_r > 0 else None),
                  delta_color="inverse")
        k5.metric("Heures en alerte", f"{int(cur['alerte'].sum())} / {len(cur)}")

        st.subheader(f"{scope_name} — {day} — prévision {horizon_label}")
        fig = go.Figure()
        prev = g[~g["is_day"]]
        fig.add_trace(go.Scatter(x=prev["target_time"], y=prev["y_true"], name="Réel (veille)",
                                 mode="lines", line=dict(color=C_REAL, width=1.5), opacity=0.35))
        fig.add_trace(go.Scatter(x=cur["target_time"], y=cur["y_true"], name="Réel",
                                 mode="lines+markers", line=dict(color=C_REAL, width=2.5), marker=dict(size=5),
                                 connectgaps=False))
        fig.add_trace(go.Scatter(x=cur["target_time"], y=cur["ref"], name="Référence (jour × heure)",
                                 mode="lines", line=dict(color=C_REF, width=1.5, dash="dot")))
        fig.add_trace(go.Scatter(x=cur["target_time"], y=cur["y_pred"], name="Prévision Blend v1.3",
                                 mode="lines+markers", line=dict(color=C_PRED, width=2.5, dash="dash"),
                                 marker=dict(size=5)))
        al = cur[cur["alerte"]]
        if len(al):
            fig.add_trace(go.Scatter(x=al["target_time"], y=al["y_pred"], name="Alerte", mode="markers",
                                     marker=dict(color=C_ALERT, size=12, symbol="triangle-up",
                                                 line=dict(color="white", width=1))))
        fig.add_vrect(x0=cur["target_time"].min(), x1=cur["target_time"].max(), fillcolor="rgba(255,127,14,0.05)",
                      line_width=0, layer="below")
        fig.update_layout(hovermode="x unified", height=430, margin=dict(l=10, r=10, t=10, b=10),
                          yaxis_title="Énergie (Wh par heure)", xaxis_title="Heure (UTC)",
                          legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
        st.plotly_chart(fig, width="stretch")

        if np.isfinite(mae_m) and np.isfinite(mae_r):
            verdict = "meilleure" if mae_m < mae_r else "moins bonne"
            st.caption(f"Sur ce jour, la prévision est {verdict} que la référence "
                       f"(erreur moyenne {fmt_energy(mae_m)} contre {fmt_energy(mae_r)}).")

        with st.expander("📋 Détail heure par heure", expanded=False):
            tbl = pd.DataFrame({
                "Heure (UTC)": cur["target_time"].dt.strftime("%H:%M"),
                "Réel (Wh)": cur["y_true"],
                "Prévision (Wh)": cur["y_pred"],
                "Référence (Wh)": cur["ref"],
                "Écart vs réf. (%)": cur["ecart_ref_pct"],
                "Erreur prévision (Wh)": cur["y_pred"] - cur["y_true"],
                "Alerte": np.where(cur["alerte"], "🚨", ""),
            }).reset_index(drop=True)
            styled = tbl.style.format(
                {"Réel (Wh)": "{:.0f}", "Prévision (Wh)": "{:.0f}", "Référence (Wh)": "{:.0f}",
                 "Écart vs réf. (%)": "{:+.0f}%", "Erreur prévision (Wh)": "{:+.0f}"}, na_rep="—"
            ).apply(lambda r: ["background-color:#fde2e2" if r["Alerte"] else "" for _ in r], axis=1)
            st.dataframe(styled, width="stretch", height=380, hide_index=True)
            st.download_button("⬇️ Télécharger en CSV", tbl.to_csv(index=False).encode("utf-8"),
                               file_name=f"prevision_{scope_value or 'batiment'}_{horizon}_{day}.csv",
                               mime="text/csv")

# ----------------------------------------------------------------------------
# ONGLET 2 — PRÉCISION
# ----------------------------------------------------------------------------
with tab_acc:
    st.subheader(f"Erreur moyenne par circuit — {horizon_label} — semaine de validation")
    acc = accuracy_by_circuit(horizon)
    tot_m = np.average(acc["MAE_modele"], weights=acc["heures"])
    tot_r = np.average(acc["MAE_ref"], weights=acc["heures"])
    a1, a2, a3 = st.columns(3)
    a1.metric("MAE modèle (16 circuits)", f"{tot_m:.1f} Wh")
    a2.metric("MAE référence", f"{tot_r:.1f} Wh")
    a3.metric("Gain vs référence", f"{(1 - tot_m / tot_r) * 100:.0f} %")

    top = acc.sort_values("MAE_modele")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(y=top["series_id"].astype(str), x=top["MAE_ref"], name="Référence", orientation="h",
                          marker_color=C_REF))
    fig2.add_trace(go.Bar(y=top["series_id"].astype(str), x=top["MAE_modele"], name="Blend v1.3", orientation="h",
                          marker_color=C_PRED))
    fig2.update_layout(barmode="group", height=520, margin=dict(l=10, r=10, t=10, b=10),
                       xaxis_title="MAE (Wh par heure) — plus bas = mieux", legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig2, width="stretch")
    st.dataframe(
        acc.rename(columns={"series_id": "Circuit", "MAE_modele": "MAE modèle (Wh)", "MAE_ref": "MAE réf. (Wh)",
                            "heures": "Heures notées", "conso_moy": "Conso moy. (Wh)",
                            "gain_vs_ref_%": "Gain vs réf. (%)"}),
        width="stretch", hide_index=True,
        column_config={"MAE modèle (Wh)": st.column_config.NumberColumn(format="%.1f"),
                       "MAE réf. (Wh)": st.column_config.NumberColumn(format="%.1f"),
                       "Conso moy. (Wh)": st.column_config.NumberColumn(format="%.0f"),
                       "Gain vs réf. (%)": st.column_config.NumberColumn(format="%+.0f")},
    )
    st.caption("Les circuits NW · Plugs & Sockets, NW · Lighting et SE · Lighting concentrent l'essentiel de l'erreur "
               "(voir RESULTS.md, section 5).")
    st.caption("⚠️ Ces MAE couvrent toutes les heures valides du jeu v1.2 sur la semaine de validation. "
               "Elles peuvent différer des chiffres de RESULTS.md (Task 6), qui ne notent que les heures valides "
               "dans les deux versions du jeu de données.")

# ----------------------------------------------------------------------------
# ONGLET 3 — MODÈLE
# ----------------------------------------------------------------------------
with tab_model:
    st.subheader("Blend v1.3 — modèle final (règle D10, 29 oct. 2025)")
    st.markdown(
        "Moyenne pondérée de trois prévisions gelées : **GBM v1.3**, **ChronosGBM v1.3** (GBM alimenté par Chronos) "
        "et **Chronos-Bolt v1.3**. Un modèle groupé par horizon, 16 circuits, choisi sur la validation uniquement."
    )
    rows = []
    for label, key in HORIZONS.items():
        h = config["horizons"][key]
        rows.append({"Horizon": label, "GBM": h["w_gbm"], "ChronosGBM": h["w_hybrid"], "Chronos-Bolt": h["w_chronos"],
                     "MAE test (Wh)": TEST_MAE[key], "MAE réf. test (Wh)": TEST_MAE_B2[key]})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ("GBM", "ChronosGBM", "Chronos-Bolt")})
    st.markdown(
        "**À savoir**\n"
        "- Les chiffres de test viennent de `RESULTS.md` (semaine 29 sept. → 5 oct.). Les courbes de cette app "
        "rejouent la semaine de **validation**, où le modèle a été choisi : l'erreur y est un peu plus faible.\n"
        "- À +1 h, aucun modèle ne bat significativement la persistance ; l'intérêt est surtout à +6 h et J+1.\n"
        "- Les circuits SE/SW sont peu ou pas vus à l'entraînement : prudence sur leurs prévisions.\n"
        "- Puissance (W) et courant (I) ne sont pas modélisés."
    )
    st.caption(f"Sources : `{RES.name}/blend_validation_predictions_v1.3.parquet`, "
               f"`{MODELS.name}/blend_frozen_config_v1.3.json`.")
