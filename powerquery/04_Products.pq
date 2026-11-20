// DIMENSION: one row per product, with the same composite ProductKey as the fact table.
let
    Source = stg_Orders,
    #"Selected Columns" = Table.SelectColumns(Source, {"Product ID", "Category", "Sub-Category", "Product Name"}),
    #"Removed Duplicates" = Table.Distinct(#"Selected Columns"),
    #"Added ProductKey" = Table.AddColumn(#"Removed Duplicates", "ProductKey",
        each Text.Combine({[Product ID], [Product Name]}, ","), type text)
in
    #"Added ProductKey"
