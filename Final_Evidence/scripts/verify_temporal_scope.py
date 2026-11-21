"""Read-only verification of temporal scope; no model fitting or model selection.

Run from this folder or the repository root. See README.md for input options.
The historical profile check audits an existing post-selection exploratory test;
it is not a new independent test or a combined-Blend experiment.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import pandas as pd


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_hourly(data, reader_path=None):
    try:
        return pd.read_parquet(io.BytesIO(data))
    except ImportError:
        if reader_path is None:
            raise RuntimeError('Install pyarrow or provide --parquet-reader pointing to Task 6 minipq.py')
        spec = importlib.util.spec_from_file_location('scope_minipq', reader_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'hourly.parquet'
            p.write_bytes(data)
            return mod.read_parquet(str(p))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path.cwd())
    ap.add_argument('--clean-zip', type=Path)
    ap.add_argument('--model-zip', type=Path)
    ap.add_argument('--task6-zip', type=Path)
    ap.add_argument('--parquet-reader', type=Path)
    ap.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'analysis' / 'temporal_scope')
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    log = ['Temporal scope verification', 'No input file is modified. No model is trained, tuned or selected.',
           f'Python {sys.version.split()[0]}; pandas {pd.__version__}; numpy {np.__version__}']
    model = a.repo / 'TBDA_v1.3_ChronosGBM_29-10'
    if a.model_zip:
        with zipfile.ZipFile(a.model_zip) as z:
            def member(suffix):
                names = [n for n in z.namelist() if n.endswith(suffix) and '__MACOSX' not in n]
                if len(names) != 1: raise ValueError(f'Expected one member for {suffix}')
                return z.read(names[0])
            hb = member('/derived/Storey1_hourly_v1.2.parquet')
            mb = member('/derived/Storey1_hourly_v1.2_META.json')
            cb = member('/config.py')
        log.append(f'Model archive SHA256: {sha(a.model_zip.read_bytes())}')
    else:
        hb = (model / 'derived/Storey1_hourly_v1.2.parquet').read_bytes()
        mb = (model / 'derived/Storey1_hourly_v1.2_META.json').read_bytes()
        cb = (model / 'config.py').read_bytes()
    meta = json.loads(mb)
    assert sha(hb) == meta['derived_sha256'], 'Hourly dataset checksum mismatch'
    log += [f'PASS hourly dataset SHA256: {sha(hb)}', f'META SHA256: {sha(mb)}', f'config.py SHA256: {sha(cb)}']
    h = read_hourly(hb, a.parquet_reader)
    h['hour_utc'] = pd.to_datetime(h.hour_utc, utc=True)
    assert not h.duplicated(['series_id', 'hour_utc']).any()
    assert h.series_id.nunique() == 16
    cuts = meta['parameters']['SPLITS']
    config_tree = ast.parse(cb.decode('utf-8'))
    config_splits = next(ast.literal_eval(node.value) for node in config_tree.body
                         if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SPLITS' for t in node.targets))
    assert {k: list(v) for k, v in config_splits.items()} == cuts, 'config.py / META split mismatch'
    log.append('PASS config.py split literals agree with META')
    scope = {}
    for label, (start, end) in cuts.items():
        scope[label] = (pd.Timestamp(start, tz='UTC'), pd.Timestamp(end, tz='UTC'))
    assert scope['train'][1] == scope['validation'][0]
    assert scope['validation'][1] == scope['test'][0]
    expected = pd.Series('outside', index=h.index)
    for label, (start, end) in scope.items():
        expected.loc[(h.hour_utc >= start) & (h.hour_utc < end)] = label
    assert (expected == h.split).all()
    expected_hours = pd.date_range(h.hour_utc.min(), h.hour_utc.max(), freq='h')
    assert len(h) == 16 * len(expected_hours)
    assert h.groupby('series_id').size().eq(len(expected_hours)).all()
    log.append('PASS unique circuit-hour keys, complete 16-circuit hourly grid, chronological disjoint splits and exact META membership')
    groups = dict((k, h[h.split == k]) for k in scope)
    groups['outside_before_train'] = h[h.hour_utc < scope['train'][0]]
    groups['outside_after_test'] = h[h.hour_utc >= scope['test'][1]]
    sr = []
    for label, g in groups.items():
        for circuit, x in [('ALL_16', g)] + list(g.groupby('series_id')):
            sr.append(dict(split=label, circuit=circuit, first_hour_utc=x.hour_utc.min(), last_hour_utc=x.hour_utc.max(),
                           calendar_hours=x.hour_utc.nunique(), circuit_hour_rows=len(x), valid_energy_pairs=x.energy_Wh.notna().sum(),
                           valid_share=x.energy_Wh.notna().mean(),
                           monday_to_friday_hours=x.loc[x.hour_utc.dt.weekday < 5, 'hour_utc'].nunique(),
                           weekend_hours=x.loc[x.hour_utc.dt.weekday >= 5, 'hour_utc'].nunique()))
    pd.DataFrame(sr).to_csv(a.output / 'split_validation_summary.csv', index=False)
    log.append('Valid counts refer to dataset energy_Wh, not fitted-model rows or Task 6 common-model scoring masks.')
    log.append('UTC split boundaries are 02:00 Madrid during this window; seven UTC days are not seven full Madrid calendar days.')
    clean = a.clean_zip or a.repo / 'CLEAN DATA all zones.zip'
    log.append(f'Clean archive SHA256: {sha(clean.read_bytes())}')
    parts = []
    with zipfile.ZipFile(clean) as z:
        for zone in ['NE','NW','SE','SW']:
            name = f'{zone}/clean_Storey1_{zone}_CLEAN_DATA.csv'
            with z.open(name) as f:
                d = pd.read_csv(f, usecols=['sensor','Timestamp','energy_Wh','energy_source'])
            d['series_id'] = zone + '|' + d.sensor
            d['utc'] = pd.to_datetime(d.Timestamp, utc=True)
            parts.append(d)
    d = pd.concat(parts, ignore_index=True).sort_values(['series_id','utc'])
    assert d.utc.notna().all()
    assert not d.duplicated(['series_id','utc']).any()
    d['regime'] = np.where(d.utc < pd.Timestamp('2024-01-01', tz='UTC'), 'historical', 'recent')
    d['hour'] = d.utc.dt.floor('h')
    raw = d.groupby(['series_id','regime','hour']).agg(n=('energy_Wh','size'), nv=('energy_Wh','count'),
                                                    E=('energy_Wh',lambda x:x.sum(min_count=1))).reset_index()
    raw['eligible_exploratory'] = (raw.nv == raw.n) & (raw.n > 0)
    cr, sources = [], []
    for (circuit, regime), g in d.groupby(['series_id','regime']):
        x = raw[(raw.series_id == circuit) & (raw.regime == regime)]
        delta = g.utc.diff().dt.total_seconds().div(60).dropna()
        first,last = x.hour.min(), x.hour.max()
        cr.append(dict(circuit=circuit, regime=regime, first_timestamp_utc=g.utc.min(), last_timestamp_utc=g.utc.max(),
                       calendar_hours_in_span=int((last-first).total_seconds()/3600)+1,
                       observed_hours=len(x), hours_all_energy_readings_nonmissing=int(x.eligible_exploratory.sum()),
                       median_rows_per_observed_hour=x.n.median(), median_positive_spacing_minutes=delta[delta>0].median(),
                       raw_rows=len(g), nonmissing_energy_rows=g.energy_Wh.notna().sum(),
                       mean_Wh_per_eligible_hour=x.loc[x.eligible_exploratory,'E'].mean()))
        for source, s in g.groupby('energy_source', dropna=False):
            sources.append(dict(circuit=circuit, regime=regime, energy_source=source, rows=len(s),
                                row_share=len(s)/len(g), energy_sum_Wh=s.energy_Wh.sum(min_count=1)))
    pd.DataFrame(cr).to_csv(a.output/'temporal_coverage_summary.csv', index=False)
    pd.DataFrame(sources).to_csv(a.output/'energy_source_summary.csv', index=False)
    hist = d.loc[d.regime=='historical','utc'].max()
    recent = d.loc[d.regime=='recent','utc'].min()
    log.append(f'Last historical timestamp: {hist}; first recent timestamp: {recent}; elapsed gap days: {(recent-hist).total_seconds()/86400:.6f}')
    # Descriptive seasonal coverage; no attempt to identify the cause of level changes.
    x = raw[raw.eligible_exploratory].copy()
    x['year'] = x.hour.dt.year
    x['month'] = x.hour.dt.month
    x.groupby(['series_id','year','month']).agg(observed_eligible_hours=('E','size'),mean_energy_Wh=('E','mean')).reset_index().to_csv(a.output/'monthly_observed_energy.csv',index=False)
    if a.task6_zip:
        with zipfile.ZipFile(a.task6_zip) as z:
            names=[n for n in z.namelist() if n.endswith('/ML_Blend_v1.3_test_predictions.csv') and '__MACOSX' not in n]
            if len(names)!=1:raise ValueError('Expected one Blend test prediction file')
            pb=z.read(names[0])
    else:
        pb=(a.repo/'Task6_rev0_03-11/results/predictions/ML_Blend_v1.3_test_predictions.csv').read_bytes()
    log.append(f'Existing Blend test predictions SHA256: {sha(pb)}')
    p=pd.read_csv(io.BytesIO(pb))
    p=p[p.horizon_h==1][['zone','target_hour','actual_Wh']].rename(columns={'zone':'series_id'})
    p['hour']=pd.to_datetime(p.target_hour,utc=True)
    assert not p.duplicated(['series_id','hour']).any()
    p['dow'],p['hr']=p.hour.dt.weekday,p.hour.dt.hour
    x['dow'],x['hr']=x.hour.dt.weekday,x.hour.dt.hour
    win=(x.hour.dt.month*100+x.hour.dt.day).between(818,1013)
    tr=x[(x.hour>=scope['train'][0]) & (x.hour<scope['train'][1])]
    old=x[x.regime=='historical']
    season=x[(x.regime=='historical') & win]
    sets={'recent_training':tr,'historical_all_seasons':old,'historical_same_season':season,
          'recent_plus_historical_same_season':pd.concat([tr,season])}
    joined=p.copy()
    for key,train in sets.items():
        profile=train.groupby(['series_id','dow','hr']).E.median().rename(key).reset_index()
        joined=joined.merge(profile,on=['series_id','dow','hr'],how='left',validate='many_to_one')
    common=joined.dropna(subset=['actual_Wh']+list(sets)).copy()
    assert len(common)>0
    rows=[]
    for key in sets:
        for selection,g in [('ALL_16',common),('EXCLUDING_SE_PLUGS',common[common.series_id!='SE|Plugs & Sockets'])]:
            errors=(g[key]-g.actual_Wh).abs()
            per=errors.groupby(g.series_id).mean()
            rows.append(dict(training_period=key,scope=selection,n_scored_pairs=len(g),n_circuits=len(per),
                             pooled_MAE_Wh=errors.mean(),macro_circuit_MAE_Wh=per.mean()))
    pd.DataFrame(rows).to_csv(a.output/'historical_profile_check.csv',index=False)
    log.append(f'Profile audit: {len(p)} target pairs; {p.actual_Wh.notna().sum()} nonmissing actuals; {len(common)} pairs common to all four profiles.')
    log.append('Profile audit uses cleaned-data hourly sums with all energy readings nonmissing, NOT v1.2 D1/D2 validity for profile training.')
    log.append('Profile audit is retrospective on the previously inspected test week; it cannot validate a new model choice or annual/winter performance.')
    log.append('Monthly means condition on observed eligible hours; missingness, season, sampling and operational changes are not disentangled.')
    log.append('The script does not establish that the chosen dates are optimal, that old data are unusable, or that 34 training days are a statistical minimum.')
    (a.output/'verification_log.txt').write_text('\n'.join(log)+'\n',encoding='utf-8')
    print('\n'.join(log))
    print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':
    main()
