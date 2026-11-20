"""Static checks for SQL that cannot be executed in CI (BigQuery) and a parse check for the DuckDB models."""
import importlib.util
from pathlib import Path

import pytest
import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
BQ_DIR = ROOT / "warehouse" / "bigquery"
MODELS = sorted((ROOT / "warehouse" / "duckdb" / "models").glob("*.sql"))


def render(path: Path) -> str:
    return path.read_text().replace("{{project}}", "my-proj").replace("{{dataset}}", "ds")


def load_loader():
    spec = importlib.util.spec_from_file_location("load_to_bigquery", BQ_DIR / "load_to_bigquery.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("path", MODELS, ids=lambda p: p.name)
def test_duckdb_models_parse(path):
    statements = [s for s in sqlglot.parse(path.read_text(), read="duckdb") if s]
    assert len(statements) == 1 and isinstance(statements[0], exp.Create)


@pytest.mark.parametrize("name", ["00_schema.sql", "10_views.sql"])
def test_bigquery_sql_parses_in_bigquery_dialect(name):
    sql = render(BQ_DIR / name)
    assert "{{" not in sql
    statements = [s for s in sqlglot.parse(sql, read="bigquery") if s]
    assert statements and all(isinstance(s, exp.Create) for s in statements)


def ddl_columns() -> dict[str, list[str]]:
    out = {}
    for stmt in sqlglot.parse(render(BQ_DIR / "00_schema.sql"), read="bigquery"):
        table = stmt.this.this.name
        out[table] = [c.name for c in stmt.this.expressions if isinstance(c, exp.ColumnDef)]
    return out


def test_fact_table_is_partitioned_and_clustered():
    sql = render(BQ_DIR / "00_schema.sql")
    fact = sql[sql.index("fact_orders` ("):]
    assert "PARTITION BY order_date" in fact and "CLUSTER BY" in fact


def test_views_reference_only_tables_defined_in_the_ddl():
    defined = set(ddl_columns())
    for stmt in sqlglot.parse(render(BQ_DIR / "10_views.sql"), read="bigquery"):
        ctes = {c.alias for c in stmt.find_all(exp.CTE)}
        view = stmt.this.this.name
        for t in stmt.find_all(exp.Table):
            if t.name == view or t.name in ctes:
                continue
            assert t.name in defined, f"view {view} references unknown table {t.name}"


def test_loader_frames_match_the_bigquery_ddl_exactly(built):
    cfg, _, con = built
    frames = load_loader().frames(con)
    cols = ddl_columns()
    assert set(frames) == set(cols)
    for table, expected in cols.items():
        assert list(frames[table].columns) == expected, f"{table}: loader columns differ from DDL"


def test_loader_dry_run_needs_no_credentials(built, capsys):
    cfg, _, _ = built
    rc = load_loader().main(["--project", "p", "--dataset", "d", "--dry-run", "--duckdb", str(cfg.duckdb_path)])
    out = capsys.readouterr().out
    assert rc == 0 and "fact_orders" in out and "9,994 rows" in out


def test_loader_reports_missing_warehouse(tmp_path, capsys):
    rc = load_loader().main(["--project", "p", "--dry-run", "--duckdb", str(tmp_path / "missing.duckdb")])
    assert rc == 2
