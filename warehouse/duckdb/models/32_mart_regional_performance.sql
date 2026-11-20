CREATE OR REPLACE TABLE mart_regional_performance AS
SELECT
    g.region,
    g.state,
    SUM(f.sales)                            AS sales,
    SUM(f.profit)                           AS profit,
    SUM(f.profit) / NULLIF(SUM(f.sales), 0) AS margin,
    COUNT(DISTINCT f.order_id)              AS orders,
    COUNT(DISTINCT f.customer_key)          AS customers,
    AVG(f.discount)                         AS avg_discount,
    RANK() OVER (ORDER BY SUM(f.profit) DESC) AS profit_rank
FROM fact_orders f
JOIN dim_geography g ON g.geography_key = f.geography_key
GROUP BY g.region, g.state
ORDER BY profit_rank;
