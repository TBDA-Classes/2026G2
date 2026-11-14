# Sprint 4 — Task 3: UX (Dash dashboard)

An interactive web dashboard for the **final model, Blend v1.3**. It shows hourly energy forecasts for the 16
circuits of CeDInt Storey 1 and lets the user choose a **zone**, a **time horizon** and, optionally, a **type of
consumption**. It shows the **latest measured data with the forecast ahead** (Live forecast), replays the model on
the evaluation weeks, and shows the model's **performance indicators** and **known limitations**. It **runs the
frozen model** itself.

This is a second interface, separate from the Streamlit app (`UX_V3.py`). It is built with Dash and
Dash Bootstrap Components.

## How to run it

### Quick start: double-click

| Computer | Double-click |
|---|---|
| Windows | `Sprint4_Task3_UX_Dash/Start_dashboard.bat` |
| macOS / Linux | `Sprint4_Task3_UX_Dash/Start_dashboard.command` |

The launcher does everything by itself: it uses the repository that contains the app folder, creates a `.venv`
with Python 3.11+ if there is none, installs the packages the first time only, starts the app and opens the browser
at http://127.0.0.1:8050. Close the terminal window (or press `Ctrl+C`) to stop it.

- **Get the whole repository** (`git clone https://github.com/TBDA-Classes/2026G2.git` or GitHub Desktop): the app
  reads the model (`TBDA_v1.3_ChronosGBM_29-10`) and the Task 6 results (`Task6_rev0_03-11`) next to its folder.
