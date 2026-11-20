-- Wide, denormalised order-line table: the simplest source for Excel, Tableau, Looker Studio and Cognos.
-- Contains masked customer tokens and generalised postal prefixes only.
CREATE OR REPLACE TABLE mart_sales_flat AS
SELECT
    f.order_line_id,
    f.order_id,
    od.full_date                         AS order_date,
    sd.full_date                         AS ship_date,
    od.year,
    od.quarter,
    od.month_number,
    od.month_name,
    od.year_month,
    f.ship_mode,
    c.customer_id,
    c.segment,
    g.region,
    g.state,
    g.city,
    g.postal_prefix,
    p.category,
    p.sub_category,
    p.product_name,
    f.sales,
    f.quantity,
    f.discount,
    CASE
        WHEN f.discount = 0    THEN '0. No discount'
        WHEN f.discount <= 0.2 THEN '1. 1-20%'
        WHEN f.discount <= 0.4 THEN '2. 21-40%'
        ELSE                        '3. Over 40%'
    END                                  AS discount_band,
    f.profit,
    f.cost,
    f.gross_sales,
    f.ship_days,
    f.profit < 0                         AS is_loss_making
FROM fact_orders f
JOIN dim_date      od ON od.date_key = f.order_date_key
JOIN dim_date      sd ON sd.date_key = f.ship_date_key
JOIN dim_customer  c  ON c.customer_key = f.customer_key
JOIN dim_geography g  ON g.geography_key = f.geography_key
JOIN dim_product   p  ON p.product_key = f.product_key
ORDER BY f.order_line_id;
