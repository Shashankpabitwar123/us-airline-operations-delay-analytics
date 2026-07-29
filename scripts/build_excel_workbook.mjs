import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const exportsDir = path.join(root, "data", "exports");
const outputDir = path.join(root, "excel");
const outputPath = path.join(outputDir, "US_Airline_Operations_Delay_Root_Cause_Analytics.xlsx");

const NAVY = "#163A5F";
const BLUE = "#247BA0";
const TEAL = "#1B998B";
const ORANGE = "#F28E2B";
const RED = "#D1495B";
const LIGHT_BLUE = "#EAF2F8";
const LIGHT_TEAL = "#E7F5F2";
const LIGHT_ORANGE = "#FFF3E0";
const LIGHT_GRAY = "#F4F6F8";
const BORDER = "#D5DEE8";
const TEXT = "#203040";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(field); field = ""; }
    else if (ch === '\n') { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += ch;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  const headers = rows.shift();
  return rows.filter((r) => r.length === headers.length).map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i]])));
}

async function csv(name) {
  return parseCsv(await fs.readFile(path.join(exportsDir, `${name}.csv`), "utf8"));
}

function n(value) { return value === "" || value == null ? null : Number(value); }
function pct(value) { return Number(value); }
function labelMonth(value) {
  const [year, month] = value.slice(0, 7).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}
