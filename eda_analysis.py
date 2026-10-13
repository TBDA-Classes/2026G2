"""
===============================================================================
Sprint 1 - Task 5 (Group A): Energy Data Lead - Exploratory Data Analysis (EDA)
CeDInt building, Storey 1 - energy meter data (BM321 / BMT01)
===============================================================================

WHAT DOES THIS SCRIPT DO?
It reads the four Excel exports (one file per zone NE/NW/SE/SW, one sheet per
device category such as HVAC, Lighting ...) and analyses ONLY the electrical
quantities measured by the energy meters:
    W  = active power (instantaneous)          I  = current
    Ea = active energy (cumulative counter)    Er = reactive energy (counter)
    Pa = apparent power
The ambient sensors (Lum, Hum, Temp, Pres) are NOT part of Task 5 and are
only checked for availability.

OUTPUT
- tables (CSV) and figures (PNG) in the folder "eda_output"
- an automatically generated summary "00_key_findings.txt"
- an hourly time series "hourly_energy.parquet" for Node A / Node B

HOW TO RUN IN PYCHARM
1. Terminal:  pip install pandas numpy matplotlib seaborn python-calamine pyarrow openpyxl
2. Put a folder "data" next to this file and copy the 4 Excel files into it
3. Click the green ▶ next to  if __name__ == "__main__":
===============================================================================
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import glob                      # find files by pattern (e.g. *.xlsx)
import os                        # paths and folders
import re                        # regular expressions (read zone from file name)
from pathlib import Path         # OS-independent paths

import matplotlib
import matplotlib.pyplot as plt  # plotting
import numpy as np               # numerical computations
import pandas as pd              # tables (DataFrames)
import seaborn as sns            # statistical plots with nicer defaults

# ============================ CONFIGURATION ================================
# Change settings here without touching the rest of the code.
BASE_DIR = Path(__file__).resolve().parent   # folder containing this script
DATA_DIR = BASE_DIR / "data"                 # folder with the Excel files
OUT_DIR = BASE_DIR / "eda_output"            # folder for all results

SHOW_PLOTS = True        # True  = show all figures once at the END of the run (and save them)
                         # False = only save PNGs (no windows)
GAP_THRESHOLD_MIN = 180  # a pause longer than this (minutes) counts as a "gap"
MIN_HOURS_PER_DAY = 20   # days with fewer hours are ignored for daily energy
OUTLIER_Z = 6            # threshold for the robust z-score (outliers)
# ==========================================================================

ENERGY_COLS = ["W", "I", "Ea", "Er", "Pa"]   # electrical quantities (our focus)
SENSOR_COLS = ["Lum", "Hum", "Temp", "Pres"] # ambient sensors (not part of Task 5)

# Consistent look for all figures
sns.set_theme(style="whitegrid", context="notebook")

# Without display we use the "Agg" backend: figures go to files only, no windows.
if not SHOW_PLOTS:
    matplotlib.use("Agg")

# Key findings collected during the run (written to 00_key_findings.txt)
FINDINGS: list[str] = []


def note(text: str):
    """Store a finding and print it to the console."""
    FINDINGS.append(text)
    print(f"  -> {text}")


def finish(fig, name: str):
    """Save a figure as PNG. Figures are NOT shown here - if SHOW_PLOTS is True,
    all of them are displayed together at the end of main()."""
    fig.tight_layout()
    fig.savefig(OUT_DIR / name, dpi=130)          # always save as PNG
    if not SHOW_PLOTS:
        plt.close(fig)                            # free memory if nothing is shown later


# ===========================================================================
# 1) INGESTION: every sheet of every file -> one long table
# ===========================================================================
def load_all(data_dir: Path) -> pd.DataFrame:
    """Read all 'Storey1_<ZONE>_report_by_device.xlsx' files.

    Each file = one zone, each sheet = one device category.
    Result: one DataFrame with the extra columns 'Zone' and 'Category'.
    Excel is slow, so the first run stores a Parquet copy (cache).
    New/changed Excel files are detected automatically (-> cache is rebuilt).
    """
    cache = data_dir / "_energy_raw.parquet"
    files = sorted(glob.glob(str(data_dir / "*report_by_device*.xlsx")))
    if not files:
        raise FileNotFoundError(
            f"No '*report_by_device*.xlsx' files found in {data_dir}.\n"
            f"-> Put the Excel files there or change DATA_DIR at the top of the script.")

    # Use the cache only if it is newer than every Excel file
    if cache.exists() and all(cache.stat().st_mtime > os.path.getmtime(f) for f in files):
        print(f"[load] using cache: {cache.name}")
        return pd.read_parquet(cache)

    frames = []
    for f in files:
        # Extract the zone (NE, NW, SE, SW) from the file name
        zone = re.search(r"Storey1_([A-Z]{2})_", os.path.basename(f)).group(1)
        try:
            sheets = pd.read_excel(f, sheet_name=None, engine="calamine")  # fast
        except ImportError:
            print("  python-calamine not installed -> using openpyxl (much slower)")
            sheets = pd.read_excel(f, sheet_name=None)                      # fallback
        # sheet_name=None returns a dictionary {sheet name: DataFrame}
        for sheet, df in sheets.items():
            df = df.copy()
            df["Zone"] = zone
            df["Category"] = sheet.strip()
            frames.append(df)
            print(f"[load] {zone:2s} | {sheet:16s} | {len(df):>7,} rows")

    raw = pd.concat(frames, ignore_index=True)       # stack everything vertically

    # Enforce data types: invalid entries become NaT/NaN instead of crashing
    raw["Timestamp"] = pd.to_datetime(raw["Timestamp"], errors="coerce")
    for c in ENERGY_COLS + SENSOR_COLS + ["Number of Edevices"]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")

    # 'E Device type' is identical to the sheet name -> redundant
    raw = raw.drop(columns=["E Device type"], errors="ignore")
    raw = raw.sort_values(["Zone", "Category", "Timestamp"]).reset_index(drop=True)
    raw.to_parquet(cache)
    return raw


# ===========================================================================
# 2) DATA QUALITY: overview per series (zone x category)
# ===========================================================================
def quality_overview(df: pd.DataFrame) -> pd.DataFrame:
    """One row per series with time range, number of devices, missing values,
    duplicates and the share of negative / zero power readings."""
    g = df.groupby(["Zone", "Category"])
    q = pd.DataFrame({
        "rows": g.size(),
        "start": g["Timestamp"].min(),
        "end": g["Timestamp"].max(),
        "n_devices": g["Number of Edevices"].first(),
        "bad_timestamps": g["Timestamp"].apply(lambda s: s.isna().sum()),
        "duplicate_timestamps": g["Timestamp"].apply(lambda s: s.duplicated().sum()),
        "missing_values": g[ENERGY_COLS].apply(lambda x: x.isna().sum().sum()),
        "W_negative_%": g["W"].apply(lambda s: (s < 0).mean() * 100).round(1),
        "W_zero_%": g["W"].apply(lambda s: (s == 0).mean() * 100).round(1),
        # True if a series contains only zeros (meter dead / not connected)
        "all_energy_zero": g[ENERGY_COLS].apply(lambda x: bool((x.fillna(0) == 0).all().all())),
    })
    q.to_csv(OUT_DIR / "01_quality_overview.csv")
    print("\n=== DATA QUALITY ===\n", q.to_string())

    # Turn the table into written findings
    for (z, c), r in q.iterrows():
        if r["all_energy_zero"]:
            note(f"{z} | {c}: contains only zeros (inactive meter) -> removed from figures.")
        elif r["W_negative_%"] > 90:
            note(f"{z} | {c}: {r['W_negative_%']}% negative power -> probably inverted sign.")
    last_end = q["end"].max()
    for (z, c), r in q.iterrows():
        if r["end"] < last_end - pd.Timedelta(days=30):
            note(f"{z} | {c}: data already ends on {r['end']:%Y-%m-%d}.")
    return q


def prepare(df: pd.DataFrame, q: pd.DataFrame) -> pd.DataFrame:
    """IMPROVEMENT: prepare series for analysis (raw data stays unchanged).
    - remove series without any readings (zeros only)
    - series with almost only negative values -> flip the sign (meter wired the
      wrong way round). This is an EDA assumption and must be agreed with Node A!
    """
    df = df.copy()
    dead = q.index[q["all_energy_zero"]]
    flipped = q.index[(q["W_negative_%"] > 90) & ~q["all_energy_zero"]]
    key = list(zip(df["Zone"], df["Category"]))
    df = df[~pd.Series(key, index=df.index).isin(dead)]
    mask = pd.Series(list(zip(df["Zone"], df["Category"])), index=df.index).isin(flipped)
    df.loc[mask, ["W", "Pa"]] = -df.loc[mask, ["W", "Pa"]]
    return df


# ===========================================================================
# 3) SAMPLING RATE & GAPS (consequence of the data retention policy)
# ===========================================================================
def sampling_analysis(df: pd.DataFrame):
    """How often was data recorded and where is data missing?"""
    df = df.copy()
    # Time difference to the previous reading of the same series (minutes)
    df["dt_min"] = df.groupby(["Zone", "Category"])["Timestamp"].diff().dt.total_seconds() / 60
    df["year"] = df["Timestamp"].dt.year

    # Most frequent interval per year (= typical sampling rate)
    freq = (df.groupby("year")["dt_min"]
              .agg(lambda s: s.mode().iloc[0] if s.notna().any() else np.nan)
              .rename("typical_interval_min"))
    fy = pd.concat([df.groupby("year").size().rename("rows"), freq], axis=1)
    fy.to_csv(OUT_DIR / "02_sampling_by_year.csv")
    print("\n=== SAMPLING INTERVAL PER YEAR ===\n", fy.to_string())
    note("Sampling interval: " + ", ".join(f"{int(y)}: {v:.0f} min" for y, v in freq.items()))

    # Gaps: intervals longer than GAP_THRESHOLD_MIN
    gaps = df[df["dt_min"] > GAP_THRESHOLD_MIN][["Zone", "Category", "Timestamp", "dt_min"]].copy()
    gaps["gap_start"] = gaps["Timestamp"] - pd.to_timedelta(gaps["dt_min"], unit="min")
    gaps["gap_days"] = (gaps["dt_min"] / 1440).round(2)
    gaps = gaps.rename(columns={"Timestamp": "gap_end"})[["Zone", "Category", "gap_start", "gap_end", "gap_days"]]
    gaps = gaps.sort_values("gap_days", ascending=False)
    gaps.to_csv(OUT_DIR / "03_gaps.csv", index=False)
    print(f"\n=== GAPS > {GAP_THRESHOLD_MIN} min: {len(gaps)} (10 largest) ===\n",
          gaps.head(10).to_string(index=False))
    if len(gaps):
        g0 = gaps.iloc[0]
        note(f"Largest gap: {g0.gap_start:%Y-%m-%d} to {g0.gap_end:%Y-%m-%d} ({g0.gap_days:.0f} days).")

    # IMPROVEMENT: time zone check. Is there a missing or duplicated hour on
    # daylight-saving days? If not, the timestamps are most likely UTC.
    hourly = df[df["dt_min"] == 60]
    dst_days = [d for d in pd.to_datetime(["2021-03-28", "2022-03-27"])
                if d in set(hourly["Timestamp"].dt.normalize())]
    if dst_days:
        s = df[(df["Timestamp"].dt.normalize() == dst_days[0])].groupby(["Zone", "Category"]).size()
        note(f"DST change {dst_days[0]:%Y-%m-%d}: {int(s.median())} readings/day instead of 23 "
             f"-> timestamps are probably UTC (important for Node B's weather merge).")

    # Figure: data availability (readings per month, log scale)
    avail = (df.assign(month=df["Timestamp"].dt.to_period("M").dt.to_timestamp(),
                       series=df["Zone"] + " | " + df["Category"])
               .groupby(["series", "month"]).size().unstack(fill_value=0))
    # insert empty months so the big gap becomes visible
    avail = avail.reindex(columns=pd.date_range(avail.columns.min(), avail.columns.max(), freq="MS"),
                          fill_value=0)
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.heatmap(np.log10(avail + 1), cmap="viridis", ax=ax,
                cbar_kws={"label": "log10(readings per month)"})
    ax.set_xticks(np.arange(0, avail.shape[1], 6) + 0.5)
    ax.set_xticklabels([c.strftime("%Y-%m") for c in avail.columns[::6]], rotation=45)
    ax.set_title("Data availability per series – switch hourly → 1-min, gap 2023–2025")
    ax.set_xlabel(""); ax.set_ylabel("")
    finish(fig, "fig01_availability.png")


# ===========================================================================
# 4) DESCRIPTIVE STATISTICS
# ===========================================================================
def descriptive_stats(df: pd.DataFrame):
    """Mean, spread, percentiles and distributions of the measured quantities."""
    desc = df.groupby(["Zone", "Category"])[ENERGY_COLS].describe(percentiles=[.01, .5, .99]).round(2)
    desc.to_csv(OUT_DIR / "04_descriptive_stats.csv")

    # Boxplot of power per category and zone (outliers hidden for readability)
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.boxplot(data=df[df["W"].notna()], x="Category", y="W", hue="Zone", showfliers=False, ax=ax)
    ax.set_title("Active power W per category and zone (outliers hidden)")
    ax.set_ylabel("W")
    finish(fig, "fig02_power_boxplot.png")

    # Correlation between the electrical quantities
    corr = df[ENERGY_COLS].corr().round(2)
    corr.to_csv(OUT_DIR / "05_correlation.csv")
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(corr, annot=True, cmap="RdBu_r", vmin=-1, vmax=1, ax=ax)
    ax.set_title("Correlation of electrical variables")
    finish(fig, "fig03_correlation.png")


# ===========================================================================
# 5) COUNTER RESETS & CONSISTENCY of Ea
# ===========================================================================
def reset_analysis(df: pd.DataFrame):
    """Ea is a cumulative counter and should only increase. Every backward step
    is an anomaly (device reset, overflow or transmission error)."""
    df = df.copy()
    df["dEa"] = df.groupby(["Zone", "Category"])["Ea"].diff()   # change vs. previous reading
    df["ea_drop"] = df["dEa"] < 0                              # any backward step
    df["reset_to_zero"] = df["ea_drop"] & (df["Ea"] <= 1)       # drop to ~0 = real reset
    df["ea_negative"] = df["Ea"] < 0                            # physically impossible
    r = df.groupby(["Zone", "Category"]).agg(
        rows=("Ea", "size"),
        ea_backward_steps=("ea_drop", "sum"),
        resets_to_zero=("reset_to_zero", "sum"),
        ea_negative_values=("ea_negative", "sum"),
    )
    r["backward_%"] = (r["ea_backward_steps"] / r["rows"] * 100).round(1)
    r.to_csv(OUT_DIR / "06_counter_resets.csv")
    print("\n=== Ea COUNTER ANOMALIES ===\n", r.to_string())
    note(f"Ea steps backwards {int(r['ea_backward_steps'].sum()):,} times in total "
         f"({int(r['resets_to_zero'].sum()):,} of them to ~0) -> Ea is unreliable as a consumption source.")

    # IMPROVEMENT: does Ea match W at all? For hourly data the following should hold:
    # increase of Ea within one hour ≈ mean power W (in Wh or kWh).
    df["dt_h"] = df.groupby(["Zone", "Category"])["Timestamp"].diff().dt.total_seconds() / 3600
    ok = df[(df["dt_h"] == 1) & (df["dEa"] > 0) & (df["W"] > 0)]
    cons = ok.groupby(["Zone", "Category"]).apply(
        lambda s: pd.Series({"corr_dEa_W": s["dEa"].corr(s["W"]),
                             "median_ratio_dEa_per_W": (s["dEa"] / s["W"]).median()})).round(3)
    cons.to_csv(OUT_DIR / "06b_ea_vs_w_consistency.csv")
    print("\n=== CONSISTENCY hourly Ea increase vs. W ===\n", cons.to_string())
    note(f"Correlation of hourly Ea increase vs. W: median {cons['corr_dEa_W'].median():.2f} "
         f"-> Ea and W do not match; units of Ea must be clarified. Consumption is therefore derived from W.")

    # Figure: raw Ea for the 4 most affected series, backward steps in red
    worst = r["ea_backward_steps"].sort_values(ascending=False).head(4).index
    fig, axes = plt.subplots(len(worst), 1, figsize=(13, 2.6 * len(worst)), sharex=True)
    for ax, (z, c) in zip(np.atleast_1d(axes), worst):
        s = df[(df.Zone == z) & (df.Category == c)]
        ax.plot(s["Timestamp"], s["Ea"], lw=0.6)
        drops = s[s["ea_drop"]]
        ax.scatter(drops["Timestamp"], drops["Ea"], s=4, color="crimson", label="backward step")
        ax.set_title(f"{z} | {c}: raw Ea counter", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)
    finish(fig, "fig04_ea_resets.png")


# ===========================================================================
# 6) HOURLY TIME SERIES & TIME PATTERNS
# ===========================================================================
def to_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Bring hourly (2020-23) and 1-minute (2025) data onto a common basis:
    the mean per hour. Mean power W over 1 h = energy in Wh for that hour.
    'n_obs' counts how many raw readings went into each hour."""
    h = (df.set_index("Timestamp")
           .groupby(["Zone", "Category"])
           .resample("1h")
           .agg(W=("W", "mean"), I=("I", "mean"), Pa=("Pa", "mean"), n_obs=("W", "count"))
           .reset_index())
    h = h[h["n_obs"] > 0]                 # drop hours without any reading (e.g. gap 2023-25)
    h["W_pos"] = h["W"].clip(lower=0)     # small negative values = measurement noise -> 0
    h.to_parquet(OUT_DIR / "hourly_energy.parquet")
    return h


