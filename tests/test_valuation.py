"""Tests for the illustrative DCF module, and a cross-check against the committed Excel model."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from superstore_pipeline import valuation as v

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "excel" / "finance" / "Superstore_DCF_Valuation.xlsx"


def test_flat_perpetuity_closed_form():
    """Five years of 100 at 10% with zero growth is exactly a 100 / 0.10 = 1000 perpetuity."""
    pv, tv, pv_tv, ev = v.enterprise_value([100.0] * 5, 0.10, 0.0)
    assert ev == pytest.approx(1000.0)
    assert tv == pytest.approx(1000.0)
    assert pv + pv_tv == pytest.approx(ev)


def test_rate_must_exceed_growth():
    with pytest.raises(ValueError):
        v.enterprise_value([100.0], 0.03, 0.03)


def test_wacc_formula():
    a = v.Assumptions()
    expected = 0.8 * (0.0425 + 1.10 * 0.05) + 0.2 * 0.06 * 0.75
    assert v.wacc(a) == pytest.approx(expected)
    assert v.wacc(a) == pytest.approx(0.087)


def test_scenarios_ordered_and_higher_rate_lowers_value():
    base_rev = 733_215.26
    ev = {name: v.value(base_rev, s).enterprise_value for name, s in v.SCENARIOS.items()}
    assert ev["Bear"] < ev["Base"] < ev["Bull"]
    low = v.value(base_rev, v.SCENARIOS["Base"], rate=0.08).enterprise_value
    high = v.value(base_rev, v.SCENARIOS["Base"], rate=0.10).enterprise_value
    assert high < low


def test_cash_flow_identity():
    flows = v.project(733_215.26, v.SCENARIOS["Base"], v.Assumptions())
    for f in flows:
        assert f.fcf == pytest.approx(f.ebit + f.taxes + f.da + f.capex + f.d_nwc)
        assert f.nopat == pytest.approx(f.ebit * 0.75)
    assert flows[0].revenue == pytest.approx(733_215.26 * 1.12)


def test_sensitivity_centre_equals_base_case_and_is_monotonic():
    base_rev = 733_215.26
    waccs, growths, grid = v.sensitivity(base_rev, v.SCENARIOS["Base"])
    base = v.value(base_rev, v.SCENARIOS["Base"]).enterprise_value
    assert grid[2][2] == pytest.approx(base)
    for i in range(len(waccs) - 1):               # higher WACC -> lower value, for every growth column
        assert all(grid[i][j] > grid[i + 1][j] for j in range(len(growths)))
    for j in range(len(growths) - 1):             # higher terminal growth -> higher value
        assert all(grid[i][j] < grid[i][j + 1] for i in range(len(waccs)))


def test_terminal_value_share_and_multiple_are_plausible():
    res = v.value(733_215.26, v.SCENARIOS["Base"])
    assert 0.5 < res.tv_share < 0.95
    assert 2 < res.implied_exit_multiple < 25


def _named(wb, name):
    ref = wb.defined_names[name].attr_text
    sheet, cell = ref.split("!")
    return wb[sheet.strip("'")][cell.replace("$", "")].value


@pytest.mark.skipif(not XLSX.exists(), reason="Excel DCF model not built")
def test_excel_model_matches_python():
    """The recalculated Excel model (cached values) must agree with this module for every scenario."""
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    flat = pd.read_csv(ROOT / "reports" / "marts" / "mart_sales_flat.csv")
    base_rev = flat.loc[flat["year"] == 2017, "sales"].sum()
    assert _named(wb, "o_EV") is not None, "workbook has no cached values - run recalc.py"
    for key, scen in (("Base", "Base"), ("Bull", "Bull"), ("Bear", "Bear")):
        expected = v.value(base_rev, v.SCENARIOS[scen])
        assert _named(wb, f"o_EV_{key}") == pytest.approx(expected.enterprise_value, rel=1e-9)
    selected = wb["Assumptions"]["B4"].value
    names = {1: "Base", 2: "Bull", 3: "Bear"}
    expected = v.value(base_rev, v.SCENARIOS[names[selected]])
    assert _named(wb, "o_EV") == pytest.approx(expected.enterprise_value, rel=1e-9)
    assert _named(wb, "o_WACC") == pytest.approx(expected.wacc, rel=1e-12)
    assert _named(wb, "o_TVShare") == pytest.approx(expected.tv_share, rel=1e-9)
    assert _named(wb, "o_ExitMultiple") == pytest.approx(expected.implied_exit_multiple, rel=1e-9)
