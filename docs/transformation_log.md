# Power Query / ETL Transformation Log

| Step | Transformation | Purpose |
| --- | --- | --- |
| 1 | Folder-based monthly BTS import | Load one complete source file per month for 2023-2025 |
| 2 | Column selection and type correction | Keep operational fields; cast dates, flags, IDs, and numeric delay fields |
| 3 | Normalize text/keys | Trim carrier, airport, city/state, and cancellation-code values; construct stable route and flight keys |
| 4 | Duplicate detection | Test exact duplicated flight keys and preserve a documented reconciliation result |
| 5 | Missing-value treatment | Retain cancelled/diverted records; use null where arrival-only metrics are not applicable; map missing cancellation codes to Unknown only when cancelled |
| 6 | Derived flags | Create operated, arrived-on-time, delayed-flight, cancellation, diversion, and valid-delay-cause fields |
| 7 | Derived categories | Create departure periods and delay-severity bands |
| 8 | Dimension extraction | Build date, airline, airport, and route dimensions from the cleaned fact data |
| 9 | Reconciliation | Compare raw rows, retained rows, unique keys, and aggregate totals before publishing extracts |

The Python pipeline implements the same logged business logic so that the project can be rerun outside Excel. The Excel workbook documents the equivalent folder-import design and uses compact generated aggregates rather than loading raw flight-level data into worksheets.
