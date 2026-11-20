// DIMENSION: one row per city / postal code, with the same composite GeographyKey as the fact table.
let
    Source = stg_Orders,
    #"Selected Columns" = Table.SelectColumns(Source, {"Country", "City", "State", "Postal Code", "Region"}),
    #"Removed Duplicates" = Table.Distinct(#"Selected Columns"),
    #"Added GeographyKey" = Table.AddColumn(#"Removed Duplicates", "GeographyKey",
        each Text.Combine({[City], [Postal Code]}, ","), type text)
in
    #"Added GeographyKey"
