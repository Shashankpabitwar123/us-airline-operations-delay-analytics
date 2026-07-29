# Data Dictionary

## fact_flights

**Grain:** one reported scheduled domestic flight record. The model retains cancelled and diverted flights so operations totals reconcile to BTS. On-time and arrival-delay metrics use operated, non-diverted flights unless stated otherwise.

| Field | Definition |
| --- | --- |
| flight_key | Stable composite key: flight date, reporting carrier DOT ID, flight number, origin airport ID, destination airport ID, and scheduled departure time |
| flight_date | Scheduled flight date |
| airline_key | BTS DOT reporting-carrier ID |
| origin_airport_key / dest_airport_key | BTS airport IDs; role-playing keys to dim_airport |
| route_key | Normalized origin-destination airport pair |
| cancelled / diverted | BTS reported operation flags |
| arrived_on_time | 1 when operated, non-diverted, and arrival delay is less than 15 minutes; otherwise 0/null when not applicable |
| arrival_delay_minutes | BTS arrival delay; negative early arrivals are retained in detail and excluded from delay-minute totals |
| total_delay_minutes | Sum of nonnegative reported carrier, weather, NAS, security, and late-aircraft delay minutes |
| departure_period | Derived from scheduled departure time: overnight, morning, midday, afternoon, evening |
| delay_severity | Derived for operated, non-diverted flights: on time, 15-29, 30-59, 60-119, 120+ minutes |

## Dimensions

| Table | Key | Purpose |
| --- | --- | --- |
| dim_date | date_key | Date, year, month, weekday, and weekend attributes |
| dim_airline | airline_key | Reporting carrier identifiers and names |
| dim_airport | airport_key | Airport code, city, state, and role-playing origin/destination use |
| dim_route | route_key | Normalized airport-pair route |

## Core metrics

- **Flight count:** count of fact_flights rows.
- **Arrival delay rate:** delayed operated/non-diverted flights divided by operated/non-diverted flights; delayed means arrival delay of 15+ minutes.
- **On-time rate:** operated/non-diverted flights with arrival delay below 15 minutes divided by operated/non-diverted flights.
- **Cancellation rate:** cancelled flights divided by all scheduled flight records.
- **Diversion rate:** diverted flights divided by all scheduled flight records.
- **Delay-cause contribution:** a cause's nonnegative reported minutes divided by all nonnegative reported delay-cause minutes in scope.