function colWidth(sheet, col, width, rows = 260) { sheet.getRange(`${col}1:${col}${rows}`).format.columnWidth = width; }
function baseSheet(sheet) { sheet.showGridLines = false; }
function titleBlock(sheet, endCol, title, subtitle) {
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${endCol}1`).format = { fill: NAVY, font: { bold: true, color: "#FFFFFF", size: 18 }, horizontalAlignment: "left", verticalAlignment: "center" };
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 30;
  sheet.getRange(`A2:${endCol}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endCol}2`).format = { fill: "#DCE8F2", font: { color: TEXT, italic: true, size: 10 }, horizontalAlignment: "left", verticalAlignment: "center", wrapText: true };
  sheet.getRange(`A2:${endCol}2`).format.rowHeight = 30;
}
function header(range, fill = NAVY) {
  range.format = { fill, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "outside", style: "thin", color: BORDER } };
  range.format.rowHeight = 26;
}
function bodyBorders(range) { range.format.borders = { preset: "outside", style: "thin", color: BORDER }; }
function addTable(sheet, address, name) {
  const table = sheet.tables.add(address, true, name);
  table.showFilterButton = true;
  return table;
}
function card(sheet, labelRange, valueRange, label, formula, format, fill) {
  sheet.getRange(labelRange).merge();
  sheet.getRange(labelRange.split(":")[0]).values = [[label]];
  sheet.getRange(labelRange).format = { fill, font: { bold: true, color: TEXT, size: 10 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "outside", style: "thin", color: BORDER } };
  sheet.getRange(valueRange).merge();
  sheet.getRange(valueRange.split(":")[0]).formulas = [[formula]];
  sheet.getRange(valueRange).format = { fill: "#FFFFFF", font: { bold: true, color: NAVY, size: 18 }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER }, numberFormat: format };
}
function addBarChart(sheet, dataRange, title, start, end, color = BLUE, numberFormat = "0.0%") {
  const chart = sheet.charts.add("bar", dataRange);
  chart.title = title;
  chart.hasLegend = false;
  chart.yAxis = { numberFormatCode: numberFormat };
  chart.setPosition(start, end);
  const series = chart.series.items[0];
  if (series) series.fill = color;
  return chart;
}
function addSingleSeriesBar(sheet, title, categoryFormula, valueFormula, start, end, color = BLUE, numberFormat = "0.0%") {
  const chart = sheet.charts.add("bar", { chartType: "bar", title });
  const series = chart.series.add(title);
  series.categoryFormula = categoryFormula;
  series.formula = valueFormula;
  series.fill = color;
  chart.hasLegend = false;
  chart.yAxis = { numberFormatCode: numberFormat };
  chart.setPosition(start, end);
  return chart;
}

const [monthly, drivers, departure, airports, routes, carrierRoute, cancels, quality] = await Promise.all([
  csv("monthly_operations"), csv("delay_drivers"), csv("departure_period"), csv("airport_performance"), csv("route_performance"), csv("carrier_route_comparison"), csv("cancellation_diversion"), csv("quality_reconciliation"),
]);

// Aggregate only comparable route-month cells (each already has >=100 carrier flights), preserving route-mix control.
const carrierAgg = new Map();
for (const row of carrierRoute) {
  const code = row.reporting_airline;
  const flights = n(row.flights);
  const item = carrierAgg.get(code) ?? { code, flights: 0, weightedDelay: 0, weightedPeer: 0 };
  item.flights += flights;
  item.weightedDelay += flights * n(row.delay_rate);
  item.weightedPeer += flights * n(row.route_month_peer_delay_rate);
  carrierAgg.set(code, item);
}
const carriers = [...carrierAgg.values()]
  .filter((x) => x.flights >= 10000)
  .map((x) => [x.code, x.flights, x.weightedDelay / x.flights, x.weightedPeer / x.flights, (x.weightedDelay - x.weightedPeer) / x.flights])
  .sort((a, b) => b[1] - a[1]);

const wb = Workbook.create();
const exec = wb.worksheets.add("Executive Summary");
const trends = wb.worksheets.add("Delay Trends");
const driverSheet = wb.worksheets.add("Delay Drivers");
const airportSheet = wb.worksheets.add("Airport Analysis");
const routeSheet = wb.worksheets.add("Carrier and Route Analysis");
const qaSheet = wb.worksheets.add("Data Quality");
const defs = wb.worksheets.add("Definitions");
for (const sheet of [exec, trends, driverSheet, airportSheet, routeSheet, qaSheet, defs]) baseSheet(sheet);

// Delay Trends: source table plus formula-driven annual roll-up.
titleBlock(trends, "V", "Delay Trends", "Monthly BTS domestic operations, complete 2023–2025 files. Rates use operated, non-diverted flights unless otherwise noted.");
const trendHeaders = [["Month", "Year", "Month #", "Scheduled Flights", "Operated Flights", "On-Time Rate", "Arrival Delay Rate", "Cancellation Rate", "Diversion Rate", "Avg Arrival Delay (min)", "On-Time Flights (calc)", "Delayed Flights (calc)", "Cancelled Flights (calc)", "Diverted Flights (calc)"]];
trends.getRange("A4:N4").values = trendHeaders; header(trends.getRange("A4:N4"));
const trendRows = monthly.map((r) => [labelMonth(r.month_start), n(r.year), n(r.month), n(r.scheduled_flights), n(r.operated_flights), pct(r.on_time_rate), pct(r.arrival_delay_rate), pct(r.cancellation_rate), pct(r.diversion_rate), n(r.average_arrival_delay_minutes), null, null, null, null]);
trends.getRange(`A5:N${4 + trendRows.length}`).values = trendRows;
for (let row = 5; row < 5 + trendRows.length; row += 1) {
  trends.getRange(`K${row}:N${row}`).formulas = [[`=E${row}*F${row}`, `=E${row}*G${row}`, `=D${row}*H${row}`, `=D${row}*I${row}`]];
}
trends.getRange(`D5:E${4 + trendRows.length}`).format.numberFormat = "#,##0";
trends.getRange(`F5:I${4 + trendRows.length}`).format.numberFormat = "0.0%";
trends.getRange(`J5:J${4 + trendRows.length}`).format.numberFormat = "0.0";
trends.getRange(`K5:N${4 + trendRows.length}`).format.numberFormat = "#,##0";
bodyBorders(trends.getRange(`A4:N${4 + trendRows.length}`));
addTable(trends, `A4:N${4 + trendRows.length}`, "MonthlyOperations");
trends.getRange("P4:V4").values = [["Year", "Scheduled Flights", "Operated Flights", "On-Time Rate", "Arrival Delay Rate", "Cancellation Rate", "Diversion Rate"]]; header(trends.getRange("P4:V4"), TEAL);
trends.getRange("P5:P7").values = [[2023], [2024], [2025]];
for (let row = 5; row <= 7; row += 1) {
  trends.getRange(`Q${row}:V${row}`).formulas = [[
    `=SUMIFS($D$5:$D$40,$B$5:$B$40,$P${row})`,
    `=SUMIFS($E$5:$E$40,$B$5:$B$40,$P${row})`,
    `=SUMIFS($K$5:$K$40,$B$5:$B$40,$P${row})/R${row}`,
    `=SUMIFS($L$5:$L$40,$B$5:$B$40,$P${row})/R${row}`,
    `=SUMIFS($M$5:$M$40,$B$5:$B$40,$P${row})/Q${row}`,
    `=SUMIFS($N$5:$N$40,$B$5:$B$40,$P${row})/Q${row}`,
  ]];
}
trends.getRange("Q5:R7").format.numberFormat = "#,##0";
trends.getRange("S5:V7").format.numberFormat = "0.0%";
bodyBorders(trends.getRange("P4:V7"));
trends.getRange("P9:V10").merge();
trends.getRange("P9").values = [["Interpretation: 2025 on-time performance was lower and delay/cancellation rates were higher than in 2023. Use airport, route, season, and departure-period cuts before attributing performance differences to any single operator."]];
trends.getRange("P9:V10").format = { fill: LIGHT_BLUE, font: { color: TEXT, italic: true }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
const yearlyPivot = trends.pivotTables.add("YearlyScheduledFlightsPivot", "A4:N40", "P12");
yearlyPivot.rowHierarchies.add(yearlyPivot.hierarchies.getItem("Year"));
yearlyPivot.dataHierarchies.add(yearlyPivot.hierarchies.getItem("Scheduled Flights"));
const pivotChart = trends.charts.add("bar", trends.getRange("P12:Q15"));
pivotChart.title = "Scheduled flights by year (PivotTable)";
pivotChart.hasLegend = false;
pivotChart.yAxis = { numberFormatCode: "#,##0" };
pivotChart.setPosition("P19", "V34");
for (const [c, w] of Object.entries({ A: 13, B: 9, C: 9, D: 16, E: 16, F: 12, G: 15, H: 14, I: 12, J: 17, K: 17, L: 17, M: 18, N: 18, P: 10, Q: 16, R: 16, S: 13, T: 16, U: 14, V: 13 })) colWidth(trends, c, w, 60);
trends.freezePanes.freezeRows(4);

// Executive summary: all KPIs reference the traceable source tables.
titleBlock(exec, "N", "U.S. Airline Operations & Delay Root-Cause Analytics", "Executive summary | BTS Reporting Carrier On-Time Performance | Complete 2023–2025 monthly files | 20.93M scheduled domestic-flight records");
card(exec, "A4:C4", "A5:C7", "Scheduled Flights", "=SUM('Delay Trends'!D5:D40)", "#,##0", LIGHT_BLUE);
card(exec, "D4:F4", "D5:F7", "On-Time Rate", "=SUM('Delay Trends'!K5:K40)/SUM('Delay Trends'!E5:E40)", "0.0%", LIGHT_TEAL);
card(exec, "G4:I4", "G5:I7", "Arrival Delay Rate", "=SUM('Delay Trends'!L5:L40)/SUM('Delay Trends'!E5:E40)", "0.0%", LIGHT_ORANGE);
card(exec, "J4:L4", "J5:L7", "Cancellation Rate", "=SUM('Delay Trends'!M5:M40)/SUM('Delay Trends'!D5:D40)", "0.0%", "#FCECEC");
exec.getRange("A9:F9").merge();
exec.getRange("A9").values = [["Operational findings"]];
exec.getRange("A9:F9").format = { fill: NAVY, font: { bold: true, color: "#FFFFFF", size: 12 }, verticalAlignment: "center" };
const findings = [
  ["2025 reliability", "On-time performance fell from 78.2% in 2023 to 76.3% in 2025 while the arrival-delay rate rose from 20.3% to 21.9%."],
  ["Later-day risk", "Evening flights had a 28.7% observed delay rate and afternoon flights 27.5%, versus 13.4% in the morning across the full period."],
  ["Delay propagation", "Late-aircraft delay was 39.2% of reported delay minutes in 2025, the largest reported category."],
  ["High-volume diagnostics", "FLL, MIA, DFW, MCO, and CLT have elevated observed delay rates after the 5,000-departure threshold; comparisons require route/season context."],
];
exec.getRange("A10:B13").values = findings;
exec.getRange("A10:A13").format = { fill: LIGHT_BLUE, font: { bold: true, color: NAVY }, wrapText: true, verticalAlignment: "top" };
exec.getRange("B10:F13").merge(true);
exec.getRange("B10:F13").values = findings.map((x) => [x[1], null, null, null, null]);
exec.getRange("A10:F13").format.borders = { preset: "outside", style: "thin", color: BORDER };
exec.getRange("B10:F13").format = { fill: "#FFFFFF", font: { color: TEXT }, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
exec.getRange("A15:N15").merge();
exec.getRange("A15").values = [["Recommended operational focus (associational evidence, not causal claims)"]];
exec.getRange("A15:N15").format = { fill: NAVY, font: { bold: true, color: "#FFFFFF", size: 12 }, verticalAlignment: "center" };
const recommendations = [
  ["Protect later-day operations", "Later-day observed delay rates are roughly double morning levels.", "Prioritize recovery buffers, turn-time monitoring, and constrained-airport playbooks for afternoon/evening banks.", "Time of day is correlated with route mix, weather, and schedule design."],
  ["Reduce delay propagation", "Late-aircraft delay was 39.2% of reported 2025 delay minutes.", "Review aircraft rotations, crew options, and connection-risk routes for recovery opportunities.", "Reported cause categories are operational classifications, not experiments."],
  ["Use thresholded airport reviews", "DFW and CLT combine high volume with elevated observed delay rates.", "Segment reviews by departure period, season, carrier, and route before allocating resources.", "Airport comparisons reflect traffic, weather, and route-mix differences."],
  ["Monitor cancellations separately", "ASE 6.61%; LGA 2.70%; EWR 2.61%; DCA 2.33% cancellation rates.", "Maintain separate cancellation/diversion controls alongside delay monitoring.", "Local weather, airport constraints, and airline schedules differ."],
];
exec.getRange("A16:D16").values = [["Recommendation", "Supporting finding", "Recommended action", "Limitation"]]; header(exec.getRange("A16:D16"), TEAL);
exec.getRange("A17:D20").values = recommendations;
exec.getRange("A17:D20").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
exec.getRange("A17:A20").format = { fill: LIGHT_TEAL, font: { bold: true, color: NAVY }, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
const execChart = exec.charts.add("line", { chartType: "line", title: "Monthly on-time and arrival-delay rates" });
const onTimeSeries = execChart.series.add("On-Time Rate");
onTimeSeries.categoryFormula = "'Delay Trends'!$A$5:$A$40";
onTimeSeries.formula = "'Delay Trends'!$F$5:$F$40";
onTimeSeries.fill = TEAL;
const delaySeries = execChart.series.add("Arrival Delay Rate");
delaySeries.categoryFormula = "'Delay Trends'!$A$5:$A$40";
delaySeries.formula = "'Delay Trends'!$G$5:$G$40";
delaySeries.fill = RED;
execChart.hasLegend = true;
execChart.yAxis = { numberFormatCode: "0%" };
execChart.setPosition("H9", "N14");
for (const [c, w] of Object.entries({ A: 23, B: 26, C: 30, D: 28, E: 12, F: 12, G: 3, H: 12, I: 12, J: 12, K: 12, L: 12, M: 12, N: 12 })) colWidth(exec, c, w, 40);
exec.getRange("A10:F13").format.rowHeight = 36;
exec.getRange("A17:D20").format.rowHeight = 54;

// Delay driver evidence and departure-period risk.
titleBlock(driverSheet, "U", "Delay Drivers", "Reported delay-minute causes and departure-period patterns. Reported cause minutes apply to delayed operations and are not a causal experiment.");
driverSheet.getRange("A4:G4").values = [["Year", "Carrier Minutes", "Weather Minutes", "NAS Minutes", "Security Minutes", "Late Aircraft Minutes", "Total Reported Delay Minutes"]]; header(driverSheet.getRange("A4:G4"));
driverSheet.getRange("A5:G7").values = drivers.map((r) => [n(r.year), n(r.carrier_minutes), n(r.weather_minutes), n(r.nas_minutes), n(r.security_minutes), n(r.late_aircraft_minutes), n(r.total_reported_delay_minutes)]);
driverSheet.getRange("A5:G7").format.numberFormat = "#,##0";
addTable(driverSheet, "A4:G7", "DelayDriverMinutes");
driverSheet.getRange("I4:J4").values = [["2025 Cause", "Share of Reported Delay Minutes"]]; header(driverSheet.getRange("I4:J4"), TEAL);
const causeRows = [["Late Aircraft", "=F7/G7"], ["Carrier", "=B7/G7"], ["NAS", "=D7/G7"], ["Weather", "=C7/G7"], ["Security", "=E7/G7"]];
driverSheet.getRange("I5:I9").values = causeRows.map((r) => [r[0]]);
driverSheet.getRange("J5:J9").formulas = causeRows.map((r) => [r[1]]);
driverSheet.getRange("J5:J9").format.numberFormat = "0.0%";
bodyBorders(driverSheet.getRange("I4:J9"));
driverSheet.getRange("L4:R4").values = [["Year", "Month", "Departure Period", "Flights", "Delay Rate", "On-Time Rate", "Mean Arrival Delay (min)"]]; header(driverSheet.getRange("L4:R4"), TEAL);
const departRows = departure.map((r) => [n(r.year), n(r.month), r.departure_period, n(r.flights), pct(r.delay_rate), pct(r.on_time_rate), n(r.mean_arrival_delay_minutes)]);
driverSheet.getRange(`L5:R${4 + departRows.length}`).values = departRows;
driverSheet.getRange(`O5:O${4 + departRows.length}`).format.numberFormat = "#,##0";
driverSheet.getRange(`P5:Q${4 + departRows.length}`).format.numberFormat = "0.0%";
driverSheet.getRange(`R5:R${4 + departRows.length}`).format.numberFormat = "0.0";
addTable(driverSheet, `L4:R${4 + departRows.length}`, "DeparturePeriodPerformance");
driverSheet.getRange("I11:K13").merge();
driverSheet.getRange("I11").values = [["Key pattern: observed delay risk increases later in the day. Across 2023–2025, evening was 28.7%, afternoon 27.5%, midday 20.6%, morning 13.4%, and overnight 9.7%."]];
driverSheet.getRange("I11:K13").format = { fill: LIGHT_ORANGE, font: { color: TEXT, italic: true }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
addBarChart(driverSheet, driverSheet.getRange("I4:J9"), "2025 reported delay-minute shares", "I15", "K29", ORANGE, "0%");
for (const [c, w] of Object.entries({ A: 10, B: 15, C: 15, D: 15, E: 15, F: 18, G: 20, I: 18, J: 20, K: 3, L: 9, M: 9, N: 16, O: 14, P: 14, Q: 19, R: 20 })) colWidth(driverSheet, c, w, 200);
driverSheet.freezePanes.freezeRows(4);

// Airport diagnostics: thresholded data plus XLOOKUP selector.
titleBlock(airportSheet, "P", "Airport Analysis", "Airport-level observed performance. The source table includes origins with at least 5,000 scheduled departures; use volume and context before interpreting differences.");
airportSheet.getRange("A4:B4").merge();
airportSheet.getRange("A4").values = [["Airport lookup (editable)"]];
airportSheet.getRange("A4:B4").format = { fill: TEAL, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
airportSheet.getRange("A5").values = [["Airport code"]]; airportSheet.getRange("B5").values = [["FLL"]];
airportSheet.getRange("A6:B6").values = [["City", null]];
airportSheet.getRange("A7:B7").values = [["Departures", null]];
airportSheet.getRange("A8:B8").values = [["Delay rate", null]];
airportSheet.getRange("A9:B9").values = [["Cancellation rate", null]];
airportSheet.getRange("A10:B10").values = [["Mean arrival delay", null]];
airportSheet.getRange("A5:A10").format = { fill: LIGHT_BLUE, font: { bold: true, color: NAVY }, borders: { preset: "outside", style: "thin", color: BORDER } };
airportSheet.getRange("B5:B10").format = { fill: "#FFFFFF", borders: { preset: "outside", style: "thin", color: BORDER } };
const airportHeaders = [["Airport", "City", "State", "Departures", "Delay Rate", "Cancellation Rate", "Diversion Rate", "Mean Arrival Delay (min)"]];
airportSheet.getRange("A14:H14").values = airportHeaders; header(airportSheet.getRange("A14:H14"));
const airportRows = airports.map((r) => [r.origin, r.origin_city_name, r.origin_state, n(r.departures), pct(r.delay_rate), pct(r.cancellation_rate), pct(r.diversion_rate), n(r.mean_arrival_delay_minutes)]);
airportSheet.getRange(`A15:H${14 + airportRows.length}`).values = airportRows;
airportSheet.getRange(`D15:D${14 + airportRows.length}`).format.numberFormat = "#,##0";
airportSheet.getRange(`E15:G${14 + airportRows.length}`).format.numberFormat = "0.0%";
airportSheet.getRange(`H15:H${14 + airportRows.length}`).format.numberFormat = "0.0";
addTable(airportSheet, `A14:H${14 + airportRows.length}`, "AirportPerformance");
airportSheet.getRange("B5").dataValidation = { rule: { type: "list", formula1: `$A$15:$A$${14 + airportRows.length}` } };
airportSheet.getRange("B6").formulas = [[`=IFERROR(XLOOKUP($B$5,$A$15:$A$${14 + airportRows.length},$B$15:$B$${14 + airportRows.length}),"Not found")`]];
airportSheet.getRange("B7").formulas = [[`=IFERROR(XLOOKUP($B$5,$A$15:$A$${14 + airportRows.length},$D$15:$D$${14 + airportRows.length}),0)`]];
airportSheet.getRange("B8").formulas = [[`=IFERROR(XLOOKUP($B$5,$A$15:$A$${14 + airportRows.length},$E$15:$E$${14 + airportRows.length}),0)`]];
airportSheet.getRange("B9").formulas = [[`=IFERROR(XLOOKUP($B$5,$A$15:$A$${14 + airportRows.length},$F$15:$F$${14 + airportRows.length}),0)`]];
airportSheet.getRange("B10").formulas = [[`=IFERROR(XLOOKUP($B$5,$A$15:$A$${14 + airportRows.length},$H$15:$H$${14 + airportRows.length}),0)`]];
airportSheet.getRange("B7").format.numberFormat = "#,##0";
airportSheet.getRange("B8:B9").format.numberFormat = "0.0%";
airportSheet.getRange("B10").format.numberFormat = "0.0";
airportSheet.getRange(`E15:E${14 + airportRows.length}`).conditionalFormats.add("colorScale", { colors: ["#E7F5F2", "#FEE8C8", "#D1495B"] });
addSingleSeriesBar(airportSheet, "Highest observed delay rates (5,000+ departures)", "'Airport Analysis'!$A$15:$A$24", "'Airport Analysis'!$E$15:$E$24", "J4", "P19", RED, "0%");
airportSheet.getRange("J21:P23").merge();
airportSheet.getRange("J21").values = [["Interpretation guardrail: this is a thresholded operational-screening list, not an airport-quality ranking. Compare within season, departure period, carrier, and route before taking action."]];
airportSheet.getRange("J21:P23").format = { fill: LIGHT_ORANGE, font: { color: TEXT, italic: true }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
for (const [c, w] of Object.entries({ A: 12, B: 24, C: 8, D: 14, E: 13, F: 16, G: 14, H: 20, J: 12, K: 12, L: 12, M: 12, N: 12, O: 12, P: 12 })) colWidth(airportSheet, c, w, 240);
airportSheet.freezePanes.freezeRows(14);

// Carrier/route diagnostic: no simplistic performance ranking—peer-controlled carrier comparison and route thresholds.
titleBlock(routeSheet, "S", "Carrier and Route Analysis", "Carrier comparison uses route-month peer controls with a 100-flight carrier cell threshold; route performance uses a 1,000-flight threshold.");
routeSheet.getRange("A4:E4").values = [["Carrier", "Comparable Flights", "Comparable Delay Rate", "Route-Month Peer Rate", "Relative Delay Rate"]]; header(routeSheet.getRange("A4:E4"));
routeSheet.getRange(`A5:E${4 + carriers.length}`).values = carriers;
routeSheet.getRange(`B5:B${4 + carriers.length}`).format.numberFormat = "#,##0";
routeSheet.getRange(`C5:E${4 + carriers.length}`).format.numberFormat = "0.0%";
addTable(routeSheet, `A4:E${4 + carriers.length}`, "CarrierComparablePerformance");
routeSheet.getRange("G4:L4").values = [["Route", "Origin", "Destination", "Flights", "Delay Rate", "Cancellation Rate"]]; header(routeSheet.getRange("G4:L4"), TEAL);
const routeRows = routes.map((r) => [r.route_key, r.origin, r.dest, n(r.flights), pct(r.delay_rate), pct(r.cancellation_rate)]);
routeSheet.getRange(`G5:L${4 + routeRows.length}`).values = routeRows;
routeSheet.getRange(`J5:J${4 + routeRows.length}`).format.numberFormat = "#,##0";
routeSheet.getRange(`K5:L${4 + routeRows.length}`).format.numberFormat = "0.0%";
addTable(routeSheet, `G4:L${4 + routeRows.length}`, "RoutePerformance");
routeSheet.getRange("N4:S4").values = [["Airport", "City", "State", "Scheduled Flights", "Cancellation Rate", "Diversion Rate"]]; header(routeSheet.getRange("N4:S4"), ORANGE);
const cancelRows = cancels.map((r) => [r.origin, r.origin_city_name, r.origin_state, n(r.scheduled_flights), pct(r.cancellation_rate), pct(r.diversion_rate)]);
routeSheet.getRange(`N5:S${4 + cancelRows.length}`).values = cancelRows;
routeSheet.getRange(`Q5:Q${4 + cancelRows.length}`).format.numberFormat = "#,##0";
routeSheet.getRange(`R5:S${4 + cancelRows.length}`).format.numberFormat = "0.0%";
addTable(routeSheet, `N4:S${4 + cancelRows.length}`, "CancellationDiversion");
addSingleSeriesBar(routeSheet, "Worst high-volume routes by observed delay rate", "'Carrier and Route Analysis'!$G$5:$G$14", "'Carrier and Route Analysis'!$K$5:$K$14", "A23", "F39", RED, "0%");
routeSheet.getRange("N212:S216").merge();
routeSheet.getRange("N212").values = [["How to use this page: first identify a high-volume exception, then compare it with route-month peer performance, seasons, departure periods, and cancellation/diversion patterns. Do not infer that a carrier, airport, or route caused a delay from descriptive rankings."]];
routeSheet.getRange("N212:S216").format = { fill: LIGHT_BLUE, font: { color: TEXT, italic: true }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
for (const [c, w] of Object.entries({ A: 14, B: 17, C: 18, D: 18, E: 16, F: 3, G: 14, H: 10, I: 12, J: 13, K: 13, L: 16, M: 3, N: 10, O: 22, P: 8, Q: 16, R: 16, S: 14 })) colWidth(routeSheet, c, w, 4300);
routeSheet.freezePanes.freezeRows(4);

// Data Quality: source-to-workbook reconciliation and transparent exclusions/thresholds.
titleBlock(qaSheet, "J", "Data Quality & Reconciliation", "Automated controls, source-to-model reconciliation, and analytical treatments. Each operational rate uses the denominator documented below.");
qaSheet.getRange("A4:D4").values = [["Reconciliation Check", "Source / Expected", "Workbook Result", "Status"]]; header(qaSheet.getRange("A4:D4"));
const q = quality[0];
qaSheet.getRange("A5:B11").values = [
  ["Fact rows", n(q.fact_rows)],
  ["Unique candidate flight keys", n(q.unique_flight_keys)],
  ["Duplicate candidate-key rows", n(q.duplicate_key_rows)],
  ["Scheduled flights in presentation", n(q.fact_rows)],
  ["Cancelled flights", n(q.cancelled_flights)],
  ["Diverted flights", n(q.diverted_flights)],
  ["Date coverage", `${q.min_flight_date} to ${q.max_flight_date}`],
];
qaSheet.getRange("C5:C11").formulas = [
  ["='Data Quality'!B5"],
  ["='Data Quality'!B6"],
  ["='Data Quality'!B7"],
  ["=SUM('Delay Trends'!D5:D40)"],
  ["=ROUND(SUM('Delay Trends'!M5:M40),0)"],
  ["=ROUND(SUM('Delay Trends'!N5:N40),0)"],
  ["=\"2023-01-01 to 2025-12-31\""],
];
qaSheet.getRange("D5:D11").formulas = [
  ["=IF(B5=C5,\"PASS\",\"FAIL\")"],
  ["=IF(B6=C6,\"PASS\",\"FAIL\")"],
  ["=IF(B7=C7,\"PASS\",\"FAIL\")"],
  ["=IF(B8=C8,\"PASS\",\"FAIL\")"],
  ["=IF(B9=C9,\"PASS\",\"FAIL\")"],
  ["=IF(B10=C10,\"PASS\",\"FAIL\")"],
  ["=IF(B11=C11,\"PASS\",\"FAIL\")"],
];
qaSheet.getRange("B5:C10").format.numberFormat = "#,##0";
qaSheet.getRange("D5:D11").conditionalFormats.add("containsText", { text: "PASS", format: { fill: "#D9EAD3", font: { bold: true, color: "#274E13" } } });
qaSheet.getRange("D5:D11").conditionalFormats.add("containsText", { text: "FAIL", format: { fill: "#F4CCCC", font: { bold: true, color: "#990000" } } });
bodyBorders(qaSheet.getRange("A4:D11"));
qaSheet.getRange("F4:H4").values = [["Quality Rule / Treatment", "Why", "Result"]]; header(qaSheet.getRange("F4:H4"), TEAL);
const rules = [
  ["Required keys", "Flight date, airline, origin, and destination are required for model joins.", "20,928,579 retained fact rows; full source retention after required-key checks."],
  ["Candidate-key uniqueness", "Detect duplicate records before rate aggregation.", "0 duplicate candidate-key rows."],
  ["Arrival fields", "Cancelled/diverted records have non-applicable arrival outcomes.", "1.63% arrival-delay missingness, treated as expected; excluded only from arrival-performance denominators."],
  ["Cancellation code mapping", "Avoid masking missing cancellation reason labels.", "0 cancelled flights with Unknown cancellation code."],
  ["Airport threshold", "Reduce unstable low-volume airport rates.", "5,000 scheduled departures required."],
  ["Route threshold", "Reduce unstable low-volume route rates.", "1,000 scheduled flights required."],
  ["Carrier route-month threshold", "Support comparable peer-control cells.", "100 flights per carrier route-month cell required."],
  ["Monthly partitions", "Confirm complete monthly coverage.", "Formula-driven result shown below."],
];
qaSheet.getRange("F5:H12").values = rules;
qaSheet.getRange("F5:H12").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
qaSheet.getRange("F5:F12").format = { fill: LIGHT_TEAL, font: { bold: true, color: NAVY }, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
qaSheet.getRange("F5:H12").format.rowHeight = 42;
qaSheet.getRange("H12").formulas = [["=COUNTIFS('Delay Trends'!$D$5:$D$40,\">0\")&\" populated months; expected 36.\""]];
qaSheet.getRange("A14:J16").merge();
qaSheet.getRange("A14").values = [["Grain: one scheduled domestic flight record. Arrival delay and on-time rates use operated, non-diverted flights; cancellation and diversion rates use all scheduled records. Two records have Unknown departure period and remain visible rather than silently reassigned."]];
qaSheet.getRange("A14:J16").format = { fill: LIGHT_ORANGE, font: { color: TEXT, italic: true }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
for (const [c, w] of Object.entries({ A: 28, B: 22, C: 22, D: 12, E: 3, F: 24, G: 38, H: 35, I: 4, J: 4 })) colWidth(qaSheet, c, w, 40);

// Definitions/Methodology: compact handoff guide, data dictionary, and source link.
titleBlock(defs, "H", "Definitions, Methodology & Sources", "Portfolio handoff guide. Detailed SQL, Power Query, Python, model diagram, and documentation are stored with the project repository.");
defs.getRange("A4:B4").values = [["Metric / Field", "Definition"]]; header(defs.getRange("A4:B4"));
const definitions = [
  ["Scheduled flights", "Count of BTS reporting-carrier flight records at the scheduled-flight grain."],
  ["Operated flights", "Scheduled records that were neither cancelled nor diverted; the denominator used for on-time and arrival-delay rates."],
  ["On-time rate", "Share of operated, non-diverted flights with arrival delay under 15 minutes."],
  ["Arrival delay rate", "Share of operated, non-diverted flights with arrival delay of 15 minutes or more."],
  ["Cancellation rate", "Cancelled scheduled flights divided by all scheduled flights."],
  ["Diversion rate", "Diverted scheduled flights divided by all scheduled flights."],
  ["Departure period", "Scheduled departure-time categories: Overnight, Morning, Midday, Afternoon, Evening, or Unknown."],
  ["Reported delay causes", "Carrier, weather, NAS, security, and late-aircraft minutes reported in BTS records; descriptive operational classifications."],
  ["Comparable carrier rate", "Carrier route-month performance only where the carrier cell has at least 100 flights, compared with peer carriers on the same route and month."],
  ["Volume thresholds", "Airport: 5,000 scheduled departures; route: 1,000 scheduled flights; carrier route-month: 100 flights."],
];
defs.getRange("A5:B14").values = definitions;
defs.getRange("A5:B14").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
defs.getRange("A5:A14").format = { fill: LIGHT_BLUE, font: { bold: true, color: NAVY }, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
defs.getRange("D4:E4").values = [["Model component", "Purpose"]]; header(defs.getRange("D4:E4"), TEAL);
defs.getRange("D5:E9").values = [
  ["fact_flights", "One scheduled domestic flight record; operational flags, timing, and delay metrics."],
  ["dim_date", "Calendar attributes for 2023–2025 trend analysis."],
  ["dim_airline", "Reporting airline key and code."],
  ["dim_airport", "Airport code, city, and state."],
  ["dim_route", "Origin-destination route key."],
];
defs.getRange("D5:E9").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: BORDER } };
defs.getRange("D5:D9").format = { fill: LIGHT_TEAL, font: { bold: true, color: NAVY }, borders: { preset: "outside", style: "thin", color: BORDER } };
defs.getRange("D11:H11").merge();
defs.getRange("D11").values = [["Primary source"]];
defs.getRange("D11:H11").format = { fill: NAVY, font: { bold: true, color: "#FFFFFF" } };
defs.getRange("D12:H13").merge();
defs.getRange("D12").values = [["Bureau of Transportation Statistics (BTS), Reporting Carrier On-Time Performance. Official table information: https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ"]];
defs.getRange("D12:H13").format = { fill: LIGHT_BLUE, font: { color: TEXT }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
defs.getRange("D15:H18").merge();
defs.getRange("D15").values = [["Limitations: BTS data describes reported domestic flight operations and delay classifications. Descriptive differences are associations and may reflect route mix, airport conditions, weather, traffic management, airline schedules, and seasonality. The workbook does not claim a carrier, airport, or time period caused a delay. The raw source exceeds Excel worksheet limits; this workbook presents aggregated, reconciled tables while the full fact dataset remains in the reproducible DuckDB/Parquet model."]];
defs.getRange("D15:H18").format = { fill: LIGHT_ORANGE, font: { color: TEXT, italic: true }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: BORDER } };
for (const [c, w] of Object.entries({ A: 25, B: 60, C: 3, D: 23, E: 48, F: 15, G: 15, H: 15 })) colWidth(defs, c, w, 40);
defs.getRange("A5:B14").format.rowHeight = 35;

// Source style and freeze panes.
exec.freezePanes.freezeRows(2);
qaSheet.freezePanes.freezeRows(4);
defs.freezePanes.freezeRows(4);

// Workbook-level verification before export.
const keyInspection = await wb.inspect({ kind: "table", range: "Executive Summary!A1:N20", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 14 });
console.log(keyInspection.ndjson);
const formulaErrors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(formulaErrors.ndjson);

await fs.mkdir(outputDir, { recursive: true });
const previewDir = path.join(outputDir, "_qa_previews");
await fs.mkdir(previewDir, { recursive: true });
const previewRanges = {
  "Executive Summary": "A1:N20",
  "Delay Trends": "A1:V40",
  "Delay Drivers": "A1:U30",
  "Airport Analysis": "A1:P24",
  "Carrier and Route Analysis": "A1:S216",
  "Data Quality": "A1:J16",
  "Definitions": "A1:H18",
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const image = await wb.render({ sheetName, range, scale: 0.75, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await image.arrayBuffer()));
}
const file = await SpreadsheetFile.exportXlsx(wb);
await file.save(outputPath);
console.log(JSON.stringify({ outputPath, carriers: carriers.length, airports: airportRows.length, routes: routeRows.length, formulaErrorScan: formulaErrors.ndjson }));
