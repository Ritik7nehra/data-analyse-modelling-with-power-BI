-- RFM segmentation on masked customers: Recency (days since last order), Frequency (distinct orders),
-- Monetary (sales). Quintile scores via NTILE; customer_key is the deterministic tie-breaker.
CREATE OR REPLACE TABLE mart_customer_rfm AS
WITH cust AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.segment,
        MAX(d.full_date)             AS last_order_date,
        COUNT(DISTINCT f.order_id)   AS frequency,
        SUM(f.sales)                 AS monetary,
        SUM(f.profit)                AS profit
    FROM fact_orders f
    JOIN dim_customer c ON c.customer_key = f.customer_key
    JOIN dim_date d     ON d.date_key = f.order_date_key
    GROUP BY c.customer_key, c.customer_id, c.segment
),
ref AS (SELECT MAX(last_order_date) AS as_of FROM cust),
scored AS (
    SELECT
        cust.*,
        DATE_DIFF('day', cust.last_order_date, ref.as_of)                                   AS recency_days,
        NTILE(5) OVER (ORDER BY DATE_DIFF('day', cust.last_order_date, ref.as_of) DESC, cust.customer_key) AS r_score,
        NTILE(5) OVER (ORDER BY cust.frequency, cust.customer_key)                          AS f_score,
        NTILE(5) OVER (ORDER BY cust.monetary,  cust.customer_key)                          AS m_score
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
FROM scored
ORDER BY monetary DESC;
