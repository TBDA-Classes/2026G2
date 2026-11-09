from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

folder = Path(__file__).resolve().parent
source = folder / 'ML_Blend_v1.3_validation_predictions.csv'
out = folder / 'outputs'
out.mkdir(exist_ok=True)
df = pd.read_csv(source)
keys = ['zone', 'horizon_h', 'target_hour']
if df.duplicated(keys).any():
    raise ValueError('Duplicate circuit/horizon/target keys')
times = pd.to_datetime(df.target_hour, utc=True)
if not ((times >= pd.Timestamp('2025-09-22', tz='UTC')) & (times < pd.Timestamp('2025-09-29', tz='UTC'))).all():
    raise ValueError('Unexpected validation period')
if set(df.model) != {'ML_Blend_v1.3'} or set(df.horizon_h) != {1, 6, 24}:
    raise ValueError('Unexpected model or horizons')
for col in ['actual_Wh', 'predicted_Wh']:
    df[col] = pd.to_numeric(df[col], errors='raise')
    if np.isinf(df[col]).any():
        raise ValueError('Infinite values')
valid = df.dropna(subset=['actual_Wh', 'predicted_Wh']).copy()
valid['absolute_error'] = (valid.predicted_Wh - valid.actual_Wh).abs()
valid['squared_error'] = (valid.predicted_Wh - valid.actual_Wh) ** 2

def metrics(group_cols):
    grid = df.groupby(group_cols).size().rename('n_expected')
    m = valid.groupby(group_cols).agg(n_valid=('absolute_error', 'size'), MAE_Wh=('absolute_error', 'mean'), MSE=('squared_error', 'mean'), SAE_Wh=('absolute_error', 'sum'))
    m = grid.to_frame().join(m)
    m['n_valid'] = m.n_valid.fillna(0).astype(int)
    m['n_excluded'] = m.n_expected - m.n_valid
    m['valid_pair_pct'] = 100 * m.n_valid / m.n_expected
    m['RMSE_Wh'] = np.sqrt(m.pop('MSE'))
    m = m.reset_index()
    # Share of pooled absolute error within each horizon, not percentage error.
    total = valid.groupby('horizon_h').absolute_error.sum()
    m['absolute_error_share_pct'] = 100 * m.SAE_Wh / m.horizon_h.map(total)
    return m

overall = metrics(['horizon_h'])
zones = metrics(['circuit_zone', 'horizon_h'])
circuits = metrics(['zone', 'circuit_zone', 'horizon_h'])
circuits['MAE_rank'] = circuits.groupby('horizon_h').MAE_Wh.rank(method='min', ascending=False).astype(int)
circuits['RMSE_rank'] = circuits.groupby('horizon_h').RMSE_Wh.rank(method='min', ascending=False).astype(int)
for name, frame in [('metrics_overall_validation', overall), ('metrics_by_zone_validation', zones), ('metrics_by_circuit_validation', circuits)]:
    frame.to_csv(out / (name + '.csv'), index=False)
shortlist = circuits[(circuits.MAE_rank <= 3) | (circuits.RMSE_rank <= 3)].sort_values(['horizon_h', 'MAE_rank'])
shortlist.to_csv(out / 'worst_cases_validation.csv', index=False)

# Reconcile the circuit results with independently pooled overall errors.
for horizon in [1, 6, 24]:
    c = circuits[circuits.horizon_h == horizon]
    o = overall[overall.horizon_h == horizon].iloc[0]
    assert c.n_valid.sum() == o.n_valid
    assert np.isclose(np.average(c.MAE_Wh, weights=c.n_valid), o.MAE_Wh)
    assert np.isclose(np.sqrt(np.average(c.RMSE_Wh ** 2, weights=c.n_valid)), o.RMSE_Wh)
    assert np.isclose(c.absolute_error_share_pct.sum(), 100)