def time_patterns(h: pd.DataFrame):
    """Typical patterns: daily energy, shares, weekly/daily profile, seasonality, distribution."""
    h = h.copy()

    # 6a) Daily energy per category (sum over all zones).
    # IMPROVEMENT: only days with enough hours, otherwise incomplete days look like drops.
    h["day"] = h["Timestamp"].dt.floor("D")
    hours_per_day = h.groupby(["Zone", "Category", "day"])["Timestamp"].transform("count")
    daily = (h[hours_per_day >= MIN_HOURS_PER_DAY]
               .groupby(["Category", "day"])["W_pos"].sum().div(1000).rename("kWh").reset_index())
    piv = daily.pivot(index="day", columns="Category", values="kWh")
    piv = piv.reindex(pd.date_range(piv.index.min(), piv.index.max(), freq="D"))  # keep gaps visible
    fig, ax = plt.subplots(figsize=(14, 5))
    piv.rolling(7, min_periods=3).mean().plot(ax=ax, lw=1)
    ax.set_ylabel("kWh/day (7-day mean)")
    ax.set_title("Daily energy per category, Storey 1 (assumes W in watts)")
    finish(fig, "fig05_daily_energy.png")

    # 6b) Average load per zone, stacked by category
    share = h.groupby(["Zone", "Category"])["W_pos"].mean().unstack().fillna(0)
    fig, ax = plt.subplots(figsize=(9, 5))
    share.plot(kind="bar", stacked=True, ax=ax, colormap="tab10")
    ax.set_ylabel("mean power [W]"); ax.set_title("Average load by zone and category")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
    finish(fig, "fig06_load_share.png")
    cat_mean = h.groupby("Category")["W_pos"].mean()
    tot_share = cat_mean / cat_mean.sum() * 100
    note("Load shares: " + ", ".join(f"{c} {v:.0f}%" for c, v in tot_share.sort_values(ascending=False).items()))

    # 6c) Weekly profile (hour x weekday) of the total load
    tot = h.groupby("Timestamp")["W_pos"].sum().to_frame("W")
    tot["hour"] = tot.index.hour
    tot["weekday"] = tot.index.dayofweek          # 0 = Monday ... 6 = Sunday
    prof = tot.pivot_table(index="weekday", columns="hour", values="W", aggfunc="median")
    prof.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][:len(prof)]
    fig, ax = plt.subplots(figsize=(13, 4))
    sns.heatmap(prof, cmap="rocket_r", ax=ax, cbar_kws={"label": "median W"})
    ax.set_title("Typical weekly profile of total load (hour in UTC)")
    finish(fig, "fig07_weekly_profile.png")
    wk = tot[tot.weekday < 5]["W"].median(); we = tot[tot.weekday >= 5]["W"].median()
    note(f"Median total load weekday {wk:.0f} W vs. weekend {we:.0f} W (+{(wk / we - 1) * 100:.0f}%).")

    # 6d) Daily profile per category: weekday vs. weekend
    h["daytype"] = np.where(h["Timestamp"].dt.dayofweek < 5, "weekday", "weekend")
    h["hour"] = h["Timestamp"].dt.hour
    cats = sorted(h["Category"].unique())
    ncol = int(np.ceil(len(cats) / 2))
    fig, axes = plt.subplots(2, ncol, figsize=(4 * ncol, 6), sharex=True)
    for ax, c in zip(axes.flat, cats):
        p = h[h.Category == c].groupby(["daytype", "hour"])["W_pos"].median().unstack(0)
        p.plot(ax=ax, lw=1.5); ax.set_title(c, fontsize=10); ax.set_xlabel("hour (UTC)")
    for ax in list(axes.flat)[len(cats):]:
        ax.axis("off")                            # hide empty panels
    fig.suptitle("Median daily load profile (W): weekday vs. weekend")
    finish(fig, "fig08_daily_profiles.png")

    # 6e) Seasonality: mean load per calendar month
    mon = h.groupby([h["Timestamp"].dt.month.rename("month"), "Category"])["W_pos"].mean().unstack()
    fig, ax = plt.subplots(figsize=(11, 4))
    mon.plot(ax=ax, marker="o"); ax.set_ylabel("mean W"); ax.set_title("Seasonality: mean load per month")
    ax.set_xticks(range(1, 13))
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
    finish(fig, "fig09_monthly.png")

    # 6f) NEW: distribution of hourly power per category (log scale due to wide range)
    fig, ax = plt.subplots(figsize=(11, 4))
    for c in cats:
        v = h.loc[(h.Category == c) & (h.W_pos > 0), "W_pos"]
        if len(v):
            ax.hist(v, bins=np.logspace(-1, 4, 60), histtype="step", lw=1.5, label=c)
    ax.set_xscale("log"); ax.set_xlabel("hourly power W (log)"); ax.set_ylabel("number of hours")
    ax.set_title("Distribution of hourly power per category")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
    finish(fig, "fig10_distribution.png")

    # 6g) NEW: autocorrelation of total load – reveals daily (24 h) and weekly (168 h) rhythm.
    # Relevant for Sprint 2: which lags are good features for forecasting models?
    s = tot["W"].asfreq("1h")                   # regular hourly grid (gaps = NaN)
    lags = np.arange(1, 24 * 14 + 1)
    acf = [s.autocorr(lag=int(l)) for l in lags]
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.plot(lags, acf, lw=1.2)
    for x in (24, 168, 336):
        ax.axvline(x, color="grey", ls="--", lw=0.8)
    ax.set_xlabel("lag [hours]"); ax.set_ylabel("autocorrelation")
    ax.set_title("Autocorrelation of total load (dashed: 1 day, 1 week, 2 weeks)")
    finish(fig, "fig11_autocorrelation.png")
    note(f"Autocorrelation of total load: lag 24 h = {acf[23]:.2f}, lag 168 h = {acf[167]:.2f} "
         f"-> strong daily/weekly patterns, good lag features for Sprint 2.")


