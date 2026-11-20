// Nigeria Covid-19 dashboard source: HTML table scraped from the NCDC website (as in the original report).
let
    Source = Web.BrowserContents("https://covid19.ncdc.gov.ng/"),
    #"Extracted Table From Html" = Html.Table(Source, {
        {"Column1", "TABLE[id='custom1'] > * > TR > :nth-child(1)"},
        {"Column2", "TABLE[id='custom1'] > * > TR > :nth-child(2)"},
        {"Column3", "TABLE[id='custom1'] > * > TR > :nth-child(3)"},
        {"Column4", "TABLE[id='custom1'] > * > TR > :nth-child(4)"},
        {"Column5", "TABLE[id='custom1'] > * > TR > :nth-child(5)"}},
        [RowSelector = "TABLE[id='custom1'] > * > TR"]),
    #"Promoted Headers" = Table.PromoteHeaders(#"Extracted Table From Html", [PromoteAllScalars = true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"States Affected", type text}, {"No. of Cases (Lab Confirmed)", Int64.Type},
        {"No. of Cases (on admission)", Int64.Type}, {"No. Discharged", Int64.Type}, {"No. of Deaths", Int64.Type}}),
    #"Renamed Columns" = Table.RenameColumns(#"Changed Type", {
        {"States Affected", "State"}, {"No. of Cases (Lab Confirmed)", "Confirmed Cases"},
        {"No. of Cases (on admission)", "Active Cases"}, {"No. Discharged", "Discharged Cases"},
        {"No. of Deaths", "Deaths Recorded"}})
in
    #"Renamed Columns"
