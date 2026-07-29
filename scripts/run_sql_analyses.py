#!/usr/bin/env python3
"""Execute reviewed DuckDB analyses and export compact workbook-ready tables."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "airline_operations.duckdb"
OUT = ROOT / "data" / "exports"

QUERIES = {
    "monthly_operations": """
        SELECT flight_month AS month_start, year, month, COUNT(*) AS scheduled_flights,
               SUM(operated) AS operated_flights, AVG(arrived_on_time) AS on_time_rate,
               AVG(delayed_flight) AS arrival_delay_rate, AVG(cancelled) AS cancellation_rate,
               AVG(diverted) AS diversion_rate, AVG(arrival_delay_minutes) AS average_arrival_delay_minutes
        FROM fact_flights GROUP BY 1,2,3 ORDER BY 1
    """,
    "delay_drivers": """
        SELECT year, SUM(carrier_delay) AS carrier_minutes, SUM(weather_delay) AS weather_minutes,
               SUM(nas_delay) AS nas_minutes, SUM(security_delay) AS security_minutes,
               SUM(late_aircraft_delay) AS late_aircraft_minutes,
               SUM(total_delay_minutes) AS total_reported_delay_minutes
        FROM fact_flights GROUP BY 1 ORDER BY 1
    """,
    "departure_period": """
        SELECT year, month, departure_period, COUNT(*) AS flights, AVG(delayed_flight) AS delay_rate,
               AVG(arrived_on_time) AS on_time_rate, AVG(arrival_delay_minutes) AS mean_arrival_delay_minutes
        FROM fact_flights GROUP BY 1,2,3 ORDER BY 1,2,3
    """,
    "airport_performance": """
        SELECT origin_airport_key, origin, origin_city_name, origin_state, COUNT(*) AS departures,
               AVG(delayed_flight) AS delay_rate, AVG(cancelled) AS cancellation_rate,
               AVG(diverted) AS diversion_rate, AVG(arrival_delay_minutes) AS mean_arrival_delay_minutes
        FROM fact_flights GROUP BY 1,2,3,4 HAVING COUNT(*) >= 5000 ORDER BY delay_rate DESC
    """,
    "route_performance": """
        SELECT route_key, origin, dest, COUNT(*) AS flights, AVG(delayed_flight) AS delay_rate,
               AVG(cancelled) AS cancellation_rate, AVG(arrival_delay_minutes) AS mean_arrival_delay_minutes
        FROM fact_flights GROUP BY 1,2,3 HAVING COUNT(*) >= 1000 ORDER BY delay_rate DESC
    """,
    "carrier_route_comparison": """
        WITH route_carrier AS (
          SELECT flight_month, route_key, reporting_airline, airline_name, COUNT(*) AS flights,
                 AVG(delayed_flight) AS delay_rate
          FROM fact_flights GROUP BY 1,2,3,4
        ), comparable AS (SELECT * FROM route_carrier WHERE flights >= 100)
        SELECT *, AVG(delay_rate) OVER (PARTITION BY flight_month, route_key) AS route_month_peer_delay_rate,
               delay_rate - AVG(delay_rate) OVER (PARTITION BY flight_month, route_key) AS relative_delay_rate
        FROM comparable ORDER BY flight_month, route_key, reporting_airline
    """,
    "cancellation_diversion": """
        SELECT origin, origin_city_name, origin_state, COUNT(*) AS scheduled_flights,
               SUM(cancelled) AS cancelled_flights, SUM(diverted) AS diverted_flights,
               AVG(cancelled) AS cancellation_rate, AVG(diverted) AS diversion_rate
        FROM fact_flights GROUP BY 1,2,3 HAVING COUNT(*) >= 5000
        ORDER BY cancellation_rate DESC, diversion_rate DESC
    """,
    "quality_reconciliation": """
        SELECT COUNT(*) AS fact_rows, COUNT(DISTINCT flight_key) AS unique_flight_keys,
               COUNT(*) - COUNT(DISTINCT flight_key) AS duplicate_key_rows,
               MIN(flight_date) AS min_flight_date, MAX(flight_date) AS max_flight_date,
               SUM(cancelled) AS cancelled_flights, SUM(diverted) AS diverted_flights,
               SUM(operated) AS operated_flights
        FROM fact_flights
    """,
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    for name, query in QUERIES.items():
        dataframe = con.execute(query).fetchdf()
        dataframe.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name}: {len(dataframe):,} rows")
    con.close()

if __name__ == "__main__":
    main()
