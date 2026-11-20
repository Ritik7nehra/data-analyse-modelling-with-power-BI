# Pipeline management

How a run is orchestrated, observed and recovered. Run it with `python -m superstore_pipeline run` (or `make pipeline`).

## Steps and dependencies

| # | Step | Depends on | What it does | Stops the run when |
|---|---|---|---|---|
| 1 | `extract` | none | Reads the source CSV (postal code as text) and records lineage (file name, SHA-256 hash, row count) | the file is missing or unreadable |
| 2 | `validate` | extract | Runs 21 data-quality checks and writes `build/data_quality_report.json` | any **error**-severity check fails |
| 3 | `mask` | validate | Pseudonymises customer IDs, generalises postcodes, proves no raw ID remains | masking cannot be applied or a raw ID leaks |
| 4 | `load_staging` | mask | Rebuilds the DuckDB file from scratch and loads `stg_orders` | load fails |
| 5 | `build_models` | load_staging | Executes `warehouse/duckdb/models/*.sql` in filename order | any model fails |
| 6 | `reconcile` | build_models | Compares row count, sales and profit with `config/pipeline.yml` control totals and checks for orphan foreign keys | any total is outside tolerance or a key is orphaned |
| 7 | `publish` | reconcile | Stores `dq_results`, exports every `mart_*` table to `reports/marts/*.csv` | export fails |

If a step fails, every step that depends on it is recorded as `skipped` (fail-fast), and nothing is published. The process exit code is `0` on success and `1` on failure, so schedulers and CI can act on it. `validate` alone (`python -m superstore_pipeline validate`) exits `1` if any error-severity check fails.

## Observability

- **Run log:** `build/pipeline_runs.jsonl`, one JSON object per step with `run_id`, `step`, `status` (`success`, `failed` or `skipped`), `started_at`, `duration_s` and a `detail` payload (row counts, masking report, control totals, error type and message).
- **In the warehouse:** the same records are stored in `pipeline_runs`, and each quality check in `dq_results`, so run history can be queried with SQL or shown in a BI tool.
- **Console:** one line per step with its duration and the headline number.
- **Quality report:** `build/data_quality_report.json` lists every check with its severity, failing row count and description.

## Data-quality gates

21 checks in four groups:

- **Schema and completeness:** all 17 expected columns present, no missing values.
- **Value rules:** sales and quantity positive, discount between 0 and 1, profit not above sales, ship date not before order date, shipping takes at most 14 days, no order dated in the future.
- **Formats and domains:** Order ID and Customer ID patterns, and allowed values for ship mode, segment, region and category.
- **Consistency:** one segment per customer, one region per state (both needed for the dimension tables), Order ID year versus order date, Customer ID letter case (uppercase, and no two IDs differing only by case), and no duplicate order lines.

Three checks currently raise **warnings** because they describe real quirks in the source data, not pipeline bugs. They are reported on every run but do not stop it:

| Warning check | Rows | Meaning |
|---|---|---|
| `order_id_year_matches_order_date` | 7 | The year inside the Order ID differs from the order date's year |
| `customer_id_uppercase` | 43 | Some customer IDs use lower-case letters (3 customers) |
| `no_duplicate_rows` | 1 | One order line appears twice with identical values |

## Control totals are a change-control gate

`config/pipeline.yml` holds the expected row count, sales and profit (taken from the original Power BI report). A genuine data refresh will therefore fail `reconcile` until someone updates those numbers on purpose. That is intentional: the totals must be reviewed, not silently accepted.

## Runbook

| Symptom | Likely cause | Action |
|---|---|---|
| `validate` failed | Source file changed or is corrupt | Read `build/data_quality_report.json`; fix the source or, if the rule is wrong, change the rule in a reviewed commit |
| `mask` failed with `MaskingKeyError` | `--strict-masking` without `MASKING_KEY` | Provide the secret in the environment |
| `reconcile` failed | Totals differ from `config/pipeline.yml`, or an orphan foreign key | Compare `detail.control_totals` in the run log with the config; investigate before changing the config |
| `build_models` failed | SQL error in a model | The error names the model file; `pytest tests/test_sql_static.py` parses all models |
| Downstream steps `skipped` | An upstream step failed | Fix the first failed step and re-run; runs are idempotent |
| Marts differ between two runs | Should not happen (`test_marts_are_byte_reproducible`) | Check the DuckDB version and that `SET threads = 1` is applied in `warehouse.connect` |

## Re-runs and idempotency

Every run deletes and rebuilds the DuckDB file, so re-running after a fix is always safe and produces identical marts. The JSONL log is append-only, so history is kept across runs.

## What exists around the pipeline

| Concern | Status |
|---|---|
| CI on every push and pull request (lint, tests, strict-mode run, notebook execution) | Written in `.github/workflows/ci.yml`; commands verified locally; **not yet run on GitHub Actions** |
| Manual rebuild of Excel and deck artifacts | `.github/workflows/deliverables.yml`; not yet run |
| Manual BigQuery deployment with a dry-run option | `.github/workflows/bigquery-deploy.yml`; **not executed** (needs a GCP project and secrets) |
| Scheduling | Not implemented. Options: a `schedule:` cron trigger in GitHub Actions, Cloud Scheduler plus Cloud Run, Airflow, or Fabric Data Factory pipelines (see [fabric_mapping.md](fabric_mapping.md)) |
| Alerting | Not implemented. Add a failure notification step to the workflow or scheduler |
| Retries and incremental loads | Not implemented. Not needed at this data size |

## Suggested environments

For a real deployment: `dev` (local, dev key allowed), `test` (CI, ephemeral key, synthetic or sampled data) and `prod` (secret key from a secret manager, strict mode, approval gate on the deploy workflow using a GitHub Environment with required reviewers).
