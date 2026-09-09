> **Superseded release.** This folder preserves the original Excel project. Its arrival-rate calculation was corrected in the current release. Use the [current project](../../README.md) and [current metric definitions](../../docs/methodology_and_limitations.md) for findings.

# U.S. Airline Operations & Delay Root-Cause Analytics

**Tools:** Excel, Power Query, SQL, Python, Statistics

## Purpose

Analyze U.S. domestic flight operations from complete BTS Reporting Carrier On-Time Performance files for 2023-2025. The project examines on-time performance, delay causes, cancellations, diversions, high-volume airports/routes, and operational factors associated with delay risk.

## Start here (plain-English guide)

This project answers a simple operations question: **where and when are flight disruptions most common, and what patterns should an operations team investigate first?**

1. Open the [Excel workbook](excel/US_Airline_Operations_Delay_Root_Cause_Analytics.xlsx) for the business-facing analysis and charts.
2. Read the [executive memo](docs/executive_memo.md) for the five findings, recommended actions, and their limits.
3. Review the [Data Quality](docs/data_quality_report.md) and [Definitions](docs/data_dictionary.md) documents to see exactly how rates were calculated.
4. Open the SQL, Power Query, Python notebook, and model diagram only if you want to inspect the technical work behind the results.

In short, I collected all 36 monthly BTS files for 2023-2025, cleaned and checked the flight records, built a star-shaped analytical model, calculated operational rates, compared high-volume airports/routes/carriers fairly, and presented the results in Excel. The project identifies patterns worth investigating; it does **not** claim that an airline, airport, or time of day caused a delay.

## Source and scope

- Source: [BTS Reporting Carrier On-Time Performance](https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ)
- Coverage: complete January 2023 through December 2025 monthly files
- Grain: one reported scheduled domestic flight record
- On-time definition: arrival delay under 15 minutes for operated, non-diverted flights

## Repository structure

- `scripts/` - reproducible download, transformation, SQL-export, notebook, and workbook builders
- `sql/` - reviewed analytical queries
- `data/processed/` - compact dimension tables and quality profile (committed); detailed fact files and DuckDB model are generated locally and not committed
- `data/exports/` - generated, compact dashboard/workbook extracts (not committed)
- `docs/` - data dictionary, transformation log, quality report, methodology, and executive memo
- `notebooks/` - executed Python/statistics analysis
- `excel/` - final Excel presentation workbook and rendered QA screenshots

## Run order

1. `python scripts/build_dataset.py`
2. `python scripts/run_sql_analyses.py`
3. `python scripts/build_notebook.py`
4. `jupyter nbconvert --execute --to notebook --inplace notebooks/airline_operations_analysis.ipynb`
5. `node scripts/build_excel_workbook.mjs`

## Final Excel workbook

`excel/US_Airline_Operations_Delay_Root_Cause_Analytics.xlsx` is the primary presentation layer. It includes Executive Summary, Delay Trends, Delay Drivers, Airport Analysis, Carrier and Route Analysis, Data Quality, and Definitions worksheets. The workbook uses formula-driven annual rollups, `SUMIFS`, `COUNTIFS`, `IFERROR`, `XLOOKUP`, native Excel tables and filters, a PivotTable with a PivotTable-linked chart, conditional formatting, and interactive airport lookup. It intentionally loads compact, reconciled aggregates rather than the 20.93M-row fact table, which exceeds Excel's worksheet limit.

## Reconciled headline results

- 20,928,579 scheduled records; 0 duplicate candidate business keys.
- 77.5% weighted on-time rate and 20.9% weighted arrival-delay rate across the complete period.
- 2025 on-time rate: 76.3%, down from 78.2% in 2023.
- 2025 largest reported delay-minute category: late aircraft (39.2%).

## Interpretation limits

- Associations are not causal findings. Carrier, airport, route, and departure-period comparisons can be affected by network, weather, seasonality, and route mix.
- Delay-cause minutes are reported fields and may be missing or not applicable for some flight outcomes.
- Rankings use documented minimum-flight thresholds to avoid over-interpreting small samples.
