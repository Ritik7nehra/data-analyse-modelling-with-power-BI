"""Load the DuckDB warehouse into BigQuery and create the mart views.

    pip install -e ".[bigquery]"
    gcloud auth application-default login
    python warehouse/bigquery/load_to_bigquery.py --project MY_PROJECT --dataset superstore_analytics

    # no credentials needed: shows what would be loaded and validates the generated frames
    python warehouse/bigquery/load_to_bigquery.py --project demo --dataset demo --dry-run

STATUS: the dry run is tested in CI. The live load has not been executed against a real BigQuery project
in this repository's build environment.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_DB = ROOT / "build" / "superstore.duckdb"

FACT_SQL = """
SELECT f.order_line_id, f.order_id, od.full_date AS order_date, sd.full_date AS ship_date,
       f.order_date_key, f.ship_date_key, f.customer_key, f.geography_key, f.product_key,
       f.ship_mode, f.sales, f.quantity, f.discount, f.profit, f.cost, f.gross_sales, f.ship_days
FROM fact_orders f
JOIN dim_date od ON od.date_key = f.order_date_key
JOIN dim_date sd ON sd.date_key = f.ship_date_key
ORDER BY f.order_line_id
"""
LOAD_ORDER = ["dim_date", "dim_customer", "dim_product", "dim_geography", "fact_orders"]


def render(sql: str, project: str, dataset: str) -> str:
    return sql.replace("{{project}}", project).replace("{{dataset}}", dataset)


def frames(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    """DataFrames to load, one per BigQuery table, with column names matching 00_schema.sql."""
    out = {t: con.execute(f"SELECT * FROM {t}").df() for t in LOAD_ORDER if t != "fact_orders"}
    out["fact_orders"] = con.execute(FACT_SQL).df()
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", required=True)
    p.add_argument("--dataset", default="superstore_analytics")
    p.add_argument("--location", default="US")
    p.add_argument("--duckdb", default=str(DEFAULT_DB), help="warehouse produced by the pipeline")
    p.add_argument("--dry-run", action="store_true", help="validate and print the plan without calling BigQuery")
    args = p.parse_args(argv)

    db = Path(args.duckdb)
    if not db.exists():
        print(f"warehouse not found: {db} (run `python -m superstore_pipeline run` first)", file=sys.stderr)
        return 2
    with duckdb.connect(str(db), read_only=True) as con:
        data = frames(con)
    schema_sql = render((HERE / "00_schema.sql").read_text(), args.project, args.dataset)
    views_sql = render((HERE / "10_views.sql").read_text(), args.project, args.dataset)

    if args.dry_run:
        print(f"[dry-run] target: {args.project}.{args.dataset} ({args.location})")
        for name in LOAD_ORDER:
            print(f"[dry-run]   {name:<15}{len(data[name]):>7,} rows  {len(data[name].columns)} columns")
        print(f"[dry-run]   DDL statements: {schema_sql.count(';')}, view statements: {views_sql.count(';')}")
        return 0

    from google.cloud import bigquery  # imported lazily: not needed for dry runs

    client = bigquery.Client(project=args.project, location=args.location)
    client.create_dataset(bigquery.Dataset(f"{args.project}.{args.dataset}"), exists_ok=True)
    client.query(schema_sql).result()
    for name in LOAD_ORDER:
        cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
        if name == "fact_orders":
            cfg.time_partitioning = bigquery.TimePartitioning(field="order_date")
            cfg.clustering_fields = ["customer_key", "product_key", "geography_key"]
        client.load_table_from_dataframe(data[name], f"{args.project}.{args.dataset}.{name}", job_config=cfg).result()
        print(f"loaded {name}: {len(data[name]):,} rows")
    client.query(views_sql).result()
    print("views created")
    return 0


if __name__ == "__main__":
    sys.exit(main())
