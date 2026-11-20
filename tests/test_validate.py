import pandas as pd
import pytest

from superstore_pipeline import validate


def errors(report):
    return {c.name for c in report.errors}


def test_real_data_passes_with_documented_warnings(raw_df):
    report = validate.run_checks(raw_df)
    assert report.ok
    assert {c.name for c in report.warnings} == {
        "order_id_year_matches_order_date", "customer_id_uppercase", "no_duplicate_rows"}


@pytest.mark.parametrize("column,value,failing_check", [
    ("Sales", -5.0, "sales_positive"),
    ("Quantity", 0, "quantity_positive"),
    ("Discount", 1.5, "discount_in_range"),
    ("Ship Mode", "Teleport", "domain_ship_mode"),
    ("Region", "North", "domain_region"),
    ("Order ID", "BAD-ID", "order_id_format"),
])
def test_each_rule_catches_its_violation(raw_df, column, value, failing_check):
    bad = raw_df.copy()
    bad.loc[0, column] = value
    assert failing_check in errors(validate.run_checks(bad))


def test_ship_before_order_is_an_error(raw_df):
    bad = raw_df.copy()
    bad.loc[0, "Ship Date"] = bad.loc[0, "Order Date"] - pd.Timedelta(days=2)
    assert "ship_not_before_order" in errors(validate.run_checks(bad))


def test_profit_above_sales_is_an_error(raw_df):
    bad = raw_df.copy()
    bad.loc[0, "Profit"] = bad.loc[0, "Sales"] + 10
    assert "profit_not_above_sales" in errors(validate.run_checks(bad))


def test_missing_values_are_an_error(raw_df):
    bad = raw_df.copy()
    bad.loc[3, "State"] = None
    assert "no_null_values" in errors(validate.run_checks(bad))


def test_missing_column_short_circuits(raw_df):
    report = validate.run_checks(raw_df.drop(columns=["Profit"]))
    assert errors(report) == {"schema_required_columns"}


def test_duplicate_rows_warn_but_do_not_fail(raw_df):
    dup = pd.concat([raw_df, raw_df.iloc[[5]]], ignore_index=True)
    report = validate.run_checks(dup)
    assert report.ok
    assert next(c for c in report.checks if c.name == "no_duplicate_rows").failed_rows >= 1


def test_customer_id_case_collision_is_an_error(raw_df):
    bad = raw_df.copy()
    original = bad.loc[0, "Customer ID"]
    bad.loc[1, "Customer ID"] = original.lower()
    assert "customer_id_case_collisions" in errors(validate.run_checks(bad))


def test_two_segments_for_one_customer_is_an_error(raw_df):
    bad = raw_df.copy()
    cid = bad.loc[0, "Customer ID"]
    idx = bad.index[bad["Customer ID"] == cid]
    bad.loc[idx[0], "Segment"] = "Consumer"
    bad.loc[idx[-1], "Segment"] = "Corporate" if bad.loc[idx[0], "Segment"] == "Consumer" else "Consumer"
    if len(idx) > 1:
        assert "one_segment_per_customer" in errors(validate.run_checks(bad))


def test_report_serialises(raw_df):
    d = validate.run_checks(raw_df).to_dict()
    assert d["ok"] is True and d["checks_total"] == len(d["checks"]) and d["errors"] == 0


def test_reconcile_detects_mismatch():
    expected = {"row_count": 10, "sales": 100.0, "profit": 20.0, "tolerance": 0.01}
    assert validate.reconcile({"row_count": 10, "sales": 100.0, "profit": 20.0}, expected) == []
    problems = validate.reconcile({"row_count": 9, "sales": 99.0, "profit": 20.0}, expected)
    assert len(problems) == 2
