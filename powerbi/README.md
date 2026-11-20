# Power BI reports

Open the `.pbix` files in **Power BI Desktop**. The details below were read directly from each file's data model and report layout.

## `sales-report-data-modelling.pbix`: Superstore sales

**Source:** the Superstore sample workbook (`Orders` sheet), loaded with Power Query and split into dimension tables.

### Data model (star schema)

| Table | Role | Rows | Key columns |
|---|---|---|---|
| `Orders` | Fact | 9,994 | Order ID, Order Date, Ship Date, Ship Mode, Sales, Quantity, Discount, Profit |
| `Customers` | Dimension | 793 | Customer ID, Customer Name, Segment |
| `Geography` | Dimension | 632 | Country, State, City, Postal Code, Region, GeographyKey |
| `Products` | Dimension | 1,894 | Product ID, Category, Sub-Category, Product Name, ProductKey |
| `Calendar` | Date table | 1,826 days | Date, Year, Quarter, Month, Month Number (`CALENDARAUTO()`) |

Relationships (all many-to-one, single direction): `Orders[Customer ID]` to `Customers`, `Orders[GeographyKey]` to `Geography`, `Orders[ProductKey]` to `Products`.

### DAX measures

| Measure | Definition |
|---|---|
| Revenue | `SUM(Orders[Sales])` |
| Previous Month Revenue | `CALCULATE([Revenue], PREVIOUSMONTH('Calendar'[Date]))` |
| Revenue MOM Var | `[Revenue] - [Previous Month Revenue]` |
| Revenue MOM% Var | `DIVIDE([Revenue MOM Var], [Previous Month Revenue], 0)` |
| Revenue SPLY | `CALCULATE([Revenue], SAMEPERIODLASTYEAR('Calendar'[Date]))` |
| Revenue YTD | `CALCULATE([Revenue], DATESYTD('Calendar'[Date]))` |
| Revenue YTD 2 / YTD 3 | `TOTALYTD([Revenue], 'Calendar'[Date])` |
| Total Rev for the year | `CALCULATE([Revenue], REMOVEFILTERS('Calendar'[Month], 'Calendar'[Month Number]))` |
| Monthly %age share | `DIVIDE([Revenue], [Total Rev for the year], 0)` |
| Central Revenue | `CALCULATE([Revenue], Geography[Region] = "Central")` |
| Revenue vs Central | `[Revenue] - [Central Revenue]` |

### Report pages

- **Sales Report 1:** year and month slicers; cards for Revenue, Previous Month Revenue and Revenue YTD; line charts of Revenue vs Revenue SPLY by month and Revenue by date; a waterfall of MoM% variance; a month-by-year matrix.
- **Sales Report 2:** a donut of revenue by customer segment; revenue vs previous-month revenue by region; revenue by product category; a ribbon chart of category revenue by year; year and month slicers.

## `nigeria-covid19-dashboard.pbix`: Nigeria Covid-19

**Source:** the NCDC Nigeria website (`covid19.ncdc.gov.ng`), an HTML table scraped with Power Query (`Web.BrowserContents` and `Html.Table`) and typed. The embedded snapshot holds 37 rows (36 states + FCT) and is dated to about 31 May 2022 by the file's metadata.

### Data model

One table, `Covid` (State, Confirmed Cases, Active Cases, Discharged Cases, Deaths Recorded), plus a `DAX Measures` table.

| Measure | Definition |
|---|---|
| Total Confirmed Cases | `SUM(Covid[Confirmed Cases])` |
| Total Active cases | `SUM('Covid'[Active Cases])` |
| Total Discharged Cases | `SUM(Covid[Discharged Cases])` |
| Total Deaths Recorded | `SUM(Covid[Deaths Recorded])` |
| Recovery Rate | `DIVIDE([Total Discharged Cases], [Total Confirmed Cases], 0)` |
| Death Rate | `DIVIDE([Total Deaths Recorded], [Total Confirmed Cases], 0)` |

### Report page

Six KPI cards (the measures above), a state-level table, a bar chart of deaths by state and a map of active cases by state.

---

Python analyses of the same data live in [`../notebooks/`](../notebooks/).
