import re

import pytest


def scalar(con, sql):
    return con.execute(sql).fetchall()[0][0]


def test_monthly_mart_is_complete_and_ties_to_fact(built):
    _, _, con = built
    assert scalar(con, "SELECT COUNT(*) FROM mart_monthly_sales") == 48            # required by the LAG(…, 12) logic
    assert scalar(con, "SELECT SUM(sales) FROM mart_monthly_sales") == pytest.approx(scalar(con, "SELECT SUM(sales) FROM fact_orders"))


def test_ytd_in_december_equals_the_annual_total(built):
    _, _, con = built
    rows = con.execute(
        "SELECT m.year, m.ytd_sales, (SELECT SUM(sales) FROM mart_monthly_sales x WHERE x.year = m.year) "
        "FROM mart_monthly_sales m WHERE month_number = 12").fetchall()
    assert len(rows) == 4
    for _, ytd, annual in rows:
        assert ytd == pytest.approx(annual)


def test_yoy_and_mom_are_computed_correctly(built):
    _, _, con = built
    jan14, jan15, yoy15, dec14, mom15 = con.execute(
        "SELECT (SELECT sales FROM mart_monthly_sales WHERE year_month='2014-01'),"
        "       (SELECT sales FROM mart_monthly_sales WHERE year_month='2015-01'),"
        "       (SELECT yoy_pct FROM mart_monthly_sales WHERE year_month='2015-01'),"
        "       (SELECT sales FROM mart_monthly_sales WHERE year_month='2014-12'),"
        "       (SELECT mom_pct FROM mart_monthly_sales WHERE year_month='2015-01')").fetchall()[0]
    assert yoy15 == pytest.approx(jan15 / jan14 - 1)
    assert mom15 == pytest.approx(jan15 / dec14 - 1)
    assert scalar(con, "SELECT COUNT(*) FROM mart_monthly_sales WHERE year = 2014 AND yoy_pct IS NOT NULL") == 0


def test_kpi_totals_tie_to_fact(built):
    _, _, con = built
    s, p, orders, customers = con.execute(
        "SELECT sales, profit, orders, customers FROM mart_executive_kpis WHERE period = 'All years'").fetchall()[0]
    assert (round(s, 2), round(p, 2), orders, customers) == (2297200.86, 286397.02, 5009, 793)
    assert scalar(con, "SELECT SUM(sales) FROM mart_executive_kpis WHERE period <> 'All years'") == pytest.approx(s)


def test_discount_bands_partition_all_lines_and_losses(built):
    _, _, con = built
    assert scalar(con, "SELECT SUM(order_lines) FROM mart_discount_impact") == 9994
    assert scalar(con, "SELECT SUM(share_of_all_losses) FROM mart_discount_impact") == pytest.approx(1.0)
    margins = [r[0] for r in con.execute("SELECT margin FROM mart_discount_impact ORDER BY discount_band").fetchall()]
    assert margins == sorted(margins, reverse=True), "deeper discounts must not improve margin in this dataset"


def test_product_and_regional_marts_tie_to_fact(built):
    _, _, con = built
    total = scalar(con, "SELECT SUM(sales) FROM fact_orders")
    assert scalar(con, "SELECT SUM(sales) FROM mart_product_profitability") == pytest.approx(total)
    assert scalar(con, "SELECT SUM(sales) FROM mart_regional_performance") == pytest.approx(total)
    assert scalar(con, "SELECT SUM(sales_share) FROM mart_product_profitability") == pytest.approx(1.0)
    assert scalar(con, "SELECT COUNT(*) FROM mart_product_profitability") == 17


def test_what_if_extremes_are_consistent(built):
    _, _, con = built
    drop_all = con.execute(
        "SELECT baseline_profit_affected, profit_delta FROM mart_discount_what_if "
        "WHERE volume_retention = 0 AND discount_cap = 0.2").fetchall()[0]
    assert drop_all[1] == pytest.approx(-drop_all[0])                  # dropping the lines removes their (negative) profit
    deltas = [r[0] for r in con.execute(
        "SELECT profit_delta FROM mart_discount_what_if WHERE discount_cap = 0.2 ORDER BY volume_retention DESC").fetchall()]
    assert deltas == sorted(deltas, reverse=True)                      # more volume loss -> smaller gain
    affected = scalar(con, "SELECT affected_lines FROM mart_discount_what_if WHERE discount_cap = 0.2 LIMIT 1")
    assert affected == scalar(con, "SELECT COUNT(*) FROM fact_orders WHERE discount > 0.2")


def test_rfm_covers_every_customer_with_valid_scores(built):
    _, _, con = built
    assert scalar(con, "SELECT COUNT(*) FROM mart_customer_rfm") == 793
    assert scalar(con, "SELECT SUM(monetary) FROM mart_customer_rfm") == pytest.approx(2297200.86)
    for col in ("r_score", "f_score", "m_score"):
        lo, hi = con.execute(f"SELECT MIN({col}), MAX({col}) FROM mart_customer_rfm").fetchall()[0]
        assert (lo, hi) == (1, 5)
    assert scalar(con, "SELECT COUNT(*) FROM mart_customer_rfm WHERE rfm_segment IS NULL") == 0


def test_marts_never_expose_raw_customer_ids(built):
    cfg, _, _ = built
    raw_id = re.compile(r"\b[A-Za-z]{2}-\d{5}\b")
    for csv in cfg.marts_dir.glob("*.csv"):
        assert not raw_id.search(csv.read_text()), f"raw-looking customer id found in {csv.name}"