# ===========================================================================
# 7) OUTLIERS (robust z-score on hourly power)
# ===========================================================================
def outliers(h: pd.DataFrame):
    """Robust z-score = (value - median) / (1.4826 * MAD).
    Unlike mean/std, median and MAD are barely distorted by the outliers themselves."""
    def robust_z(s):
        # Use operating hours only (W > 0) as reference: for on/off loads such as
        # lighting the median would otherwise be 0 and EVERY 'on' hour an outlier.
        on = s[s > 0]
        if len(on) < 10:
            return s * 0
        med = on.median()
        mad = (on - med).abs().median()          # median absolute deviation
        z = (s - med) / (1.4826 * mad) if mad > 0 else s * 0
        return z.where(s > 0, 0)                 # 'off' hours are not outliers
    h = h.copy()
    h["rz"] = h.groupby(["Zone", "Category"])["W"].transform(robust_z)
    o = (h.assign(outlier=h["rz"].abs() > OUTLIER_Z)
           .groupby(["Zone", "Category"])["outlier"].agg(["sum", "mean"]))
    o.columns = ["outlier_hours", "outlier_share_%"]
    o["outlier_share_%"] = (o["outlier_share_%"] * 100).round(2)
    o.to_csv(OUT_DIR / "07_outliers_hourly.csv")
    print(f"\n=== OUTLIER HOURS (|robust z| > {OUTLIER_Z}) ===\n", o.to_string())
    top = o["outlier_share_%"].idxmax()
    note(f"Most outliers: {top[0]} | {top[1]} ({o.loc[top, 'outlier_share_%']}% of hours) "
         f"- mostly real winter peaks, do not delete blindly.")


