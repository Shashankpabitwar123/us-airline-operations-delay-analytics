-- U.S. Airline Operations & Delay Root-Cause Analytics
-- Engine: DuckDB. All queries use the cleaned fact_flights model built from BTS monthly files.

-- 1. Monthly operations and on-time trend.
SELECT date_trunc('month', flight_date) AS month_start,
       COUNT(*) AS scheduled_flights,
       AVG(arrived_on_time) AS on_time_rate,
       AVG(delayed_flight) AS arrival_delay_rate,
       AVG(cancelled) AS cancellation_rate,
       AVG(diverted) AS diversion_rate
FROM fact_flights
GROUP BY 1
ORDER BY 1;

-- 2. Delay-cause contribution by year using conditional aggregation.
SELECT year,
       SUM(carrier_delay) AS carrier_minutes,
       SUM(weather_delay) AS weather_minutes,
       SUM(nas_delay) AS nas_minutes,
       SUM(security_delay) AS security_minutes,
       SUM(late_aircraft_delay) AS late_aircraft_minutes
FROM fact_flights
GROUP BY 1
ORDER BY 1;

-- 3. Carrier-month performance with an explicit minimum-volume threshold.
WITH carrier_month AS (
  SELECT flight_month, reporting_airline, airline_name, COUNT(*) AS flights,
         AVG(delayed_flight) AS delay_rate, AVG(arrived_on_time) AS on_time_rate
  FROM fact_flights
  GROUP BY 1,2,3
)
SELECT * FROM carrier_month WHERE flights >= 500 ORDER BY flight_month, delay_rate DESC;

-- 4. High-volume route rankings using a window function.
WITH route_metrics AS (
  SELECT route_key, origin, dest, COUNT(*) AS flights, AVG(delayed_flight) AS delay_rate
  FROM fact_flights GROUP BY 1,2,3
), ranked AS (
  SELECT *, DENSE_RANK() OVER (ORDER BY delay_rate DESC) AS delay_rate_rank
  FROM route_metrics WHERE flights >= 1000
)
SELECT * FROM ranked ORDER BY delay_rate_rank, route_key;

-- 5. Airport rankings with a minimum-flight threshold.
SELECT origin_airport_key, origin, origin_city_name, origin_state,
       COUNT(*) AS departures, AVG(delayed_flight) AS delay_rate,
       AVG(cancelled) AS cancellation_rate
FROM fact_flights
GROUP BY 1,2,3,4 HAVING COUNT(*) >= 5000
ORDER BY delay_rate DESC;

-- 6. Seasonal and departure-period comparisons.
SELECT year, month, departure_period, COUNT(*) AS flights,
       AVG(delayed_flight) AS delay_rate, AVG(arrival_delay_minutes) AS mean_arrival_delay_minutes
FROM fact_flights GROUP BY 1,2,3 ORDER BY 1,2,3;

-- 7. Rolling three-month delay rate by carrier.
WITH monthly AS (
  SELECT flight_month, reporting_airline, COUNT(*) AS flights, AVG(delayed_flight) AS delay_rate
  FROM fact_flights GROUP BY 1,2
)
SELECT *, AVG(delay_rate) OVER (PARTITION BY reporting_airline ORDER BY flight_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS rolling_3m_delay_rate
FROM monthly ORDER BY reporting_airline, flight_month;

-- 8. Year-over-year month comparison.
WITH monthly AS (
  SELECT year, month, COUNT(*) AS flights, AVG(delayed_flight) AS delay_rate
  FROM fact_flights GROUP BY 1,2
)
SELECT *, delay_rate - LAG(delay_rate) OVER (PARTITION BY month ORDER BY year) AS yoy_delay_rate_change
FROM monthly ORDER BY year, month;

-- 9. Comparable carrier performance within route-month cells.
WITH route_carrier AS (
  SELECT flight_month, route_key, reporting_airline, COUNT(*) AS flights, AVG(delayed_flight) AS delay_rate
  FROM fact_flights GROUP BY 1,2,3
), comparable AS (
  SELECT * FROM route_carrier WHERE flights >= 100
)
SELECT flight_month, route_key, reporting_airline, flights, delay_rate,
       AVG(delay_rate) OVER (PARTITION BY flight_month, route_key) AS route_month_peer_delay_rate,
       delay_rate - AVG(delay_rate) OVER (PARTITION BY flight_month, route_key) AS relative_delay_rate
FROM comparable ORDER BY flight_month, route_key, reporting_airline;

-- 10. Data-quality reconciliation and duplicate-key test.
SELECT COUNT(*) AS fact_rows, COUNT(DISTINCT flight_key) AS unique_flight_keys,
       COUNT(*) - COUNT(DISTINCT flight_key) AS duplicate_key_rows,
       MIN(flight_date) AS min_date, MAX(flight_date) AS max_date
FROM fact_flights;
