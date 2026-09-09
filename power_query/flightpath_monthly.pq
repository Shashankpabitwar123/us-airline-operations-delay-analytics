// Paste into a Blank Query in Excel Power Query Advanced Editor.
// Edit ExportFolder to your local data/exports path. This query is separate from the XLSX.
let
    ExportFolder = "/replace/with/flightpath/data/exports/",
    Source = Csv.Document(File.Contents(ExportFolder & "monthly.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"year", Int64.Type}, {"month", Int64.Type}, {"scheduled_flights", Int64.Type}, {"eligible_arrivals", Int64.Type}, {"delayed_flights", Int64.Type}, {"cancelled_flights", Int64.Type}, {"on_time_flights", Int64.Type}}),
    DelayRate = Table.AddColumn(Typed, "arrival_delay_rate", each if [eligible_arrivals] = 0 then null else [delayed_flights] / [eligible_arrivals], Percentage.Type),
    OnTimeRate = Table.AddColumn(DelayRate, "on_time_rate", each if [eligible_arrivals] = 0 then null else [on_time_flights] / [eligible_arrivals], Percentage.Type),
    CancellationRate = Table.AddColumn(OnTimeRate, "cancellation_rate", each if [scheduled_flights] = 0 then null else [cancelled_flights] / [scheduled_flights], Percentage.Type)
in
    CancellationRate
