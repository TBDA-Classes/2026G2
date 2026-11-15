"""Accuracy of the final model by circuit / load type, with skill scores and daily totals (complements analysis_accuracy.py, which it does not change).

Adds what the pooled tables do not show:
  * a fourth naive benchmark, B4 "same hour yesterday" (energy of the same circuit 24 h earlier; always known when a forecast is issued),
  * skill score = 1 - RMSE_model / RMSE_naive, against B3 persistence and against B4, for every circuit,
  * ASHRAE Guideline 14 hourly reference values (CV(RMSE) <= 30 %, |NMBE| <= 10 %), used as a common reference and not as a pass/fail test,
  * indicative targets by load type (instructor guidance, 15 Nov 2026),
  * daily totals made by summing the 24 hourly day-ahead forecasts (Madrid calendar days with all 24 hours valid).

Inputs : Task6_rev0_03-11/results/predictions/*_predictions.csv, TBDA_v1.3_ChronosGBM_29-10/derived/Storey1_hourly_v1.2.parquet
Outputs: analysis/accuracy_by_load_type.csv, accuracy_daily_totals.csv"""
import pandas as pd, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
T6 = REPO / "Task6_rev0_03-11" / "results" / "predictions"
HOURLY = REPO / "TBDA_v1.3_ChronosGBM_29-10" / "derived" / "Storey1_hourly_v1.2.parquet"
OUT = ROOT / "analysis"; OUT.mkdir(exist_ok=True)
HN = {1: '+1h', 6: '+6h', 24: 'day-ahead'}
LABEL = {'HVAC': 'HVAC', 'Plugs & Sockets': 'Plugs & Sockets', 'Emerg. Lighting': 'Emergency lighting', 'Hand Dryer': 'Hand dryer', 'Lighting': 'Lighting', 'RACK': 'Rack'}
# Indicative hourly CV(RMSE) target by load type (instructor guidance). None = hourly CV(RMSE) is not a meaningful metric for this load.
TARGET = {'RACK': 15, 'Emerg. Lighting': 15, 'Plugs & Sockets': 30, 'HVAC': 50, 'Lighting': None, 'Hand Dryer': None}
ASHRAE_CV, ASHRAE_NMBE = 30.0, 10.0

h = pd.read_parquet(HOURLY)
h = h[h.energy_valid][['series_id', 'hour_utc', 'energy_Wh']].copy()
h['target_hour'] = h.hour_utc + pd.Timedelta(hours=24)       # value observed 24 h before the target hour
lag = h.rename(columns={'series_id': 'zone', 'energy_Wh': 'B4'})[['zone', 'target_hour', 'B4']]

