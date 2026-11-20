CREATE OR REPLACE TABLE dim_product AS
SELECT
    DENSE_RANK() OVER (ORDER BY category, sub_category, product_name) AS product_key,
    product_name,
    category,
    sub_category
FROM (SELECT DISTINCT product_name, category, sub_category FROM stg_orders);
