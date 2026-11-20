-- Window-function equivalents of the Power BI DAX measures:
--   Previous Month Revenue (PREVIOUSMONTH), Revenue SPLY (SAMEPERIODLASTYEAR), Revenue YTD (DATESYTD).
-- LAG over the month sequence is valid because every month of the period has orders (asserted in tests).
CREATE OR REPLACE TABLE mart_monthly_sales AS
WITH monthly AS (
    SELECT
        d.year,
        d.month_number,
        d.year_month,
        SUM(f.sales)                 AS sales,
        SUM(f.profit)                AS profit,
        COUNT(DISTINCT f.order_id)   AS orders,
        SUM(f.quantity)              AS units
    FROM fact_orders f
    JOIN dim_date d ON d.date_key = f.order_date_key
    GROUP BY d.year, d.month_number, d.year_month
)
SELECT
    year,
    month_number,
    year_month,
    sales,
    profit,
    profit / NULLIF(sales, 0)                                                    AS margin,
    orders,
    units,
    LAG(sales, 1)  OVER w                                                        AS prev_month_sales,
    sales - LAG(sales, 1) OVER w                                                 AS mom_change,
    (sales - LAG(sales, 1) OVER w) / NULLIF(LAG(sales, 1) OVER w, 0)             AS mom_pct,
    LAG(sales, 12) OVER w                                                        AS sales_sply,
    (sales - LAG(sales, 12) OVER w) / NULLIF(LAG(sales, 12) OVER w, 0)           AS yoy_pct,
    SUM(sales) OVER (PARTITION BY year ORDER BY month_number)                    AS ytd_sales,
    sales / SUM(sales) OVER (PARTITION BY year)                                  AS share_of_year
FROM monthly
WINDOW w AS (ORDER BY year, month_number)
ORDER BY year, month_number;
