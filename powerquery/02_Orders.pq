// FACT table: one row per order line, with composite keys to the Geography and Products dimensions.
let
    Source = stg_Orders,
    #"Selected Columns" = Table.SelectColumns(Source, {
        "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID", "City", "Postal Code",
        "Product ID", "Product Name", "Sales", "Quantity", "Discount", "Profit"}),
    #"Merged GeographyKey" = Table.CombineColumns(#"Selected Columns", {"City", "Postal Code"},
        Combiner.CombineTextByDelimiter(",", QuoteStyle.None), "GeographyKey"),
    #"Merged ProductKey" = Table.CombineColumns(#"Merged GeographyKey", {"Product ID", "Product Name"},
        Combiner.CombineTextByDelimiter(",", QuoteStyle.None), "ProductKey")
in
    #"Merged ProductKey"
