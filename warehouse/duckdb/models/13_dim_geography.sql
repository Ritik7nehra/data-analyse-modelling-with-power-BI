-- Postal codes are already generalised to a prefix by the masking step.
CREATE OR REPLACE TABLE dim_geography AS
SELECT
    DENSE_RANK() OVER (ORDER BY region, state, city, postal_prefix) AS geography_key,
    city,
    state,
    postal_prefix,
    region
FROM (SELECT DISTINCT city, state, postal_prefix, region FROM stg_orders);
