from pathlib import Path
import pandas as pd

# Find the CSV in the same folder as this script.
folder = Path(__file__).resolve().parent
file = folder / "ML_Blend_v1.3_validation_predictions.csv"

df = pd.read_csv(file)

print("File loaded successfully!")
print("Number of rows:", len(df))

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head().to_string(index=False))

# Convert target timestamps from UTC to Madrid local time.
df["target_utc"] = pd.to_datetime(df["target_hour"], utc=True)
df["target_madrid"] = df["target_utc"].dt.tz_convert("Europe/Madrid")

# Extract local calendar information.
df["hour_local"] = df["target_madrid"].dt.hour
df["date_local"] = df["target_madrid"].dt.date
df["weekday_number"] = df["target_madrid"].dt.dayofweek
df["is_weekend"] = df["weekday_number"] >= 5

# Positive error = overprediction; negative error = underprediction.
df["error_Wh"] = df["predicted_Wh"] - df["actual_Wh"]
df["absolute_error_Wh"] = df["error_Wh"].abs()

# Exclude missing actual values from error calculations.
valid = df.dropna(subset=["actual_Wh", "predicted_Wh"]).copy()

print("\n--- DATA CHECK ---")
print("Total rows:", len(df))
print("Valid rows for error analysis:", len(valid))
print("Rows excluded from error calculations:", len(df) - len(valid))

print("\n--- PREPARED DATA SAMPLE ---")
columns = [
    "zone",
    "horizon_h",
    "target_madrid",
    "actual_Wh",
    "predicted_Wh",
    "error_Wh",
]
print(valid[columns].head(5).to_string(index=False))


# Summarise errors by forecasting horizon and Madrid local hour.
hourly_errors = (
    valid.groupby(["horizon_h", "hour_local"])
    .agg(
        n_observations=("error_Wh", "size"),
        MAE_Wh=("absolute_error_Wh", "mean"),
        mean_error_Wh=("error_Wh", "mean"),
    )
    .reset_index()
)

print("\n--- ERRORS BY LOCAL HOUR AND HORIZON ---")
print(hourly_errors.round(3).to_string(index=False))

# Save the summary without changing the original predictions.
output_folder = folder / "outputs"
output_folder.mkdir(exist_ok=True)

hourly_errors.to_csv(
    output_folder / "errors_by_local_hour.csv",
    index=False,
)

print("\nSummary saved to outputs/errors_by_local_hour.csv")





import matplotlib.pyplot as plt

# Plot hourly MAE separately for each forecasting horizon.
horizon_labels = {
    1: "+1h",
    6: "+6h",
    24: "Day-ahead",
}

fig, ax = plt.subplots(figsize=(10, 5))

for horizon, label in horizon_labels.items():
    subset = hourly_errors[
        hourly_errors["horizon_h"] == horizon
    ].sort_values("hour_local")

    ax.plot(
        subset["hour_local"],
        subset["MAE_Wh"],
        marker="o",
        label=label,
    )

ax.set(
    title="Blend v1.3 — Hourly MAE on validation data",
    xlabel="Target hour — Europe/Madrid",
    ylabel="MAE (Wh)",
)
ax.set_xticks(range(24))
ax.grid(alpha=0.3)
ax.legend(title="Forecast horizon")

fig.tight_layout()
fig.savefig(output_folder / "hourly_mae_validation.png", dpi=200)
plt.close(fig)



# Summarise hourly errors separately for each circuit and horizon.
circuit_hourly_errors = (
    valid.groupby(["zone", "horizon_h", "hour_local"])
    .agg(
        n_observations=("error_Wh", "size"),
        MAE_Wh=("absolute_error_Wh", "mean"),
        mean_error_Wh=("error_Wh", "mean"),
        total_absolute_error_Wh=("absolute_error_Wh", "sum"),
    )
    .reset_index()
)

circuit_hourly_errors.to_csv(
    output_folder / "errors_by_circuit_and_hour.csv",
    index=False,
)

