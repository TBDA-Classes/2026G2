# Dossier de justification — Maquette UX « Energy Watch » (TBDA Groupe 2, CeDInt-SEF)

Responsable UX : Jules. Version du 12 nov. 2026. Présentation finale : 30 nov. Moodle : 14 déc.

## 1. Choix d'outils (pourquoi pas Streamlit ?)

| Besoin (backlog / consigne) | Streamlit | Page HTML + JS (retenu) |
|---|---|---|
| Fluidité (filtres instantanés, rejeu animé) | Chaque clic relance le script Python, latence visible | Tout tourne dans le navigateur, réaction immédiate |
| Intégrer du HTML, rendu soigné | Possible mais limité, CSS contourné | Contrôle total du design (thème clair/sombre, mobile) |
| Démo le 30 nov. | Besoin d'un serveur Python | Un seul fichier, ouvrable partout, pas de serveur |
| Reproductibilité | Bonne | Bonne : `build_data.py` (Python) calcule les données, `build_html.py` les injecte |
| Coût de maintenance | Faible | Plus élevé (JS à écrire) |

Choix : Python (pandas) pour tout le calcul (modèle, seuils, alertes), HTML/JS + Plotly.js pour l'affichage. Python reste la source de vérité, le HTML n'est qu'une vue. Streamlit a été gardé pour les versions v1–v4 (prototypage rapide, validation du backlog). Dash : même contrainte serveur que Streamlit. Power BI/Tableau : pas de logique d'alerte sur mesure, pas versionnable dans Git. Limite assumée : la maquette lit des données figées (pas de temps réel), conforme au cahier des charges (« pas de streaming »).

## 2. Registre des hypothèses et décisions

- **Valeur attendue** : Blend v1.3 (+1 h, +6 h, jour suivant), émis à 00:00 Madrid. Zone normale : bande 10–90 % de Chronos-Bolt v1.3 (couverture mesurée 82 % pour 80 % visés).
- **Heure en alerte** : consommation > borne haute et excès ≥ max(plancher Wh, part × consommation moyenne du circuit). Sensibilités : Strict (20 %, 40 Wh), Équilibré (10 %, 20 Wh), Sensible (5 %, 10 Wh). Heures consécutives = une alerte.
- **Gravité High** : excès ≥ 1 kWh, ou ≥ 6 h, ou (≥ 50 % hors heures d'occupation et ≥ 0,5 kWh). Sinon Warning. Seuils choisis pour obtenir une liste lisible (≈ 5 alertes/jour en Équilibré) ; ils sont réglables.
- **Heures d'occupation** : jours ouvrés non fériés, 07:00–20:00 Madrid. Dérivé du capteur de présence `Pres` des données gelées (nommé « Bsens » oralement) : NW et SE donnent une courbe exploitable, la règle couvre 85–91 % des heures avec présence ; NE n'a pas de capteur ; SW est bloqué à ≈ 1 (inutilisable).
- **CO₂** : 0,27 kg/kWh (réseau, valeur centrale ; MITECO, inventaire d'empreinte carbone 2024, 0,265–0,275 hors garantie d'origine ; 0 avec garantie d'origine renouvelable).
- **Prix** : 0,18 €/kWh hors TVA, **hypothèse non sourcée** (plage 0,12–0,25 ; 0,25 = prix résidentiel TTC ES, H1 2026). À remplacer par la facture UPM.
- **Impact** : toujours « estimé ». L'excès au-dessus de l'attendu seulement. Le mensuel/annuel est une extrapolation de 14 jours. Le cahier des charges interdit d'affirmer économies ou gaspillage confirmés sans tarif et validation.
- **Heures avec problème de mesure** : jamais en alerte, listées à part (ex. NW éclairage de secours 5–6 oct : énergie > 2 × puissance).
- **Fenêtre** : 22 sept – 5 oct 2025 (validation + test), car ce sont les seules prévisions disponibles pour Blend.

## 3. Pourquoi W et I ne sont pas modélisés

Le cahier de modélisation fait de `energy_Wh` la cible principale, de W une cible secondaire et de I une cible exploratoire « à abandonner si la valeur ajoutée est insuffisante ». Nos constats : W est fortement corrélé à l'énergie horaire (≈ 0,87), I l'est à W (≈ 0,92) : ils n'apportent presque pas d'information nouvelle ; les unités ne sont pas documentées ; la couverture est inégale. Décision : alertes fondées sur l'énergie seule ; W et I restent une piste (pics de puissance) pour une version ultérieure. Fichier : `analysis/W_I_vs_energy.csv`.

## 4. Fiabilité du modèle (test 29 sept – 5 oct)

MAE Blend : 20,1 / 31,1 / 30,7 Wh (+1 h / +6 h / J+1) par circuit-heure. WAPE 16 / 25 / 25 %. CV(RMSE) 71 / 103 / 105 %. MAPE 12 / 17 / 17 % (heures ≥ 10 Wh seulement). Détail par circuit et bâtiment : `analysis/accuracy_metrics_MAPE_CVRMSE.csv`. Biais négatif du Blend (NMBE −2 à −12 %). Mes recalculs peuvent différer légèrement des chiffres officiels de RESULTS.md (masques de données). Le Blend surpasse B1 et B2 partout et B3 (persistance) nettement à +6 h ; à +1 h l'écart est faible.

## 5. Limites connues

- Extension du modèle impossible ici (poids Hugging Face inaccessibles, pas de torch). Les données horaires vont jusqu'au 13 oct : l'équipe modélisation peut relancer les prévisions pour allonger la fenêtre.
- Entraînement sur ~5 semaines d'été : pas de saison de chauffage.
- NW Prises : ≈ 535 Wh/h jour et nuit, ≈ 35 des 62 kWh d'excès : à confirmer sur place (charge permanente légitime ?).
- ≈ 60 % de l'énergie est consommée hors heures d'occupation.
- Un seul événement connu (NE CVC laissée allumée le 3 oct) : le taux de fausses alertes ne peut pas encore être mesuré.
- Température extérieure testée, non retenue.

## 6. Couverture du backlog par la maquette

| Exigence | Écran |
|---|---|
| État du bâtiment en un coup d'œil | Overview (statut, KPI, énergie par jour) |
| Réel vs attendu avec zone normale | Actual vs expected |
| Vue par zone / étage | Floor & zones |
| Liste d'alertes triable, détail, heures hors occupation, vérifications possibles, marquer « traité » | Alerts + panneau latéral |
| Distinguer problèmes de données et gaspillage | Alerts → Data issues |
| Motifs récurrents, veille (baseline hors occupation) | Waste patterns |
| € et CO₂ estimés, hypothèses modifiables, export CSV | Savings + Settings |
| Démonstration « comme en direct » (retour sponsor) | Replay |
| Fiabilité, MAPE / CV(RMSE), limites, règles | Reliability & data |
| Filtres période / zone / charge, sensibilité | barre globale + Settings |
| Clair / sombre, mobile | toute la page |

À faire plus tard (non faisable par moi) : **test utilisateur** et **guide utilisateur** (après la maquette finale), **retour du sponsor** (mi-parcours positif ; présentation finale le 30 nov.), facture UPM réelle pour le prix.

## 7. Contribution individuelle (à adapter)

Jules : conception UX, traduction du backlog en écrans, choix des seuils et de la règle d'occupation, justification des hypothèses (€, CO₂, W/I), choix d'outils. Calculs et assemblage réalisés avec l'aide de Claude ; chaque décision ci-dessus est justifiée et modifiable.
