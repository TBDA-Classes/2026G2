"""Accuracy metrics (MAE, RMSE, WAPE, MAPE, CV(RMSE), NMBE) of the final model and the baselines, and coverage of the Chronos-Bolt q10-q90 band.
Outputs: analysis/accuracy_metrics_MAPE_CVRMSE.csv, accuracy_by_circuit_blend.csv, band_coverage_chronos.csv, band_coverage_by_circuit_test.csv"""
import pandas as pd, numpy as np
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent          # package folder (Sprint4_UX_EnergyWatch)
REPO = ROOT.parent                                      # repository root
MODEL = REPO / "TBDA_v1.3_ChronosGBM_29-10"
T6 = REPO / "Task6_rev0_03-11" / "results" / "predictions"
OUT = ROOT / "analysis"; OUT.mkdir(exist_ok=True)
M={'Blend v1.3':'ML_Blend_v1.3','Chronos-Bolt v1.3':'ML_Chronos_v1.3','B3 persistence':'B3_persistence','B2 weekday×hour median':'B2_weekday_hour_median','B1 same hour last week':'B1_last_week'}
HN={1:'+1h',6:'+6h',24:'day-ahead'}
def met(a,p,minact=10):
    e=p-a; n=len(a)
    m=a>=minact
    return dict(n=n,mean_actual_Wh=a.mean(),MAE_Wh=e.abs().mean(),RMSE_Wh=np.sqrt((e**2).mean()),WAPE_pct=100*e.abs().sum()/a.sum(),
        CV_RMSE_pct=100*np.sqrt((e**2).mean())/a.mean(),NMBE_pct=100*e.sum()/a.sum(),
        MAPE_pct=100*(e[m].abs()/a[m]).mean() if m.sum() else np.nan,MAPE_n=int(m.sum()))
out=[]; outz=[]; outb=[]; outc=[]
for split in ['validation','test']:
    dfs={k:pd.read_csv(T6 / f'{m}_{split}_predictions.csv',parse_dates=['target_hour']).set_index(['zone','horizon_h','target_hour'])[['actual_Wh','predicted_Wh','circuit_zone']] for k,m in M.items()}
    base=dfs['Blend v1.3'][['actual_Wh','circuit_zone']].copy()
    for k,d in dfs.items(): base[k]=d['predicted_Wh']
    base=base.dropna().reset_index()
    for h,g in base.groupby('horizon_h'):
        for k in M:
            r=met(g.actual_Wh,g[k]); r.update(split=split,horizon=HN[h],model=k,level='circuit-hour (pooled 16 circuits)'); out.append(r)
        # per circuit for Blend
        for s,gc in g.groupby('zone'):
            r=met(gc.actual_Wh,gc['Blend v1.3']); r.update(split=split,horizon=HN[h],circuit=s,n_B3=None); 
            r['MAE_persistence_Wh']=(gc['B3 persistence']-gc.actual_Wh).abs().mean(); outc.append(r)
        # zone totals (hours where all circuits of the zone are present)
        for zc,gz in g.groupby('circuit_zone'):
            ncirc=gz.zone.nunique()
            cnt=gz.groupby('target_hour').zone.nunique(); full=cnt[cnt==ncirc].index
            t=gz[gz.target_hour.isin(full)].groupby('target_hour')[['actual_Wh']+list(M)].sum()
            for k in M:
                if len(t)>=10:
                    r=met(t.actual_Wh,t[k],minact=50); r.update(split=split,horizon=HN[h],model=k,level=f'zone total {zc} ({ncirc} circuits)'); outz.append(r)
        cnt=g.groupby('target_hour').zone.nunique(); full=cnt[cnt==16].index
        t=g[g.target_hour.isin(full)].groupby('target_hour')[['actual_Wh']+list(M)].sum()
        for k in M:
            r=met(t.actual_Wh,t[k],minact=100); r.update(split=split,horizon=HN[h],model=k,level='building total (hours with all 16 circuits)'); outb.append(r)
A=pd.DataFrame(out+outz+outb); 
cols=['level','split','horizon','model','n','mean_actual_Wh','MAE_Wh','RMSE_Wh','WAPE_pct','MAPE_pct','MAPE_n','CV_RMSE_pct','NMBE_pct']
A=A[cols].round(2); A.to_csv(OUT / 'accuracy_metrics_MAPE_CVRMSE.csv',index=False)
C=pd.DataFrame(outc).round(2); C.to_csv(OUT / 'accuracy_by_circuit_blend.csv',index=False)
pd.set_option('display.width',250)
print(A[(A.model=='Blend v1.3')].to_string(index=False))
print(A[(A.split=='test')&(A.level.str.startswith('circuit'))].to_string(index=False))

# ---------- band coverage (Chronos q10-q90) 
bc=[]
for s in ['validation','test']:
    c=pd.read_parquet(MODEL / 'results' / f'chronos_{s}_predictions_v1.3.parquet').dropna(subset=['y_true','q10','q90'])
    c['inside']=(c.y_true>=c.q10)&(c.y_true<=c.q90); c['below']=c.y_true<c.q10; c['above']=c.y_true>c.q90; c['width']=c.q90-c.q10
    c['hz']=c.horizon
    for h,g in c.groupby('hz'):
        bc.append(dict(split=s,horizon=h,n=len(g),coverage_pct=100*g.inside.mean(),above_pct=100*g.above.mean(),below_pct=100*g.below.mean(),mean_width_Wh=g.width.mean(),scope='all 16 circuits'))
    bc.append(dict(split=s,horizon='all',n=len(c),coverage_pct=100*c.inside.mean(),above_pct=100*c.above.mean(),below_pct=100*c.below.mean(),mean_width_Wh=c.width.mean(),scope='all 16 circuits'))
    if s=='test':
        pc=c.groupby('series_id').agg(n=('inside','size'),coverage_pct=('inside',lambda x:100*x.mean()),above_pct=('above',lambda x:100*x.mean()),below_pct=('below',lambda x:100*x.mean()),mean_width_Wh=('width','mean')).round(1)
        pc.to_csv(OUT / 'band_coverage_by_circuit_test.csv')
B=pd.DataFrame(bc).round(1); B.to_csv(OUT / 'band_coverage_chronos.csv',index=False); print(B.to_string(index=False))
print(pd.read_csv(OUT / 'band_coverage_by_circuit_test.csv').sort_values('coverage_pct').to_string(index=False))
