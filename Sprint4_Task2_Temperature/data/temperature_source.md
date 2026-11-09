# Outdoor temperature — data source

## File

`temperature_cedint_hourly_2025.csv` — one row per hour, 1 Aug – 13 Oct 2025, timestamps in **UTC**.

| Column | Meaning | Unit |
|---|---|---|
| `hour_utc` | Start of the hour (same convention as the energy dataset `Storey1_hourly_v1.2`) | UTC |
| `temp_obs_C` | Best available estimate of the actual outdoor temperature at 2 m | °C |
| `temp_fc48_C` | Forecast of the same hour, made **48 hours before** that hour | °C |

`temperature_download.json` records the exact request, the download time and the grid point returned.

## Source and why it was chosen

- **Provider:** Open-Meteo, Previous Runs API (`https://previous-runs-api.open-meteo.com/v1/forecast`), free, no registration.
- **Location:** requested at the CeDInt coordinates (40.4044, −3.8368, Campus de Montegancedo). The provider returns the
  nearest model grid point: 40.414, −3.854, **1.8 km** from CeDInt, elevation 718 m.
- **Why this source:** it is the only source among those in `Source Evaluation.xlsx` that offers, at the same time,
  (1) hourly values, (2) the building's exact location, and (3) archived forecasts.
  - AEMET and the Madrid city network (`S1-B2 Data *.csv`) provide **daily** values only, and CeDInt is outside the
    Madrid municipality.
  - ERA5 is hourly but is a reanalysis: it gives the actual temperature, not a forecast.
- **Why the forecast matters:** when a forecast is issued, the actual temperature of future hours is not yet known.
  Using it would leak future information into the model. The 48-hour forecast was published at least 25 hours before
  any issue time, because target hours are at most 23 hours after the issue time.

## Quality checks (results in `../outputs/temperature_qa.csv`)

| Check | Result |
|---|---|
| Hours expected / present | 1,776 / 1,776 |
| Missing values, duplicated hours | 0, 0 |
| Value range | 8.2 to 39.3 °C (plausible for Madrid, Aug–Oct) |
| Units | °C |
| Time zone | UTC, the same as the energy dataset, so no conversion is needed |
| Aggregation | none: the source is already hourly |
| 48 h forecast vs actual | MAE 0.57 °C (training period), 0.53 °C (validation week) |
| Daily mean vs Casa de Campo station (24) | 39 days, correlation 0.983, mean difference −0.24 °C |
| Daily mean vs El Pardo station (58) | 41 days, correlation 0.957, mean difference +1.58 °C (El Pardo is a colder, rural site) |

**Conclusion:** the data are complete, plausible and consistent with an official nearby station. They are suitable for
the experiment.
