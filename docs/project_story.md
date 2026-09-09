# From flight records to a dashboard

## The question

I wanted to understand when flights tend to arrive late and let someone explore that question for an airport or airline they know. The project started in Excel. I then expanded the data through June 2026 and built an interactive Tableau version on one dashboard.

## The data work behind the charts

The dataset contains 24,416,952 scheduled flights across 42 months. Python reads the monthly BTS releases, standardizes the fields and saves Parquet files. SQL builds the flight table and smaller tables for months, airports, airlines, departure times and routes.

The original release needed a metric correction. Its arrival flags were averaged over scheduled flights, even though the intended definition excluded cancellations and diversions. I rebuilt the flags from recorded arrival-delay minutes and made the denominator explicit. This matters because a dashboard can look right while describing the wrong population.

A flight is late when it arrives at least 15 minutes after schedule. Arrival rates use flights with a recorded arrival that were neither cancelled nor diverted. Cancellation rates use all planned flights. Each chart divides summed counts, rather than averaging percentages from smaller groups.

Checks reconcile the source records, flight table and summaries. The current snapshot has no duplicate candidate flight keys, two missing arrival-delay records and coordinates for all 367 airport codes. [Quality report](data_quality_report.md) · [Metric definitions](data_dictionary.md)

## Two ways to explore the same analysis

**Excel** provides network, airport, airline and time-of-day views, with supporting data and audit sheets. A separate Power Query script imports the monthly CSV export. The saved workbook can be opened without running the Python pipeline.

**Tableau** combines departure-time comparisons, morning versus evening, reported delay reasons and a U.S. route map. The layout follows a simple reading order: choose flights at the top, compare the charts, then explore the map below. Filters, reset and help controls support that flow.

The data is aggregated by year, month, directional route, carrier and departure period. That produces 1,006,379 summary rows while preserving the counts needed by the filters. The final Hyper extract adds 93,900 route-geometry rows; those rows carry zero additive flight counts. Geometry therefore does not multiply the reported totals. The map displays up to 150 busy routes at once.

## Getting the published workbook to work

Earlier generated workbooks had two separate classes of problems:

- **Workbook errors:** unsupported XML elements, invalid attribute values, missing sheet registrations and inconsistent field references prevented some versions from opening.
- **Public loading problems:** a simple workbook using the CSV-derived data published successfully, and a full dashboard with actions removed also loaded successfully. These tests showed that file size alone did not explain the failure and narrowed the investigation to workbook structure and actions. They did not establish one failing action as the sole cause.

The successful approach was to keep a known-working Tableau workbook frame, use supported native structures and restore actions with their required feature declarations. Later visual edits were made within that working frame. The finished packaged workbook includes five actions and renders on Tableau Public.

I also corrected clipped wording, simplified the help panel, matched route legend colors to the map, used line-shaped legend marks, standardized airport labels and gave the map more space. The preview in the main README comes from the published dashboard itself.

## What the results mean

In January–June 2026, 14.2% of eligible morning arrivals were late, compared with 29.8% of evening arrivals. This is an observed comparison, not a causal estimate. The notebook adds a restricted comparison within the same route, carrier and month; it is kept separate from the dashboard's all-selected-flights figures.

Reported delay reasons describe shares of attributed delay minutes. They are not shares of flights, and weather can also appear indirectly in other categories. Route curves connect airports schematically; they are not recorded paths or live aircraft positions.

## Where to go next

[Explore Tableau](https://public.tableau.com/app/profile/shashank.pabitwar/viz/WHENAMERICARUNSLATE/WhenAmericaRunsLate) · [Open Excel](../excel/Flightpath.xlsx) · [Read the notebook](../notebooks/flightpath_analysis.ipynb) · [Inspect the SQL](../sql/analysis_queries.sql)