checks = {'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'total_rows': len(df), 'valid_pairs': len(valid), 'excluded_pairs': len(df)-len(valid), 'unique_circuits': df.zone.nunique(), 'duplicate_keys': 0, 'weighted_reconciliation': 'passed'}
(out / 'checks.json').write_text(json.dumps(checks, indent=2))

def table(frame, columns):
    rows = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for _, row in frame.iterrows():
        vals = []
        for col in columns:
            x = row[col]
            vals.append(f'{x:.2f}' if isinstance(x, (float, np.floating)) else str(x).replace('|', ' / '))
        rows.append('| ' + ' | '.join(vals) + ' |')
    return '\n'.join(rows)

report = '''# Sprint 4 — Task 1 Part 1: Performance analysis of Blend v1.3

**Authors:** Maria Francesca Casillo and Yasmin Sarbout Atif  
**Status:** Recalculated validation analysis, prepared for team review on 6 November 2026. This revision replaces the unsupported performance tables in the supplied Part 1 draft; the original document is preserved separately.

## Purpose

Identify **where the selected model makes errors** using MAE, RMSE and valid observation counts by zone, circuit and forecasting horizon. The deliverables are complete metric tables and a shortlist of cases requiring further investigation. Temporal patterns belong to Part 2; data conditions and possible explanations belong to Part 3.

## Data and method

Source: `ML_Blend_v1.3_validation_predictions.csv`, the saved Task 6 predictions also used in Part 2. Validation targets run from 22 September 2025 00:00 UTC to 29 September 2025 00:00 UTC, end exclusive. No test data, training or tuning are used here.

The file contains 8,064 rows: 16 circuits × 168 hours × 3 horizons. There are 7,239 valid actual/prediction pairs, 2,413 per horizon; 825 rows are excluded because the actual value is missing. Missing actuals are never replaced by zero. The repeated horizons do not represent independent target hours.

`zone` is the circuit identifier; `circuit_zone` is NE/NW/SE/SW. The inventory contains 2 NE, 6 NW, 4 SE and 4 SW circuits. `horizon_h=24` labels day-ahead, not a fixed lead of 24 hours for every forecast.

- MAE = mean absolute difference between forecast and actual, in Wh.
- RMSE = square root of the mean squared difference, in Wh; large misses receive greater weight.
- Valid-pair percentage = valid actual/prediction pairs divided by the expected circuit-hour rows in this file.
- Absolute-error share = a scope's sum of absolute errors divided by the all-circuit sum at the same horizon. This is not percentage prediction error or the share of the unweighted sum of circuit MAEs.

Zone and overall metrics pool circuit-hour pairs: MAE is weighted by valid counts and RMSE is computed from pooled squared errors. RMSE values must not be averaged directly. These results use Blend's available validation pairs, not Task 6's common mask across competing models and dataset versions. Consequently they do not reproduce the official comparison scores and must not be substituted into that comparison.

## Overall and zone results

'''
report += table(overall, ['horizon_h', 'n_expected', 'n_valid', 'n_excluded', 'MAE_Wh', 'RMSE_Wh']) + '\n\n'
report += table(zones, ['circuit_zone', 'horizon_h', 'n_expected', 'n_valid', 'valid_pair_pct', 'MAE_Wh', 'RMSE_Wh', 'absolute_error_share_pct'])
report += '\n\nNW Plugs & Sockets has the largest MAE and RMSE at every horizon, followed by SE Lighting. Their combined shares of pooled absolute error are 76.1% at +1 h, 78.0% at +6 h and 75.9% day-ahead. These are the strongest absolute-error priorities in this sample. SE Plugs & Sockets ranks third by MAE at each horizon, but has only 98 valid observations out of 168. SW Lighting enters the +1 h shortlist through RMSE rather than MAE, indicating that its largest misses deserve inspection. These rankings describe the available validation observations, not future performance.\n'
report += '\n\n## Complete circuit results\n\nCircuit names below are rendered with `/` for readability; CSVs preserve the original identifiers containing `|`.\n\n'
for h in [1, 6, 24]:
    report += f'### {"Day-ahead" if h == 24 else "+" + str(h) + " h"}\n\n'
    report += table(circuits[circuits.horizon_h == h].sort_values('MAE_rank'), ['zone', 'n_valid', 'n_excluded', 'valid_pair_pct', 'MAE_Wh', 'RMSE_Wh', 'absolute_error_share_pct', 'MAE_rank', 'RMSE_rank']) + '\n\n'
report += '''## Shortlist for further investigation

The exported `worst_cases_validation.csv` includes the three highest-MAE or highest-RMSE circuits at each horizon. Ranking uses unrounded values. High absolute error prioritises investigation; it does not establish a physical cause or intrinsic difficulty independent of circuit consumption scale.

'''
report += table(shortlist, ['zone', 'horizon_h', 'n_valid', 'MAE_Wh', 'RMSE_Wh', 'absolute_error_share_pct', 'MAE_rank', 'RMSE_rank'])
report += '''

### Handover to the other contributions

- **NW Plugs & Sockets:** compare its performance rank and error share with Part 2's night and episode analysis, then Part 3's training/validation level checks. Do not infer equipment changes from error metrics alone.
- **SE Lighting:** connect its MAE/RMSE to Part 2's 22 and 24 September afternoon cases. Part 3 should check measurement provenance and missing power readings before attributing the events to operations.
- **Other ranked cases:** retain the shortlist at every horizon rather than assuming that day-ahead rankings apply to +1 h and +6 h.
- **SE Plugs & Sockets:** interpret its metrics with its valid count and exclusion rate. Part 3's much smaller common-comparison sample answers a different question; do not mix the two counts.

## Limits

This is one validation week already used during model selection. The diagnosis is exploratory and does not provide an independent estimate of future generalisation. Availability differs across circuits and may change which operating conditions are scored. Absolute metrics depend on consumption scale; no training-mean-normalised metric is calculated from this file alone. No confidence intervals, significance tests, baseline rankings, physical causes or numerical improvement promises are inferred here. A lower zone MAE does not establish generalisation to unseen circuits.

## Reproduction and checks

Keep the script and input CSV together, then run:

```bash
python -m pip install pandas numpy
python performance_analysis.py
```

The script regenerates this report and four CSV tables in `outputs/`, plus a JSON record of input hash and checks. It validates the split, horizons, duplicate keys and finite values, and reconciles circuit-level metrics with directly pooled overall MAE/RMSE and error shares. Rerunning overwrites these generated files. It does not execute forecasting or modify the frozen model.
'''
(folder / 'REPORT.md').write_text(report, encoding='utf-8')
print(overall.to_string(index=False))
print(shortlist[['zone','horizon_h','MAE_Wh','RMSE_Wh','absolute_error_share_pct']].to_string(index=False))
print(json.dumps(checks))
