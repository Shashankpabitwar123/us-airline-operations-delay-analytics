#!/usr/bin/env python3
"""Download, clean, model, and validate complete 2023-2025 BTS monthly flight files.

The script processes one compressed source file at a time and removes it after
successful ingestion. It writes a compact DuckDB analytical model, dimensions,
and reproducible quality evidence without keeping bulky raw source files.
"""
from __future__ import annotations

import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_cache"
PROCESSED = ROOT / "data" / "processed"
EXPORTS = ROOT / "data" / "exports"
DB_PATH = PROCESSED / "airline_operations.duckdb"
YEARS = (2023, 2024, 2025)
MONTHS = range(1, 13)
CHUNK_SIZE = 250_000

CANDIDATES = [
    "FlightDate", "Year", "Quarter", "Month", "DayofMonth", "DayOfWeek",
    "Reporting_Airline", "DOT_ID_Reporting_Airline", "IATA_CODE_Reporting_Airline",
    "Flight_Number_Reporting_Airline", "OriginAirportID", "Origin", "OriginCityName",
    "OriginState", "DestAirportID", "Dest", "DestCityName", "DestState",
    "CRSDepTime", "DepTime", "DepDelay", "DepDel15", "DepartureDelayGroups",
    "DepTimeBlk", "CRSArrTime", "ArrTime", "ArrDelay", "ArrDel15",
    "ArrivalDelayGroups", "ArrTimeBlk", "Cancelled", "CancellationCode", "Diverted",
    "CRSElapsedTime", "ActualElapsedTime", "AirTime", "Distance", "CarrierDelay",
    "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay",
]


def source_url(year: int, month: int) -> str:
    return "https://www.transtats.bts.gov/PREZIP/" \
        f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"


def download(year: int, month: int) -> Path:
    target = RAW / f"bts_{year}_{month:02d}.zip"
    if not target.exists():
        print(f"Downloading {year}-{month:02d}", flush=True)
        urllib.request.urlretrieve(source_url(year, month), target)
    return target


