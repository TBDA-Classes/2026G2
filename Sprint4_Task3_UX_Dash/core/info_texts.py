"""Explanations shown in the (i) pop-ups next to every chart, table and indicator of the dashboard.

Key = the title shown on screen (or its beginning). Each text says what is shown, how to read it and how it is
computed. Keep them short: they open in a small pop-up.
"""

INFO = {
    # ---------------------------------------------------------------- Overview
    "Typical error": "Official mean absolute error (MAE) of Blend v1.3 on the test week (29 Sep – 5 Oct 2025): on "
                     "average, how many Wh the forecast is away from the measured value, per circuit and hour. The "
                     "95% confidence interval comes from a 24-hour block bootstrap. Lower is better.",
    "Forecast health": "Share of measured hours that fall inside the forecast interval, against the level chosen in "
                       "Settings (black marker). Green = close to the level (the model behaves as expected); amber/red "
                       "= more hours outside than expected, so look at the anomalies. Below: number of anomalies by "
                       "level.",
    "Measured energy": "Total energy measured on the hours with a valid reading, all selected circuits, in the period "
                       "chosen in Settings. The note says the share of circuit-hours that have a valid reading.",
    "Energy cost (est.)": "Measured energy × the price of its tariff period (peak / standard / off-peak, set in "
                          "Settings). An estimate: the prices are assumptions until UPM's real tariff is known.",
    "Extra energy in spikes": "Energy above the forecast during spikes (hours above the forecast interval). Its cost "
                              "uses the tariff price of each hour; CO₂ uses the factor in Settings.",
    "Drops below forecast": "Number of drops: periods where a circuit used clearly less than the forecast interval. "
                            "They cost nothing extra but can mean equipment off, a tripped breaker, an outage or a "
                            "meter problem.",
    "Energy per day by tariff period": "Bars: measured energy per day, split into off-peak (pale blue), standard (blue) "
                                       "and peak (violet) hours. Dotted line: the energy the model forecast for that "
                                       "day. ⚡ = days with critical anomalies. Hover a bar for the exact kWh.",
    "Biggest anomalies": "The four anomalies with the largest deviation from the forecast (kWh, positive for spikes, "
                         "negative for drops). Click one to open its full story on the Anomalies page.",
    "How to read a forecast": "Short definitions of the three ideas used everywhere: horizon (how far ahead), energy in "
                              "Wh per hour, and the error (MAE).",
    # ---------------------------------------------------------------- Live forecast
    "Latest data and forecast": "Hourly total of the selected circuits. Dark line + grey area = measured; thin blue = "
                                "the forecast made at the time; NOW = end of the last measurement; blue dashed line "
                                "with dots = forecast ahead (1 point for +1 h, 6 for +6 h, rest of the day for "
                                "day-ahead). ▲/▼ (day-ahead) = spikes and drops, coloured by level. Band (switch) = "
                                "90% interval. Drag to zoom, double-click to reset.",
    "Last measured hour": "Energy measured in the last hour that has data, summed over the selected circuits. Not shown "
                          "if one of the circuits has no valid reading in that hour.",
    "Next hour": "Forecast for the first hour after the last measurement (+1 h model), selected circuits summed.",
    "Next 6 hours": "Total forecast for the six hours after the last measurement. Each hour was forecast 6 hours "
                    "earlier (+6 h model).",
    "Rest of today": "Total forecast from the last measurement to midnight, from the day-ahead forecast issued at "
                     "00:00 of today.",
    "Highest upcoming hour": "The future hour with the highest forecast, and its value.",
    "Error on the latest days": "Mean absolute error of the chosen horizon on the latest days (after the test week): "
                                "data never used to build or choose the model, so an honest check.",
    "Upcoming hours": "One row per circuit and future hour: when the forecast was issued and its value (plus low/high "
                      "limits if the interval is switched on). Click a header to sort.",
    "Compute the live forecast": "Runs the frozen model on the newest data: Chronos-Bolt live, the two saved gradient-"
                                 "boosting models and the frozen blend weights. Nothing is retrained.",
    "Storey 1 at a glance": "One tile per zone: forecast energy for the rest of today (day-ahead) and the energy "
                            "measured in the last hour. Click a tile to select that zone.",
    # ---------------------------------------------------------------- Anomalies
    "Deviation map": "Rows = circuits (grouped by zone), columns = hours. Colour = how far the measurement is from the "
                     "forecast, in interval widths: grey = as expected, orange = above, blue = below (capped at ±3). "
                     "Black outlined squares = anomaly hours: click one to open it. Blank = no valid reading.",
    "Anomaly list": "One row per anomaly: ID (S = spike, D = drop), level, time, circuit, duration, deviation in kWh, "
                    "extra cost (spikes only) and the share of hours at night/weekend. Ordered by level then size; "
                    "click a row for details, use CSV to export.",
    "Why hours were excluded": "Circuit-hours left out of every calculation because the measurement failed a data-"
                               "quality rule of dataset v1.2 (catch-up after a gap, hour cut by an outage, energy above "
                               "what the power allows, other rules).",
    "Measured hours per circuit": "Share of hours with a valid reading for each circuit. Fewer hours = less reliable "
                                  "scores and anomalies for that circuit (SE and SW have the most gaps).",
    "Excluded periods": "Every run of excluded hours: from, to, circuit, number of hours and the reason.",
    # ---------------------------------------------------------------- Energy & costs
    "Energy": "Total measured energy in the period and the average per day, for the selected zones and types.",
    "Estimated cost": "Measured energy priced by tariff period, and how much of the cost falls in peak hours.",
    "Extra cost of spikes": "Cost of the energy above the forecast in spikes, and its share of the total cost.",
    "Monthly bill, projected": "The period's cost and CO₂ scaled to 30 days. Indicative only: the data cover a few "
                               "weeks of late summer and autumn.",
    "Where the energy goes": "Treemap: each rectangle's area is its share of the energy, coloured by zone. Click a zone "
                             "to see its circuits; click the top bar to go back. Percentages are of the whole floor.",
    "Cost per day by tariff period": "Estimated € per day, split into off-peak, standard and peak hours. Weekends are "
                                     "all off-peak, so they are cheaper per kWh.",
    "Weekly rhythm": "Heatmap of weekdays × hours (Madrid time). 'Average use': mean energy per hour; darker = more. "
                     "'Extra in spikes': total energy above the forecast in that weekday and hour — repeated dark cells "
                     "point to a schedule problem.",
    "Base load vs average use": "For each circuit: black diamond = base load (10th percentile of hourly use, the level "
                                "it never goes below); blue dot = average use. Diamond close to the dot = almost "
                                "constant load. Log scale so large and small circuits fit; data 19 Aug – 13 Oct 2025.",
    "What if the base load were lower?": "Move the slider to see the yearly energy, € and CO₂ saved if the base load of "
                                         "the selection were cut by that share, priced at the average of standard and "
                                         "off-peak prices.",
    # ---------------------------------------------------------------- Forecast replay
    "Forecast energy": "Total forecast energy of the selected circuits in the chosen week (or day).",
    "Peak forecast hour": "The hour with the highest forecast total in the selection, and its value.",
    "Error on this selection": "Mean absolute error over the circuit-hours of this selection that have a valid "
                               "measurement. Official scores (common hours of all models) are on the Performance page.",
    "Bias": "Average of (forecast − measured). Negative = the model forecasts too little; positive = too much.",
    "Measured vs forecast energy": "Hour by hour for the chosen week or day: measured (dark line, grey area) vs forecast "
                                   "(blue). With the switch on, the blue band is the 90% interval. Gaps = hours where a "
                                   "selected circuit has no valid reading.",
    "Forecast energy by circuit": "Forecast kWh of each selected circuit over the period, coloured by zone.",
    "Daily profile": "Average measured and forecast energy for each hour of the day over the period: the 'typical "
                     "day'. Where the lines separate, the model is systematically off at that hour.",
    "Hour-by-hour playback": "Press Play to replay the week hour by hour (1×, 3×, 8×) or drag the slider: measured "
                             "energy appears against the day-ahead forecast and interval; ▲ spikes and ▼ drops are "
                             "flagged when they start, with running totals and a clickable feed.",
    "Forecast table": "One row per circuit and hour: issue time, forecast, measured, error (and interval limits when "
                      "switched on). Sort, filter and download as CSV.",
    # ---------------------------------------------------------------- Performance
    "Score cards": "Official Task 6 scores of the final model for each horizon: MAE with its 95% CI, RMSE (punishes "
                   "big errors), scaled MAE (error ÷ circuit's average use — the team's selection metric), WAPE (total "
                   "error ÷ total energy) and the number of circuit-hours scored.",
    "Error by zone": "MAE per zone for the chosen horizon, with the 95% confidence interval as a whisker. A wide "
                     "whisker = few hours or a few very large errors.",
    "Error by circuit and horizon": "MAE of each circuit at each horizon; darker blue = larger error. Rows sorted by the "
                                    "day-ahead error.",
    "Error by hour of day": "MAE for each hour of the day (Madrid time) for the chosen horizon. Shaded dark bars = "
                            "night/early morning (00–08 h), where the model errs most.",
    "Forecast interval at each level": "How often the measurement fell inside the forecast interval at 80, 90 and 95%. "
                                       "A good interval holds about its nominal share. Validation is in-sample (the "
                                       "interval was calibrated there); the test week is the honest check.",
    "Prediction interval check": "The 90% interval (Chronos-Bolt 10–90% band calibrated per circuit on the validation week) by horizon on the test week: share of measured hours inside, target "
                                 "and mean width. Experimental until validated by Pole 1.",
    # ---------------------------------------------------------------- Detection test
    "Detection rate by size and duration": "Share of injected anomalies the dashboard found, all 16 circuits and all "
                                           "start hours pooled. Rows = size of the injected change (% of the circuit's "
                                           "mean hourly use), columns = how long it lasted. Darker = found more often.",
    "Alerts vs detection: the trade-off": "Each dot is one detector setting. Right = more anomalies per day on the real "
                                          "data (more to check); up = more injected +100%/6 h anomalies found. A good "
                                          "setting is high and not too far right. Click a dot to look at that setting.",
    "Detection rate by circuit": "For each circuit, the share of injected anomalies of the chosen size that were found. "
                                 "Large, stable circuits reach 100%; tiny circuits (hand dryers, emergency lights) "
                                 "cannot, because their whole use is below the minimum deviation.",
    "Smallest extra use the dashboard can see": "Median extra energy (Wh in one hour) a circuit must use before a spike "
                                                "is flagged. It must clear both the top of the forecast interval and the "
                                                "minimum deviation: blue bars are limited by the interval (uncertain "
                                                "forecast), grey by the minimum deviation. Log scale.",
    "Anomalies per day (real data)": "Number of anomalies on the unmodified evaluation weeks with this setting: the "
                                     "workload a user would see.",
    "Found:": "Share of injected anomalies of that size and duration that the detector found, all circuits pooled.",
    "Known real event": "Check on the only confirmed real event: NE|HVAC left on, 3 Oct 2025 11:00–14:00.",
    "Cases tested": "Number of injected cases for this setting (circuits × start hours × sizes × durations × timing).",
    # ---------------------------------------------------------------- Limitations / model
    "NW | Plugs & Sockets: night consumption keeps rising": "Mean night consumption (00–09 h) of this circuit in the "
                                                            "training, validation and test periods. It doubled after "
                                                            "the period the model learned from, which explains most "
                                                            "night errors.",
    "Blend weights by horizon": "Share of each component in the final forecast, per horizon. Chronos-Bolt always has at "
                                "least half the weight, more the further ahead.",
    "Run the frozen model": "Recomputes a week's forecasts from the saved model files (no retraining) and checks they "
                            "equal the stored Task 6 forecasts.",
    "Add new measurements": "Rebuilds the hourly dataset from a newer export with the team's v1.2 cleaning rules and "
                            "refreshes the live forecast from the new last measurement. The frozen dataset is never "
                            "changed.",
    "Data and evaluation": "Reminder of the data, periods, horizons and metrics behind every number.",
}


def info_for(title: str) -> str | None:
    if not title:
        return None
    if title in INFO:
        return INFO[title]
    for k, v in INFO.items():
        if title.startswith(k):
            return v
    return None
