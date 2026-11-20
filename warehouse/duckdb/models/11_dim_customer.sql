-- One row per (masked) customer. Surrogate key is deterministic: rank of the masked ID.
CREATE OR REPLACE TABLE dim_customer AS
SELECT
    DENSE_RANK() OVER (ORDER BY customer_id) AS customer_key,
    customer_id,
    segment
FROM (SELECT DISTINCT customer_id, segment FROM stg_orders);
