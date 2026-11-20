# BI and dashboards: Power BI, Looker Studio, Tableau, Cognos

One governed set of numbers, several front ends. Every tool reads the same marts and the same metric definitions.

> **Status.** The marts and the SQL metrics are built and tested. The **Looker Studio, Tableau and Cognos material below is a build guide, not a delivered dashboard**: no report was built or published in those tools from this repo. The DAX, Tableau and Looker Studio expressions are hand-written equivalents of the tested SQL and have **not been run** in those tools. Build one, compare every card with the control totals, and then add a link or screenshot here.

## What to connect to

| Source | Use when | Notes |
|---|---|---|
| `reports/marts/mart_sales_flat.csv` | Quickest start in any tool | One denormalised row per order line (28 columns, about 2.5 MB). Customers are masked tokens |
| `reports/marts/mart_*.csv` | Pre-aggregated views | Monthly sales, product profitability, regions, discount impact, RFM, what-if, executive KPIs |
| BigQuery dataset | Looker Studio, Tableau, Cognos with a database connection | Deploy with `warehouse/bigquery/load_to_bigquery.py` (see its [README](../warehouse/bigquery/README.md)); read the star schema or the `mart_*` views |

## Metric layer

`bi/metrics.yml` defines 10 metrics and 11 dimensions once. [`generated/metrics_reference.md`](generated/metrics_reference.md) renders them for each tool side by side. Regenerate with `python bi/generate_bi_snippets.py` (a test fails if the committed reference is stale).

| Metric | Control value to compare against |
|---|---|
| Revenue | $2,297,200.86 |
| Profit | $286,397.02 |
| Profit margin | 12.47% |
| Orders | 5,009 |
| Customers | 793 |
| Average order value | $458.61 |

If a card in any tool disagrees with these figures, the tool's expression is wrong, not the data.

## Looker Studio (free)

1. Create a data source: **BigQuery** (project, dataset, table `mart_sales_flat` or the views), or upload `mart_sales_flat.csv` through a file or Google Sheets connector.
2. Add calculated fields from the *Looker Studio* column of the metric reference, for example `SUM(profit) / SUM(sales)` for profit margin and `COUNT_DISTINCT(order_id)` for orders.
3. Set the field types: `order_date` as a date, `discount` and margin fields as percent, `sales` and `profit` as currency.
4. Suggested pages:
   - **Overview:** scorecards (Revenue, Profit, Margin, Orders), time series of revenue by month with a year control, and a region filter.
   - **Products:** sub-category profit bar with negative values highlighted, plus a discount-band margin chart.
   - **Customers:** RFM segment table from `mart_customer_rfm`.
5. Share with view-only access. Looker Studio can show data from sources you connect, so connect only the masked marts.

## Tableau (Public is free)

1. Connect to `mart_sales_flat.csv` (text file). Tableau Public can publish only to the public web, so use only the masked data and never anything private.
2. Create calculated fields from the *Tableau* column, for example `SUM([Profit]) / SUM([Sales])`.
3. Build: a sheet of profit by sub-category sorted descending, margin by discount band, monthly sales with year-over-year as a quick table calculation, and a dashboard that ties them together with filter actions.
4. Check each KPI against the control values above before publishing.

## Cognos Analytics

Cognos needs a licensed or trial environment, which was not available here, so this is a design only.

1. Upload `mart_sales_flat.csv` (or connect to the BigQuery or relational copy) and create a **data module**.
2. Define measures (Revenue, Profit, Orders) with the right aggregation (sum, and distinct count for orders and customers) and calculated items for margin.
3. Build a dashboard with the same three pages as above.
4. Compare totals with the control values before sharing.

## Power BI

The original reports are in [`../powerbi/`](../powerbi/). To build a new report on the masked data:

1. Load `reports/marts/mart_sales_flat.csv` with [`powerquery/20_sales_flat_masked.pq`](../powerquery/20_sales_flat_masked.pq) (table name `sales_flat`).
2. Add a `Calendar` date table related to `sales_flat[order_date]`.
3. Add the measures from [`../powerbi/proposed_measures.dax`](../powerbi/proposed_measures.dax) (unvalidated; compare with the control values).

## Dashboard checklist

- Every KPI card matches the control values.
- Negative profit is visible (colour or sign), not hidden by an axis starting at zero.
- Customers appear only as masked tokens.
- Filters are labelled and a reset is available.
- A caption says the data is a 2014 to 2017 sample and gives its source.