def rmse(e): return float(np.sqrt(np.mean(np.square(e))))
rows, drows = [], []
for split in ['validation', 'test']:
    bl = pd.read_csv(T6 / f'ML_Blend_v1.3_{split}_predictions.csv', parse_dates=['target_hour'])
    b3 = pd.read_csv(T6 / f'B3_persistence_{split}_predictions.csv', parse_dates=['target_hour'])
    b3 = b3.rename(columns={'predicted_Wh': 'B3'})[['zone', 'horizon_h', 'target_hour', 'B3']]
    d = bl.rename(columns={'predicted_Wh': 'Blend'})[['zone', 'horizon_h', 'target_hour', 'actual_Wh', 'Blend']].merge(b3, on=['zone', 'horizon_h', 'target_hour'], how='left')
    d = d.merge(lag, on=['zone', 'target_hour'], how='left').dropna(subset=['actual_Wh', 'Blend'])
    for hz, g in d.groupby('horizon_h'):
        groups = [(s, gg) for s, gg in g.groupby('zone')] + [('ALL 16 circuits (pooled)', g)]
        for s, gg in groups:
            a = gg.actual_Wh; e = gg.Blend - a
            r = dict(split=split, horizon=HN[hz], circuit=s, load_type=LABEL.get(s.split('|')[-1], 'all'), n=len(gg), mean_actual_Wh=round(a.mean(), 2),
                     MAE_Wh=round(e.abs().mean(), 2), MAE_kWh=round(e.abs().mean() / 1000, 4), RMSE_Wh=round(rmse(e), 2),
                     CV_RMSE_pct=round(100 * rmse(e) / a.mean(), 1), NMBE_pct=round(100 * e.sum() / a.sum(), 1))
            # NMBE = 100 * sum(forecast - actual) / sum(actual), same convention as accuracy_analysis.py: positive = forecast above actual use
            p3 = gg.dropna(subset=['B3']); r['n_vs_B3'] = len(p3)
            r['skill_RMSE_vs_B3_persistence_pct'] = round(100 * (1 - rmse(p3.Blend - p3.actual_Wh) / rmse(p3.B3 - p3.actual_Wh)), 1) if len(p3) else np.nan
            p4 = gg.dropna(subset=['B4']); r['n_vs_B4'] = len(p4)
            r['skill_RMSE_vs_B4_yesterday_pct'] = round(100 * (1 - rmse(p4.Blend - p4.actual_Wh) / rmse(p4.B4 - p4.actual_Wh)), 1) if len(p4) else np.nan
            r['skill_MAE_vs_B4_yesterday_pct'] = round(100 * (1 - (p4.Blend - p4.actual_Wh).abs().mean() / (p4.B4 - p4.actual_Wh).abs().mean()), 1) if len(p4) else np.nan
            lt = s.split('|')[-1]
            r['ashrae_hourly_CV_le_30'] = r['CV_RMSE_pct'] <= ASHRAE_CV
            r['ashrae_hourly_NMBE_le_10'] = abs(r['NMBE_pct']) <= ASHRAE_NMBE
            tg = TARGET.get(lt, 'n/a') if '|' in s else 'n/a'
            r['indicative_CV_target_pct'] = 'not meaningful hourly (use MAE and daily energy)' if tg is None else tg
            r['meets_indicative_target'] = ('' if tg in (None, 'n/a') else bool(r['CV_RMSE_pct'] <= tg and (lt != 'HVAC' or abs(r['NMBE_pct']) <= ASHRAE_NMBE)))
            rows.append(r)
        if hz == 24:
            # daily totals: Madrid calendar days where the circuit has all 24 hourly forecasts and (for B4) all 24 lagged values
            g = g.copy(); g['day'] = g.target_hour.dt.tz_convert('Europe/Madrid').dt.date
            full = g.groupby(['zone', 'day']).filter(lambda x: len(x) == 24 and x.B4.notna().all() and x.B3.notna().all())
            dd = full.groupby(['zone', 'day']).agg(actual=('actual_Wh', 'sum'), blend=('Blend', 'sum'), b4=('B4', 'sum'), b3=('B3', 'sum')).reset_index()
            for s, x in dd.groupby('zone'):
                e = x.blend - x.actual
                drows.append(dict(split=split, circuit=s, load_type=LABEL.get(s.split('|')[-1]), complete_days=len(x), mean_daily_kWh=round(x.actual.mean() / 1000, 3),
                                  MAE_daily_kWh=round(e.abs().mean() / 1000, 3), WAPE_daily_pct=round(100 * e.abs().sum() / x.actual.sum(), 1),
                                  CV_RMSE_daily_pct=round(100 * rmse(e) / x.actual.mean(), 1), NMBE_daily_pct=round(100 * e.sum() / x.actual.sum(), 1),
                                  MAE_daily_B4_yesterday_kWh=round((x.b4 - x.actual).abs().mean() / 1000, 3), MAE_daily_B3_persistence_kWh=round((x.b3 - x.actual).abs().mean() / 1000, 3)))
R = pd.DataFrame(rows); R.to_csv(OUT / 'accuracy_by_load_type.csv', index=False)
D = pd.DataFrame(drows); D.to_csv(OUT / 'accuracy_daily_totals.csv', index=False)
pd.set_option('display.width', 280); pd.set_option('display.max_columns', 30)
t = R[(R.split == 'test') & (R.horizon == 'day-ahead')]
print(t[['circuit', 'n', 'mean_actual_Wh', 'MAE_Wh', 'CV_RMSE_pct', 'NMBE_pct', 'skill_RMSE_vs_B3_persistence_pct', 'skill_RMSE_vs_B4_yesterday_pct', 'indicative_CV_target_pct', 'meets_indicative_target']].to_string(index=False))
print(D[D.split == 'test'].to_string(index=False))
