# Final-phase evidence pack

TBDA Group 2 · CeDInt Storey 1 · 17 Nov 2026 · **Authors: Jules (main author), Claude (co-author)**

Evidence prepared for the final presentation (30 Nov) and the Moodle hand-over (14 Dec).

| File | Content |
|---|---|
| `documents/08_Scope_Decision_2025_Only.md` | Why the model is trained on 2025 only; regime differences; exploratory test; protocol for a combined model |
| `documents/09_ASHRAE14_Assessment.md` | ASHRAE Guideline 14 reference check by level, teacher targets |
| `documents/09b_ASHRAE14_Traffic_Light.html` | Colour-coded table (green / yellow / red) by building, zone and circuit |
| `documents/10_Evidence_Map.md` | Every claim of the presentation → proving file; numbers to retire |
| `documents/11_Deliverables_Index_Dash.md` | Deliverables index and demo plan with Dash as main dashboard |
| `documents/12_Data_Cleaning_Justification.md` | Data cleaning: every decision with reason, evidence, rejected alternative and weakness; results in numbers; open points; likely questions |
| `documents/12a_Cleaning_Checks.md` | Data cleaning checks: impact of the 5 sensors flagged by the cleaning on test results and model selection; counter-direct share vs error and coverage |
| `documents/13_Prophet_Justification.md` | Prophet (backlog PB-28): why it was tested, how (same protocol, 112 configurations, validation only) and why it was not kept |
| `documents/14_Evaluation_Protocol_Justification.md` | Evaluation protocol: split, data after 5 Oct, horizons, metrics, baselines, rule D10, same-hours comparison and bootstrap; each with reason, evidence, alternative and weakness |
| `documents/15_Random_Forest_Justification.md` | Random Forest (Model 3): every build decision with reason, evidence, alternative and weakness; test result; why it is not the final model (not a D10 candidate, and would not have passed D10); corrections to the model package |
| `scripts/ashrae14_by_level.py` | Computes `analysis/ashrae14_by_level_{test,validation}.csv` |
| `scripts/ashrae14_traffic_light.py` | Computes `analysis/ashrae14_traffic_light_test.csv` |
| `scripts/regime_comparison.py` | Computes the regime comparison and the exploratory profile test |
| `scripts/cleaning_checks.py` | Computes `analysis/cleaning_flags_impact_{test,selection}.csv` and `analysis/cleaning_energy_source_vs_error.csv` |
| `scripts/rf_checks.py` | Computes `analysis/rf_d10_style_check.csv` and `analysis/rf_seed_noise.csv` |
| `documents/16_Temporal_Scope_Justification.md` | Detailed temporal scope rationale: verified training, validation and test boundaries; historical-data comparability; evidence supporting the retained model; limitations concerning winter and annual performance. |
| `documents/16a_Temporal_Scope_Reproduction.md` | File index, required inputs, reproduction commands and verification boundaries for the temporal scope contribution. |
| `scripts/verify_temporal_scope.py` | Read-only verification of temporal coverage, split membership and input integrity; exploratory historical-profile comparison. |
| `analysis/temporal_scope/` | Generated coverage, split, energy-source, monthly and historical-profile evidence tables, together with the verification log. |
| `documents/17_Model_Justification_Blend_v1.3.pdf` | Final model (Blend v1.3): numbers, selection, how the blend works, alternatives, weaknesses, likely questions |
| `documents/18_GBM_Justification.pdf` | GBM v1.3 (part of the Blend): why it was built, decisions with reason, evidence, alternative and weakness; test result; why it is not the final model; what it adds to the Blend; numbers to retire; if we did it again |
| `documents/19_ChronosGBM_Justification.pdf` | ChronosGBM v1.3 (GBM with Chronos-Bolt inputs, part of the Blend): same structure; lost the D10 tie-break at +1h and +6h |
| `documents/20_Chronos_Bolt_Justification.pdf` | Chronos-Bolt v1.3 (pretrained, zero-shot; largest part of the Blend and its fallback): same structure; size/context search; normal range |
| `documents/21_Linear_Regression_Justification.md` | Linear regression (Model 1): build decisions with reason, evidence, alternative and weakness; test result; why it is not the final model |
| `scripts/gbm_contribution_check.py` | Computes `analysis/gbm_contribution_test.csv` (Blend with and without the GBM on the test week, Task 6 scoring code) and `analysis/gbm_validation_recompute.csv` (GBM v1.3 validation scores from the stored forecasts) |
| `documents/22_Model_Comparison_Justification.md` | Model comparison (Task 6): how 11 models built on two dataset versions were made comparable and checked; every decision with reason, evidence, alternative and weakness; robustness of the result (bootstrap block length and seed, Diebold–Mariano, blend weights, days won, rank stability); likely questions |
| `documents/23_Dash_Dashboard_Justification.md` | Dash dashboard: every design decision (Dash vs Energy Watch, users and pages, frozen model, forecast interval, anomaly rule and defaults, levels, injection test, costs and CO₂, data quality, base load, live forecast and updates) with reason, evidence, alternative and weakness; errors found in the app and the user guide; likely questions. Detailed register: `Sprint4_Task3_UX_Dash/documents/02_Assumptions_and_Decisions_Dash.md` |
| `scripts/model_comparison_checks.py` | Computes `analysis/model_comparison/` (verification checks and robustness of the Task 6 comparison) |
| `analysis/model_comparison/` | `verification_checks.csv`, `robust_block_seed.csv`, `robust_diebold_mariano.csv`, `robust_blend_weights.csv`, `robust_days.csv`, `robust_selection.csv` |

Run from the repository root: `python Final_Evidence/scripts/ashrae14_by_level.py` (needs pandas, numpy) and `python Final_Evidence/scripts/regime_comparison.py` (needs `CLEAN DATA all zones.zip` in the root). `python Final_Evidence/scripts/cleaning_checks.py` needs pandas, numpy, scipy, pyarrow and `CLEAN DATA all zones.zip` in the root. `python Final_Evidence/scripts/rf_checks.py` needs pandas. `python Final_Evidence/scripts/gbm_contribution_check.py` needs pandas, numpy and pyarrow. `python Final_Evidence/scripts/model_comparison_checks.py` needs pandas, numpy and scipy.
