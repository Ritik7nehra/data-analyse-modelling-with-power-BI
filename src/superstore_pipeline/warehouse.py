"""Load masked data into a DuckDB warehouse and run the SQL models in order."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

STG_COLUMNS = {
    "Order ID": "order_id", "Order Date": "order_date", "Ship Date": "ship_date", "Ship Mode": "ship_mode",
    "Customer ID": "customer_id", "Sales": "sales", "Quantity": "quantity", "Discount": "discount",
    "Profit": "profit", "Segment": "segment", "City": "city", "State": "state",
    "Postal Prefix": "postal_prefix", "Region": "region", "Category": "category",
    "Sub-Category": "sub_category", "Product Name": "product_name",
}


def connect(path: Path) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    # One thread makes floating-point aggregation order (and so every output) identical from run to run. The data
    # set is small, so there is no meaningful cost.
    con.execute("SET threads = 1")
    return con


def load_staging(con: duckdb.DuckDBPyConnection, masked: pd.DataFrame) -> int:
    """Create stg_orders from the masked frame (typed, snake_case). Returns the row count."""
    stg = masked[list(STG_COLUMNS)].rename(columns=STG_COLUMNS).copy()
    stg["order_date"] = pd.to_datetime(stg["order_date"]).dt.date
    stg["ship_date"] = pd.to_datetime(stg["ship_date"]).dt.date
    for col in ("order_id", "ship_mode", "customer_id", "segment", "city", "state", "postal_prefix",
                "region", "category", "sub_category", "product_name"):
        stg[col] = stg[col].astype(str)
    con.register("stg_df", stg)
    con.execute("CREATE OR REPLACE TABLE stg_orders AS SELECT * FROM stg_df")
    con.unregister("stg_df")
    return con.execute("SELECT COUNT(*) FROM stg_orders").fetchall()[0][0]


def model_files(models_dir: Path) -> list[Path]:
    """SQL models run in filename order (numeric prefixes encode dependencies)."""
    files = sorted(models_dir.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"no SQL models found in {models_dir}")
    return files


def run_models(con: duckdb.DuckDBPyConnection, models_dir: Path) -> list[dict]:
    """Execute each model; return [{model, table, rows}] for the run log."""
    results = []
    for path in model_files(models_dir):
        sql = path.read_text()
        con.execute(sql)
        table = sql.split("CREATE OR REPLACE TABLE", 1)[1].split()[0]
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchall()[0][0]
        results.append({"model": path.name, "table": table, "rows": rows})
    return results


def export_marts(con: duckdb.DuckDBPyConnection, marts_dir: Path) -> list[str]:
    """Write every mart_* table to CSV so any BI tool (Excel, Tableau, Looker Studio, Power BI) can read it."""
    marts_dir.mkdir(parents=True, exist_ok=True)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'mart_%' ORDER BY 1").fetchall()]
    for t in tables:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position", [t]).fetchall()
        # DOUBLE columns are rounded to 6 decimals so exports are clean and stable across platforms and versions.
        select = ", ".join(f'ROUND("{c}", 6) AS "{c}"' if typ == "DOUBLE" else f'"{c}"' for c, typ in cols)
        out = marts_dir / f"{t}.csv"
        con.execute(f"COPY (SELECT {select} FROM {t}) TO '{out}' (HEADER, DELIMITER ',')")
    return tables


def control_totals(con: duckdb.DuckDBPyConnection) -> dict:
    row_count, sales, profit = con.execute(
        "SELECT COUNT(*), ROUND(SUM(sales), 2), ROUND(SUM(profit), 2) FROM fact_orders").fetchall()[0]
    return {"row_count": int(row_count), "sales": float(sales), "profit": float(profit)}


def referential_integrity(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Count fact rows whose foreign key has no matching dimension row (must all be zero)."""
    checks = {
        "order_date_key": "dim_date.date_key",
        "ship_date_key": "dim_date.date_key",
        "customer_key": "dim_customer.customer_key",
        "geography_key": "dim_geography.geography_key",
        "product_key": "dim_product.product_key",
    }
    out = {}
    for fk, target in checks.items():
        table, col = target.split(".")
        out[fk] = con.execute(
            f"SELECT COUNT(*) FROM fact_orders f LEFT JOIN {table} d ON f.{fk} = d.{col} WHERE d.{col} IS NULL"
        ).fetchall()[0][0]
    return out
