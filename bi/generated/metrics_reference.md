# Metric reference (generated)

Generated from `bi/metrics.yml` by `bi/generate_bi_snippets.py`. Do not edit by hand.

Source table: `mart_sales_flat` (Power BI / Fabric table name: `sales_flat`).

The **SQL** column is executed and tested. The DAX, Tableau and Looker Studio columns are hand-written
equivalents that have **not** been run in those tools.

| Metric | Format | SQL (tested) | Power BI (DAX) | Tableau | Looker Studio |
|---|---|---|---|---|---|
| Revenue | currency | `SUM(sales)` | `SUM(sales_flat[sales])` | `SUM([Sales])` | `SUM(sales)` |
| Profit | currency | `SUM(profit)` | `SUM(sales_flat[profit])` | `SUM([Profit])` | `SUM(profit)` |
| Profit margin | percent | `SUM(profit) / NULLIF(SUM(sales), 0)` | `DIVIDE(SUM(sales_flat[profit]), SUM(sales_flat[sales]))` | `SUM([Profit]) / SUM([Sales])` | `SUM(profit) / SUM(sales)` |
| Orders | integer | `COUNT(DISTINCT order_id)` | `DISTINCTCOUNT(sales_flat[order_id])` | `COUNTD([Order Id])` | `COUNT_DISTINCT(order_id)` |
| Customers | integer | `COUNT(DISTINCT customer_id)` | `DISTINCTCOUNT(sales_flat[customer_id])` | `COUNTD([Customer Id])` | `COUNT_DISTINCT(customer_id)` |
| Average order value | currency | `SUM(sales) / NULLIF(COUNT(DISTINCT order_id), 0)` | `DIVIDE(SUM(sales_flat[sales]), DISTINCTCOUNT(sales_flat[order_id]))` | `SUM([Sales]) / COUNTD([Order Id])` | `SUM(sales) / COUNT_DISTINCT(order_id)` |
| Units sold | integer | `SUM(quantity)` | `SUM(sales_flat[quantity])` | `SUM([Quantity])` | `SUM(quantity)` |
| Average discount | percent | `AVG(discount)` | `AVERAGE(sales_flat[discount])` | `AVG([Discount])` | `AVG(discount)` |
| Loss-making line share | percent | `AVG(CASE WHEN profit < 0 THEN 1.0 ELSE 0.0 END)` | `DIVIDE(COUNTROWS(FILTER(sales_flat, sales_flat[profit] < 0)), COUNTROWS(sales_flat))` | `SUM(IIF([Profit] < 0, 1, 0)) / COUNT([Order Line Id])` | `SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) / COUNT(order_line_id)` |
| Average days to ship | decimal | `AVG(ship_days)` | `AVERAGE(sales_flat[ship_days])` | `AVG([Ship Days])` | `AVG(ship_days)` |

## Definitions

- **Revenue**: Net sales after discounts.
- **Profit**: Profit as reported per order line in the source data (the source does not document its exact definition).
- **Profit margin**: Profit divided by revenue.
- **Orders**: Distinct orders (an order can have several lines).
- **Customers**: Distinct (masked) customers who ordered.
- **Average order value**: Revenue per distinct order.
- **Units sold**: Total quantity sold.
- **Average discount**: Mean discount across order lines (line-weighted, not revenue-weighted).
- **Loss-making line share**: Share of order lines with negative profit.
- **Average days to ship**: Mean days between order and ship date.

## Dimensions

`order_date` (Order date), `year` (Year), `quarter` (Quarter), `year_month` (Year-month), `region` (Region), `state` (State), `segment` (Customer segment), `category` (Category), `sub_category` (Sub-category), `ship_mode` (Ship mode), `discount_band` (Discount band)
