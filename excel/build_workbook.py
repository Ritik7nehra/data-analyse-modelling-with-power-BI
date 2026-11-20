"""Build excel/Superstore_Sales_Analysis.xlsx from the pipeline's masked marts.

    python -m superstore_pipeline run         # produce reports/marts/*.csv
    python excel/build_workbook.py            # writes excel/Superstore_Sales_Analysis.xlsx

Every number on the analysis sheets is a live formula over the Data / RFM_Data sheets (SUMIFS, COUNTIFS,
INDEX/MATCH, VLOOKUP), so the workbook recalculates when the data changes. Functions are limited to those
supported by both Excel and LibreOffice (no XLOOKUP / dynamic arrays) so results can be verified headlessly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "reports" / "marts"
OUT = Path(__file__).resolve().parent / "Superstore_Sales_Analysis.xlsx"

# ----------------------------------------------------------------------------------------------- styles
FONT = "Arial"
F_BASE = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_TITLE = Font(name=FONT, size=16, bold=True, color="1F3864")
F_SUB = Font(name=FONT, size=10, italic=True, color="595959")
F_HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_INPUT = Font(name=FONT, size=10, color="0000FF", bold=True)         # hard-coded input (blue)
F_LINK = Font(name=FONT, size=10, color="008000")                     # link to another sheet (green)
F_KPI = Font(name=FONT, size=18, bold=True, color="1F3864")
FILL_HEAD = PatternFill("solid", fgColor="1F3864")
FILL_INPUT = PatternFill("solid", fgColor="FFFF00")
FILL_TOTAL = PatternFill("solid", fgColor="D9E1F2")
FILL_KPI = PatternFill("solid", fgColor="F2F2F2")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
TOP = Border(top=Side(style="thin", color="000000"))

USD = '$#,##0;($#,##0);"-"'
USD2 = '$#,##0.00;($#,##0.00);"-"'
PCT = '0.0%;(0.0%);"-"'
INT = '#,##0;(#,##0);"-"'
DATE = "yyyy-mm-dd"


def style_range(ws, ref, font=None, fill=None, fmt=None, border=None, align=None):
    for row in ws[ref]:
        for c in row:
            if font:
                c.font = font
            if fill:
                c.fill = fill
            if fmt:
                c.number_format = fmt
            if border:
                c.border = border
            if align:
                c.alignment = align


def header_row(ws, row, labels, start_col=1):
    for i, text in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=text)
        c.font, c.fill, c.border = F_HEAD, FILL_HEAD, BOX
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def title(ws, text, sub=None):
    ws["A1"], ws["A1"].font = text, F_TITLE
    if sub:
        ws["A2"], ws["A2"].font = sub, F_SUB
    ws.sheet_view.showGridLines = False


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def base_font(ws):
    """Apply the base font to every cell that has no explicit styling yet."""
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None and c.font.name != FONT:
                c.font = F_BASE


# ------------------------------------------------------------------------------------------------- data
flat = pd.read_csv(MARTS / "mart_sales_flat.csv", parse_dates=["order_date", "ship_date"])
rfm = pd.read_csv(MARTS / "mart_customer_rfm.csv", parse_dates=["last_order_date"])
flat = flat.sort_values(["order_id", "order_line_id"]).reset_index(drop=True)   # sorted so the first-line flag is O(n)
N = len(flat)
LAST = N + 1
YEARS = sorted(flat["year"].unique().tolist())
CATEGORIES = sorted(flat["category"].unique())
REGIONS = sorted(flat["region"].unique())
BANDS = sorted(flat["discount_band"].unique())
subcat_rank = (flat.groupby(["category", "sub_category"])["profit"].sum().reset_index()
               .sort_values("profit", ascending=False))                # row order only; values stay formulas
SUBCATS = subcat_rank["sub_category"].tolist()
SUB_TO_CAT = dict(zip(subcat_rank["sub_category"], subcat_rank["category"], strict=True))
RFM_SEGMENTS = ["Champions", "Loyal", "New / Promising", "Needs Attention", "At Risk", "Lost / Hibernating"]

# name, csv column, defined name, number format, width
DATA_COLS = [
    ("Order Line ID", "order_line_id", "d_OrderLineID", "0", 12),
    ("Order ID", "order_id", "d_OrderID", None, 16),
    ("Order Date", "order_date", "d_OrderDate", DATE, 12),
    ("Ship Date", "ship_date", "d_ShipDate", DATE, 12),
    ("Year", "year", "d_Year", "0", 7),
    ("Quarter", "quarter", "d_Quarter", "0", 8),
    ("Month #", "month_number", "d_MonthNum", "0", 9),
    ("Month", "month_name", "d_Month", None, 8),
    ("Year-Month", "year_month", "d_YearMonth", None, 11),
    ("Ship Mode", "ship_mode", "d_ShipMode", None, 15),
    ("Customer (masked)", "customer_id", "d_Customer", None, 17),
    ("Segment", "segment", "d_Segment", None, 12),
    ("Region", "region", "d_Region", None, 9),
    ("State", "state", "d_State", None, 16),
    ("City", "city", "d_City", None, 16),
    ("Postal Prefix", "postal_prefix", "d_PostalPrefix", None, 9),
    ("Category", "category", "d_Category", None, 15),
    ("Sub-Category", "sub_category", "d_SubCategory", None, 13),
    ("Product", "product_name", "d_Product", None, 36),
    ("Sales", "sales", "d_Sales", USD2, 11),
    ("Quantity", "quantity", "d_Quantity", "0", 9),
    ("Discount", "discount", "d_Discount", "0%", 9),
    ("Discount Band", "discount_band", "d_DiscountBand", None, 15),
    ("Profit", "profit", "d_Profit", USD2, 11),
    ("Cost", "cost", "d_Cost", USD2, 11),
    ("Gross Sales", "gross_sales", "d_GrossSales", USD2, 12),
    ("Ship Days", "ship_days", "d_ShipDays", "0", 9),
    ("Loss-making Line", "is_loss_making", "d_IsLoss", None, 11),
]
COL_OF = {name: get_column_letter(i + 1) for i, (_, _, name, _, _) in enumerate(DATA_COLS)}
FLAG_COL = get_column_letter(len(DATA_COLS) + 1)

wb = Workbook()

# --------------------------------------------------------------------------------------------- Data sheet
ws_data = wb.active
ws_data.title = "Data"
header_row(ws_data, 1, [c[0] for c in DATA_COLS] + ["First Line of Order"])
for r, rec in enumerate(flat.itertuples(index=False), start=2):
    for ci, (_, col, _, fmt, _) in enumerate(DATA_COLS, start=1):
        v = getattr(rec, col)
        if isinstance(v, pd.Timestamp):
            v = v.to_pydatetime()
        elif hasattr(v, "item"):
            v = v.item()
        cell = ws_data.cell(row=r, column=ci, value=v)
        cell.font = F_BASE
        if fmt:
            cell.number_format = fmt
    f = ws_data.cell(row=r, column=len(DATA_COLS) + 1, value=f"=IF(B{r}<>B{r - 1},1,0)")   # 1 on each order's first line
    f.font = F_BASE
for i, (_, _, _, _, w) in enumerate(DATA_COLS, start=1):
    ws_data.column_dimensions[get_column_letter(i)].width = w
ws_data.column_dimensions[FLAG_COL].width = 12
ws_data.freeze_panes = "C2"
tab = Table(displayName="tblSales", ref=f"A1:{FLAG_COL}{LAST}")
tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
ws_data.add_table(tab)

for _, _, name, _, _ in DATA_COLS:
    wb.defined_names[name] = DefinedName(name, attr_text=f"Data!${COL_OF[name]}$2:${COL_OF[name]}${LAST}")
wb.defined_names["d_OrderFlag"] = DefinedName("d_OrderFlag", attr_text=f"Data!${FLAG_COL}$2:${FLAG_COL}${LAST}")

# ---------------------------------------------------------------------------------------- RFM_Data sheet
ws_rfm = wb.create_sheet("RFM_Data")
rfm_cols = ["customer_id", "segment", "last_order_date", "frequency", "monetary", "profit", "recency_days",
            "r_score", "f_score", "m_score", "rfm_segment"]
rfm_heads = ["Customer (masked)", "Segment", "Last Order", "Orders", "Sales", "Profit", "Recency (days)",
             "R", "F", "M", "RFM Segment"]
rfm_fmt = [None, None, DATE, "0", USD2, USD2, "0", "0", "0", "0", None]
header_row(ws_rfm, 1, rfm_heads)
for r, rec in enumerate(rfm[rfm_cols].itertuples(index=False), start=2):
    for ci, v in enumerate(rec, start=1):
        if isinstance(v, pd.Timestamp):
            v = v.to_pydatetime()
        elif hasattr(v, "item"):
            v = v.item()
        c = ws_rfm.cell(row=r, column=ci, value=v)
        c.font = F_BASE
        if rfm_fmt[ci - 1]:
            c.number_format = rfm_fmt[ci - 1]
RFM_LAST = len(rfm) + 1
widths(ws_rfm, {"A": 18, "B": 13, "C": 12, "D": 9, "E": 12, "F": 12, "G": 14, "H": 5, "I": 5, "J": 5, "K": 20})
ws_rfm.freeze_panes = "B2"
ws_rfm.auto_filter.ref = f"A1:K{RFM_LAST}"
wb.defined_names["r_Segment"] = DefinedName("r_Segment", attr_text=f"RFM_Data!$K$2:$K${RFM_LAST}")
wb.defined_names["r_Sales"] = DefinedName("r_Sales", attr_text=f"RFM_Data!$E$2:$E${RFM_LAST}")
wb.defined_names["r_Profit"] = DefinedName("r_Profit", attr_text=f"RFM_Data!$F$2:$F${RFM_LAST}")


# ----------------------------------------------------------------------------- pivot-style matrix helper
def matrix(ws, top, heading, row_label, items, row_name, value_name, fmt, *, col_name="d_Year", col_items=YEARS,
           label_col=1, extra_total=True):
    """SUMIFS matrix. Returns dict with the cell coordinates of the block."""
    ws.cell(row=top, column=label_col, value=heading).font = F_BOLD
    hr = top + 1
    header_row(ws, hr, [row_label] + list(col_items) + (["Total"] if extra_total else []), start_col=label_col)
    first = hr + 1
    for i, item in enumerate(items):
        r = first + i
        ws.cell(row=r, column=label_col, value=item).font = F_BASE
        for j in range(len(col_items)):
            col = get_column_letter(label_col + 1 + j)
            lab = f"${get_column_letter(label_col)}{r}"
            c = ws[f"{col}{r}"]
            c.value = f"=SUMIFS({value_name},{row_name},{lab},{col_name},{col}${hr})"
            c.number_format, c.font = fmt, F_BASE
        if extra_total:
            tc = get_column_letter(label_col + 1 + len(col_items))
            c = ws[f"{tc}{r}"]
            c.value = f"=SUM({get_column_letter(label_col + 1)}{r}:{get_column_letter(label_col + len(col_items))}{r})"
            c.number_format, c.font = fmt, F_BOLD
    last = first + len(items) - 1
    tr = last + 1
    ws.cell(row=tr, column=label_col, value="Total").font = F_BOLD
    for j in range(len(col_items) + (1 if extra_total else 0)):
        col = get_column_letter(label_col + 1 + j)
        c = ws[f"{col}{tr}"]
        c.value = f"=SUM({col}{first}:{col}{last})"
        c.number_format, c.font = fmt, F_BOLD
    style_range(ws, f"{get_column_letter(label_col)}{tr}:{get_column_letter(label_col + len(col_items) + (1 if extra_total else 0))}{tr}",
                fill=FILL_TOTAL, border=TOP)
    return {"header": hr, "first": first, "last": last, "total": tr, "label_col": label_col, "n_cols": len(col_items)}


def margin_block(ws, top, heading, row_label, items, profit_blk, sales_blk, label_col=1):
    """Margin = profit / sales, built from two existing blocks (cell-by-cell formulas)."""
    ws.cell(row=top, column=label_col, value=heading).font = F_BOLD
    hr = top + 1
    n = sales_blk["n_cols"]
    header_row(ws, hr, [row_label] + [f"={get_column_letter(label_col + 1 + j)}{sales_blk['header']}" for j in range(n)] + ["Total"],
               start_col=label_col)
    for j in range(n + 1):                         # header cells hold links to the sales block's year headers
        ws.cell(row=hr, column=label_col + 1 + j).number_format = "0"
    first = hr + 1
    for i, item in enumerate(items):
        r = first + i
        ws.cell(row=r, column=label_col, value=item).font = F_BASE
        for j in range(n + 1):
            col = get_column_letter(label_col + 1 + j)
            p, s = f"{col}{profit_blk['first'] + i}", f"{col}{sales_blk['first'] + i}"
            c = ws[f"{col}{r}"]
            c.value = f"=IF({s}=0,0,{p}/{s})"
            c.number_format, c.font = PCT, F_BASE
    tr = first + len(items)
    ws.cell(row=tr, column=label_col, value="Total").font = F_BOLD
    for j in range(n + 1):
        col = get_column_letter(label_col + 1 + j)
        c = ws[f"{col}{tr}"]
        c.value = f"=IF({col}{sales_blk['total']}=0,0,{col}{profit_blk['total']}/{col}{sales_blk['total']})"
        c.number_format, c.font = PCT, F_BOLD
    style_range(ws, f"{get_column_letter(label_col)}{tr}:{get_column_letter(label_col + n + 1)}{tr}", fill=FILL_TOTAL, border=TOP)
    return {"header": hr, "first": first, "last": first + len(items) - 1, "total": tr}


# --------------------------------------------------------------------------------------- Pivot_Sales sheet
ws_ps = wb.create_sheet("Pivot_Sales")
title(ws_ps, "Sales, profit and margin by category and region",
      "Pivot-style summaries: each cell is a SUMIFS over the Data sheet, so they recalculate with the data.")
cat_sales = matrix(ws_ps, 4, "Sales by category and year ($)", "Category", CATEGORIES, "d_Category", "d_Sales", USD)
cat_profit = matrix(ws_ps, cat_sales["total"] + 3, "Profit by category and year ($)", "Category", CATEGORIES,
                    "d_Category", "d_Profit", USD)
cat_margin = margin_block(ws_ps, cat_profit["total"] + 3, "Profit margin by category and year", "Category", CATEGORIES,
                          cat_profit, cat_sales)
reg_sales = matrix(ws_ps, cat_margin["total"] + 3, "Sales by region and year ($)", "Region", REGIONS, "d_Region", "d_Sales", USD)
reg_profit = matrix(ws_ps, reg_sales["total"] + 3, "Profit by region and year ($)", "Region", REGIONS, "d_Region", "d_Profit", USD)
reg_margin = margin_block(ws_ps, reg_profit["total"] + 3, "Profit margin by region and year", "Region", REGIONS,
                          reg_profit, reg_sales)
chk_row = reg_margin["total"] + 3
ws_ps.cell(row=chk_row, column=1, value="Reconciliation to Data sheet").font = F_BOLD
checks = [
    ("Category sales total = SUM of Data sales", f"=IF(ABS(F{cat_sales['total']}-SUM(d_Sales))<0.005,\"OK\",\"CHECK\")"),
    ("Category profit total = SUM of Data profit", f"=IF(ABS(F{cat_profit['total']}-SUM(d_Profit))<0.005,\"OK\",\"CHECK\")"),
    ("Region sales total = SUM of Data sales", f"=IF(ABS(F{reg_sales['total']}-SUM(d_Sales))<0.005,\"OK\",\"CHECK\")"),
]
for i, (label, formula) in enumerate(checks, start=1):
    ws_ps.cell(row=chk_row + i, column=1, value=label).font = F_BASE
    c = ws_ps.cell(row=chk_row + i, column=6, value=formula)
    c.font, c.alignment = F_BOLD, Alignment(horizontal="center")
widths(ws_ps, {"A": 40, "B": 13, "C": 13, "D": 13, "E": 13, "F": 14})
for blk in (cat_margin, reg_margin):
    ws_ps.conditional_formatting.add(f"B{blk['first']}:F{blk['total']}", CellIsRule(operator="lessThan", formula=["0"],
                                     font=Font(name=FONT, color="C00000")))
for blk in (cat_profit, reg_profit):
    ws_ps.conditional_formatting.add(f"B{blk['first']}:F{blk['total']}", CellIsRule(operator="lessThan", formula=["0"],
                                     font=Font(name=FONT, color="C00000")))
ws_ps.freeze_panes = "B4"

# --------------------------------------------------------------------------------------- Pivot_SubCat sheet
ws_sc = wb.create_sheet("Pivot_SubCat")
title(ws_sc, "Profit by sub-category and year",
      "Rows are ordered by total profit at build time; every value is a live SUMIFS. Red = loss-making.")
header_row(ws_sc, 4, ["Category", "Sub-Category"] + YEARS + ["Total profit", "Total sales", "Margin"])
SC_FIRST = 5
for i, sub in enumerate(SUBCATS):
    r = SC_FIRST + i
    ws_sc.cell(row=r, column=1, value=SUB_TO_CAT[sub]).font = F_BASE
    ws_sc.cell(row=r, column=2, value=sub).font = F_BASE
    for j in range(len(YEARS)):
        col = get_column_letter(3 + j)
        c = ws_sc[f"{col}{r}"]
        c.value = f"=SUMIFS(d_Profit,d_SubCategory,$B{r},d_Year,{col}$4)"
        c.number_format, c.font = USD, F_BASE
    tcol = get_column_letter(3 + len(YEARS))
    c = ws_sc[f"{tcol}{r}"]
    c.value = f"=SUM(C{r}:{get_column_letter(2 + len(YEARS))}{r})"
    c.number_format, c.font = USD, F_BOLD
    c = ws_sc[f"{get_column_letter(4 + len(YEARS))}{r}"]
    c.value = f"=SUMIFS(d_Sales,d_SubCategory,$B{r})"
    c.number_format, c.font = USD, F_BASE
    c = ws_sc[f"{get_column_letter(5 + len(YEARS))}{r}"]
    c.value = f"=IF({get_column_letter(4 + len(YEARS))}{r}=0,0,{tcol}{r}/{get_column_letter(4 + len(YEARS))}{r})"
    c.number_format, c.font = PCT, F_BASE
SC_LAST = SC_FIRST + len(SUBCATS) - 1
SC_TOT = SC_LAST + 1
ws_sc.cell(row=SC_TOT, column=2, value="Total").font = F_BOLD
for j in range(len(YEARS) + 2):
    col = get_column_letter(3 + j)
    c = ws_sc[f"{col}{SC_TOT}"]
    c.value = f"=SUM({col}{SC_FIRST}:{col}{SC_LAST})"
    c.number_format, c.font = USD, F_BOLD
mcol = get_column_letter(5 + len(YEARS))
c = ws_sc[f"{mcol}{SC_TOT}"]
c.value = f"=IF({get_column_letter(4 + len(YEARS))}{SC_TOT}=0,0,{get_column_letter(3 + len(YEARS))}{SC_TOT}/{get_column_letter(4 + len(YEARS))}{SC_TOT})"
c.number_format, c.font = PCT, F_BOLD
style_range(ws_sc, f"A{SC_TOT}:{mcol}{SC_TOT}", fill=FILL_TOTAL, border=TOP)
YC1, YCN = get_column_letter(3), get_column_letter(2 + len(YEARS))
ws_sc.conditional_formatting.add(f"{YC1}{SC_FIRST}:{YCN}{SC_LAST}", ColorScaleRule(
    start_type="min", start_color="F8696B", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="max", end_color="63BE7B"))
TC = get_column_letter(3 + len(YEARS))
ws_sc.conditional_formatting.add(f"{TC}{SC_FIRST}:{TC}{SC_LAST}", DataBarRule(start_type="min", end_type="max", color="5B9BD5"))
ws_sc.conditional_formatting.add(f"{mcol}{SC_FIRST}:{mcol}{SC_LAST}", CellIsRule(operator="lessThan", formula=["0"],
                                 font=Font(name=FONT, color="C00000", bold=True)))
widths(ws_sc, {"A": 17, "B": 15, "C": 12, "D": 12, "E": 12, "F": 12, "G": 14, "H": 14, "I": 9})
ws_sc.freeze_panes = "C5"
SC_RANGE_NAMES = f"Pivot_SubCat!$B${SC_FIRST}:$B${SC_LAST}"
SC_GRID = f"Pivot_SubCat!${YC1}${SC_FIRST}:${YCN}${SC_LAST}"
SC_YEARS = f"Pivot_SubCat!${YC1}$4:${YCN}$4"

# ---------------------------------------------------------------------------------------- Pivot_Month sheet
ws_pm = wb.create_sheet("Pivot_Month")
title(ws_pm, "Monthly sales by year (seasonality)", "SUMIFS by month number and year. The share column shows each month's average slice of annual sales.")
header_row(ws_pm, 4, ["Month #", "Month"] + YEARS + ["Total", "Avg share of year"])
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PM_FIRST = 5
PM_LAST = PM_FIRST + 11
PM_TOT = PM_LAST + 1
for i, m in enumerate(MONTHS):
    r = PM_FIRST + i
    ws_pm.cell(row=r, column=1, value=i + 1).font = F_BASE
    ws_pm.cell(row=r, column=2, value=m).font = F_BASE
    for j in range(len(YEARS)):
        col = get_column_letter(3 + j)
        c = ws_pm[f"{col}{r}"]
        c.value = f"=SUMIFS(d_Sales,d_MonthNum,$A{r},d_Year,{col}$4)"
        c.number_format, c.font = USD, F_BASE
    tcol = get_column_letter(3 + len(YEARS))
    c = ws_pm[f"{tcol}{r}"]
    c.value = f"=SUM(C{r}:{get_column_letter(2 + len(YEARS))}{r})"
    c.number_format, c.font = USD, F_BOLD
    shares = ",".join(f"{get_column_letter(3 + j)}{r}/{get_column_letter(3 + j)}${PM_TOT}" for j in range(len(YEARS)))
    c = ws_pm[f"{get_column_letter(4 + len(YEARS))}{r}"]
    c.value = f"=AVERAGE({shares})"
    c.number_format, c.font = "0.0%", F_BASE
ws_pm.cell(row=PM_TOT, column=2, value="Total").font = F_BOLD
for j in range(len(YEARS) + 1):
    col = get_column_letter(3 + j)
    c = ws_pm[f"{col}{PM_TOT}"]
    c.value = f"=SUM({col}{PM_FIRST}:{col}{PM_LAST})"
    c.number_format, c.font = USD, F_BOLD
c = ws_pm[f"{get_column_letter(4 + len(YEARS))}{PM_TOT}"]
c.value = f"=SUM({get_column_letter(4 + len(YEARS))}{PM_FIRST}:{get_column_letter(4 + len(YEARS))}{PM_LAST})"
c.number_format, c.font = "0.0%", F_BOLD
style_range(ws_pm, f"A{PM_TOT}:{get_column_letter(4 + len(YEARS))}{PM_TOT}", fill=FILL_TOTAL, border=TOP)
SH = get_column_letter(4 + len(YEARS))
ws_pm.cell(row=PM_TOT + 2, column=2, value="Nov + Dec share of annual sales").font = F_BOLD
c = ws_pm.cell(row=PM_TOT + 2, column=3 + len(YEARS) + 1, value=f"={SH}{PM_FIRST + 10}+{SH}{PM_FIRST + 11}")
c.number_format, c.font = "0.0%", F_BOLD
ws_pm.cell(row=PM_TOT + 3, column=2, value="Even spread would be").font = F_BASE
c = ws_pm.cell(row=PM_TOT + 3, column=3 + len(YEARS) + 1, value="=2/12")
c.number_format, c.font = "0.0%", F_BASE
ws_pm.conditional_formatting.add(f"C{PM_FIRST}:{YCN}{PM_LAST}", ColorScaleRule(
    start_type="min", start_color="FFFFFF", end_type="max", end_color="F4B183"))
widths(ws_pm, {"A": 9, "B": 30, "C": 13, "D": 13, "E": 13, "F": 13, "G": 14, "H": 17})
ws_pm.freeze_panes = "C5"

# -------------------------------------------------------------------------------------- Pivot_Discount sheet
ws_pd = wb.create_sheet("Pivot_Discount")
title(ws_pd, "Discount bands: volume, profit and margin", "COUNTIFS / SUMIFS by discount band. Deeper discounts destroy margin.")
header_row(ws_pd, 4, ["Discount band", "Order lines", "Share of lines", "Sales", "Profit", "Margin", "Loss-making lines", "Share of all losses"])
PD_FIRST = 5
PD_LAST = PD_FIRST + len(BANDS) - 1
PD_TOT = PD_LAST + 1
for i, b in enumerate(BANDS):
    r = PD_FIRST + i
    ws_pd.cell(row=r, column=1, value=b).font = F_BASE
    fm = {
        "B": (f"=COUNTIFS(d_DiscountBand,$A{r})", INT),
        "C": (f"=B{r}/B${PD_TOT}", "0.0%"),
        "D": (f"=SUMIFS(d_Sales,d_DiscountBand,$A{r})", USD),
        "E": (f"=SUMIFS(d_Profit,d_DiscountBand,$A{r})", USD),
        "F": (f"=IF(D{r}=0,0,E{r}/D{r})", PCT),
        "G": (f"=COUNTIFS(d_DiscountBand,$A{r},d_Profit,\"<0\")", INT),
        "H": (f"=SUMIFS(d_Profit,d_DiscountBand,$A{r},d_Profit,\"<0\")/SUMIFS(d_Profit,d_Profit,\"<0\")", "0.0%"),
    }
    for col, (f, fmt) in fm.items():
        c = ws_pd[f"{col}{r}"]
        c.value, c.number_format, c.font = f, fmt, F_BASE
ws_pd.cell(row=PD_TOT, column=1, value="Total").font = F_BOLD
for col, fmt in {"B": INT, "C": "0.0%", "D": USD, "E": USD, "G": INT, "H": "0.0%"}.items():
    c = ws_pd[f"{col}{PD_TOT}"]
    c.value, c.number_format, c.font = f"=SUM({col}{PD_FIRST}:{col}{PD_LAST})", fmt, F_BOLD
c = ws_pd[f"F{PD_TOT}"]
c.value, c.number_format, c.font = f"=IF(D{PD_TOT}=0,0,E{PD_TOT}/D{PD_TOT})", PCT, F_BOLD
style_range(ws_pd, f"A{PD_TOT}:H{PD_TOT}", fill=FILL_TOTAL, border=TOP)
ws_pd.conditional_formatting.add(f"E{PD_FIRST}:F{PD_LAST}", CellIsRule(operator="lessThan", formula=["0"],
                                 font=Font(name=FONT, color="C00000", bold=True)))
ws_pd.cell(row=PD_TOT + 2, column=1, value="Lines discounted over 20%: share of lines").font = F_BASE
c = ws_pd.cell(row=PD_TOT + 2, column=3, value=f"=C{PD_FIRST + 2}+C{PD_FIRST + 3}")
c.number_format, c.font = "0.0%", F_BOLD
ws_pd.cell(row=PD_TOT + 3, column=1, value="Lines discounted over 20%: share of all losses").font = F_BASE
c = ws_pd.cell(row=PD_TOT + 3, column=3, value=f"=H{PD_FIRST + 2}+H{PD_FIRST + 3}")
c.number_format, c.font = "0.0%", F_BOLD
widths(ws_pd, {"A": 46, "B": 13, "C": 14, "D": 14, "E": 14, "F": 11, "G": 18, "H": 18})

# ------------------------------------------------------------------------------------------ Pivot_RFM sheet
ws_pr = wb.create_sheet("Pivot_RFM")
title(ws_pr, "Customer segments (RFM)", "Customers are masked tokens. Recency, Frequency and Monetary scores are quintiles (5 = best).")
header_row(ws_pr, 4, ["RFM segment", "Customers", "Share of customers", "Sales", "Profit", "Avg sales per customer"])
PR_FIRST = 5
PR_LAST = PR_FIRST + len(RFM_SEGMENTS) - 1
PR_TOT = PR_LAST + 1
for i, s in enumerate(RFM_SEGMENTS):
    r = PR_FIRST + i
    ws_pr.cell(row=r, column=1, value=s).font = F_BASE
    fm = {"B": (f"=COUNTIF(r_Segment,$A{r})", INT), "C": (f"=B{r}/B${PR_TOT}", "0.0%"),
          "D": (f"=SUMIFS(r_Sales,r_Segment,$A{r})", USD), "E": (f"=SUMIFS(r_Profit,r_Segment,$A{r})", USD),
          "F": (f"=IF(B{r}=0,0,D{r}/B{r})", USD)}
    for col, (f, fmt) in fm.items():
        c = ws_pr[f"{col}{r}"]
        c.value, c.number_format, c.font = f, fmt, F_BASE
ws_pr.cell(row=PR_TOT, column=1, value="Total").font = F_BOLD
for col, fmt in {"B": INT, "C": "0.0%", "D": USD, "E": USD}.items():
    c = ws_pr[f"{col}{PR_TOT}"]
    c.value, c.number_format, c.font = f"=SUM({col}{PR_FIRST}:{col}{PR_LAST})", fmt, F_BOLD
c = ws_pr[f"F{PR_TOT}"]
c.value, c.number_format, c.font = f"=IF(B{PR_TOT}=0,0,D{PR_TOT}/B{PR_TOT})", USD, F_BOLD
style_range(ws_pr, f"A{PR_TOT}:F{PR_TOT}", fill=FILL_TOTAL, border=TOP)
widths(ws_pr, {"A": 22, "B": 12, "C": 18, "D": 14, "E": 14, "F": 22})

# ------------------------------------------------------------------------------------------- Lookups sheet
ws_lk = wb.create_sheet("Lookups")
title(ws_lk, "Lookup toolkit", "Change the yellow cells (blue text). Everything else is a formula. INDEX/MATCH, VLOOKUP and SUMIFS are used for compatibility.")
widths(ws_lk, {"A": 3, "B": 34, "C": 26, "D": 4, "E": 60})


def section(row, text):
    c = ws_lk.cell(row=row, column=2, value=text)
    c.font = Font(name=FONT, size=11, bold=True, color="FFFFFF")
    for col in (2, 3):
        ws_lk.cell(row=row, column=col).fill = FILL_HEAD


def put(row, label, formula, fmt=None, note=None):
    ws_lk.cell(row=row, column=2, value=label).font = F_BASE
    c = ws_lk.cell(row=row, column=3, value=formula)
    c.font, c.alignment = F_BASE, Alignment(horizontal="left")
    if fmt:
        c.number_format = fmt
    if note:
        ws_lk.cell(row=row, column=5, value=note).font = F_SUB


def input_cell(row, label, value, fmt=None, note=None):
    ws_lk.cell(row=row, column=2, value=label).font = F_BOLD
    c = ws_lk.cell(row=row, column=3, value=value)
    c.font, c.fill, c.border, c.alignment = F_INPUT, FILL_INPUT, BOX, Alignment(horizontal="left")
    if fmt:
        c.number_format = fmt
    if note:
        ws_lk.cell(row=row, column=5, value=note).font = F_SUB


multi = flat.groupby("order_id").size()
default_order = multi[multi >= 3].index[0]
default_customer = rfm.iloc[0]["customer_id"]
default_sub = SUBCATS[0]

section(4, "1. Order lookup: INDEX / MATCH (exact)")
input_cell(5, "Order ID", default_order, note="Type any Order ID from the Data sheet, e.g. CA-2014-100678")
put(6, "Order date", '=IFERROR(INDEX(d_OrderDate,MATCH($C$5,d_OrderID,0)),"Order not found")', DATE,
    "INDEX returns the value at the row that MATCH finds")
put(7, "Customer segment", '=IFERROR(INDEX(d_Segment,MATCH($C$5,d_OrderID,0)),"Order not found")')
put(8, "Region / state", '=IFERROR(INDEX(d_Region,MATCH($C$5,d_OrderID,0))&" / "&INDEX(d_State,MATCH($C$5,d_OrderID,0)),"Order not found")',
    note="Two lookups concatenated with &")
put(9, "Ship mode", '=IFERROR(INDEX(d_ShipMode,MATCH($C$5,d_OrderID,0)),"Order not found")')
put(10, "Order lines", "=COUNTIF(d_OrderID,$C$5)", "0", "COUNTIF: an order can have several lines")
put(11, "Order sales", "=SUMIFS(d_Sales,d_OrderID,$C$5)", USD2, "SUMIFS adds up every line of the order")
put(12, "Order profit", "=SUMIFS(d_Profit,d_OrderID,$C$5)", USD2)

section(14, "2. Customer lookup: VLOOKUP across sheets (exact)")
input_cell(15, "Customer token", default_customer, note="Masked customer IDs; copy one from the RFM_Data sheet")
put(16, "Customer segment", '=IFERROR(VLOOKUP($C$15,RFM_Data!$A:$K,2,FALSE),"Customer not found")')
put(17, "RFM segment", '=IFERROR(VLOOKUP($C$15,RFM_Data!$A:$K,11,FALSE),"Customer not found")')
put(18, "Orders placed", '=IFERROR(VLOOKUP($C$15,RFM_Data!$A:$K,4,FALSE),"Customer not found")', "0")
put(19, "Lifetime sales", '=IFERROR(VLOOKUP($C$15,RFM_Data!$A:$K,5,FALSE),"Customer not found")', USD2)
put(20, "Days since last order", '=IFERROR(VLOOKUP($C$15,RFM_Data!$A:$K,7,FALSE),"Customer not found")', "0",
    "Column index 7 = Recency (days) in RFM_Data")

section(22, "3. Two-way lookup: INDEX / MATCH / MATCH")
input_cell(23, "Sub-category", default_sub, note="Pick from the drop-down")
input_cell(24, "Year", YEARS[-1], "0", note="Pick from the drop-down")
put(25, "Profit", f'=IFERROR(INDEX({SC_GRID},MATCH($C$23,{SC_RANGE_NAMES},0),MATCH($C$24,{SC_YEARS},0)),"Not found")', USD,
    "Row from the first MATCH, column from the second, both feeding INDEX")
dv1 = DataValidation(type="list", formula1=f"={SC_RANGE_NAMES}", allow_blank=False)
dv2 = DataValidation(type="list", formula1='"' + ",".join(str(y) for y in YEARS) + '"', allow_blank=False)
ws_lk.add_data_validation(dv1)
ws_lk.add_data_validation(dv2)
dv1.add("C23")
dv2.add("C24")

section(27, "4. Approximate match: VLOOKUP (TRUE)")
input_cell(28, "Discount on a line", 0.35, "0%", note="Try 0%, 10%, 25%, 50%")
ws_lk.cell(row=29, column=2, value="Tier table (sorted ascending)").font = F_BOLD
for i, (lo, lab) in enumerate([(0, BANDS[0]), (0.0001, BANDS[1]), (0.2001, BANDS[2]), (0.4001, BANDS[3])]):
    a = ws_lk.cell(row=30 + i, column=2, value=lo)
    a.font, a.number_format, a.alignment = F_INPUT, "0.00%", Alignment(horizontal="left")
    ws_lk.cell(row=30 + i, column=3, value=lab).font = F_INPUT
put(34, "Discount band", '=VLOOKUP($C$28,$B$30:$C$33,2,TRUE)', note="TRUE = approximate match: finds the largest lower bound that is not above the input")
put(35, "Margin of that band (all sales)", f"=INDEX(Pivot_Discount!$F${PD_FIRST}:$F${PD_LAST},MATCH($C$34,Pivot_Discount!$A${PD_FIRST}:$A${PD_LAST},0))",
    PCT, "A second lookup chained onto the first result")
ws_lk.cell(row=37, column=2, value="Note").font = F_BOLD
ws_lk.cell(row=37, column=3, value="In Excel 365, XLOOKUP is the modern equivalent of INDEX/MATCH and VLOOKUP. It is deliberately not used here so the workbook works in older Excel and LibreOffice.").font = F_SUB
ws_lk["C37"].alignment = Alignment(wrap_text=True, vertical="top")
ws_lk.merge_cells("C37:E39")

# ------------------------------------------------------------------------------------------ Dashboard sheet
ws_db = wb.create_sheet("Dashboard", 0)
title(ws_db, "Superstore sales dashboard", "All figures are formulas over the Data sheet (masked customer tokens). 2014-2017.")
kpis = [
    ("Sales", "=SUM(d_Sales)", USD), ("Profit", "=SUM(d_Profit)", USD),
    ("Profit margin", "=IF(SUM(d_Sales)=0,0,SUM(d_Profit)/SUM(d_Sales))", PCT),
    ("Orders", "=SUM(d_OrderFlag)", INT), ("Customers", f"=COUNTA(RFM_Data!A2:A{RFM_LAST})", INT),
    ("Avg order value", "=IF(SUM(d_OrderFlag)=0,0,SUM(d_Sales)/SUM(d_OrderFlag))", USD),
]
for i, (label, formula, fmt) in enumerate(kpis):
    col = get_column_letter(2 + i * 2)
    nxt = get_column_letter(3 + i * 2)
    lc = ws_db[f"{col}4"]
    lc.value, lc.font = label, Font(name=FONT, size=9, bold=True, color="595959")
    vc = ws_db[f"{col}5"]
    vc.value, vc.number_format, vc.font = formula, fmt, F_KPI
    ws_db.merge_cells(f"{col}4:{nxt}4")
    ws_db.merge_cells(f"{col}5:{nxt}5")
    for r in (4, 5):
        for cc in (col, nxt):
            ws_db[f"{cc}{r}"].fill = FILL_KPI
    lc.alignment = vc.alignment = Alignment(horizontal="center", vertical="center")
ws_db.row_dimensions[5].height = 34
for i in range(1, 15):
    ws_db.column_dimensions[get_column_letter(i)].width = 12

# chart data block (links, green) at the bottom
CD = 53
ws_db.cell(row=CD - 1, column=1, value="Chart data (links to the pivot sheets)").font = F_BOLD
header_row(ws_db, CD, ["Year", "Sales", "Profit"])
for j in range(len(YEARS)):
    r = CD + 1 + j
    col = get_column_letter(2 + j)
    ws_db.cell(row=r, column=1, value=f"=Pivot_Sales!{col}{cat_sales['header']}").font = F_LINK
    ws_db.cell(row=r, column=1).number_format = "0"
    c = ws_db.cell(row=r, column=2, value=f"=Pivot_Sales!{col}{cat_sales['total']}")
    c.font, c.number_format = F_LINK, USD
    c = ws_db.cell(row=r, column=3, value=f"=Pivot_Sales!{col}{cat_profit['total']}")
    c.font, c.number_format = F_LINK, USD


def finish_chart(ch, title_text, x_title=None, y_title=None):
    ch.title = title_text
    ch.roundedCorners = False
    ch.title.overlay = False
    if ch.legend is not None:
        ch.legend.overlay = False
    if x_title:
        ch.x_axis.title = x_title
        ch.x_axis.title.overlay = False
    if y_title:
        ch.y_axis.title = y_title
        ch.y_axis.title.overlay = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.width, ch.height = 16.5, 8.2


c1 = BarChart()
c1.type = "col"
c1.add_data(Reference(ws_db, min_col=2, max_col=3, min_row=CD, max_row=CD + len(YEARS)), titles_from_data=True)
c1.set_categories(Reference(ws_db, min_col=1, min_row=CD + 1, max_row=CD + len(YEARS)))
c1.y_axis.numFmt = '$#,##0'
c1.y_axis.number_format = '$#,##0'
finish_chart(c1, "Sales and profit by year", None, "USD")
ws_db.add_chart(c1, "B7")

c2 = LineChart()
c2.add_data(Reference(ws_pm, min_col=3, max_col=2 + len(YEARS), min_row=4, max_row=PM_LAST), titles_from_data=True)
c2.set_categories(Reference(ws_pm, min_col=2, min_row=PM_FIRST, max_row=PM_LAST))
c2.y_axis.number_format = '$#,##0'
for ser in c2.series:
    ser.smooth = False
finish_chart(c2, "Monthly sales by year (seasonality)", None, "USD")
ws_db.add_chart(c2, "I7")

c3 = BarChart()
c3.type = "bar"
c3.add_data(Reference(ws_sc, min_col=3 + len(YEARS), min_row=4, max_row=SC_LAST), titles_from_data=True)
c3.set_categories(Reference(ws_sc, min_col=2, min_row=SC_FIRST, max_row=SC_LAST))
c3.x_axis.scaling.orientation = "maxMin"
c3.x_axis.tickLblPos = "low"        # keep labels clear of negative bars
c3.x_axis.tickLblSkip = 1
c3.legend = None
c3.y_axis.number_format = '$#,##0'
finish_chart(c3, "Total profit by sub-category", None, "USD")
c3.height = 12.5
ws_db.add_chart(c3, "B25")

c4 = BarChart()
c4.type = "col"
c4.add_data(Reference(ws_pd, min_col=6, min_row=4, max_row=PD_LAST), titles_from_data=True)
c4.set_categories(Reference(ws_pd, min_col=1, min_row=PD_FIRST, max_row=PD_LAST))
c4.legend = None
c4.x_axis.tickLblPos = "low"
c4.y_axis.number_format = '0%'
finish_chart(c4, "Profit margin by discount band", None, "Margin")
c4.height = 12.5
ws_db.add_chart(c4, "I25")

# --------------------------------------------------------------------------------------------- README sheet
ws_rd = wb.create_sheet("README", 0)
title(ws_rd, "Superstore Sales Analysis workbook", "Built by excel/build_workbook.py from the pipeline's masked marts.")
rows = [
    ("Purpose", "Demonstrates Excel lookups, pivot-style summaries, conditional formatting, named ranges, data validation and charts on the Superstore sales data."),
    ("Data", "9,994 order lines (2014-2017) from reports/marts/mart_sales_flat.csv. Customer IDs are masked tokens and postal codes are generalised. No personal data."),
    ("Sheets", "Dashboard (KPIs + charts) | Lookups (interactive) | Pivot_Sales, Pivot_SubCat, Pivot_Month, Pivot_Discount, Pivot_RFM (summaries) | Data | RFM_Data"),
    ("Pivot-style summaries", "Built with SUMIFS/COUNTIFS so they recalculate and can be verified automatically. For native PivotTables: click inside the Data table and use Insert > PivotTable (Superstore_PivotTables.xlsx in this folder has examples)."),
    ("Named ranges", "d_Sales, d_Profit, d_Region, d_Category, d_Year ... refer to the columns of the Data sheet (Formulas > Name Manager)."),
    ("Colour legend", "Yellow fill + blue text = input you can change. Black = formula. Green = link to another sheet."),
    ("Reconciliation", "Pivot_Sales shows OK/CHECK cells proving the summaries tie to the Data sheet."),
    ("Row order", "Pivot_SubCat rows were ordered by total profit when the workbook was built; the values themselves are live formulas."),
    ("Refreshing", "Re-run the pipeline, then python excel/build_workbook.py, or paste new rows into the Data table and extend the named ranges."),
]
for i, (k, v) in enumerate(rows):
    r = 4 + i
    ws_rd.cell(row=r, column=1, value=k).font = F_BOLD
    c = ws_rd.cell(row=r, column=2, value=v)
    c.font, c.alignment = F_BASE, Alignment(wrap_text=True, vertical="top")
    ws_rd.cell(row=r, column=1).alignment = Alignment(vertical="top")
    ws_rd.row_dimensions[r].height = 44 if len(v) > 110 else 30
widths(ws_rd, {"A": 24, "B": 120})

# order sheets
order = ["README", "Dashboard", "Lookups", "Pivot_Sales", "Pivot_SubCat", "Pivot_Month", "Pivot_Discount", "Pivot_RFM", "Data", "RFM_Data"]
wb._sheets = [wb[n] for n in order]
wb.active = 1
for ws in wb.worksheets:
    if ws.title not in ("Data", "RFM_Data"):
        base_font(ws)
ws_lk.sheet_properties.tabColor = "FFC000"
ws_db.sheet_properties.tabColor = "1F3864"
for n in ("Data", "RFM_Data"):
    wb[n].sheet_properties.tabColor = "7F7F7F"

wb.save(OUT)
print(f"wrote {OUT.relative_to(ROOT)}  ({N:,} data rows)")
sys.exit(0)
