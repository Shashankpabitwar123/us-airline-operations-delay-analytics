# Reproduce or inspect the project

## Start with the finished files

You do not need to run the pipeline to explore the project. Open the [Excel workbook](../excel/Flightpath.xlsx), [Tableau workbook](../tableau/When_America_Runs_Late.twbx), [published dashboard](https://public.tableau.com/app/profile/shashank.pabitwar/viz/WHENAMERICARUNSLATE/WhenAmericaRunsLate) or [executed notebook](../notebooks/flightpath_analysis.ipynb).

## Rebuild the analytical data

The Python pipeline downloads BTS monthly releases, saves Parquet files, builds a local DuckDB database and exports summaries. A full historical download is substantial; it requires time, disk space and network access. Raw files and the flight-level database are excluded from Git.

From the repository root, in a Python 3.12 virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/refresh.py --through 2026-06
python scripts/build_evidence.py
```

Outputs include:

- `data/processed/flightpath.duckdb`: local flight table and analytical tables.
- `data/exports/`: summary CSVs and the Excel builder's JSON input.
- `data/source_manifest.json`: downloaded source metadata and active partitions.
- `docs/evidence/`: reconciliations, result tables and threshold checks.
- `notebooks/flightpath_analysis.ipynb`: regenerated, executed analysis.

`refresh.py` imports the parsing functions from `legacy_bts_loader.py`; run `refresh.py` as the entry point. It can reuse an optional local `historical_2023_2025.parquet` snapshot, but that large file is not distributed in this repository. Without it, the pipeline downloads the individual months. The row-count check now uses only the partitions loaded in the current run, so an inherited manifest entry or a later cached release is not counted twice.

The published snapshot used an inherited processed 2023–2025 dataset and six new 2026 monthly releases. Original 2023–2025 ZIP hashes were not retained. A fresh download may differ if BTS has revised historical files. The committed evidence describes the released snapshot; the full 24.42-million-flight pipeline was not rerun during the GitHub documentation update.

## Excel and Power Query

The saved `.xlsx` is ready to open. For the separate Power Query import, edit `ExportFolder` in [flightpath_monthly.pq](../power_query/flightpath_monthly.pq) and use it in Excel's Power Query editor. It imports the monthly export and calculates rates; it does not rebuild the entire workbook layout.

[scripts/build_excel.mjs](../scripts/build_excel.mjs) records the workbook-generation code. It requires the `@oai/artifact-tool` runtime used during development, which is not installed by `requirements.txt`. It is included for transparency, not advertised as a standalone public npm build. The Python data pipeline and executed notebook can be used independently.

## Tableau

The [packaged workbook](../tableau/When_America_Runs_Late.twbx) is the exact downloaded publication. Open it to inspect the data source, calculations, worksheets, layout and actions. It includes the combined flight-summary and route-geometry extract.

The Python analytical refresh does **not** automatically regenerate the final Tableau presentation extract, assets or `.twbx`. The published package is the reproducible presentation snapshot for this release. For a future data refresh, rebuild the same presentation schema, reconcile its additive counts and verify the workbook in Desktop and Public before replacing this release.

[Source data](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ) · [BTS release information](https://www.transtats.bts.gov/ReleaseInfo.asp) · [Airport coordinate reference](https://github.com/datasets/airport-codes) · [Methods](methodology_and_limitations.md)
