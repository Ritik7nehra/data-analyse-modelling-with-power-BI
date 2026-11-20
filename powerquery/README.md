# Power Query (M) ETL

The M queries behind the two Power BI reports, extracted from the `.pbix` files and tidied.

> **Status: written, not run here.** The transformation steps are copied from the reports, but these exact `.pq` files were not
> executed in Power BI Desktop in this repo's build environment. Open Power BI Desktop > Transform data > Advanced Editor to try them.
> The Python pipeline in `src/` implements the same logic and *is* tested.

## What changed from the original report

| Original | Refactored here | Why |
|---|---|---|
| Four queries each re-read and re-typed the Excel sheet | One staging query `stg_Orders`; the others reference it | Source is read once; one place to fix a type or rule |
| Hard-coded `C:\Users\...\Super+Store+Data.xlsx` | `SourcePath` parameter | Portable, no personal path in the repo |

## Query map (Superstore report)

| File | Role | Key steps |
|---|---|---|
| `00_parameter_SourcePath.pq` | Parameter | File location |
| `01_stg_Orders.pq` | Staging (disable load) | Read workbook, promote headers, set data types, drop `Row ID`, postal code to text |
| `02_Orders.pq` | Fact | Keep order/measure columns, build `GeographyKey` (city + postal code) and `ProductKey` (product ID + name) |
| `03_Customers.pq` | Dimension | Select customer columns, remove duplicates |
| `04_Products.pq` | Dimension | Select product columns, remove duplicates, add `ProductKey` |
| `05_Geography.pq` | Dimension | Select location columns, remove duplicates, add `GeographyKey` |
| `10_Covid_NCDC_web.pq` | Covid-19 report source | Scrape the NCDC HTML table, promote headers, type, rename columns |
| `19_parameter_MartsFolder.pq` | Parameter | Folder holding the pipeline's mart CSV exports |
| `20_sales_flat_masked.pq` | New report source | Load `mart_sales_flat.csv` (masked tokens) with explicit types, as table `sales_flat` |

## The same ETL in three places

| Step | Power Query (M) | Python pipeline (`src/`) | SQL warehouse (`warehouse/duckdb/models/`) |
|---|---|---|---|
| Read source | `Excel.Workbook` | `extract.extract_orders` | n/a |
| Types, postal code as text | `TransformColumnTypes` | `dtype={"Postal Code": "string"}` | typed `stg_orders` |
| Quality checks | (none in the original) | `validate.run_checks` (21 checks) | `dq_results` table |
| Masking | (none in the original) | `mask.mask_orders` | n/a |
| Split into dimensions | `Table.Distinct` + `Table.SelectColumns` | n/a | `dim_customer`, `dim_product`, `dim_geography` |
| Surrogate / composite keys | `Table.CombineColumns` (text keys) | n/a | `DENSE_RANK()` integer surrogate keys |
| Load | Power BI model | DuckDB (BigQuery loader provided) | fact + marts |

**Microsoft Fabric:** Dataflows Gen2 use Power Query, so these queries can be pasted into a Dataflow Gen2 unchanged
(set `SourcePath` to a OneLake or SharePoint location). See [`docs/fabric_mapping.md`](../docs/fabric_mapping.md).