# ===========================================================================
# MAIN PROGRAM
# ===========================================================================
def main():
    OUT_DIR.mkdir(exist_ok=True)
    print(f"Reading Excel files from: {DATA_DIR}  (first run ~30 s, then cached)")

    df = load_all(DATA_DIR)
    print(f"\n{len(df):,} rows | {df.Zone.nunique()} zones | {df.Category.nunique()} categories")
    print(f"Time range: {df.Timestamp.min()} → {df.Timestamp.max()}")
    note("Note: data is aggregated per zone and device category (column 'Number of Edevices'), "
         "not per individual meter.")

    q = quality_overview(df)        # 2) quality of the raw data
    sampling_analysis(df)           # 3) sampling rate, gaps, time zone
    df_clean = prepare(df, q)       #    drop dead series, fix sign
    descriptive_stats(df_clean)     # 4) statistics
    reset_analysis(df)              # 5) counter resets (on raw data!)
    h = to_hourly(df_clean)         # 6) common hourly basis
    time_patterns(h)                #    time patterns
    outliers(h)                     # 7) outliers

    # Summary as text file - good starting point for the sprint report
    (OUT_DIR / "00_key_findings.txt").write_text(
        "KEY FINDINGS - Energy EDA (generated automatically)\n\n" +
        "\n".join(f"- {f}" for f in FINDINGS), encoding="utf-8")
    print(f"\nDone. Figures and tables in {OUT_DIR}/")

    if SHOW_PLOTS:
        # Show all finished figures in one go (only the final versions, no intermediate steps)
        print(f"Showing {len(plt.get_fignums())} figures ...")
        plt.show()


if __name__ == "__main__":
    main()
