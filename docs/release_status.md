# Release verification — September 9, 2026

## Tableau publication

The final dashboard is published at [When America Runs Late](https://public.tableau.com/app/profile/shashank.pabitwar/viz/WHENAMERICARUNSLATE/WhenAmericaRunsLate).

For this GitHub release, the packaged workbook and dashboard PNG were downloaded from that publication. The PNG was visually checked: the full dashboard, route legend, airport labels and footer render. The committed `.twbx` is that downloaded package, with a simpler filename; its data and workbook XML were not edited for this release.

- Package size: **23,978,205 bytes** (about 24 MB).
- One dashboard, **47 worksheets**, five actions.
- ZIP integrity and targeted workbook checks passed with no errors.
- The static checker reports one native wrapper-zone warning. It is not a complete Tableau schema validator or a replacement for application testing.
- The packaged Hyper extract matches the final locally tested version by SHA-256.

The author had confirmed that the dashboard worked before this release. A new end-to-end filter/reset/Desktop interaction test was **not** performed during the GitHub update; server rendering was checked through the publication's image export. No universal compatibility or load-time guarantee is claimed.

[Static inspection](evidence/tableau_static_inspection.json) · [Download hashes and verification receipt](evidence/github_release_verification.json)

## Data and analysis

The committed model evidence contains 26 passing checks. It reconciles 24,416,952 source records to the flight table and summary tables, checks candidate-key uniqueness and verifies the arrival/cancellation/diversion partition. Threshold checks cover actual records at the boundaries used in the calculations.

The committed notebook contains nine executed code cells, with no recorded error outputs. During this release review, its saved execution state and the evidence files were checked; the entire historical ingestion and notebook were not rerun.

## Excel

The saved workbook contains ten sheets, 229 formulas, three charts and two data-validation controls. The development checks include recalculation, selector changes, formula-error scanning and rendered sheets. The saved workbook's ZIP integrity was also checked for this release.

Native Microsoft Excel interaction and the separate Power Query import were not tested. The saved workbook does not require the builder runtime to open, but rebuilding its layout from the JavaScript script requires the development runtime described in the [reproduction guide](reproduction.md).

## Refresh-script correction

The GitHub version fixes the source-row reconciliation to count only partitions loaded for the requested date window. Focused checks cover a fresh clone with a stale inherited manifest entry, a run using the historical snapshot and a shorter requested period. They stop before database generation; they are not a new full data refresh.

## Version history

The [2025 archive](../archive/2025-release/README.md) preserves the original Excel-only project. Its old arrival-rate figures are superseded by the [corrected method](methodology_and_limitations.md). The current release expands coverage through June 2026, adds the published Tableau dashboard and packages the supporting analysis and evidence.
