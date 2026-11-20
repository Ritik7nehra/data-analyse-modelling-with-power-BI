"""The metric layer: every SQL definition is executed and compared with an independent pandas calculation."""
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = yaml.safe_load((ROOT / "bi" / "metrics.yml").read_text())


def pandas_truth(df):
    """Independent implementation of each metric on the raw frame."""
    return {
        "revenue": df["Sales"].sum(),
        "profit": df["Profit"].sum(),
        "profit_margin": df["Profit"].sum() / df["Sales"].sum(),
        "orders": df["Order ID"].nunique(),
        "customers": df["Customer ID"].nunique(),
        "avg_order_value": df["Sales"].sum() / df["Order ID"].nunique(),
        "units": df["Quantity"].sum(),
        "avg_discount": df["Discount"].mean(),
        "loss_line_share": (df["Profit"] < 0).mean(),
        "avg_ship_days": (df["Ship Date"] - df["Order Date"]).dt.days.mean(),
    }


def test_every_metric_has_an_expression_for_every_tool():
    for m in SPEC["metrics"]:
        for key in ("name", "label", "format", "description", "sql", "dax", "tableau", "looker_studio"):
            assert m.get(key), f"{m.get('name')} is missing {key}"


@pytest.mark.parametrize("metric", SPEC["metrics"], ids=lambda m: m["name"])
def test_sql_metric_matches_pandas(built, raw_df, metric):
    _, _, con = built
    value = con.execute(f"SELECT {metric['sql']} FROM {SPEC['source_table']}").fetchall()[0][0]
    assert value == pytest.approx(pandas_truth(raw_df)[metric["name"]], rel=1e-9)


def test_layer_covers_exactly_the_independently_verified_metrics(raw_df):
    assert {m["name"] for m in SPEC["metrics"]} == set(pandas_truth(raw_df))


def test_dimensions_exist_in_the_flat_table(built):
    _, _, con = built
    cols = {r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{SPEC['source_table']}'").fetchall()}
    for d in SPEC["dimensions"]:
        assert d["name"] in cols


def test_flat_mart_ties_to_fact(built):
    _, _, con = built
    n, sales, profit = con.execute("SELECT COUNT(*), ROUND(SUM(sales), 2), ROUND(SUM(profit), 2) FROM mart_sales_flat").fetchall()[0]
    assert (n, sales, profit) == (9994, 2297200.86, 286397.02)


def test_generated_reference_is_up_to_date():
    spec = importlib.util.spec_from_file_location("gen", ROOT / "bi" / "generate_bi_snippets.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    committed = (ROOT / "bi" / "generated" / "metrics_reference.md").read_text()
    assert committed == gen.build(), "run `python bi/generate_bi_snippets.py` to refresh the metric reference"
