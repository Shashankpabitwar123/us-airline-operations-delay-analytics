# Methods and limitations

## Arrival-rate correction
The old release documented an eligible-arrival denominator but averaged zero/one arrival flags across scheduled flights. Recomputed results use actual recorded arrival-delay minutes and explicitly exclude cancelled, diverted and missing-arrival records. Full-year 2025 on-time rate is **77.69%**, replacing the old 76.3% claim. There are two missing arrival-delay records across the full refreshed dataset.

## Comparable periods
Excel reader pages compare January–June of the selected year so incomplete 2026 is compared with equal windows. All 42 months remain in Monthly data. Tableau readers must inspect selected year/month coverage; 2023–2025 are complete years and 2026 is January–June.

## Matched departure-period comparison
A cell is directional route × reporting carrier × year/month. Morning is 06:00–10:59; evening is 19:00–23:59. Each must have at least 30 eligible arrivals. Compute each cell's delay rates, then use the smaller period count as the common weight for both rates. The reported gap is weighted evening minus weighted morning. Sensitivity repeats with minimum 60 and 100 arrivals. The notebook reports cell count and represented eligible arrivals.

This controls the matching dimensions only. It does not identify the effect of changing departure time. Schedule composition, weekday, weather, congestion and other variables can remain different. Flights are clustered in operations and time; no unsupported independent-flight significance test is presented.

## Airline peers
Within route/year/month, retain carriers with at least 100 eligible arrivals. A focal carrier must have qualifying competitors. Peer rates exclude the focal carrier; aggregate gaps use focal eligible-arrival weights. Results apply to this competitive-route sample, not a universal airline ranking. The legacy self-including peer calculation is archived.

## Reported causes
Shares refer to reported attributed minutes. They are not the share of flights or passengers affected. Weather can contribute indirectly through NAS and late aircraft, so the weather category is not total weather impact. No causal propagation model, live tracking, ticket cost or passenger-loss estimate is claimed.

## Provenance and refresh
The 2023–2025 local bootstrap is an inherited processed snapshot. Original raw ZIP hashes were not retained. New releases have raw ZIP and Parquet SHA-256 hashes and retrieval timestamps. A clean full download may differ if BTS revises historical releases. Scripts stop on failed count/key/reconciliation checks. Airport coordinates are reference enrichment rather than the historical geographic authority for flight performance.
