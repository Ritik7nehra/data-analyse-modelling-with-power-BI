// Loads the pipeline's flat BI extract (masked customer tokens, generalised postcodes) into Power BI as `sales_flat`.
// STATUS: written, not run in Power BI Desktop. Column names/types match reports/marts/mart_sales_flat.csv.
let
    Source = Csv.Document(File.Contents(MartsFolder & "mart_sales_flat.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"order_line_id", Int64.Type}, {"order_id", type text}, {"order_date", type date}, {"ship_date", type date},
        {"year", Int64.Type}, {"quarter", Int64.Type}, {"month_number", Int64.Type}, {"month_name", type text},
        {"year_month", type text}, {"ship_mode", type text}, {"customer_id", type text}, {"segment", type text},
        {"region", type text}, {"state", type text}, {"city", type text}, {"postal_prefix", type text},
        {"category", type text}, {"sub_category", type text}, {"product_name", type text}, {"sales", type number},
        {"quantity", Int64.Type}, {"discount", type number}, {"discount_band", type text}, {"profit", type number},
        {"cost", type number}, {"gross_sales", type number}, {"ship_days", Int64.Type}, {"is_loss_making", type logical}},
        "en-US")
in
    Typed
