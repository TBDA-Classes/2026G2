# Final-phase evidence pack

TBDA Group 2 · CeDInt Storey 1 · 17 Nov 2026 · **Authors: Jules (main author), Claude (co-author)**

Evidence prepared for the final presentation (30 Nov) and the Moodle hand-over (14 Dec).

| File | Content |
|---|---|
| `documents/08_Scope_Decision_2025_Only.md` | Why the model is trained on 2025 only; regime differences; exploratory test; protocol for a combined model |
| `documents/09_ASHRAE14_Assessment.md` | ASHRAE Guideline 14 reference check by level, teacher targets |
| `documents/10_Evidence_Map.md` | Every claim of the presentation → proving file; numbers to retire |
| `documents/11_Deliverables_Index_Dash.md` | Deliverables index and demo plan with Dash as main dashboard |
| `scripts/ashrae14_by_level.py` | Computes `analysis/ashrae14_by_level_{test,validation}.csv` |
| `scripts/regime_comparison.py` | Computes the regime comparison and the exploratory profile test |

Run from the repository root: `python Final_Evidence/scripts/ashrae14_by_level.py` (needs pandas, numpy) and `python Final_Evidence/scripts/regime_comparison.py` (needs `CLEAN DATA all zones.zip` in the root).
