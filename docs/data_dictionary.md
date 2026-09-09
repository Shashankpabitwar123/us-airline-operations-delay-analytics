# Data dictionary

## Grain and keys
`fact_flights`: one reporting-carrier scheduled flight. Candidate key combines date, DOT carrier, reporting flight number, origin/destination airport IDs and scheduled departure time. All 24,416,952 candidate keys are unique in this snapshot; the key is not a universal airline identity.

`tableau_operations`: year × month × directional origin/destination × reporting carrier × departure period. Counts and minutes are additive; coordinates and labels are dimensions. 1,006,379 rows.

`monthly`, `hourly`, `airport_monthly`, `carrier_monthly`, `route_monthly`, `airport_hourly`: respective grouping dimensions plus additive metrics. `matched_dayparts` and `carrier_peers` are restricted comparison samples, not complete traffic totals.

## Metrics
| Field / measure | Meaning |
|---|---|
| scheduled_flights | All records, including cancellations/diversions |
| eligible_arrivals | Not cancelled, not diverted, recorded arrival-delay minutes |
| on_time_flights | Eligible arrival delay <15 minutes, including early arrivals |
| delayed_flights | Eligible arrival delay >=15 minutes |
| severe_flights | Eligible arrival delay >=60 minutes |
| cancelled_flights | Cancelled scheduled flights |
| diverted_flights | Diverted scheduled flights |
| *_minutes | Reported carrier/weather/NAS/security/late-aircraft cause minutes |
| delay_rate | SUM(delayed_flights) / SUM(eligible_arrivals) |
| cancellation_rate | SUM(cancelled_flights) / SUM(scheduled_flights) |

Aggregate rates must be recomputed from counts; do not average subgroup percentages. Zero denominator displays no result / n.a., not zero performance.

Scheduled departure time is origin-local. 2400 maps to hour zero. Periods: overnight 00–05, morning 06–10, midday 11–14, afternoon 15–18, evening 19–23. Arrival delay is the outcome even when grouping by departure hour.

Carrier names use stable DOT carrier IDs. Airports use period airport codes/IDs and a current geographic reference; historical PBI is explicitly retained. This is domestic reporting-carrier coverage, not every U.S. aircraft movement.