- **Python 3.11 or newer** must be installed ([python.org](https://www.python.org/downloads/); on Windows tick
  "Add python.exe to PATH").
- The first start takes a few minutes (package install, about 1 GB with Chronos). Later starts take seconds.
- **macOS, if the double-click is refused** (this happens when the repository was downloaded as a ZIP from the
  browser, or the file lost its "executable" flag):
  - "cannot be opened / Apple cannot verify": System Settings → Privacy & Security → **Open Anyway** (once), or
    right-click the file → **Open** → **Open**;
  - "you do not have permission": run once `chmod +x Sprint4_Task3_UX_Dash/Start_dashboard.command` from the
    repository folder;
  - always works: `bash Sprint4_Task3_UX_Dash/Start_dashboard.command`.
- **Windows, if SmartScreen warns** ("Windows protected your PC"): **More info** → **Run anyway** (once).

### By hand

The app reads files that are already in the repository, so run it from a clone of `TBDA-Classes/2026G2`.

```bash
cd 2026G2                                  # repository root
python3 -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r Sprint4_Task3_UX_Dash/requirements.txt
python Sprint4_Task3_UX_Dash/app.py
```

Then open **http://127.0.0.1:8050** in a browser. Stop the app with `Ctrl+C`.

- **Python 3.11 or newer** is needed for scikit-learn 1.9.1. This is the version the frozen GBM files were saved
  with, and only the **Run model** and **live forecast** buttons need it. The other pages work without it.
- **For the live forecast** also install Chronos-Bolt:
  `pip install -r Sprint4_Task3_UX_Dash/requirements-live.txt`. Then press **Compute / update live forecast** on the
  Live forecast page. The first run downloads the Chronos-Bolt weights (tiny + base, about 250 MB).
- The folder `Sprint4_Task3_UX_Dash` must be **inside** `2026G2`. If it is not, every page shows which files are
  missing, and so does the terminal at start-up. If the app folder is moved out of the repository, set
  `TBDA_REPO=/path/to/2026G2`.
- `python Sprint4_Task3_UX_Dash/app.py --debug` shows Dash's error panel in the browser.

## 1. Users and their needs

| User | Who they are | What they need | Where in the app |
|---|---|---|---|
| **Building energy manager** | Plans and reports the building's consumption and looks for savings | Tomorrow's consumption per wing, where and when the big loads are, how far to trust the numbers | Live forecast (day-ahead, by zone), Performance |
| **Maintenance / facility technician** | Runs HVAC, lighting and the IT rack day to day | What a circuit should use in the next hours, whether a measurement is far from the forecast, which circuits behave unusually | Live forecast (+1 h / +6 h, one consumption type), Known limitations |
| **Researcher / project evaluator** | Checks how the model was built and how good it is | Which model is used and why, the error and its uncertainty, the known weaknesses | Performance, The model, Known limitations |

Design choices that follow from these needs:

- **Plain language.** Every metric is explained on the page where it appears ("on average, how many Wh the
  forecast is away from the measured value").
- **Madrid local time everywhere.** The model works in UTC; users think in local time.
- **Consumption type is optional.** If no type is chosen, all circuits of the zone are shown and added up.
- **Limitations sit next to the numbers.** Each one has an impact level (icon + label) and a "what it means for
  you" line.
- **Uncertainty is visible.** Official scores carry their 95% confidence intervals. Prediction intervals are
  clearly marked "experimental" until Pole 1 validates them.

## 2. Pages

| Page | Content |
|---|---|
| **Overview** | Purpose, headline error per horizon, the three users and the pages they need, how to read a forecast |
| **Live forecast** | The latest measured data (up to Mon 13 Oct 2025, 16:00 Madrid) and the forecast ahead: next hour (+1 h), the next six hours (+6 h), the rest of today (day-ahead). Same controls as the replay. Shows 4 indicators (last measured hour, upcoming energy, highest upcoming hour, error since 6 Oct), a chart with a "now" line and a table of the upcoming hours |
| **Anomalies** | Hours where the measured energy left the forecast interval: ▲ spikes (extra energy and cost) and ▼ drops (possible faults or outages), graded Critical / Moderate / Minor. A deviation map (every circuit × every hour, coloured by how far it is from the forecast), a sortable list with CSV, and a side panel per anomaly: the story, kWh and € by tariff period, how often it happened on that circuit, a chart of the day before and after, where to start looking, Previous/Next and Acknowledge. A "Data quality" tab shows why hours were excluded and how many hours each circuit has |
| **Energy & costs** | Energy, estimated cost by tariff period (peak / standard / off-peak), extra cost of the spikes and the projected monthly bill; a treemap of where the energy goes (click to zoom into a zone); cost per day by tariff period; the weekly rhythm (weekday × hour); base load vs average use per circuit; and a what-if slider: savings per year if the base load were cut |
| **Settings** (top bar) | Period (evaluation weeks or latest data), forecast-interval level (80 / 90 / 95 %), minimum deviation to flag, the three tariff prices and the CO₂ factor. Every page updates at once |
| **Forecast replay** | Also has an "Hour-by-hour playback": play/pause, 1× / 3× / 8× speed, a time slider, the forecast interval, spikes and drops flagged as time passes and running totals. Controls: zone, horizon (+1 h / +6 h / day-ahead), optional consumption type, period (test / validation week), day, interval switch. Outputs: 4 indicators (forecast energy, peak hour, error, bias), measured-vs-forecast chart, energy by circuit, daily profile, hourly table with CSV download |
| **Performance** | Official Task 6 scores of Blend v1.3, with 95% bootstrap CIs: MAE, RMSE, scaled MAE and WAPE per horizon; MAE by zone; heatmap by circuit × horizon; MAE by hour of day; prediction-interval check |
| **Known limitations** | 7 limitations ranked by impact, with evidence charts (NW Plugs & Sockets night drift, measured hours per circuit) |
| **The model** | How Blend v1.3 works, its weights per horizon, the data split, and the **Run model** button |

## 3. Connection to the final model

- **Stored forecasts.** By default the app reads the frozen forecasts of Blend v1.3 saved in Task 6:
  `Task6_rev0_03-11/results/predictions/ML_Blend_v1.3_{test,validation}_predictions.csv`.
- **Running the model.** On **The model** page, the **Run model** button starts `model_engine.py` in a separate
  process. It does the following:
  - loads dataset v1.2 and the two frozen gradient-boosting parts (`task8_v1.3_*.joblib`, `hybrid_v1.3_*.joblib`);
  - takes the frozen Chronos-Bolt forecasts from their caches (`chronos_cache_v1.3*.parquet`), so torch is not
    needed;
  - blends the three with the frozen weights in `blend_frozen_config_v1.3.json`.

  Nothing is retrained. The recomputed forecasts are saved in `Sprint4_Task3_UX_Dash/cache/` and the Forecast replay page
  switches to them.
- **Check (11 Nov 2026).** Recomputed vs stored, test and validation: 8,064 forecasts each, largest difference
  5.7e-14 Wh (identical). It takes about 2 s per week.
- **Model choice.** The model is Blend v1.3 because Sprint 4 Task 2 found that outdoor temperature does not
  improve it.

## 3b. Live forecast (`live_engine.py`)

- **Data.** The repository's dataset v1.2 runs to **13 Oct 2025, 14:00 UTC** (16:00 Madrid). The week after the test
  week (6–13 Oct, split `outside`) was never used to build, choose or score any model, so it is new data.
- **How the forecasts are made.** The frozen Blend v1.3 makes them exactly as it would have in real time, issued one
  hour after the last measurement:
  - **+1 h:** every hour up to the next hour;
  - **+6 h:** every hour up to 6 hours past the data, each issued 6 h earlier;
  - **day-ahead:** every day issued at 00:00 Madrid, including today. The rest of today is a forecast.
  - Tomorrow's day-ahead forecast is not shown. It is issued at midnight, and the data stop at 16:00.
- **Chronos-Bolt runs live.** It uses the frozen size, context and point forecast per horizon. The weights are read
  from `TBDA_v1.3_ChronosGBM_29-10/weights/` if present, otherwise from the official Hugging Face release, and
  their SHA-256 is compared with the one recorded when the model was frozen. The two GBM parts and the weights are
  the frozen ones.
- **Self-test:** `python live_engine.py --check`.
  - It rebuilds the test week with the live task builder and the frozen Chronos cache.
  - The live task builder equals `forecast_tasks` for every horizon.
  - The Blend forecasts equal the stored Task 6 forecasts: 8,064 rows, max difference 2e-13 Wh.
- **Missing forecasts.** Some SE/SW circuit-hours have no forecast. The +6 h Chronos part reads only the last 24 h,
  and those circuits had longer measurement gaps on 7–8 Oct. This is reported on the page.

## 3c. Anomalies and costs (`anomalies.py`)

Built on the app's own forecast interval (section 4).

- **Forecast:** Blend v1.3 day-ahead.
- **Interval:** the forecast interval of section 4, at the level chosen in Settings (80 / 90 / 95 %), calibrated per
  circuit on the validation week. That week is therefore in-sample; the test week and the latest data are not.
- **Anomaly hour:** measured value outside the interval and at least the minimum deviation away from the forecast
  (default 25 Wh). Above the interval = **spike**; below = **drop**. Consecutive hours of one circuit in the same
  direction form one anomaly.
- **Level:**
  - **Critical:** at least 1 kWh away from the forecast, or 6 hours or longer;
  - **Moderate:** at least 0.25 kWh, or 3 hours or longer;
  - **Minor:** everything else.
- **Cost:** each extra kWh of a spike is priced by the tariff period of its hour (Spanish 2.0TD periods: peak on
  weekdays 10–14 h and 18–22 h, standard 8–10, 14–18 and 22–24 h, off-peak at night, weekends and holidays). The
  prices and the CO₂ factor are assumptions, editable in Settings.
- **Base load:** the 10th percentile of each circuit's hourly use, 19 Aug – 13 Oct 2025.
- **Default result (evaluation weeks):** 80 anomalies (54 spikes, 26 drops; 19 critical), and the 90 % interval holds
  90.3 % of the measured hours.
- **Data quality:** hours without a valid measurement (team dataset v1.2 rules) are excluded everywhere and listed
  with their reason.

## 3d. Adding new days (scalability)

The model stays frozen; the data can grow.

1. Export the newest cleaned data in the format the team already uses: the zip or folder with `NE/ NW/ SE/ SW/` and
   `clean_Storey1_<zone>_CLEAN_DATA.csv`, or one CSV for all zones.
2. On **The model** page, write its path in **Add new measurements** and press **Update data & forecast**. Or from
   the terminal:
   ```bash
   python Sprint4_Task3_UX_Dash/engines/update_data.py "CLEAN DATA all zones.zip"
   ```
   followed by "Compute / update live forecast".
3. `update_data.py` runs the team's own pipeline (`task7_pipeline.py`, dataset v1.2 rules) and writes
   `Sprint4_Task3_UX_Dash/data_live/Storey1_hourly_v1.2.parquet`. The frozen dataset of the repository is never
   touched.
4. The live forecast, the "Latest data" period, the anomalies and the data-quality checks then use the newest data,
   starting from the new last measurement and showing the latest 8 days.

**Check:** rebuilt from `CLEAN DATA all zones.zip`, the dataset is identical to the frozen one (21,456 rows, same
values, validity flags and splits). The pipeline needs the `holidays` package (in `requirements.txt`).

## 3e. Detection test (injected anomalies)

How well does the dashboard find a fault? `injection_test.py` adds artificial anomalies to the real data of the two
evaluation weeks and checks whether the anomaly detector of section 3c flags them. It tests about 321,000 cases in about
6 seconds: 16 circuits × every valid start hour × spikes of +25/50/100/200% and drops of −50/−100% of the circuit's
mean use × 1, 3 and 6 hours × 5 detector settings. The results are shown on the **Performance** page
("Detection test") and explained in [`documents/04_Detection_Validation_Dash.md`](documents/04_Detection_Validation_Dash.md),
with the same structure and file names as the Energy Watch test, plus the suffix `_dash`.

```bash
python Sprint4_Task3_UX_Dash/engines/injection_test.py      # writes Sprint4_Task3_UX_Dash/analysis/injection_*_dash.csv
```

Headline (default setting, 90% interval, 25 Wh): an appliance left on at double its usual use for 6 hours is found in
**45.4%** of cases; a circuit switched off for 6 hours in **46.1%**; 4.8 anomalies per day on the real data; the known
real event (NE|HVAC left on, 3 Oct) is found at every setting. A like-for-like comparison with Energy Watch on the
same cases is in [`documents/Injection_Tests_Explained.md`](documents/Injection_Tests_Explained.md). Large, stable circuits are found 100% of the time; the
tiny ones (hand dryers, emergency lights) cannot be checked at this minimum deviation.

## 4. Prediction intervals (pending Pole 1)

Task 3 asks for prediction intervals "if validated by Pole 1". Until then the switch is **off by default** and the
intervals are labelled **experimental**.

- **Method (since 14 Nov 2026): Chronos-Bolt band, calibrated per circuit** (conformalized quantile band, CQR).
  - Start from the Chronos-Bolt v1.3 10–90% band of the frozen configuration (Chronos is one of the three parts of
    Blend v1.3), widened so that it always contains the Blend forecast. This band follows the daily shape: narrow at
    night, wide when the building is in use.
  - For each horizon and circuit, compute on the **validation week** the score `max(lower − actual, actual − upper)`
    and take its conformal quantile `Q` at the chosen level (`ceil((n+1)·level)`-th smallest).
  - Interval = `[max(0, lower − Q), upper + Q]`, always containing the forecast. `Q` can be negative, which narrows a
    band that was too wide.
  - Circuits with fewer than 30 validation hours use the horizon-wide value scaled by the circuit's training mean.
    Rows without Chronos quantiles (an old live file) fall back to the previous method: symmetric split-conformal
    `forecast ± q`, with `q` the conformal quantile of |error|. `INTERVAL_METHOD = "abs"` in `core/settings.py`
    restores the previous method everywhere.
  - When several circuits are added up, the distances to the limits are added too, which is conservative.
- **Why it changed.** The same-case comparison with Energy Watch (`documents/Injection_Tests_Explained.md`) showed that the symmetric
  interval had the right total coverage but was uneven circuit by circuit (69% on NW HVAC, 100% on SE Plugs). The
  calibrated band keeps the total and evens out the circuits: mean distance from the nominal 90% per circuit on the
  test week drops from 6.6 to 3.9 points, and the anomalies on real data drop from 5.7 to 4.8 per day.
- **Check on the test week** (never used for calibration). The target is 90%.

  | Horizon | Test hours inside | Mean width | Previous method |
  |---|---|---|---|
  | +1 h | 89.9% | 97 Wh | 90.7%, 115 Wh |
  | +6 h | 91.4% | 159 Wh | 87.9%, 161 Wh |
  | day-ahead | 90.7% | 171 Wh | 89.6%, 168 Wh |

- **After Pole 1 validates the intervals,** set `INTERVALS_VALIDATED = True` in `settings.py`. The switch then
  starts on, and the label changes to "validated".

## 5. Sources of the numbers

| Shown in the app | Source |
|---|---|
| Forecasts and measured values | Task 6 prediction files, or the recomputed ones (see section 3) |
| MAE / RMSE / scaled MAE / WAPE with 95% CI, by zone, circuit and hour | `Task6_rev0_03-11/results/task6_{test,validation}_16circuits/` (`metrics_with_CI.csv`, `metrics_per_circuit.csv`, `error_by_hour_of_day.csv`): official scores on the common hours of the model comparison |
| "Error on this selection" and "Bias" (Forecast replay page) | Computed live from the forecasts, on every hour of the selection that has a measurement. It can differ slightly from the official scores, which use the hours common to all models |
| Known limitations | Task 6 `RESULTS.md`, Sprint 4 Task 1 (diagnosis) and Task 2 (temperature) reports |

## 6. Files

The app has three parts: `app.py` (the dashboard), `core/` (modules it imports) and `engines/` (scripts it runs in a
separate process, which can also be run by hand). It works in the repository clone and in a minimal package
(`app/`, `model/`, `task6_results/`, `outputs/`): `core/settings.py` detects which one it is in.

| File | Content |
|---|---|
| `app.py` | Layout, pages and callbacks (start the dashboard with this file) |
| `core/data_layer.py` | Reads forecasts and scores, prediction intervals, aggregation, runs the model |
| `engines/model_engine.py` | Runs the frozen Blend v1.3 on the evaluation weeks (called by the app, or by hand: `python model_engine.py test out.csv`) |
| `core/anomalies.py` | Forecast interval, spikes and drops, data quality, tariff costs, base load |
| `engines/update_data.py` | Rebuilds the hourly dataset from a newer export (scalability) |
| `engines/live_engine.py` | Live forecast on the latest data (Chronos-Bolt + frozen GBMs + blend); `--check` self-test |
| `engines/injection_test.py` | Detection test: injects spikes and drops and measures how many the dashboard finds |
| `analysis/` | Results of the detection test (`injection_*_dash.csv`: Energy Watch names + `_dash`), shown on the Performance page |
| `documents/04_Detection_Validation_Dash.md` | Method, results and limits of the detection test |
| `documents/Injection_Tests_Explained.md` | The two injection tests explained and compared with Energy Watch |
| `Start_dashboard.command` / `Start_dashboard.bat` | One-click launcher for macOS-Linux / Windows (venv, packages, app, browser) |
| `core/info_texts.py` | Texts of the (i) info pop-ups |
| `requirements-live.txt` | Extra packages for the live forecast (torch, chronos-forecasting) |
| `core/settings.py` | Paths, labels, colours, interval settings |
| `assets/style.css` | Styles |
| `requirements.txt` | Python packages |
