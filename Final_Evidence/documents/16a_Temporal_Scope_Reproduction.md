# Temporal scope justification — Blend v1.3

**Prepared by Maria Francesca Casillo · 21 November 2026 · TBDA Group 2**

This contribution supports the team's decision to retain the frozen 2025-only model for the final delivery. It audits the temporal evidence and defines the limits of that decision. It does not claim that 2025-only training is optimal or that historical data are unusable.

Read **[16_Temporal_Scope_Justification.md](16_Temporal_Scope_Justification.md)** first. It complements, rather than replaces, `Final_Evidence/documents/08_Scope_Decision_2025_Only.md` and `14_Evaluation_Protocol_Justification.md`. Their authors retain credit for the original analyses. This package adds checks of the exact time windows, data-validity definitions, scored sample sizes and error aggregation, together with a bounded decision rationale.

## Files

| File | Purpose |
|---|---|
| `documents/16_Temporal_Scope_Justification.md` | Decision rationale, evidence, alternatives, winter limitation and reporting clarifications |
| `scripts/verify_temporal_scope.py` | Read-only checks; creates the evidence tables below |
| `analysis/temporal_scope/temporal_coverage_summary.csv` | Sampling and observed-hour coverage by circuit and regime; exploratory validity only |
| `analysis/temporal_scope/split_validation_summary.csv` | Complete-grid counts and v1.2-valid energy pairs by split and circuit |
| `analysis/temporal_scope/historical_profile_check.csv` | Audit of four historical-profile training alternatives on a common set of measurable targets |
| `analysis/temporal_scope/energy_source_summary.csv` | Provenance of the cleaned energy target by circuit and regime |
| `analysis/temporal_scope/monthly_observed_energy.csv` | Descriptive monthly availability and means; not a seasonal causal analysis |
| `analysis/temporal_scope/verification_log.txt` | Input fingerprints, environment, checks and interpretation limits |

The three additional evidence CSVs are needed to check energy construction, the historical-profile argument and seasonal coverage. No raw data or model binaries are duplicated in this package.

## Reproduce from a repository clone

This contribution follows the existing `Final_Evidence/` layout: document in `documents/`, script in `scripts/`, generated evidence in `analysis/temporal_scope/`. Run commands from the repository root, which contains `Final_Evidence/`, the model folder and the Task 6 folder. Python 3.11+ with pandas and numpy is sufficient when using the team's Parquet reader:

```bash
python Final_Evidence/scripts/verify_temporal_scope.py --repo . --parquet-reader Task6_rev0_03-11/minipq.py
```

Alternatively install `pyarrow` and omit `--parquet-reader`. Required existing inputs:

- `CLEAN DATA all zones.zip`
- `TBDA_v1.3_ChronosGBM_29-10/derived/Storey1_hourly_v1.2.parquet`
- `TBDA_v1.3_ChronosGBM_29-10/derived/Storey1_hourly_v1.2_META.json`
- `TBDA_v1.3_ChronosGBM_29-10/config.py`
- `Task6_rev0_03-11/results/predictions/ML_Blend_v1.3_test_predictions.csv`

Archive inputs are also supported, for example:

```bash
python Final_Evidence/scripts/verify_temporal_scope.py --clean-zip "CLEAN DATA all zones.zip" --model-zip "model.zip" --task6-zip "task6.zip" --parquet-reader Task6_rev0_03-11/minipq.py
```

`--output PATH` selects a different evidence folder. The script overwrites only its generated evidence files. It never changes source data, frozen models, configurations or official scores. The hourly Parquet checksum must match its META; input fingerprints are recorded.

## Verification boundary

The verification logic was executed on the uploaded archives and completed successfully. The integrated copy changes only the default output location to `Final_Evidence/analysis/temporal_scope/`; its calculations are unchanged. The user also completed the original script locally and shared matching headline results; the full local CSV set has not been compared. It checks split literals against META and observed split membership, full-grid structure and input integrity. It recomputes the exploratory profile comparison using a common valid-target mask and explicit pooled versus circuit-average MAE. It does not rerun Blend, independently verify all cleaning rules, reconstruct Git chronology, run a historical-plus-recent Blend experiment, or establish winter performance. An existing test week is reused only to audit published exploratory evidence, not to choose or modify a model.
