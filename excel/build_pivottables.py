"""Build excel/Superstore_PivotTables.xlsx: native PivotTables over the masked sales mart.

The main workbook uses SUMIFS "pivot-style" summaries (so they can be verified headlessly). This script produces
genuine PivotTables for people who want to click around: it drives LibreOffice through UNO (DataPilot tables), and
LibreOffice exports them as native Excel PivotTables.

    python excel/build_pivottables.py

Requires LibreOffice (soffice) and its Python UNO bridge. Not part of the default CI run.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "Superstore_PivotTables.xlsx"
PORT = 2002

COLS = [  # (header, mart column)
    ("Order ID", "order_id"), ("Order Date", "order_date"), ("Year", "year"), ("Quarter", "quarter"),
    ("Region", "region"), ("Segment", "segment"), ("Category", "category"), ("Sub-Category", "sub_category"),
    ("Discount Band", "discount_band"), ("Sales", "sales"), ("Quantity", "quantity"), ("Profit", "profit"),
]


def write_source(path: Path) -> int:
    flat = pd.read_csv(ROOT / "reports" / "marts" / "mart_sales_flat.csv", parse_dates=["order_date"])
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append([h for h, _ in COLS])
    for rec in flat[[c for _, c in COLS]].itertuples(index=False):
        ws.append([v.to_pydatetime() if isinstance(v, pd.Timestamp) else (v.item() if hasattr(v, "item") else v)
                   for v in rec])
    wb.create_sheet("Pivots")
    wb.save(path)
    return len(flat)


def main() -> int:
    try:
        import uno  # noqa: F401
        from com.sun.star.beans import PropertyValue  # noqa: F401
    except ImportError:
        print("LibreOffice's Python UNO bridge is not importable; cannot build native PivotTables.", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="pivots_"))
    src = tmp / "source.xlsx"
    n = write_source(src)
    proc = subprocess.Popen(
        ["soffice", "--headless", "--norestore", "--nologo", f"--accept=socket,host=localhost,port={PORT};urp;",
         f"-env:UserInstallation=file://{tmp}/profile"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = None
        for _ in range(60):
            try:
                ctx = resolver.resolve(f"uno:socket,host=localhost,port={PORT};urp;StarOffice.ComponentContext")
                break
            except Exception:
                time.sleep(1)
        if ctx is None:
            print("could not connect to soffice", file=sys.stderr)
            return 3
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

        def pv(name, value):
            p = PropertyValue()
            p.Name, p.Value = name, value
            return p

        doc = desktop.loadComponentFromURL(src.as_uri(), "_blank", 0, (pv("Hidden", True),))
        data = doc.Sheets.getByName("Data")
        pivots = doc.Sheets.getByName("Pivots")
        src_range = data.getCellRangeByName(f"A1:L{n + 1}").getRangeAddress()
        ORI = "com.sun.star.sheet.DataPilotFieldOrientation"
        FUNC = "com.sun.star.sheet.GeneralFunction"
        names = [h for h, _ in COLS]

        def add_pivot(name, anchor, rows, cols, values):
            desc = pivots.DataPilotTables.createDataPilotDescriptor()
            desc.setSourceRange(src_range)
            fields = desc.getDataPilotFields()
            for f in rows:                       # row fields nest in the order they are assigned
                fields.getByIndex(names.index(f)).Orientation = uno.Enum(ORI, "ROW")
            for f in cols:
                fields.getByIndex(names.index(f)).Orientation = uno.Enum(ORI, "COLUMN")
            for f in values:
                fld = fields.getByIndex(names.index(f))
                fld.Orientation = uno.Enum(ORI, "DATA")
                fld.Function = uno.Enum(FUNC, "SUM")
            cell = pivots.getCellRangeByName(anchor).getCellAddress()
            pivots.DataPilotTables.insertNewByName(name, cell, desc)

        add_pivot("PT_Sales_Category_Year", "A4", ["Category"], ["Year"], ["Sales"])
        add_pivot("PT_Profit_Region_Segment", "H4", ["Region"], ["Segment"], ["Profit"])
        add_pivot("PT_SubCategory", "A16", ["Category", "Sub-Category"], [], ["Sales", "Profit"])
        add_pivot("PT_Discount_Band", "H16", ["Discount Band"], [], ["Sales", "Profit"])

        notes = {
            "A1": "Native PivotTables over the Data sheet (masked Superstore marts). Right-click > Refresh after changing Data.",
            "A3": "Sales by category and year", "H3": "Profit by region and segment",
            "A15": "Sales and profit by sub-category", "H15": "Sales and profit by discount band",
        }
        for ref, text in notes.items():
            pivots.getCellRangeByName(ref).setString(text)
        for col in ("A", "B", "H", "I"):
            pivots.getColumns().getByName(col).Width = 4200

        out = pv("FilterName", "Calc MS Excel 2007 XML")
        doc.storeToURL(OUT.as_uri(), (out,))
        doc.close(True)
        print(f"wrote {OUT.relative_to(ROOT)}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
