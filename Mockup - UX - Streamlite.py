import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------------------------------------------------------------
# CONFIGURATION DE LA PAGE
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Monitoring & Prédictions Énergétiques",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------------------
# 1. CHARGEMENT ET RAFRAÎCHISSEMENT DES DONNÉES
# ------------------------------------------------------------------------------
@st.cache_data(ttl=60) # Expire automatiquement toutes les 60 secondes
def load_realtime_data():
    """
    Remplacer ce bloc par la lecture de votre fichier réel :
    df = pd.read_csv("data/conso_batiment.csv", parse_dates=['timestamp'])
    """
    dates = pd.date_range(end=datetime.now(), periods=168, freq='h')
    np.random.seed(42)
    
    df = pd.DataFrame({'timestamp': dates})
    for zone in range(1, 5):
        base_load = 40 + zone * 25
        daily_pattern = 20 * np.sin(np.pi * dates.hour / 12)
        noise = np.random.normal(0, 4, len(dates))
        df[f'zone_{zone}_reel'] = np.maximum(0, base_load + daily_pattern + noise)
        
    return df

# ------------------------------------------------------------------------------
# 2. CHARGEMENT EN CACHE DES MODÈLES SPÉCIFIQUES
# ------------------------------------------------------------------------------
@st.cache_resource
def load_zone_model(zone_id):
    """
    Chargement du modèle pré-entraîné pour la zone demandée.
    Exemple en prod : return joblib.load(f"models/model_zone_{zone_id}.joblib")
    """
    models_metadata = {
        1: {"type": "XGBoost Regressor", "mae": "1.12 kWh", "rmse": "1.45 kWh", "r2": "0.94"},
        2: {"type": "Random Forest", "mae": "0.85 kWh", "rmse": "1.10 kWh", "r2": "0.96"},
        3: {"type": "LSTM (Deep Learning)", "mae": "1.45 kWh", "rmse": "1.80 kWh", "r2": "0.91"},
        4: {"type": "Prophet / SARIMAX", "mae": "0.98 kWh", "rmse": "1.25 kWh", "r2": "0.95"},
    }
    return models_metadata.get(zone_id, {"type": "Modèle Standard", "mae": "N/A", "r2": "N/A"})

def run_inference(df_history, zone_id, horizon_hours):
    """
    Génère les prédictions futures et calcule l'écart avec l'historique moyen.
    """
    last_timestamp = df_history['timestamp'].max()
    future_dates = pd.date_range(start=last_timestamp + timedelta(hours=1), periods=horizon_hours, freq='h')
    
    # Simulation de la prédiction du modèle
    base_load = 40 + zone_id * 25
    daily_pattern = 20 * np.sin(np.pi * future_dates.hour / 12)
    noise = np.random.normal(0, 3, len(future_dates))
    
    # Simulation d'une anomalie/pic ponctuel pour tester le système d'alerte
    anom = np.where((future_dates.hour >= 13) & (future_dates.hour <= 17), 35, 0)
    predictions = np.maximum(0, base_load + daily_pattern + noise + anom)
    
    # Calcul du profil historique moyen pour chaque heure de la journée
    hist_avg_by_hour = df_history.groupby(df_history['timestamp'].dt.hour)[f'zone_{zone_id}_reel'].mean()
    baseline = [hist_avg_by_hour[h] for h in future_dates.hour]
    
    res_df = pd.DataFrame({
        'Date & Heure': future_dates,
        'Prédiction (kWh)': np.round(predictions, 2),
        'Moyenne Historique (kWh)': np.round(baseline, 2)
    })
    
    res_df['Dépassement (%)'] = np.round(
        ((res_df['Prédiction (kWh)'] - res_df['Moyenne Historique (kWh)']) / res_df['Moyenne Historique (kWh)']) * 100, 1
    )
    return res_df

# ------------------------------------------------------------------------------
# 3. BARRE LATÉRALE (CONTRÔLES)
# ------------------------------------------------------------------------------
st.sidebar.title("⚙️ Paramètres")

