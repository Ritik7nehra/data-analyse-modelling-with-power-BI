// STAGING query (disable load). Reads and types the source ONCE; every other query references it.
// The original report re-read and re-typed the workbook separately in each of the four queries.
let
    Source = Excel.Workbook(File.Contents(SourcePath), null, true),
    Orders_Sheet = Source{[Item = "Orders", Kind = "Sheet"]}[Data],
    #"Promoted Headers" = Table.PromoteHeaders(Orders_Sheet, [PromoteAllScalars = true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"Row ID", Int64.Type}, {"Order ID", type text}, {"Order Date", type date}, {"Ship Date", type date},
        {"Ship Mode", type text}, {"Customer ID", type text}, {"Customer Name", type text}, {"Segment", type text},
        {"Country", type text}, {"City", type text}, {"State", type text}, {"Postal Code", Int64.Type},
        {"Region", type text}, {"Product ID", type text}, {"Category", type text}, {"Sub-Category", type text},
        {"Product Name", type text}, {"Sales", type number}, {"Quantity", Int64.Type},
        {"Discount", type number}, {"Profit", type number}}),
    #"Removed Columns" = Table.RemoveColumns(#"Changed Type", {"Row ID"}),
    #"Postal Code as Text" = Table.TransformColumnTypes(#"Removed Columns", {{"Postal Code", type text}})
in
    #"Postal Code as Text"