# Inspect which circuits contribute most to the day-ahead error
# at the hours highlighted by the overall plot.
for hour in [13, 15, 16]:
    subset = circuit_hourly_errors[
        (circuit_hourly_errors["horizon_h"] == 24)
        & (circuit_hourly_errors["hour_local"] == hour)
    ].copy()

    total_error = subset["total_absolute_error_Wh"].sum()

    subset["error_share_pct"] = (
        100 * subset["total_absolute_error_Wh"] / total_error
        if total_error > 0 else 0.0
    )

    top = subset.nlargest(5, "total_absolute_error_Wh")

    print(f"\n--- DAY-AHEAD: MAIN ERROR CONTRIBUTORS AT {hour:02d}:00 ---")
    print(
        top[
            [
                "zone",
                "n_observations",
                "MAE_Wh",
                "mean_error_Wh",
                "error_share_pct",
            ]
        ].round(2).to_string(index=False)
    )



    # Plot actual and predicted consumption for NW Plugs & Sockets.
# Use the full table so missing actual values remain visible as gaps.
circuit = "NW|Plugs & Sockets"

fig, axes = plt.subplots(
    3, 1,
    figsize=(13, 10),
    sharex=True,
    sharey=True,
)

for ax, (horizon, label) in zip(axes, horizon_labels.items()):
    subset = df[
        (df["zone"] == circuit)
        & (df["horizon_h"] == horizon)
    ].sort_values("target_madrid")

    ax.plot(
        subset["target_madrid"],
        subset["actual_Wh"],
        label="Actual",
        color="black",
        linewidth=1.5,
    )

    ax.plot(
        subset["target_madrid"],
        subset["predicted_Wh"],
        label="Predicted",
        color="tab:orange",
        linewidth=1.3,
    )

    ax.set_title(label)
    ax.set_ylabel("Hourly energy (Wh)")
    ax.grid(alpha=0.3)
    ax.legend()

axes[-1].set_xlabel("Target time — Europe/Madrid")

fig.suptitle(
    "NW Plugs & Sockets — Actual vs predicted — Validation",
    fontsize=14,
)
fig.autofmt_xdate()
fig.tight_layout(rect=[0, 0, 1, 0.96])

fig.savefig(
    output_folder / "nw_plugs_actual_vs_predicted_validation.png",
    dpi=200,
)
plt.close(fig)

print("\nNW Plugs plot saved successfully.")


# Analyse NW Plugs & Sockets during 00:00–05:59 Madrid time.
nw_night = valid[
    (valid["zone"] == "NW|Plugs & Sockets")
    & (valid["hour_local"] < 6)
].copy()

nw_night["is_underprediction"] = nw_night["error_Wh"] < 0

nightly_summary = (
    nw_night.groupby(["horizon_h", "date_local"])
    .agg(
        n_observations=("error_Wh", "size"),
        actual_mean_Wh=("actual_Wh", "mean"),
        predicted_mean_Wh=("predicted_Wh", "mean"),
        MAE_Wh=("absolute_error_Wh", "mean"),
        mean_error_Wh=("error_Wh", "mean"),
        underprediction_share=("is_underprediction", "mean"),
    )
    .reset_index()
)

nightly_summary["underprediction_pct"] = (
    100 * nightly_summary.pop("underprediction_share")
)

# Flag partial nights at the validation boundaries or with missing data.
nightly_summary["complete_6h_window"] = (
    nightly_summary["n_observations"] == 6
)

nightly_summary.to_csv(
    output_folder / "nw_plugs_nightly_summary_validation.csv",
    index=False,
)

print("\n--- NW PLUGS: NIGHTLY VALIDATION SUMMARY ---")
print(nightly_summary.round(2).to_string(index=False))


# Define time bands using Madrid target hours.
valid["time_band"] = valid["hour_local"].apply(
    lambda hour: "Night" if hour < 6 else "Other hours"
)

# Compare time bands for all circuits and NW Plugs separately.
scopes = {
    "All circuits": valid,
    "NW Plugs & Sockets": valid[
        valid["zone"] == "NW|Plugs & Sockets"
    ],
}

summaries = []

