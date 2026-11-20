CREATE OR REPLACE TABLE mart_discount_impact AS
WITH banded AS (
    SELECT
        CASE
            WHEN discount = 0   THEN '0. No discount'
            WHEN discount <= 0.2 THEN '1. 1-20%'
            WHEN discount <= 0.4 THEN '2. 21-40%'
            ELSE                      '3. Over 40%'
        END AS discount_band,
        sales, profit
    FROM fact_orders
)
SELECT
    discount_band,
    COUNT(*)                                                     AS order_lines,
    COUNT(*) * 1.0 / SUM(COUNT(*)) OVER ()                       AS share_of_lines,
    SUM(sales)                                                   AS sales,
    SUM(profit)                                                  AS profit,
    SUM(profit) / NULLIF(SUM(sales), 0)                          AS margin,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END)                  AS loss_lines,
    SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END)             AS total_losses,
    SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END)
        / SUM(SUM(CASE WHEN profit < 0 THEN profit ELSE 0 END)) OVER () AS share_of_all_losses
FROM banded
GROUP BY discount_band
ORDER BY discount_band;
