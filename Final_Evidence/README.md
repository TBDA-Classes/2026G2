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
| `documents/12_Data_Cleaning_Justification.md` | Data cleaning: every decision with reason, evidence, rejected alternative and weakness; results in numbers; open points; likely questions (Émile) |
| `documents/12a_Cleaning_Checks.md` | Data cleaning checks: impact of the 5 sensors flagged by the cleaning on test results and model selection; counter-direct share vs error and coverage (Émile) |
| `scripts/ashrae14_by_level.py` | Computes `analysis/ashrae14_by_level_{test,validation}.csv` |
| `scripts/ashrae14_traffic_light.py` | Computes `analysis/ashrae14_traffic_light_test.csv` |
| `scripts/regime_comparison.py` | Computes the regime comparison and the exploratory profile test |
| `scripts/cleaning_checks.py` | Computes `analysis/cleaning_flags_impact_{test,selection}.csv` and `analysis/cleaning_energy_source_vs_error.csv` |

Run from the repository root: `python Final_Evidence/scripts/ashrae14_by_level.py` (needs pandas, numpy) and `python Final_Evidence/scripts/regime_comparison.py` (needs `CLEAN DATA all zones.zip` in the root). `python Final_Evidence/scripts/cleaning_checks.py` needs pandas, numpy, scipy, pyarrow and `CLEAN DATA all zones.zip` in the root.