for scope_name, data in scopes.items():
    summary = (
        data.groupby(["horizon_h", "time_band"])
        .agg(
            n_observations=("error_Wh", "size"),
            n_dates=("date_local", "nunique"),
            MAE_Wh=("absolute_error_Wh", "mean"),
            mean_error_Wh=("error_Wh", "mean"),
        )
        .reset_index()
    )

    summary.insert(0, "scope", scope_name)
    summaries.append(summary)

time_band_summary = pd.concat(summaries, ignore_index=True)

time_band_summary.to_csv(
    output_folder / "night_vs_other_hours_validation.csv",
    index=False,
)

print("\n--- NIGHT VS OTHER HOURS ---")
print(time_band_summary.round(2).to_string(index=False))



# Compare weekdays and weekends using Madrid target dates.
valid["day_type"] = valid["is_weekend"].map({
    False: "Weekday",
    True: "Weekend",
})

scopes = {
    "All circuits": valid,
    "NW Plugs & Sockets": valid[
        valid["zone"] == "NW|Plugs & Sockets"
    ],
}

summaries = []

for scope_name, data in scopes.items():
    summary = (
        data.groupby(["horizon_h", "day_type"])
        .agg(
            n_observations=("error_Wh", "size"),
            n_dates=("date_local", "nunique"),
            MAE_Wh=("absolute_error_Wh", "mean"),
            mean_error_Wh=("error_Wh", "mean"),
        )
        .reset_index()
    )

    summary.insert(0, "scope", scope_name)
    summaries.append(summary)

weekday_weekend_summary = pd.concat(
    summaries, ignore_index=True
)

weekday_weekend_summary.to_csv(
    output_folder / "weekday_vs_weekend_validation.csv",
    index=False,
)

print("\n--- WEEKDAY VS WEEKEND ---")
print(weekday_weekend_summary.round(2).to_string(index=False))



# Inspect SE Lighting at 15:00 and 16:00 Madrid time.
se_afternoon = df[
    (df["zone"] == "SE|Lighting")
    & (df["hour_local"].isin([15, 16]))
].copy()

# Keep missing actual values visible.
se_afternoon["valid_for_error"] = (
    se_afternoon["actual_Wh"].notna()
    & se_afternoon["predicted_Wh"].notna()
)

columns = [
    "horizon_h",
    "date_local",
    "hour_local",
    "actual_Wh",
    "predicted_Wh",
    "error_Wh",
    "absolute_error_Wh",
    "valid_for_error",
]

se_afternoon = se_afternoon[columns].sort_values(
    ["horizon_h", "date_local", "hour_local"]
)

output_file = (
    output_folder / "se_lighting_afternoon_details_validation.csv"
)

se_afternoon.to_csv(output_file, index=False)

print("\n--- SE LIGHTING: AFTERNOON DETAILS ---")
print(se_afternoon.round(2).to_string(index=False))
print(f"\nTable saved to: {output_file}")



# Compare actual and day-ahead predictions at 15:00 and 16:00.
se_day_ahead = se_afternoon[
    se_afternoon["horizon_h"] == 24
].copy()

fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

for ax, hour in zip(axes, [15, 16]):
    subset = se_day_ahead[
        se_day_ahead["hour_local"] == hour
    ].sort_values("date_local")

    ax.plot(
        subset["date_local"],
        subset["actual_Wh"],
        marker="o",
        color="black",
        label="Actual",
    )

    ax.plot(
        subset["date_local"],
        subset["predicted_Wh"],
        marker="o",
        color="tab:orange",
        label="Predicted",
    )

    ax.set_title(f"Target hour: {hour:02d}:00 — Europe/Madrid")
    ax.set_ylabel("Hourly energy (Wh)")
    ax.grid(alpha=0.3)
    ax.legend()

axes[-1].set_xlabel("Local date")

fig.suptitle("SE Lighting — Day-ahead afternoon forecasts — Validation")
fig.autofmt_xdate()
fig.tight_layout(rect=[0, 0, 1, 0.95])

fig.savefig(
    output_folder / "se_lighting_afternoon_validation.png",
    dpi=200,
)
plt.close(fig)