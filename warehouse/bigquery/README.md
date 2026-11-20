# BigQuery warehouse

The same star schema as the DuckDB warehouse, expressed for BigQuery, plus the views the BI tools read.

> **Status: written, not run against a real BigQuery project.** What *is* tested: the SQL parses in BigQuery's dialect (sqlglot), the fact table is partitioned and clustered in the DDL, the views reference only defined tables, the loader's DataFrames match the DDL's columns exactly, and the loader's `--dry-run` works without credentials (`tests/test_sql_static.py`). What has *not* been verified: the live load, the views executing, and query cost and performance.

## Files

| File | Purpose |
|---|---|
| `00_schema.sql` | Dataset tables: `dim_date`, `dim_customer`, `dim_product`, `dim_geography` and `fact_orders` (partitioned by `order_date`, clustered by customer, product and geography keys). Primary and foreign keys are declared `NOT ENFORCED`, which BigQuery treats as hints for the optimiser |
| `10_views.sql` | Four views over the star schema that mirror marts: `mart_monthly_sales`, `mart_product_profitability`, `mart_discount_impact` and `mart_customer_rfm`. The other marts (regional performance, what-if, executive KPIs, flat extract) exist as CSV exports and DuckDB tables only |
| `load_to_bigquery.py` | Reads the DuckDB warehouse, creates the dataset and tables, loads them, and creates the views |

Both SQL files use the placeholders `{{project}}` and `{{dataset}}`, substituted by the loader.

## Modelling choices

- **Partition `fact_orders` by `order_date`**, so date-filtered queries scan only the relevant partitions.
- **Cluster by `customer_key`, `product_key`, `geography_key`**, the usual filter and join columns.
- **Keep the dimensions small and unpartitioned.** They are tiny; partitioning them would add nothing.
- **Money as `FLOAT64` for a simple load.** For production finance data use `NUMERIC` with decimal types in the load.
- **Customer ID holds a masked token only.** The schema description says so; raw IDs never reach BigQuery.

## Try it (free sandbox)

1. Create a Google Cloud project and open BigQuery. The **sandbox** lets you use BigQuery without a billing account, within limits and with expiry on tables. Read Google's current sandbox page for the exact limits.
2. Authenticate locally: `gcloud auth application-default login`.
3. Build the warehouse and check the plan without touching the cloud:

   ```bash
   pip install -e ".[bigquery]"
   python -m superstore_pipeline run
   python warehouse/bigquery/load_to_bigquery.py --project YOUR_PROJECT --dataset superstore_analytics --dry-run
   ```

4. Load for real (remove `--dry-run`).
5. Run the checks below. If anything differs, fix the SQL and record what you found.

## Checks after loading

```sql
-- should return 9994 rows, 2297200.86 sales, 286397.02 profit
SELECT COUNT(*) AS rows_loaded, ROUND(SUM(sales), 2) AS sales, ROUND(SUM(profit), 2) AS profit
FROM `YOUR_PROJECT.superstore_analytics.fact_orders`;

-- should return 0: no fact row without a matching customer
SELECT COUNT(*) FROM `YOUR_PROJECT.superstore_analytics.fact_orders` f
LEFT JOIN `YOUR_PROJECT.superstore_analytics.dim_customer` c USING (customer_key)
WHERE c.customer_key IS NULL;
```

In the BigQuery console, use *Query settings > Dry run* (or the bytes-processed estimate) to see how much a query would scan before running it. Partition pruning should show up when you filter on `order_date`.

## Automation

`.github/workflows/bigquery-deploy.yml` is a manual workflow with a dry-run default. It needs a project, a service account and the `GCP_SA_KEY` and `MASKING_KEY` secrets, and it has not been executed. For real use, prefer Workload Identity Federation over a long-lived JSON key.
