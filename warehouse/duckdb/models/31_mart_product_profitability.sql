CREATE OR REPLACE TABLE mart_product_profitability AS
SELECT
    p.category,
    p.sub_category,
    SUM(f.sales)                                         AS sales,
    SUM(f.profit)                                        AS profit,
    SUM(f.profit) / NULLIF(SUM(f.sales), 0)              AS margin,
    SUM(f.quantity)                                      AS units,
    AVG(f.discount)                                      AS avg_discount,
    AVG(CASE WHEN f.profit < 0 THEN 1.0 ELSE 0.0 END)    AS loss_line_share,
    SUM(CASE WHEN f.profit < 0 THEN f.profit ELSE 0 END) AS total_losses,
    SUM(f.sales) / SUM(SUM(f.sales)) OVER ()             AS sales_share,
    RANK() OVER (ORDER BY SUM(f.profit) DESC)            AS profit_rank
FROM fact_orders f
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY p.category, p.sub_category
ORDER BY profit_rank;
