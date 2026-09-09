# Quality report — refreshed build

- Source records: 24,416,952; unique candidate flight keys: 24,416,952.
- Coverage: 42 months, 2023-01-01 through 2026-06-30.
- Eligible arrivals: 23,990,755; cancellations: 363,216; diversions: 62,979; missing arrivals: 2.
- Outcome partition reconciles exactly to scheduled flights.
- All 367 airport codes map to coordinates. Scheduled hour missing: zero.
- All 26 model checks pass in [validation.json](evidence/validation.json).
- Independent flight-level versus Tableau-grain year/month reconciliation passes for counts, eligible arrivals and delayed arrivals.
- Actual records at 14/15, 59/60 and 119/120 minute boundaries are checked in [threshold_checks.csv](evidence/threshold_checks.csv).
- Executed notebook includes comparable-period analysis, matching coverage, threshold sensitivity and leave-one-out peers.
- Excel selectors were changed/recalculated for multiple years; formula-error scan found no errors. Every tab was rendered. Native Microsoft Excel is unavailable.

For exact presentation-application acceptance, see [release status](release_status.md). Structural validity is distinct from native visual and interaction validation.
