-- Grain: one row per order line. Inner joins: any lost or duplicated row is caught by the
-- control-total reconciliation in the pipeline runner.
CREATE OR REPLACE TABLE fact_orders AS
SELECT
    ROW_NUMBER() OVER (
        ORDER BY s.order_date, s.order_id, s.product_name, s.sales, s.quantity, s.profit
    )                                                         AS order_line_id,
    s.order_id,
    CAST(STRFTIME(s.order_date, '%Y%m%d') AS INTEGER)         AS order_date_key,
    CAST(STRFTIME(s.ship_date,  '%Y%m%d') AS INTEGER)         AS ship_date_key,
    c.customer_key,
    g.geography_key,
    p.product_key,
    s.ship_mode,
    s.sales,
    s.quantity,
    s.discount,
    s.profit,
    s.sales - s.profit                                        AS cost,
    s.sales / NULLIF(1 - s.discount, 0)                       AS gross_sales,   -- list price before discount
    DATE_DIFF('day', s.order_date, s.ship_date)               AS ship_days
FROM stg_orders s
JOIN dim_customer  c ON c.customer_id = s.customer_id
JOIN dim_geography g ON g.city = s.city AND g.state = s.state AND g.postal_prefix = s.postal_prefix
JOIN dim_product   p ON p.product_name = s.product_name
                    AND p.category = s.category AND p.sub_category = s.sub_category;
