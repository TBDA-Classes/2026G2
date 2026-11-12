"""Standby / out-of-hours baseline per circuit, and redundancy of W and I with energy.
Outputs: analysis/standby_baseline_by_circuit.csv, standby_weekly_median_by_circuit.csv, W_I_vs_energy.csv"""
import pandas as pd, numpy as np
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent          # package folder (Sprint4_UX_EnergyWatch)
REPO = ROOT.parent                                      # repository root
MODEL = REPO / "TBDA_v1.3_ChronosGBM_29-10"
T6 = REPO / "Task6_rev0_03-11" / "results" / "predictions"
OUT = ROOT / "analysis"; OUT.mkdir(exist_ok=True)
H=pd.read_parquet(MODEL / 'derived' / 'Storey1_hourly_v1.2.parquet')
H['loc']=H.hour_utc.dt.tz_convert('Europe/Madrid'); H['hr']=H['loc'].dt.hour; H['dow']=H['loc'].dt.dayofweek
H['occ']=(H.dow<5)&(~H.is_holiday)&(H.hr>=7)&(H.hr<20)
H=H[H.hour_utc>='2025-08-19']
V=H[H.energy_valid&H.energy_Wh.notna()].copy()
V['week']=V['loc'].dt.tz_localize(None).dt.to_period('W-SUN').astype(str)
# ---------- standby / baseline
g=V.groupby('series_id')
rows=[]
for s,d in g:
    o=d[~d.occ]; u=d[d.occ]
    tr_o=o[o.split=='train']
    rows.append(dict(series=s,hours_valid=len(d),mean_occupied_Wh=u.energy_Wh.mean(),mean_outofhours_Wh=o.energy_Wh.mean(),
      standby_median_Wh=o.energy_Wh.median(),standby_p10_Wh=o.energy_Wh.quantile(.1),standby_p90_Wh=o.energy_Wh.quantile(.9),
      standby_train_median_Wh=tr_o.energy_Wh.median(),
      share_energy_outofhours_pct=100*o.energy_Wh.sum()/d.energy_Wh.sum(),share_hours_outofhours_pct=100*len(o)/len(d),
      ratio_outofhours_to_occupied=o.energy_Wh.mean()/u.energy_Wh.mean() if u.energy_Wh.mean()>0 else np.nan))
S=pd.DataFrame(rows).round(2).sort_values('mean_outofhours_Wh',ascending=False)
S.to_csv(OUT / 'standby_baseline_by_circuit.csv',index=False); print(S.to_string(index=False))
tot=V.energy_Wh.sum(); print('building: share of energy out of hours %.1f%% (hours share %.1f%%)'%(100*V[~V.occ].energy_Wh.sum()/tot,100*(~V.occ).mean()))
# weekly out-of-hours level
wk=V[~V.occ].groupby(['series_id','week']).energy_Wh.median().unstack().round(1)
wk.to_csv(OUT / 'standby_weekly_median_by_circuit.csv'); print(wk.loc[['NW|Plugs & Sockets','SE|Lighting','NW|HVAC','NE|Plugs & Sockets']].to_string())
# by zone
V['zone']=V.series_id.str[:2]
z=V.groupby(['zone',V.occ]).energy_Wh.agg(['sum','size']).round(0); print(z)

# ---------- W and I
E=H[H.energy_valid&H.W_valid&H.energy_Wh.notna()&H.W_mean.notna()]
rw=[]
for s,d in E.groupby('series_id'):
    d2=d.merge(d[['hour_utc','I_mean']],on='hour_utc',suffixes=('','_x'))
    di=d[d.I_valid&d.I_mean.notna()]
    rw.append(dict(series=s,hours=len(d),corr_energy_W=d.energy_Wh.corr(d.W_mean),median_ratio_energy_to_W=(d.energy_Wh/d.W_mean.replace(0,np.nan)).median(),
        corr_W_I=di.W_mean.corr(di.I_mean) if len(di)>10 else np.nan, W_valid_share=H[H.series_id==s].W_valid.mean()*100,I_valid_share=H[H.series_id==s].I_valid.mean()*100,
        energy_valid_share=H[H.series_id==s].energy_valid.mean()*100))
WI=pd.DataFrame(rw).round(3); WI.to_csv(OUT / 'W_I_vs_energy.csv',index=False); print(WI.to_string(index=False))
print('median corr energy~W',WI.corr_energy_W.median(),'  corr W~I',WI.corr_W_I.median())
