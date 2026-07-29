# Data Quality Report

## Dataset and grain

- Source: BTS Reporting Carrier On-Time Performance monthly files.
- Coverage: 2023-01-01 through 2025-12-31.
- Grain: one scheduled domestic flight record.
- Raw source rows: 20,928,579.
- Retained fact rows: 20,928,579 (100.0% retained after required-key checks).

## Checks performed and results

| Check | Result | Status |
| --- | ---: | --- |
| Candidate flight keys | 20,928,579 distinct of 20,928,579 rows | PASS |
| Duplicate candidate-key rows | 0 | PASS |
| Date coverage | 2023-01-01 to 2025-12-31 | PASS |
| Fact to dimension model | Date, airline, airport, and route dimensions generated from fact keys | PASS |
| Arrival-delay missingness | 1.63% | Expected: cancelled/diverted flight outcomes are not applicable |
| Distance missingness | 0.00% | PASS |
| Cancelled flights with Unknown cancellation code | 0.00% | PASS |
| Scheduled flights reconciled | 20,928,579 fact rows | PASS |
| Cancelled flights | 287,134 | Reconciled operational population |
| Diverted flights | 53,309 | Reconciled operational population |

## Analytical risks and treatment

- **Cancelled/diverted arrival fields:** Arrival delay is null when arrival performance is not applicable. These records remain in cancellation/diversion denominators and are excluded from on-time/delay-rate denominators.
- **Departure-period Unknown:** Two records did not map to a planned departure-period bin. This is negligible but remains visible rather than being silently relabeled.
- **Candidate key:** The composite key is unique in this extract. The project still documents it as a candidate business key rather than implying BTS guarantees a universal immutable event identifier.
- **Volume thresholds:** Airport analysis requires 5,000 departures; route analysis requires 1,000 flights; route-month carrier comparisons require 100 flights per carrier cell.

## Automated controls to keep

1. Candidate flight-key uniqueness.
2. Required date/carrier/origin/destination key completeness.
3. Monthly date-coverage check for each expected BTS partition.
4. Dimension-join duplication/coverage checks.
5. Source-to-model and model-to-workbook row-count reconciliation.
