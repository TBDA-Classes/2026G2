"""Occupancy rule evidence: presence-detector (Pres) profile by hour of day for the zones with a usable detector (NW, SE).
Output: analysis/occupancy_profile_by_hour.csv.  Run prep_presence.py first."""
import pandas as pd, numpy as np
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent          # Sprint4_Task4_Documentation
REPO = ROOT.parent                                      # repository root
MODEL = REPO / "TBDA_v1.3_ChronosGBM_29-10"
T6 = REPO / "Task6_rev0_03-11" / "results" / "predictions"
OUT = ROOT / "analysis"; OUT.mkdir(exist_ok=True)
H=pd.read_parquet(MODEL / 'derived' / 'Storey1_hourly_v1.2.parquet')
H['loc']=pd.to_datetime(H.hour_local,utc=True).dt.tz_convert('Europe/Madrid') if H.hour_local.dtype==object else H.hour_utc.dt.tz_convert('Europe/Madrid')
H['hr']=H['loc'].dt.hour; H['dow']=H['loc'].dt.dayofweek
P=pd.read_csv(OUT / 'presence_hourly.csv', parse_dates=['h'])   # zone, h(UTC hour), Pres (mean of minutes)
P['any']=(P.Pres>0)
# ---- occupancy from NW & SE motion detectors
U=P[P.zone.isin(['NW','SE'])].groupby('h').agg(any=('any','max'),frac=('Pres','max')).reset_index()
U['loc']=U.h.dt.tz_convert('Europe/Madrid'); U['hr']=U['loc'].dt.hour; U['dow']=U['loc'].dt.dayofweek; U['we']=U.dow>=5
prof=U.groupby(['we','hr'])['any'].mean().unstack(0).round(3); prof.columns=['weekday','weekend']
print(prof.to_string())
# rule candidates
for a,b in [(7,20),(7,19),(6,20),(8,19),(7,21)]:
    occ=(~U.we)&(U.hr>=a)&(U.hr<b)
    cap=U[U['any']].shape[0]; inside=U[U['any'] & occ].shape[0]
    print(f'rule weekdays {a:02d}-{b:02d}: presence-hours captured {inside/cap:.1%}; occupied-hours with presence {U[occ]["any"].mean():.1%}; presence in non-occupied {1-inside/cap:.1%}')
print('hours w/ presence total',U['any'].sum(),'of',len(U), 'weekend presence hours',U[U.we]['any'].sum())
# SW constant check
sw=P[P.zone=='SW']; print('SW Pres hourly: min/max/mean',sw.Pres.min(),sw.Pres.max(),sw.Pres.mean().round(3))

print('\n--- threshold >= 2 minutes (0.033) ---')
for thr in [0.02,0.033,0.05]:
    U['occ_h']=U.frac>=thr
    pr=U.groupby(['we','hr'])['occ_h'].mean().unstack(0).round(2); pr.columns=['weekday','weekend']
    tot=U.occ_h.sum()
    res=[]
    for a,b in [(7,20),(7,19),(6,20),(7,21),(8,19)]:
        occ=(~U.we)&(U.hr>=a)&(U.hr<b)
        res.append((a,b,round((U.occ_h&occ).sum()/tot,3),round(U[occ].occ_h.mean(),3)))
    print(thr,'presence hours',tot,'weekend',U[U.we].occ_h.sum(),'(captured, share-occupied-with-presence)',res)
    if thr==0.033: pr.to_csv(OUT / 'occupancy_profile_by_hour.csv'); print(pr.to_string())
