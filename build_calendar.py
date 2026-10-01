"""B3 - UPM academic calendar -> Date | Day Type table.

Builds a daily calendar for the periods covered by the CeDInt sensor data and
labels every day with one of:

    Weekend   Saturday or Sunday
    Holiday   weekday public holiday (national, Madrid region or Madrid city)
    Lockdown  COVID-19 state of alarm (14 Mar - 21 Jun 2020)
    Vacation  UPM Christmas / Semana Santa break, and August (summer closure)
    Working   everything else

Priority when several apply: Weekend > Holiday > Lockdown > Vacation > Working.
A holiday that falls on a weekend stays "Weekend" (the name is kept in Note).

Sources: official UPM "Calendario escolar" 2019/20, 2020/21, 2021/22, 2022/23
and 2025/26 (the 2025/26 one was still a draft: "Aprobado ... el XX de XXXXX").

Usage:
    python build_calendar.py                 # writes upm_calendar.xlsx + .csv
    python build_calendar.py -o other.xlsx
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# Date ranges covered by the sensor data (see .notes/inputs.md)
DATA_RANGES = [
    (date(2020, 4, 2), date(2023, 2, 28)),
    (date(2025, 8, 18), date(2025, 10, 13)),
]

HOLIDAYS = {
    # 2019/20
    "2020-04-09": "Jueves Santo",
    "2020-04-10": "Viernes Santo",
    "2020-05-01": "Día del Trabajo",
    "2020-05-02": "Fiesta de la Comunidad de Madrid",
    "2020-05-15": "San Isidro Labrador",
    "2020-08-15": "La Asunción de Nuestra Señora",
    # 2020/21
    "2020-10-12": "Fiesta Nacional de España",
    "2020-11-02": "Todos los Santos (trasladado)",
    "2020-11-09": "Nuestra Señora de la Almudena",
    "2020-12-07": "Día de la Constitución (trasladado)",
    "2020-12-08": "La Inmaculada Concepción",
    "2020-12-25": "Natividad del Señor",
    "2021-01-01": "Año Nuevo",
    "2021-01-06": "Epifanía del Señor",
    "2021-01-28": "Santo Tomás de Aquino",
    "2021-03-19": "San José",
    "2021-04-01": "Jueves Santo",
    "2021-04-02": "Viernes Santo",
    "2021-05-01": "Día del Trabajo",
    "2021-05-02": "Fiesta de la Comunidad de Madrid",
    "2021-05-03": "Traslado Fiesta Comunidad de Madrid",
    "2021-05-15": "San Isidro Labrador",
    "2021-08-15": "La Asunción de Nuestra Señora",
    # 2021/22
    "2021-10-12": "Fiesta Nacional de España",
    "2021-11-01": "Todos los Santos",
    "2021-11-09": "Nuestra Señora de la Almudena",
    "2021-12-06": "Día de la Constitución",
    "2021-12-08": "La Inmaculada Concepción",
    "2021-12-25": "Natividad del Señor",
    "2022-01-01": "Año Nuevo",
    "2022-01-06": "Epifanía del Señor",
    "2022-01-28": "Santo Tomás de Aquino",
    "2022-04-14": "Jueves Santo",
    "2022-04-15": "Viernes Santo",
    "2022-05-01": "Día del Trabajo",
    "2022-05-02": "Fiesta de la Comunidad de Madrid",
    "2022-05-16": "San Isidro Labrador (trasladado)",
    "2022-07-25": "Santiago Apóstol",
    "2022-08-15": "La Asunción de Nuestra Señora",
    # 2022/23
    "2022-10-12": "Fiesta Nacional de España",
    "2022-11-01": "Todos los Santos",
    "2022-11-09": "Nuestra Señora de la Almudena",
    "2022-12-06": "Día de la Constitución",
    "2022-12-08": "La Inmaculada Concepción",
    "2022-12-25": "Natividad del Señor",
    "2023-01-01": "Año Nuevo",
    "2023-01-06": "Epifanía del Señor",
    "2023-01-28": "Santo Tomás de Aquino",
    "2023-04-06": "Jueves Santo",
    "2023-04-07": "Viernes Santo",
    "2023-05-01": "Día del Trabajo",
    "2023-05-02": "Fiesta de la Comunidad de Madrid",
    "2023-05-15": "San Isidro Labrador",
    "2023-08-15": "La Asunción de Nuestra Señora",
    # 2025/26 (draft calendar)
    "2025-07-25": "Santiago Apóstol",
    "2025-08-15": "La Asunción de Nuestra Señora",
    "2025-11-01": "Todos los Santos",
    "2025-11-10": "Nuestra Señora de la Almudena (trasladado)",
    "2025-12-06": "Día de la Constitución",
    "2025-12-08": "La Inmaculada Concepción",
    "2025-12-25": "Natividad del Señor",
    "2026-01-01": "Año Nuevo",
    "2026-01-06": "Epifanía del Señor",
    "2026-01-28": "Santo Tomás de Aquino",
    "2026-04-02": "Jueves Santo",
    "2026-04-03": "Viernes Santo",
    "2026-05-01": "Día del Trabajo",
    "2026-05-02": "Fiesta de la Comunidad de Madrid",
    "2026-05-15": "San Isidro Labrador",
    "2026-08-15": "La Asunción de Nuestra Señora",
}

# (first day, last day, name), both inclusive. Last day = day before
# "Reanudación de las clases" / end of the bar in the calendar.
VACATIONS = [
    ("2020-04-06", "2020-04-13", "Semana Santa"),
    ("2020-08-01", "2020-08-31", "Summer (August)"),
    ("2020-12-23", "2021-01-07", "Navidad"),
    ("2021-03-29", "2021-04-05", "Semana Santa"),
    ("2021-08-01", "2021-08-31", "Summer (August)"),
    ("2021-12-23", "2022-01-09", "Navidad"),
    ("2022-04-11", "2022-04-18", "Semana Santa"),
    ("2022-08-01", "2022-08-31", "Summer (August)"),
    ("2022-12-23", "2023-01-08", "Navidad"),
    ("2023-04-03", "2023-04-10", "Semana Santa"),
    ("2023-08-01", "2023-08-31", "Summer (August)"),
    ("2025-08-01", "2025-08-31", "Summer (August)"),
    ("2025-12-22", "2026-01-07", "Navidad"),
    ("2026-03-30", "2026-04-06", "Semana Santa"),
    ("2026-08-01", "2026-08-31", "Summer (August)"),
]

LOCKDOWNS = [
    ("2020-03-14", "2020-06-21", "COVID-19 state of alarm"),
]


def _expand(periods):
    out = {}
    for start, end, name in periods:
        d, end = date.fromisoformat(start), date.fromisoformat(end)
        while d <= end:
            out[d] = name
            d += timedelta(days=1)
    return out


def day_type(d, holidays, lockdown, vacation):
    """Return (Day Type, Note) for one date."""
    note = holidays.get(d) or lockdown.get(d) or vacation.get(d) or ""
    if d.weekday() >= 5:
        return "Weekend", note
    if d in holidays:
        return "Holiday", note
    if d in lockdown:
        return "Lockdown", note
    if d in vacation:
        return "Vacation", note
    return "Working", ""


def build(ranges=DATA_RANGES):
    holidays = {date.fromisoformat(k): v for k, v in HOLIDAYS.items()}
    lockdown, vacation = _expand(LOCKDOWNS), _expand(VACATIONS)
    rows = []
    for start, end in ranges:
        for d in pd.date_range(start, end, freq="D").date:
            dtype, note = day_type(d, holidays, lockdown, vacation)
            rows.append({"Date": d, "Day Type": dtype, "Note": note})
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-o", "--output", default=Path(__file__).with_name("upm_calendar.xlsx"))
    out = Path(p.parse_args().output)
    df = build()
    with pd.ExcelWriter(out, engine="openpyxl", date_format="YYYY-MM-DD",
                        datetime_format="YYYY-MM-DD") as xw:
        df.to_excel(xw, index=False, sheet_name="calendar")
        ws = xw.sheets["calendar"]
        for (cell,) in ws.iter_rows(min_row=2, max_col=1):
            cell.number_format = "yyyy-mm-dd"
        ws.column_dimensions["A"].width = 13
        ws.column_dimensions["B"].width = 11
        ws.column_dimensions["C"].width = 42
        ws.freeze_panes = "A2"
    df.to_csv(out.with_suffix(".csv"), index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(df)} days to {out} (+ .csv)")
    print(df["Day Type"].value_counts().to_string())


if __name__ == "__main__":
    main()
