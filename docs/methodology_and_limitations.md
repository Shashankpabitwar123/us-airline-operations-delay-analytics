# Methodology and Limitations

## Analytical design

The project uses BTS Reporting Carrier On-Time Performance monthly files for complete 2023-2025 calendar years. The detailed model is built at the scheduled-flight grain and retains cancelled and diverted records to support operational-rate reconciliation.

Arrival-delay rate and on-time rate are calculated only for operated, non-diverted flights. A delayed arrival is 15 or more minutes late; an on-time arrival is under 15 minutes late. Cancellation/diversion rates use all scheduled flight records as the denominator.

Airport and route rankings use documented minimum-flight thresholds. Carrier comparison uses route-month cells with at least 100 carrier flights to reduce, but not eliminate, route-mix differences.

## Statistical approach

- Wilson 95% confidence intervals communicate uncertainty around high-volume airport delay rates.
- Controlled carrier comparisons measure the difference between a carrier's delay rate and its route-month peer average.
- Outlier review uses distribution/severity bands, not a claim that extreme delays were data errors.

## Limitations

- Observational associations do not establish causality.
- Carrier/airport operations differ in network mix, schedule design, weather exposure, and passenger/aircraft flows.
- BTS delay-cause fields are reported operational categories, not independent causal experiments.
- Cancelled and diverted flights do not always have arrival-delay or delay-cause values; these are correctly treated as not applicable rather than zero-delay flights.
- The workbook is a presentation layer. It uses aggregated exports because full detailed data exceeds normal Excel worksheet limits.
