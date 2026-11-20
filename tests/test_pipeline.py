import json
from dataclasses import replace

import duckdb
import pandas as pd

from superstore_pipeline.runner import STEPS, run_pipeline

EXPECTED_MARTS = {
    "mart_customer_rfm", "mart_discount_impact", "mart_discount_what_if", "mart_executive_kpis",
    "mart_monthly_sales", "mart_product_profitability", "mart_regional_performance", "mart_sales_flat",
}


def test_pipeline_succeeds_end_to_end(built):
    cfg, summary, con = built
    assert [s["step"] for s in summary["steps"]] == [s.name for s in STEPS]
    assert all(s["status"] == "success" for s in summary["steps"])


def test_control_totals_reconcile_to_source(built):
    cfg, summary, con = built
    rec = next(s for s in summary["steps"] if s["step"] == "reconcile")["detail"]
    assert rec["control_totals"] == {"row_count": 9994, "sales": 2297200.86, "profit": 286397.02}
    assert sum(rec["orphan_foreign_keys"].values()) == 0


def test_fact_grain_and_dimension_keys_are_unique(built):
    _, _, con = built
    assert con.execute("SELECT COUNT(*) = COUNT(DISTINCT order_line_id) FROM fact_orders").fetchall()[0][0]
    for table, key in [("dim_customer", "customer_key"), ("dim_product", "product_key"),
                       ("dim_geography", "geography_key"), ("dim_date", "date_key")]:
        n, d = con.execute(f"SELECT COUNT(*), COUNT(DISTINCT {key}) FROM {table}").fetchall()[0]
        assert n == d, f"{table}.{key} is not unique"


def test_dim_date_covers_whole_years_with_no_gaps(built):
    _, _, con = built
    first, last, n = con.execute("SELECT MIN(full_date), MAX(full_date), COUNT(*) FROM dim_date").fetchall()[0]
    assert (first.month, first.day) == (1, 1) and (last.month, last.day) == (12, 31)
    assert n == (last - first).days + 1


def test_warehouse_holds_no_raw_customer_ids(built, raw_df):
    _, _, con = built
    ids = set(con.execute("SELECT customer_id FROM dim_customer").df()["customer_id"])
    assert ids and not ids & set(raw_df["Customer ID"])
    assert all(i.startswith("C-") for i in ids)
    cols = {r[0] for r in con.execute("SELECT column_name FROM information_schema.columns").fetchall()}
    assert "postal_code" not in cols


def test_marts_are_exported_as_csv(built):
    cfg, _, _ = built
    files = {p.stem for p in cfg.marts_dir.glob("*.csv")}
    assert files == EXPECTED_MARTS
    for p in cfg.marts_dir.glob("*.csv"):
        assert len(pd.read_csv(p)) > 0


def test_run_log_is_written_and_persisted(built):
    cfg, summary, con = built
    lines = [json.loads(x) for x in cfg.run_log.read_text().splitlines()]
    assert {x["run_id"] for x in lines} == {summary["run_id"]}
    assert {x["step"] for x in lines} == {s.name for s in STEPS}
    table = con.execute("SELECT step, status FROM pipeline_runs").df()
    assert set(table["status"]) == {"success"} and len(table) == len(STEPS)


def test_data_quality_results_are_stored(built):
    cfg, _, con = built
    assert con.execute("SELECT COUNT(*) FROM dq_results").fetchall()[0][0] == 21
    assert json.loads(cfg.dq_report.read_text())["ok"] is True


def test_pipeline_is_idempotent(tmp_cfg):
    a = run_pipeline(tmp_cfg)
    b = run_pipeline(tmp_cfg)
    assert a["status"] == b["status"] == "success" and a["run_id"] != b["run_id"]
    with duckdb.connect(str(tmp_cfg.duckdb_path), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM fact_orders").fetchall()[0][0] == 9994
    assert len(tmp_cfg.run_log.read_text().splitlines()) == 2 * len(STEPS)       # log is append-only


def test_bad_data_stops_the_pipeline_and_skips_downstream(tmp_cfg, tmp_path, raw_df):
    bad = raw_df.copy()
    bad.loc[0, "Sales"] = -1.0
    bad_csv = tmp_path / "bad.csv"
    bad.to_csv(bad_csv, index=False)
    summary = run_pipeline(replace(tmp_cfg, orders_csv=bad_csv))
    status = {s["step"]: s["status"] for s in summary["steps"]}
    assert summary["status"] == "failed"
    assert status["extract"] == "success" and status["validate"] == "failed"
    assert all(status[s] == "skipped" for s in ("mask", "load_staging", "build_models", "reconcile", "publish"))
    assert not tmp_cfg.duckdb_path.exists(), "nothing may be loaded when the quality gate fails"
    assert "sales_positive" in next(s for s in summary["steps"] if s["step"] == "validate")["detail"]["error"]


def test_reconciliation_failure_blocks_publishing(tmp_cfg):
    cfg = replace(tmp_cfg, control_totals={**tmp_cfg.control_totals, "sales": 1.0})
    summary = run_pipeline(cfg)
    status = {s["step"]: s["status"] for s in summary["steps"]}
    assert status["reconcile"] == "failed" and status["publish"] == "skipped"
    assert not list(cfg.marts_dir.glob("*.csv")) if cfg.marts_dir.exists() else True


def test_missing_source_file_fails_cleanly(tmp_cfg, tmp_path):
    summary = run_pipeline(replace(tmp_cfg, orders_csv=tmp_path / "nope.csv"))
    first = summary["steps"][0]
    assert first["status"] == "failed" and first["detail"]["error_type"] == "FileNotFoundError"


def test_marts_are_byte_reproducible(base_cfg, tmp_path):
    """Two independent runs must write identical mart files (no floating-point order noise, no timestamps)."""
    import hashlib
    from dataclasses import replace

    digests = []
    for i in range(2):
        d = tmp_path / f"run{i}"
        cfg = replace(base_cfg, duckdb_path=d / "wh.duckdb", marts_dir=d / "marts", run_log=d / "runs.jsonl",
                      dq_report=d / "dq.json")
        assert run_pipeline(cfg)["status"] == "success"
        digests.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(cfg.marts_dir.glob("*.csv"))})
    assert digests[0] and digests[0] == digests[1]
