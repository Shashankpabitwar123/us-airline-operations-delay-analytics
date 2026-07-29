# U.S. Airline Operations & Delay Root-Cause Analytics

**Tools:** Excel, Power Query, SQL, Python, Statistics

## Purpose

Analyze U.S. domestic flight operations from complete BTS Reporting Carrier On-Time Performance files for 2023-2025. The project examines on-time performance, delay causes, cancellations, diversions, high-volume airports/routes, and operational factors associated with delay risk.

## Source and scope

- Source: [BTS Reporting Carrier On-Time Performance](https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ)
- Coverage: complete January 2023 through December 2025 monthly files
- Grain: one reported scheduled domestic flight record
- On-time definition: arrival delay under 15 minutes for operated, non-diverted flights

## Repository structure

- `scripts/` - reproducible download, transformation, SQL-export, notebook, and workbook builders
- `sql/` - reviewed analytical queries
- `data/processed/` - generated fact/dimension tables and DuckDB model (not committed)
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
