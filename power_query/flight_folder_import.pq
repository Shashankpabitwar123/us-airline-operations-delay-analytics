let
    Source = Folder.Files(Parameter_FlightFolder),
    VisibleFiles = Table.SelectRows(Source, each [Attributes]?[Hidden]? <> true and Text.Lower([Extension]) = ".csv"),
    KeepMonthlyFiles = Table.SelectColumns(VisibleFiles, {"Content", "Name"}),
    Imported = Table.AddColumn(KeepMonthlyFiles, "Rows", each Csv.Document([Content], [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv])),
    PromotedHeaders = Table.AddColumn(Imported, "Table", each Table.PromoteHeaders([Rows], [PromoteAllScalars = true])),
    Combined = Table.Combine(PromotedHeaders[Table]),
    SelectedColumns = Table.SelectColumns(Combined, {
        "FlightDate", "Year", "Month", "DayOfWeek", "Reporting_Airline", "DOT_ID_Reporting_Airline",
        "Flight_Number_Reporting_Airline", "OriginAirportID", "Origin", "OriginCityName", "OriginState",
        "DestAirportID", "Dest", "DestCityName", "DestState", "CRSDepTime", "ArrDelay", "ArrDel15",
        "Cancelled", "CancellationCode", "Diverted", "Distance", "CarrierDelay", "WeatherDelay", "NASDelay",
        "SecurityDelay", "LateAircraftDelay"
    }),
    Typed = Table.TransformColumnTypes(SelectedColumns, {
        {"FlightDate", type date}, {"Year", Int64.Type}, {"Month", Int64.Type}, {"DayOfWeek", Int64.Type},
        {"DOT_ID_Reporting_Airline", Int64.Type}, {"Flight_Number_Reporting_Airline", Int64.Type},
        {"OriginAirportID", Int64.Type}, {"DestAirportID", Int64.Type}, {"CRSDepTime", Int64.Type},
        {"ArrDelay", type number}, {"ArrDel15", Int64.Type}, {"Cancelled", Int64.Type}, {"Diverted", Int64.Type},
        {"Distance", type number}, {"CarrierDelay", type number}, {"WeatherDelay", type number},
        {"NASDelay", type number}, {"SecurityDelay", type number}, {"LateAircraftDelay", type number}
    }),
    TrimmedText = Table.TransformColumns(Typed, {{"Reporting_Airline", Text.Trim}, {"Origin", Text.Trim}, {"Dest", Text.Trim}, {"CancellationCode", each if _ = null then "Unknown" else Text.Trim(_), type text}}),
    FilteredRequiredKeys = Table.SelectRows(TrimmedText, each [FlightDate] <> null and [DOT_ID_Reporting_Airline] <> null and [OriginAirportID] <> null and [DestAirportID] <> null),
    AddedRoute = Table.AddColumn(FilteredRequiredKeys, "route_key", each [Origin] & "-" & [Dest], type text),
    AddedOperated = Table.AddColumn(AddedRoute, "operated", each if [Cancelled] = 0 and [Diverted] = 0 then 1 else 0, Int64.Type),
    AddedDelayed = Table.AddColumn(AddedOperated, "delayed_flight", each if [operated] = 1 and [ArrDel15] = 1 then 1 else 0, Int64.Type),
    AddedOnTime = Table.AddColumn(AddedDelayed, "arrived_on_time", each if [operated] = 1 and [ArrDel15] = 0 then 1 else 0, Int64.Type),
    AddedDeparturePeriod = Table.AddColumn(AddedOnTime, "departure_period", each if [CRSDepTime] < 600 then "Overnight" else if [CRSDepTime] < 1100 then "Morning" else if [CRSDepTime] < 1500 then "Midday" else if [CRSDepTime] < 1900 then "Afternoon" else "Evening", type text),
    AddedSeverity = Table.AddColumn(AddedDeparturePeriod, "delay_severity", each if [operated] = 0 then "Not applicable" else if [ArrDelay] < 15 then "On time" else if [ArrDelay] < 30 then "15-29" else if [ArrDelay] < 60 then "30-59" else if [ArrDelay] < 120 then "60-119" else "120+", type text)
in
    AddedSeverity
