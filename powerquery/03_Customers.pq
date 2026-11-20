// DIMENSION: one row per customer.
let
    Source = stg_Orders,
    #"Selected Columns" = Table.SelectColumns(Source, {"Customer ID", "Customer Name", "Segment"}),
    #"Removed Duplicates" = Table.Distinct(#"Selected Columns")
in
    #"Removed Duplicates"
