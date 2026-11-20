-- Calendar dimension covering whole calendar years (like Power BI's CALENDARAUTO()).
CREATE OR REPLACE TABLE dim_date AS
WITH bounds AS (
    SELECT
        MAKE_DATE(YEAR(MIN(order_date)), 1, 1)  AS first_day,
        MAKE_DATE(YEAR(MAX(ship_date)), 12, 31) AS last_day
    FROM stg_orders
),
days AS (
    SELECT CAST(UNNEST(GENERATE_SERIES(first_day, last_day, INTERVAL 1 DAY)) AS DATE) AS full_date
    FROM bounds
)
SELECT
    CAST(STRFTIME(full_date, '%Y%m%d') AS INTEGER) AS date_key,
    full_date,
    YEAR(full_date)                                AS year,
    QUARTER(full_date)                             AS quarter,
    MONTH(full_date)                               AS month_number,
    STRFTIME(full_date, '%b')                      AS month_name,
    STRFTIME(full_date, '%Y-%m')                   AS year_month,
    WEEKOFYEAR(full_date)                          AS week_of_year,
    ISODOW(full_date)                              AS iso_day_of_week,
    STRFTIME(full_date, '%a')                      AS day_name,
    ISODOW(full_date) >= 6                         AS is_weekend
FROM days;
