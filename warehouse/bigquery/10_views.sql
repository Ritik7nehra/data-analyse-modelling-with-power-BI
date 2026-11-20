-- BI-facing marts as BigQuery views (Looker Studio and Tableau connect to these).
-- BigQuery equivalents of the DuckDB models in warehouse/duckdb/models/.

CREATE OR REPLACE VIEW `{{project}}.{{dataset}}.mart_monthly_sales` AS
WITH monthly AS (
  SELECT
    EXTRACT(YEAR FROM order_date)  AS year,
    EXTRACT(MONTH FROM order_date) AS month_number,
    FORMAT_DATE('%Y-%m', order_date) AS year_month,
    SUM(sales)                     AS sales,
    SUM(profit)                    AS profit,
    COUNT(DISTINCT order_id)       AS orders,
    SUM(quantity)                  AS units
  FROM `{{project}}.{{dataset}}.fact_orders`
  GROUP BY year, month_number, year_month
)
SELECT
  year, month_number, year_month, sales, profit,
  SAFE_DIVIDE(profit, sales)                                          AS margin,
  orders, units,
  LAG(sales, 1)  OVER w                                               AS prev_month_sales,
  SAFE_DIVIDE(sales - LAG(sales, 1) OVER w, LAG(sales, 1) OVER w)     AS mom_pct,
  LAG(sales, 12) OVER w                                               AS sales_sply,
  SAFE_DIVIDE(sales - LAG(sales, 12) OVER w, LAG(sales, 12) OVER w)   AS yoy_pct,
  SUM(sales) OVER (PARTITION BY year ORDER BY month_number)           AS ytd_sales
FROM monthly
WINDOW w AS (ORDER BY year, month_number);

CREATE OR REPLACE VIEW `{{project}}.{{dataset}}.mart_product_profitability` AS
SELECT
  p.category,
  p.sub_category,
  SUM(f.sales)                                   AS sales,
  SUM(f.profit)                                  AS profit,
  SAFE_DIVIDE(SUM(f.profit), SUM(f.sales))       AS margin,
  SUM(f.quantity)                                AS units,
  AVG(f.discount)                                AS avg_discount,
  AVG(IF(f.profit < 0, 1.0, 0.0))                AS loss_line_share,
  RANK() OVER (ORDER BY SUM(f.profit) DESC)      AS profit_rank
FROM `{{project}}.{{dataset}}.fact_orders` f
JOIN `{{project}}.{{dataset}}.dim_product` p USING (product_key)
GROUP BY p.category, p.sub_category;

CREATE OR REPLACE VIEW `{{project}}.{{dataset}}.mart_discount_impact` AS
WITH banded AS (
  SELECT
    CASE
      WHEN discount = 0   THEN '0. No discount'
      WHEN discount <= 0.2 THEN '1. 1-20%'
      WHEN discount <= 0.4 THEN '2. 21-40%'
      ELSE '3. Over 40%'
    END AS discount_band,
    sales, profit
  FROM `{{project}}.{{dataset}}.fact_orders`
)
SELECT
  discount_band,
  COUNT(*)                              AS order_lines,
  SUM(sales)                            AS sales,
  SUM(profit)                           AS profit,
  SAFE_DIVIDE(SUM(profit), SUM(sales))  AS margin,
  COUNTIF(profit < 0)                   AS loss_lines
FROM banded
GROUP BY discount_band;

CREATE OR REPLACE VIEW `{{project}}.{{dataset}}.mart_customer_rfm` AS
WITH cust AS (
  SELECT
    c.customer_key,
    c.customer_id,
    c.segment,
    MAX(f.order_date)          AS last_order_date,
    COUNT(DISTINCT f.order_id) AS frequency,
    SUM(f.sales)               AS monetary,
    SUM(f.profit)              AS profit
  FROM `{{project}}.{{dataset}}.fact_orders` f
  JOIN `{{project}}.{{dataset}}.dim_customer` c USING (customer_key)
  GROUP BY c.customer_key, c.customer_id, c.segment
),
ref AS (SELECT MAX(last_order_date) AS as_of FROM cust),
scored AS (
  SELECT
    cust.*,
    DATE_DIFF(ref.as_of, cust.last_order_date, DAY) AS recency_days,
    NTILE(5) OVER (ORDER BY DATE_DIFF(ref.as_of, cust.last_order_date, DAY) DESC, cust.customer_key) AS r_score,
    NTILE(5) OVER (ORDER BY cust.frequency, cust.customer_key) AS f_score,
    NTILE(5) OVER (ORDER BY cust.monetary,  cust.customer_key) AS m_score
  FROM cust CROSS JOIN ref
)
SELECT
  *,
  CASE
    WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
    WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
    WHEN r_score >= 4 AND f_score <= 2 THEN 'New / Promising'
    WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
    WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost / Hibernating'
    ELSE 'Needs Attention'
  END AS rfm_segment
FROM scored;
