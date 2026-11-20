-- BigQuery star schema. Placeholders {{project}} and {{dataset}} are substituted by load_to_bigquery.py.
-- Money columns use FLOAT64 for a simple load. Use NUMERIC (with decimal parquet) for production finance data.

CREATE TABLE IF NOT EXISTS `{{project}}.{{dataset}}.dim_date` (
  date_key        INT64 NOT NULL,
  full_date       DATE  NOT NULL,
  year            INT64,
  quarter         INT64,
  month_number    INT64,
  month_name      STRING,
  year_month      STRING,
  week_of_year    INT64,
  iso_day_of_week INT64,
  day_name        STRING,
  is_weekend      BOOL,
  PRIMARY KEY (date_key) NOT ENFORCED
)
OPTIONS (description = 'Calendar dimension (whole calendar years)');

CREATE TABLE IF NOT EXISTS `{{project}}.{{dataset}}.dim_customer` (
  customer_key INT64  NOT NULL,
  customer_id  STRING NOT NULL OPTIONS (description = 'Masked token (HMAC-SHA256), never the raw customer ID'),
  segment      STRING,
  PRIMARY KEY (customer_key) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS `{{project}}.{{dataset}}.dim_product` (
  product_key  INT64  NOT NULL,
  product_name STRING,
  category     STRING,
  sub_category STRING,
  PRIMARY KEY (product_key) NOT ENFORCED
);

CREATE TABLE IF NOT EXISTS `{{project}}.{{dataset}}.dim_geography` (
  geography_key INT64 NOT NULL,
  city          STRING,
  state         STRING,
  postal_prefix STRING OPTIONS (description = 'Postal code generalised to its first 3 digits'),
  region        STRING,
  PRIMARY KEY (geography_key) NOT ENFORCED
);

-- Partitioned by order date (prunes scans for time-bounded dashboards) and clustered by the
-- columns most often used in joins and filters.
CREATE TABLE IF NOT EXISTS `{{project}}.{{dataset}}.fact_orders` (
  order_line_id  INT64   NOT NULL,
  order_id       STRING  NOT NULL,
  order_date     DATE    NOT NULL,
  ship_date      DATE    NOT NULL,
  order_date_key INT64   NOT NULL,
  ship_date_key  INT64   NOT NULL,
  customer_key   INT64   NOT NULL,
  geography_key  INT64   NOT NULL,
  product_key    INT64   NOT NULL,
  ship_mode      STRING,
  sales          FLOAT64,
  quantity       INT64,
  discount       FLOAT64,
  profit         FLOAT64,
  cost           FLOAT64,
  gross_sales    FLOAT64,
  ship_days      INT64,
  PRIMARY KEY (order_line_id) NOT ENFORCED,
  FOREIGN KEY (customer_key)  REFERENCES `{{project}}.{{dataset}}.dim_customer`  (customer_key)  NOT ENFORCED,
  FOREIGN KEY (geography_key) REFERENCES `{{project}}.{{dataset}}.dim_geography` (geography_key) NOT ENFORCED,
  FOREIGN KEY (product_key)   REFERENCES `{{project}}.{{dataset}}.dim_product`   (product_key)   NOT ENFORCED
)
PARTITION BY order_date
CLUSTER BY customer_key, product_key, geography_key
OPTIONS (description = 'Grain: one row per order line');