# Bouton de rafraîchissement forcé
if st.sidebar.button("🔄 Actualiser les données en direct", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Données actualisées !")

st.sidebar.markdown("---")

selected_zone_str = st.sidebar.selectbox(
    "Sélectionner la Zone :",
    ["Zone 1", "Zone 2", "Zone 3", "Zone 4"]
)
zone_id = int(selected_zone_str.split(" ")[1])

horizon_option = st.sidebar.radio(
    "Horizon de prédiction :",
    ["Prochaine heure (+1h)", "Prochaines 24h (+24h)", "Prochains 7 jours (+168h)"]
)

horizon_map = {
    "Prochaine heure (+1h)": 1,
    "Prochaines 24h (+24h)": 24,
    "Prochains 7 jours (+168h)": 168
}
horizon_hours = horizon_map[horizon_option]

alert_threshold = st.sidebar.slider(
    "Seuil d'alerte de surconsommation (%) :",
    min_value=5, max_value=50, value=15, step=5,
    help="Surligne en rouge les prédictions dépassant x% la consommation historique observée."
)

# ------------------------------------------------------------------------------
# 4. EXÉCUTION & CHARGEMENT
# ------------------------------------------------------------------------------
df_real = load_realtime_data()
model_info = load_zone_model(zone_id)
df_preds = run_inference(df_real, zone_id, horizon_hours)

# ------------------------------------------------------------------------------
# 5. AFFICHAGE PRINCIPAL
# ------------------------------------------------------------------------------
st.title("⚡ Dashboard Consommation & Prédictions Bâtiment")

# Bannière d'information sur le modèle en cache
st.info(
    f"🤖 **Modèle en cache pour la {selected_zone_str} :** `{model_info['type']}` | "
    f"**MAE :** {model_info['mae']} | **RMSE :** {model_info['rmse']} | **R² Score :** {model_info['r2']}"
)

# KPIs rapides
col1, col2, col3, col4 = st.columns(4)
col1.metric("Dernière Conso Réelle", f"{df_real[f'zone_{zone_id}_reel'].iloc[-1]:.1f} kWh")
col2.metric("Prédiction Moyenne", f"{df_preds['Prédiction (kWh)'].mean():.1f} kWh")
col3.metric("Pic Prévu sur Période", f"{df_preds['Prédiction (kWh)'].max():.1f} kWh")
alerts_count = (df_preds['Dépassement (%)'] > alert_threshold).sum()
col4.metric("Alertes Dépassement", f"{alerts_count} heure(s)", delta_color="inverse")

# ------------------------------------------------------------------------------
# 6. GRAPHIQUE COMPARATIF (PLOTLY)
# ------------------------------------------------------------------------------
st.subheader("📈 Comparatif : Consommation Réelle Récente vs Prédictions")

# Affichage des 48 dernières heures de réel + les prédictions
recent_real = df_real.tail(48)

fig = go.Figure()

# Courbe Réel
fig.add_trace(go.Scatter(
    x=recent_real['timestamp'],
    y=recent_real[f'zone_{zone_id}_reel'],
    mode='lines+markers',
    name='Consommation Réelle',
    line=dict(color='#1f77b4', width=2)
))

# Courbe Prédictions
fig.add_trace(go.Scatter(
    x=df_preds['Date & Heure'],
    y=df_preds['Prédiction (kWh)'],
    mode='lines+markers',
    name='Prédictions du Modèle',
    line=dict(color='#ff7f0e', width=2, dash='dash')
))

# Ligne de référence historique
fig.add_trace(go.Scatter(
    x=df_preds['Date & Heure'],
    y=df_preds['Moyenne Historique (kWh)'],
    mode='lines',
    name='Moyenne Historique (Référence)',
    line=dict(color='#7f7f7f', width=1, dash='dot')
))

fig.update_layout(
    xaxis_title="Date et Heure",
    yaxis_title="Consommation (kWh)",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# 7. TABLEAUX DE PRÉDICTIONS AVEC MISE EN EVIDENCE DES ALERTES
# ------------------------------------------------------------------------------
st.subheader("📋 Détail des prédictions par horizon")

def highlight_surconso(val, threshold):
    """ Applique une couleur rouge si le dépassement passe le seuil défini. """
    if isinstance(val, (int, float)) and val > threshold:
        return 'background-color: #ff4b4b; color: white; font-weight: bold;'
    return ''

# Application du style au dataframe
styled_df = df_preds.style.applymap(
    lambda v: highlight_surconso(v, alert_threshold),
    subset=['Dépassement (%)']
).format({
    'Prédiction (kWh)': '{:.2f}',
    'Moyenne Historique (kWh)': '{:.2f}',
    'Dépassement (%)': '{:+.1f}%'
})

st.dataframe(styled_df, use_container_width=True, height=350)