def numeric(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")


def process_chunk(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame[[column for column in CANDIDATES if column in frame.columns]].copy()
    numeric(frame, [
        "DOT_ID_Reporting_Airline", "Flight_Number_Reporting_Airline", "OriginAirportID",
        "DestAirportID", "CRSDepTime", "DepDelay", "DepDel15", "ArrDelay", "ArrDel15",
        "Cancelled", "Diverted", "Distance", "CarrierDelay", "WeatherDelay", "NASDelay",
        "SecurityDelay", "LateAircraftDelay", "Month", "Year", "DayOfWeek",
    ])
    frame["flight_date"] = pd.to_datetime(frame["FlightDate"], errors="coerce")
    required = ["flight_date", "DOT_ID_Reporting_Airline", "OriginAirportID", "DestAirportID"]
    frame = frame.dropna(subset=required).copy()
    frame["year"] = frame["flight_date"].dt.year.astype("int16")
    frame["month"] = frame["flight_date"].dt.month.astype("int8")
    frame["weekday"] = frame["flight_date"].dt.dayofweek.astype("int8") + 1
    frame["is_weekend"] = frame["weekday"].isin([6, 7]).astype("int8")
    frame["flight_month"] = frame["flight_date"].values.astype("datetime64[M]")
    frame["reporting_airline"] = frame["Reporting_Airline"].fillna("Unknown").astype(str).str.strip()
    frame["airline_name"] = frame.get("IATA_CODE_Reporting_Airline", pd.Series("Unknown", index=frame.index)).fillna("Unknown").astype(str).str.strip()
    frame["airline_key"] = frame["DOT_ID_Reporting_Airline"].astype("int64")
    for column in ("Origin", "Dest", "OriginCityName", "DestCityName", "OriginState", "DestState"):
        frame[column] = frame.get(column, pd.Series("Unknown", index=frame.index)).fillna("Unknown").astype(str).str.strip()
    frame["origin_airport_key"] = frame["OriginAirportID"].astype("int64")
    frame["dest_airport_key"] = frame["DestAirportID"].astype("int64")
    frame["route_key"] = frame["Origin"] + "-" + frame["Dest"]
    frame["cancelled"] = frame["Cancelled"].fillna(0).clip(0, 1).astype("int8")
    frame["diverted"] = frame["Diverted"].fillna(0).clip(0, 1).astype("int8")
    frame["operated"] = ((frame["cancelled"] == 0) & (frame["diverted"] == 0)).astype("int8")
    frame["arrival_delay_minutes"] = frame["ArrDelay"].where(frame["operated"] == 1)
    frame["delayed_flight"] = ((frame["operated"] == 1) & (frame["ArrDel15"].fillna(0) == 1)).astype("int8")
    frame["arrived_on_time"] = ((frame["operated"] == 1) & (frame["ArrDel15"].fillna(0) == 0)).astype("int8")
    crs_dep = frame["CRSDepTime"].fillna(-1).astype(int)
    hour = crs_dep // 100
    frame["departure_period"] = np.select(
        [hour.between(0, 5), hour.between(6, 10), hour.between(11, 14), hour.between(15, 18), hour.between(19, 23)],
        ["Overnight", "Morning", "Midday", "Afternoon", "Evening"], default="Unknown",
    )
    delay = frame["arrival_delay_minutes"]
    frame["delay_severity"] = np.select(
        [frame["operated"] == 0, delay < 15, delay.between(15, 29), delay.between(30, 59), delay.between(60, 119), delay >= 120],
        ["Not applicable", "On time", "15-29", "30-59", "60-119", "120+"], default="Unknown",
    )
    for source, target in [
        ("CarrierDelay", "carrier_delay"), ("WeatherDelay", "weather_delay"),
        ("NASDelay", "nas_delay"), ("SecurityDelay", "security_delay"),
        ("LateAircraftDelay", "late_aircraft_delay"),
    ]:
        frame[target] = frame[source].fillna(0).clip(lower=0)
    frame["total_delay_minutes"] = frame[["carrier_delay", "weather_delay", "nas_delay", "security_delay", "late_aircraft_delay"]].sum(axis=1)
    flight_no = frame["Flight_Number_Reporting_Airline"].fillna(-1).astype("int64").astype(str)
    frame["flight_key"] = (
        frame["flight_date"].dt.strftime("%Y-%m-%d") + "|" + frame["airline_key"].astype(str) + "|" + flight_no + "|" +
        frame["origin_airport_key"].astype(str) + "|" + frame["dest_airport_key"].astype(str) + "|" + crs_dep.astype(str)
    )
    frame["cancellation_code"] = frame.get("CancellationCode", pd.Series(pd.NA, index=frame.index)).fillna("Unknown").astype(str).str.strip()
    output = [
        "flight_key", "flight_date", "flight_month", "year", "month", "weekday", "is_weekend",
        "airline_key", "reporting_airline", "airline_name", "origin_airport_key", "dest_airport_key",
        "Origin", "Dest", "OriginCityName", "DestCityName", "OriginState", "DestState", "route_key",
        "departure_period", "delay_severity", "cancelled", "cancellation_code", "diverted", "operated",
        "arrived_on_time", "delayed_flight", "arrival_delay_minutes", "Distance", "carrier_delay", "weather_delay",
        "nas_delay", "security_delay", "late_aircraft_delay", "total_delay_minutes",
    ]
    return frame[output].rename(columns={
        "Origin": "origin", "Dest": "dest", "OriginCityName": "origin_city_name", "DestCityName": "dest_city_name",
        "OriginState": "origin_state", "DestState": "dest_state", "Distance": "distance_miles",
    })


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True); PROCESSED.mkdir(parents=True, exist_ok=True); EXPORTS.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    raw_rows = retained_rows = 0
    first = True
    for year in YEARS:
        for month in MONTHS:
            zip_path = download(year, month)
            with zipfile.ZipFile(zip_path) as archive:
                csv_name = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
                with archive.open(csv_name) as source:
                    for chunk in pd.read_csv(source, usecols=lambda col: col in CANDIDATES, chunksize=CHUNK_SIZE, low_memory=False):
                        raw_rows += len(chunk)
                        clean = process_chunk(chunk)
                        retained_rows += len(clean)
                        con.register("chunk_frame", clean)
                        if first:
                            con.execute("CREATE TABLE fact_flights AS SELECT * FROM chunk_frame")
                            first = False
                        else:
                            con.execute("INSERT INTO fact_flights SELECT * FROM chunk_frame")
                        con.unregister("chunk_frame")
            zip_path.unlink(missing_ok=True)
            print(f"Loaded {year}-{month:02d}; raw rows so far: {raw_rows:,}", flush=True)
    con.execute("CREATE TABLE dim_date AS SELECT DISTINCT flight_date AS date_key, year, month, weekday, is_weekend FROM fact_flights ORDER BY date_key")
    con.execute("CREATE TABLE dim_airline AS SELECT DISTINCT airline_key, reporting_airline, airline_name FROM fact_flights ORDER BY airline_key")
    con.execute("CREATE TABLE dim_airport AS SELECT DISTINCT origin_airport_key AS airport_key, origin AS airport_code, origin_city_name AS city_name, origin_state AS state_code FROM fact_flights UNION SELECT DISTINCT dest_airport_key, dest, dest_city_name, dest_state FROM fact_flights")
    con.execute("CREATE TABLE dim_route AS SELECT DISTINCT route_key, origin, dest, origin_airport_key, dest_airport_key FROM fact_flights")
    con.execute("COPY fact_flights TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(PROCESSED / "fact_flights.parquet")])
    for table in ("dim_date", "dim_airline", "dim_airport", "dim_route"):
        con.execute(f"COPY {table} TO ? (HEADER, DELIMITER ',')", [str(PROCESSED / f"{table}.csv")])
    checks = con.execute("""
        SELECT COUNT(*) AS fact_rows, COUNT(DISTINCT flight_key) AS unique_keys,
               COUNT(*) - COUNT(DISTINCT flight_key) AS duplicate_key_rows,
               MIN(flight_date) AS min_date, MAX(flight_date) AS max_date,
               SUM(cancelled) AS cancelled_flights, SUM(diverted) AS diverted_flights
        FROM fact_flights
    """).fetchdf().iloc[0].to_dict()
    checks.update({"source_raw_rows": int(raw_rows), "retained_rows": int(retained_rows), "retention_rate": retained_rows / raw_rows if raw_rows else None})
    with open(PROCESSED / "quality_profile.json", "w") as file:
        json.dump(checks, file, default=str, indent=2)
    con.close()
    print(json.dumps(checks, default=str, indent=2))


if __name__ == "__main__":
    main()
