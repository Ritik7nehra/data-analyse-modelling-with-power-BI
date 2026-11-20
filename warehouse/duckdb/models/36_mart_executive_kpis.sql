CREATE OR REPLACE TABLE mart_executive_kpis AS
SELECT
    COALESCE(CAST(d.year AS VARCHAR), 'All years')              AS period,
    SUM(f.sales)                                                AS sales,
    SUM(f.profit)                                               AS profit,
    SUM(f.profit) / NULLIF(SUM(f.sales), 0)                     AS margin,
    COUNT(DISTINCT f.order_id)                                  AS orders,
    COUNT(DISTINCT f.customer_key)                              AS customers,
    SUM(f.sales) / COUNT(DISTINCT f.order_id)                   AS avg_order_value,
    SUM(f.quantity)                                             AS units,
    AVG(f.discount)                                             AS avg_discount,
    AVG(CASE WHEN f.profit < 0 THEN 1.0 ELSE 0.0 END)           AS loss_line_share,
    AVG(f.ship_days)                                            AS avg_ship_days
FROM fact_orders f
JOIN dim_date d ON d.date_key = f.order_date_key
GROUP BY ROLLUP (d.year)
ORDER BY CASE WHEN d.year IS NULL THEN 1 ELSE 0 END, d.year;
