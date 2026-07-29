# Model Diagram and Grain

```text
dim_date (date_key) ----------------------> fact_flights (one scheduled domestic flight)
dim_airline (airline_key) ----------------> fact_flights
dim_airport (airport_key) --- origin role -> fact_flights.origin_airport_key
dim_airport (airport_key) ----- dest role -> fact_flights.dest_airport_key
dim_route (route_key) --------------------> fact_flights
```

All relationships are one-to-many from a dimension to `fact_flights`. The airport table is role-playing: the same airport dimension supplies both origin and destination descriptions. The Excel model documents this design; its workbook sheets consume only summarized extracts so raw data remains outside worksheet row limits.

## Key controls

- `flight_key` is the candidate business key used for duplicate tests.
- `airline_key` uses BTS DOT carrier ID, not only IATA code, because codes can change/recur.
- Airport analysis uses BTS airport IDs and retains codes/names for display.
- A row-count reconciliation compares raw monthly rows, retained model rows, unique candidate keys, and exported workbook totals.
