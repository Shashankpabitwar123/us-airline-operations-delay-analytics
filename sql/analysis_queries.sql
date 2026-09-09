-- Run against data/processed/flightpath.duckdb after scripts/refresh.py.
-- Recalculate aggregate rates from additive counts.
SELECT year, SUM(scheduled_flights) AS flights,
       SUM(on_time_flights)::DOUBLE / SUM(eligible_arrivals) AS on_time_rate,
       SUM(cancelled_flights)::DOUBLE / SUM(scheduled_flights) AS cancellation_rate
FROM monthly WHERE month <= 6 GROUP BY year ORDER BY year;

-- Restricted matched sample; descriptive, not causal.
SELECT year, COUNT(*) AS matched_cells,
       SUM(morning_n + evening_n) AS represented_arrivals,
       SUM(common_weight * gap) / SUM(common_weight) AS evening_minus_morning
FROM matched_dayparts WHERE month <= 6 GROUP BY year ORDER BY year;

-- Peer baseline excludes each focal carrier.
SELECT year, carrier_name, COUNT(*) AS matched_cells,
       SUM(n * gap) / SUM(n) AS difference_from_competitors
FROM carrier_peers LEFT JOIN dim_airline USING (airline_key)
WHERE month <= 6 GROUP BY year, carrier_name ORDER BY year, difference_from_competitors;
