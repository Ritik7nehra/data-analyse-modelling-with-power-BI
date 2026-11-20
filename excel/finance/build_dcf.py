"""Build excel/finance/Superstore_DCF_Valuation.xlsx - an illustrative three-scenario DCF.

    python excel/finance/build_dcf.py
    python <skill>/scripts/recalc.py excel/finance/Superstore_DCF_Valuation.xlsx   # store computed values

All assumptions live on the Assumptions sheet (blue text, yellow fill). Every other number is a formula. Default
assumption values come from src/superstore_pipeline/valuation.py so the Excel model and the Python cross-check
(tests/test_valuation.py) cannot drift apart. Historical sales and profit are aggregated from the pipeline mart.

Illustrative only: see the README sheet for the limits of this model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from superstore_pipeline import valuation as val  # noqa: E402

OUT = Path(__file__).resolve().parent / "Superstore_DCF_Valuation.xlsx"

FONT = "Arial"
F = Font(name=FONT, size=10)
FB = Font(name=FONT, size=10, bold=True)
F_TITLE = Font(name=FONT, size=16, bold=True, color="1F3864")
F_SUB = Font(name=FONT, size=10, italic=True, color="595959")
F_HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_IN = Font(name=FONT, size=10, color="0000FF")          # hard-coded input
F_LINK = Font(name=FONT, size=10, color="008000")        # link to another sheet
FILL_HEAD = PatternFill("solid", fgColor="1F3864")
FILL_IN = PatternFill("solid", fgColor="FFFF00")
FILL_TOT = PatternFill("solid", fgColor="D9E1F2")
FILL_SEC = PatternFill("solid", fgColor="DDEBF7")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
TOP = Border(top=Side(style="thin", color="000000"))

USD = '$#,##0;($#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
PCT2 = '0.00%;(0.00%);"-"'
MULT = '0.0"x"'
NUM2 = '0.00'

# ---------------------------------------------------------------------------------------------------- data
flat = pd.read_csv(ROOT / "reports" / "marts" / "mart_sales_flat.csv", usecols=["year", "sales", "profit"])
hist = flat.groupby("year").agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
HIST_YEARS = hist["year"].tolist()
A = val.Assumptions()
SC = val.SCENARIOS
SC_NAMES = list(SC)
FY = val.FORECAST_YEARS
NH, NF = len(HIST_YEARS), len(FY)

wb = Workbook()


def sheet(name, title, sub):
    ws = wb.create_sheet(name)
    ws["A1"], ws["A1"].font = title, F_TITLE
    ws["A2"], ws["A2"].font = sub, F_SUB
    ws.sheet_view.showGridLines = False
    return ws


def hdr(ws, row, labels, col=1):
    for i, t in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=t)
        c.font, c.fill, c.border = F_HEAD, FILL_HEAD, BOX
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def name(n, ref):
    wb.defined_names[n] = DefinedName(n, attr_text=ref)


def put(ws, ref, value, fmt=None, font=F, fill=None, align=None):
    c = ws[ref]
    c.value, c.font = value, font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if align:
        c.alignment = align
    return c


def inp(ws, ref, value, fmt=None):
    c = put(ws, ref, value, fmt, F_IN, FILL_IN)
    c.border = BOX
    return c


def band(ws, ref, fill=FILL_TOT, border=TOP):
    for row in ws[ref]:
        for c in row:
            c.fill, c.border = fill, border


wb.remove(wb.active)

# ----------------------------------------------------------------------------------------------- README
rd = sheet("README", "Superstore DCF valuation (illustrative)", "Three-scenario discounted cash flow with a WACC x terminal-growth sensitivity.")
notes = [
    ("What this is", "A worked example of financial modelling mechanics: forecast, free cash flow, WACC, terminal value, enterprise value, scenarios and sensitivity. Every figure is a live formula."),
    ("What this is NOT", "A valuation of a real company. The Superstore data contains order-line sales and profit only. There is no balance sheet or share count, and Profit is used as an EBIT proxy."),
    ("Assumptions", "Forecast growth and margins, tax rate, D&A / capex / working-capital ratios and cost-of-capital inputs are ILLUSTRATIVE PLACEHOLDERS, not sourced market data. Replace them before using any output."),
    ("Historicals", "Annual sales and profit are sums of reports/marts/mart_sales_flat.csv (the masked pipeline mart). They are the only data-derived inputs."),
    ("How to use", "Assumptions sheet: change the scenario selector (1 Base, 2 Bull, 3 Bear) or any yellow cell. DCF shows the selected scenario in detail, Scenarios compares all three, Sensitivity flexes WACC and terminal growth."),
    ("Method", "Free cash flow = EBIT x (1 - tax) + D&A - capex - increase in working capital. End-of-year discounting at WACC. Terminal value by Gordon growth on the final-year FCF."),
    ("Checks", "Scenarios!B12, Sensitivity!B12 and Sensitivity!B14 confirm the three views agree with the DCF sheet. Python cross-check: tests/test_valuation.py."),
    ("Colour legend", "Yellow fill + blue text = input. Black = formula. Green = link to another sheet."),
    ("Not investment advice", "Educational model. It is not financial advice and no recommendation is made."),
]
for i, (k, t) in enumerate(notes):
    r = 4 + i
    put(rd, f"A{r}", k, font=FB, align=Alignment(vertical="top"))
    put(rd, f"B{r}", t, align=Alignment(wrap_text=True, vertical="top"))
    rd.row_dimensions[r].height = 44 if len(t) > 120 else 30
rd.column_dimensions["A"].width = 22
rd.column_dimensions["B"].width = 125

# ------------------------------------------------------------------------------------------ Historicals
hs = sheet("Historicals", "Historical sales and profit", "Source: reports/marts/mart_sales_flat.csv aggregated by order year (blue = hard-coded from pipeline output).")
hdr(hs, 4, ["Year", "Sales ($)", "Profit ($)", "Profit margin", "Sales growth"])
for i, row in enumerate(hist.itertuples(index=False)):
    r = 5 + i
    put(hs, f"A{r}", str(int(row.year)), font=F_IN)
    put(hs, f"B{r}", round(float(row.sales), 4), USD, F_IN)
    put(hs, f"C{r}", round(float(row.profit), 4), USD, F_IN)
    put(hs, f"D{r}", f"=IF(B{r}=0,0,C{r}/B{r})", PCT)
    if i:
        put(hs, f"E{r}", f"=B{r}/B{r - 1}-1", PCT)
HL = 4 + NH
put(hs, f"A{HL + 2}", "Sales CAGR over the period", font=FB)
put(hs, f"D{HL + 2}", f"=(B{HL}/B5)^(1/{NH - 1})-1", PCT, FB)
put(hs, f"A{HL + 3}", "Average profit margin", font=FB)
put(hs, f"D{HL + 3}", f"=SUM(C5:C{HL})/SUM(B5:B{HL})", PCT, FB)
put(hs, f"A{HL + 5}", "Profit is the order-line profit reported in the source; how overheads are treated is not documented. Using it as EBIT is a simplification that may overstate or understate true operating margin.", font=F_SUB)
for col, w in zip("ABCDE", (28, 15, 15, 14, 14), strict=True):
    hs.column_dimensions[col].width = w

# ----------------------------------------------------------------------------------------- Assumptions
asm = sheet("Assumptions", "Assumptions", "Illustrative placeholders. Change yellow cells; everything else recalculates.")
put(asm, "A4", "Scenario selector (1 = Base, 2 = Bull, 3 = Bear)", font=FB)
inp(asm, "B4", 1, "0")
put(asm, "C4", '=CHOOSE($B$4,"Base","Bull","Bear")', font=FB)
dv = DataValidation(type="list", formula1='"1,2,3"', allow_blank=False)
asm.add_data_validation(dv)
dv.add("B4")

put(asm, "A6", "Scenario drivers", font=FB)
hdr(asm, 7, ["Driver"] + SC_NAMES + ["Selected"])
for j, y in enumerate(FY):
    r = 8 + j
    put(asm, f"A{r}", f"Revenue growth {y}E")
    for k, s in enumerate(SC_NAMES):
        inp(asm, f"{L(2 + k)}{r}", SC[s].growth[j], PCT)
    put(asm, f"E{r}", f"=CHOOSE($B$4,B{r},C{r},D{r})", PCT)
for j, y in enumerate(FY):
    r = 13 + j
    put(asm, f"A{r}", f"EBIT margin {y}E")
    for k, s in enumerate(SC_NAMES):
        inp(asm, f"{L(2 + k)}{r}", SC[s].ebit_margin[j], PCT)
    put(asm, f"E{r}", f"=CHOOSE($B$4,B{r},C{r},D{r})", PCT)
GROW0, MARG0 = 8, 13   # first driver rows

put(asm, "A19", "Operating and tax assumptions", font=FB)
rows = [
    ("Tax rate on EBIT", A.tax_rate, PCT, "a_Tax"),
    ("D&A (% of sales)", A.da_pct_sales, PCT, "a_DA"),
    ("Capex (% of sales)", A.capex_pct_sales, PCT, "a_Capex"),
    ("Working-capital investment (% of change in sales)", A.nwc_pct_delta_sales, PCT, "a_NWC"),
    ("Net debt ($) - no balance sheet in the data", A.net_debt, USD, "a_NetDebt"),
]
for i, (lab, v, fmt, nm) in enumerate(rows):
    r = 20 + i
    put(asm, f"A{r}", lab)
    inp(asm, f"B{r}", v, fmt)
    name(nm, f"Assumptions!$B${r}")

put(asm, "A26", "Cost of capital (WACC)", font=FB)
wrows = [
    ("Risk-free rate", A.risk_free, PCT2, "a_Rf"),
    ("Equity risk premium", A.equity_risk_premium, PCT2, "a_ERP"),
    ("Equity beta", A.beta, NUM2, "a_Beta"),
    ("Pre-tax cost of debt", A.pre_tax_cost_of_debt, PCT2, "a_Kd"),
    ("Debt weight D / (D+E)", A.debt_weight, PCT, "a_Wd"),
]
for i, (lab, v, fmt, nm) in enumerate(wrows):
    r = 27 + i
    put(asm, f"A{r}", lab)
    inp(asm, f"B{r}", v, fmt)
    name(nm, f"Assumptions!$B${r}")
put(asm, "A32", "Cost of equity (CAPM)")
put(asm, "B32", "=a_Rf+a_Beta*a_ERP", PCT2)
put(asm, "A33", "After-tax cost of debt")
put(asm, "B33", "=a_Kd*(1-a_Tax)", PCT2)
put(asm, "A34", "WACC", font=FB)
put(asm, "B34", "=(1-a_Wd)*B32+a_Wd*B33", PCT2, FB)
band(asm, "A34:B34")
name("a_WACC", "Assumptions!$B$34")
put(asm, "A36", "Terminal growth rate", font=F)
inp(asm, "B36", A.terminal_growth, PCT2)
name("a_g", "Assumptions!$B$36")
put(asm, "A37", "Sensitivity step: WACC")
inp(asm, "B37", A.wacc_step, PCT2)
put(asm, "A38", "Sensitivity step: terminal growth")
inp(asm, "B38", A.growth_step, PCT2)
name("a_StepW", "Assumptions!$B$37")
name("a_StepG", "Assumptions!$B$38")
put(asm, "A40", "None of these inputs is sourced market data. Risk-free rate, ERP, beta and cost of debt are placeholders to show the CAPM/WACC mechanics.", font=F_SUB)
asm.column_dimensions["A"].width = 50
for col in "BCDE":
    asm.column_dimensions[col].width = 13

# --------------------------------------------------------------------------------------------------- DCF
dcf = sheet("DCF", "Discounted cash flow: selected scenario", "=\"Scenario: \"&Assumptions!C4&\"   |   $ unless stated   |   valuation date: end of \"&Historicals!A" + str(HL))
dcf["A2"].font = F_SUB
labels = {5: "Period (t)", 6: "Revenue", 7: "  growth", 8: "EBIT (profit proxy)", 9: "  margin", 10: "Taxes on EBIT",
          11: "NOPAT", 12: "+ D&A", 13: "- Capex", 14: "- Increase in working capital", 15: "Free cash flow (FCF)",
          16: "Discount factor", 17: "PV of FCF"}
ycols = [L(2 + i) for i in range(NH + NF)]            # B..
hist_cols, fc_cols = ycols[:NH], ycols[NH:]
hdr(dcf, 4, ["$"] + [f"{y}A" for y in HIST_YEARS] + [f"{y}E" for y in FY])
for r, t in labels.items():
    put(dcf, f"A{r}", t, font=FB if r in (6, 8, 11, 15) else F)
for i, c in enumerate(hist_cols):
    hr = 5 + i
    put(dcf, f"{c}6", f"=Historicals!B{hr}", USD, F_LINK)
    put(dcf, f"{c}8", f"=Historicals!C{hr}", USD, F_LINK)
    put(dcf, f"{c}9", f"=IF({c}6=0,0,{c}8/{c}6)", PCT)
    if i:
        put(dcf, f"{c}7", f"={c}6/{hist_cols[i - 1]}6-1", PCT)
for j, c in enumerate(fc_cols):
    prev = ycols[NH + j - 1]
    put(dcf, f"{c}5", j + 1, "0")
    put(dcf, f"{c}7", f"=Assumptions!E{GROW0 + j}", PCT, F_LINK)
    put(dcf, f"{c}6", f"={prev}6*(1+{c}7)", USD)
    put(dcf, f"{c}9", f"=Assumptions!E{MARG0 + j}", PCT, F_LINK)
    put(dcf, f"{c}8", f"={c}6*{c}9", USD)
    put(dcf, f"{c}10", f"=-{c}8*a_Tax", USD)
    put(dcf, f"{c}11", f"={c}8+{c}10", USD, FB)
    put(dcf, f"{c}12", f"={c}6*a_DA", USD)
    put(dcf, f"{c}13", f"=-{c}6*a_Capex", USD)
    put(dcf, f"{c}14", f"=-({c}6-{prev}6)*a_NWC", USD)
    put(dcf, f"{c}15", f"={c}11+{c}12+{c}13+{c}14", USD, FB)
    put(dcf, f"{c}16", f"=1/(1+a_WACC)^{c}5", "0.0000")
    put(dcf, f"{c}17", f"={c}15*{c}16", USD)
band(dcf, f"A15:{ycols[-1]}15")
F0, FN = fc_cols[0], fc_cols[-1]

put(dcf, "A20", "Valuation", font=FB)
dcf["A20"].fill = FILL_SEC
band(dcf, "A20:C20", FILL_SEC, Border())
vrows = [
    (21, "WACC", "=a_WACC", PCT2, "o_WACC"),
    (22, "Terminal growth", "=a_g", PCT2, None),
    (23, "Sum of PV of FCF", f"=SUM({F0}17:{FN}17)", USD, "o_PVFCF"),
    (24, "Terminal value (Gordon growth, at year N)", f"={FN}15*(1+a_g)/(a_WACC-a_g)", USD, "o_TV"),
    (25, "PV of terminal value", f"=C24*{FN}16", USD, "o_PVTV"),
    (26, "Enterprise value", "=C23+C25", USD, "o_EV"),
    (27, "Less: net debt", "=-a_NetDebt", USD, None),
    (28, "Equity value", "=C26+C27", USD, "o_Equity"),
    (30, "Terminal value as % of EV", "=C25/C26", PCT, "o_TVShare"),
    (31, "Implied terminal EV / EBITDA", f"=C24/({FN}8+{FN}12)", MULT, "o_ExitMultiple"),
    (32, f"EV / {HIST_YEARS[-1]} sales", f"=C26/{hist_cols[-1]}6", MULT, None),
    (33, f"EV / {HIST_YEARS[-1]} EBIT proxy", f"=C26/{hist_cols[-1]}8", MULT, None),
]
for r, lab, f, fmt, nm in vrows:
    put(dcf, f"A{r}", lab, font=FB if r in (26, 28) else F)
    put(dcf, f"C{r}", f, fmt, FB if r in (26, 28) else F)
    if nm:
        name(nm, f"DCF!$C${r}")
band(dcf, "A26:C26")
band(dcf, "A28:C28")
put(dcf, "A35", "Terminal value uses the final forecast year's FCF; working-capital and capex ratios are held constant. See Assumptions for caveats.", font=F_SUB)
dcf.column_dimensions["A"].width = 42
for c in ycols:
    dcf.column_dimensions[c].width = 13
dcf.freeze_panes = "B5"
dcf.conditional_formatting.add(f"B15:{ycols[-1]}15", FormulaRule(formula=["B15<0"], font=Font(name=FONT, color="C00000", bold=True)))

# FCF / revenue chart
ch = BarChart()
ch.type = "col"
ch.add_data(Reference(dcf, min_col=NH + 2, max_col=NH + 1 + NF, min_row=15, max_row=15), from_rows=True, titles_from_data=False)
ch.set_categories(Reference(dcf, min_col=NH + 2, max_col=NH + 1 + NF, min_row=4, max_row=4))
ch.series[0].tx = SeriesLabel(v="Free cash flow")
ch.title = "Forecast free cash flow ($)"
ch.roundedCorners = False
ch.title.overlay = False
ch.legend = None
ch.x_axis.delete = False
ch.y_axis.delete = False
ch.y_axis.number_format = "$#,##0"
ch.width, ch.height = 15, 7.5
dcf.add_chart(ch, "E20")

# ---------------------------------------------------------------------------------------------- Scenarios
sc = sheet("Scenarios", "Scenario comparison", "All three scenarios computed side by side with the same formulas as the DCF sheet.")
hdr(sc, 4, ["Scenario", "Enterprise value", "Equity value", "TV % of EV", "Implied EV/EBITDA", f"EV / {HIST_YEARS[-1]} sales", "vs Base"])
BLK0 = 17
blk_rows = {}
for k, s in enumerate(SC_NAMES):
    top = BLK0 + k * 12
    blk_rows[s] = top
    put(sc, f"A{top}", f"{s} scenario", font=FB)
    sc[f"A{top}"].fill = FILL_SEC
    hdr(sc, top + 1, [""] + [f"{y}E" for y in FY])
    cl = {"rev": top + 2, "ebit": top + 3, "nopat": top + 4, "da": top + 5, "capex": top + 6, "nwc": top + 7,
          "fcf": top + 8, "pv": top + 9}
    for key, lab in zip(cl, ["Revenue", "EBIT", "NOPAT", "+ D&A", "- Capex", "- Increase in working capital", "Free cash flow",
                             "PV of FCF"], strict=True):
        put(sc, f"A{cl[key]}", lab, font=FB if key == "fcf" else F)
    gcol, mcol = L(2 + k), L(2 + k)   # scenario column on Assumptions (B/C/D)
    for j in range(NF):
        c = L(2 + j)
        prev = f"DCF!{hist_cols[-1]}6" if j == 0 else f"{L(1 + j)}{cl['rev']}"
        put(sc, f"{c}{cl['rev']}", f"={prev}*(1+Assumptions!{gcol}{GROW0 + j})", USD)
        put(sc, f"{c}{cl['ebit']}", f"={c}{cl['rev']}*Assumptions!{mcol}{MARG0 + j}", USD)
        put(sc, f"{c}{cl['nopat']}", f"={c}{cl['ebit']}*(1-a_Tax)", USD)
        put(sc, f"{c}{cl['da']}", f"={c}{cl['rev']}*a_DA", USD)
        put(sc, f"{c}{cl['capex']}", f"=-{c}{cl['rev']}*a_Capex", USD)
        put(sc, f"{c}{cl['nwc']}", f"=-({c}{cl['rev']}-{prev})*a_NWC", USD)
        put(sc, f"{c}{cl['fcf']}", f"={c}{cl['nopat']}+{c}{cl['da']}+{c}{cl['capex']}+{c}{cl['nwc']}", USD, FB)
        put(sc, f"{c}{cl['pv']}", f"={c}{cl['fcf']}/(1+a_WACC)^{j + 1}", USD)
    band(sc, f"A{cl['fcf']}:{L(1 + NF)}{cl['fcf']}")
    last = L(1 + NF)
    r = 5 + k
    put(sc, f"A{r}", s, font=FB)
    ev = f"(SUM(B{cl['pv']}:{last}{cl['pv']})+{last}{cl['fcf']}*(1+a_g)/(a_WACC-a_g)/(1+a_WACC)^{NF})"
    put(sc, f"B{r}", f"={ev}", USD, FB)
    put(sc, f"C{r}", f"=B{r}-a_NetDebt", USD)
    put(sc, f"D{r}", f"=({last}{cl['fcf']}*(1+a_g)/(a_WACC-a_g)/(1+a_WACC)^{NF})/B{r}", PCT)
    put(sc, f"E{r}", f"=({last}{cl['fcf']}*(1+a_g)/(a_WACC-a_g))/({last}{cl['ebit']}+{last}{cl['da']})", MULT)
    put(sc, f"F{r}", f"=B{r}/DCF!{hist_cols[-1]}6", MULT)
    put(sc, f"G{r}", f"=B{r}/$B$5-1", PCT)
    name(f"o_EV_{s}", f"Scenarios!$B${r}")
put(sc, "A10", "Selected scenario (from Assumptions)", font=FB)
put(sc, "B10", "=Assumptions!C4", font=FB)
put(sc, "A11", "EV of the selected scenario on this sheet")
put(sc, "B11", "=CHOOSE(Assumptions!B4,B5,B6,B7)", USD)
put(sc, "A12", "Check: equals DCF sheet EV", font=FB)
put(sc, "B12", '=IF(ABS(B11-DCF!C26)<0.005,"OK","CHECK")', font=FB, align=Alignment(horizontal="center"))
put(sc, "A14", "Scenarios differ only in growth and margin paths. WACC, terminal growth and the other ratios are shared.", font=F_SUB)
sc.column_dimensions["A"].width = 38
for c in "BCDEFGH":
    sc.column_dimensions[c].width = 16

ch2 = BarChart()
ch2.type = "col"
ch2.add_data(Reference(sc, min_col=2, min_row=4, max_row=7), titles_from_data=True)
ch2.set_categories(Reference(sc, min_col=1, min_row=5, max_row=7))
ch2.title = "Enterprise value by scenario ($)"
ch2.roundedCorners = False
ch2.title.overlay = False
ch2.legend = None
ch2.x_axis.delete = False
ch2.y_axis.delete = False
ch2.y_axis.number_format = "$#,##0"
ch2.width, ch2.height = 13, 6.5
sc.add_chart(ch2, "J4")

# ------------------------------------------------------------------------------------------- Sensitivity
se = sheet("Sensitivity", "Sensitivity: WACC x terminal growth", "Selected scenario. Each cell is a closed-form formula (no Excel data table), so it recalculates anywhere.")
GR = 5   # grid size
FCF = f"DCF!${F0}$15:${FN}$15"
PER = f"DCF!${F0}$5:${FN}$5"


def grid(top, heading, cell_formula, fmt):
    put(se, f"A{top}", heading, font=FB)
    put(se, f"A{top + 1}", "WACC \\ g", font=F_HEAD, fill=FILL_HEAD, align=Alignment(horizontal="center"))
    for j in range(GR):
        c = L(2 + j)
        put(se, f"{c}{top + 1}", f"=a_g+({j - GR // 2})*a_StepG", PCT2, F_HEAD, FILL_HEAD, Alignment(horizontal="center"))
    for i in range(GR):
        r = top + 2 + i
        put(se, f"A{r}", f"=a_WACC+({i - GR // 2})*a_StepW", PCT2, F_HEAD, FILL_HEAD, Alignment(horizontal="center"))
        for j in range(GR):
            c = L(2 + j)
            put(se, f"{c}{r}", cell_formula(f"$A{r}", f"{c}${top + 1}"), fmt)
            se[f"{c}{r}"].border = BOX
    return top + 2, top + 1 + GR


def ev_formula(w, g):
    return (f'=IF({w}<={g},"n/a",SUMPRODUCT({FCF}/(1+{w})^{PER})+DCF!${FN}$15*(1+{g})/({w}-{g})/(1+{w})^DCF!${FN}$5)')


def tv_share_formula(w, g):
    return (f'=IF({w}<={g},"n/a",(DCF!${FN}$15*(1+{g})/({w}-{g})/(1+{w})^DCF!${FN}$5)/'
            f'(SUMPRODUCT({FCF}/(1+{w})^{PER})+DCF!${FN}$15*(1+{g})/({w}-{g})/(1+{w})^DCF!${FN}$5))')


g1a, g1b = grid(4, "Enterprise value ($)", ev_formula, USD)
g2a, g2b = grid(12 + 3, "Terminal value as % of enterprise value", tv_share_formula, "0%")
put(se, "A12", "Check: centre cell equals DCF EV")
put(se, "B12", f'=IF(ABS(D{g1a + GR // 2}-DCF!C26)<0.005,"OK","CHECK")', font=FB, align=Alignment(horizontal="center"))
put(se, "A14", "Check: centre cell (TV share) equals DCF")
put(se, "B14", f'=IF(ABS(D{g2a + GR // 2}-DCF!C30)<0.00001,"OK","CHECK")', font=FB, align=Alignment(horizontal="center"))
se.conditional_formatting.add(f"B{g1a}:F{g1b}", ColorScaleRule(start_type="min", start_color="F8696B", mid_type="percentile", mid_value=50,
                              mid_color="FFEB84", end_type="max", end_color="63BE7B"))
se.conditional_formatting.add(f"B{g2a}:F{g2b}", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="9DC3E6"))
se.column_dimensions["A"].width = 38
for c in "BCDEF":
    se.column_dimensions[c].width = 15

# ---------------------------------------------------------------------------------------------- finalise
order = ["README", "Assumptions", "DCF", "Scenarios", "Sensitivity", "Historicals"]
wb._sheets = [wb[n] for n in order]
wb.active = 1
for n, color in (("Assumptions", "FFC000"), ("DCF", "1F3864"), ("Scenarios", "1F3864"), ("Sensitivity", "1F3864"), ("Historicals", "7F7F7F")):
    wb[n].sheet_properties.tabColor = color
wb.save(OUT)
print(f"wrote {OUT.relative_to(ROOT)}")
