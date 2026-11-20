"""Regression tests for the committed deliverables: Excel workbook, native PivotTables and the executive deck.

They read the committed files (the Excel values were stored by a LibreOffice recalculation) and compare them with the
pipeline marts, so a stale or wrong deliverable fails the build. Tests skip when an optional library is missing.
"""
from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "reports" / "marts"
WORKBOOK = ROOT / "excel" / "Superstore_Sales_Analysis.xlsx"
PIVOTS = ROOT / "excel" / "Superstore_PivotTables.xlsx"
DECK = ROOT / "reports" / "Superstore_Executive_Deck.pptx"


@pytest.fixture(scope="module")
def flat() -> pd.DataFrame:
    return pd.read_csv(MARTS / "mart_sales_flat.csv")


@pytest.fixture(scope="module")
def workbook():
    openpyxl = pytest.importorskip("openpyxl")
    if not WORKBOOK.exists():
        pytest.skip("workbook not built")
    return openpyxl.load_workbook(WORKBOOK, data_only=True)


def test_excel_kpis_match_marts(workbook, flat):
    d = workbook["Dashboard"]
    assert d["B5"].value == pytest.approx(flat["sales"].sum(), abs=0.01)
    assert d["D5"].value == pytest.approx(flat["profit"].sum(), abs=0.01)
    assert d["F5"].value == pytest.approx(flat["profit"].sum() / flat["sales"].sum(), abs=1e-9)
    assert d["H5"].value == flat["order_id"].nunique()
    assert d["J5"].value == flat["customer_id"].nunique()


def test_excel_lookups_match_marts(workbook, flat):
    lk = workbook["Lookups"]
    order = flat[flat["order_id"] == lk["C5"].value]
    assert len(order) >= 3, "default lookup order should have several lines"
    assert lk["C10"].value == len(order)
    assert lk["C11"].value == pytest.approx(order["sales"].sum(), abs=0.01)
    assert lk["C12"].value == pytest.approx(order["profit"].sum(), abs=0.01)
    assert lk["C8"].value == f"{order['region'].iloc[0]} / {order['state'].iloc[0]}"
    sub, year = lk["C23"].value, lk["C24"].value
    expected = flat[(flat["sub_category"] == sub) & (flat["year"] == year)]["profit"].sum()
    assert lk["C25"].value == pytest.approx(expected, abs=0.01)
    band = lk["C34"].value
    in_band = flat[flat["discount_band"] == band]
    assert lk["C35"].value == pytest.approx(in_band["profit"].sum() / in_band["sales"].sum(), abs=1e-9)


def test_excel_pivot_summaries_reconcile(workbook, flat):
    ps = workbook["Pivot_Sales"]
    flags = [c.value for row in ps.iter_rows() for c in row if c.value in ("OK", "CHECK")]
    assert flags and set(flags) == {"OK"}
    pm = workbook["Pivot_Month"]
    years = sorted(flat["year"].unique())
    for month in range(1, 13):
        for j, year in enumerate(years):
            expected = flat[(flat["month_number"] == month) & (flat["year"] == year)]["sales"].sum()
            assert pm.cell(4 + month, 3 + j).value == pytest.approx(expected, abs=0.01)


def test_excel_has_no_error_values(workbook):
    for name in ("README", "Dashboard", "Lookups", "Pivot_Sales", "Pivot_SubCat", "Pivot_Month", "Pivot_Discount", "Pivot_RFM"):
        for row in workbook[name].iter_rows():
            for c in row:
                assert not (isinstance(c.value, str) and c.value.startswith("#")), f"{name}!{c.coordinate} = {c.value}"


def test_native_pivot_tables_present_and_correct(flat):
    openpyxl = pytest.importorskip("openpyxl")
    if not PIVOTS.exists():
        pytest.skip("pivot workbook not built")
    with zipfile.ZipFile(PIVOTS) as z:
        names = z.namelist()
    assert sum(n.startswith("xl/pivotTables/pivotTable") and n.endswith(".xml") for n in names) == 4
    assert any(n.startswith("xl/pivotCache/pivotCacheDefinition") for n in names)
    ws = openpyxl.load_workbook(PIVOTS, data_only=True)["Pivots"]
    # category x year pivot grand total sits on the "Total Result" row, last column
    totals = [c.value for row in ws.iter_rows(min_row=1, max_row=12, max_col=6) for c in row if c.value == "Total Result"]
    assert totals, "grand-total labels missing"
    grand = [c.value for row in ws.iter_rows(min_row=4, max_row=12, max_col=6) for c in row
             if isinstance(c.value, float) and abs(c.value - flat["sales"].sum()) < 0.01]
    assert grand, "pivot grand total does not equal total sales"


def _load_deck_data_module():
    spec = importlib.util.spec_from_file_location("build_deck_data", ROOT / "reports" / "deck" / "build_deck_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_deck_data_ties_to_marts(flat):
    mod = _load_deck_data_module()
    mod.main()
    data = json.loads(mod.OUT.read_text())
    assert data["kpi"]["sales"] == pytest.approx(flat["sales"].sum(), abs=0.01)
    assert data["kpi"]["profit"] == pytest.approx(flat["profit"].sum(), abs=0.01)
    lines = flat[flat["discount"] > 0.2]
    assert data["deep_lines"] == len(lines)
    assert data["deep_baseline_profit"] == pytest.approx(lines["profit"].sum(), abs=0.01)
    losses = flat[flat["profit"] < 0]["profit"].sum()
    assert data["deep_loss_share"] == pytest.approx(lines[lines["profit"] < 0]["profit"].sum() / losses, abs=1e-6)  # marts are rounded to 6 dp
    assert data["valuation"]["ev"]["Bear"] < data["valuation"]["ev"]["Base"] < data["valuation"]["ev"]["Bull"]
    assert data["rfm_total_customers"] == flat["customer_id"].nunique()


def test_deck_structure():
    pptx = pytest.importorskip("pptx")
    if not DECK.exists():
        pytest.skip("deck not built")
    from pptx.enum.shapes import PP_PLACEHOLDER

    prs = pptx.Presentation(DECK)
    assert len(prs.slides) == 10
    for i, slide in enumerate(prs.slides, start=1):
        assert slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip(), f"slide {i} has no speaker notes"
        titles = [ph for ph in slide.placeholders if ph.placeholder_format.type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE)]
        assert titles and titles[0].text_frame.text.strip(), f"slide {i} has no title placeholder"   # pptxgenjs uses idx=100
    charts = sum(1 for s in prs.slides for sh in s.shapes if sh.has_chart)
    assert charts >= 5, "charts should be native chart objects, not pictures"
