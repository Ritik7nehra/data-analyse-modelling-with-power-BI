"""Extract step: read the raw orders file and capture lineage metadata."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID", "Sales", "Quantity",
    "Discount", "Profit", "Segment", "City", "State", "Postal Code", "Region", "Category",
    "Sub-Category", "Product Name",
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_orders(path: Path) -> tuple[pd.DataFrame, dict]:
    """Read the orders CSV. Postal codes are read as text because leading zeros matter (e.g. 02142)."""
    if not path.exists():
        raise FileNotFoundError(f"source file not found: {path}")
    df = pd.read_csv(path, dtype={"Postal Code": "string"}, parse_dates=["Order Date", "Ship Date"])
    lineage = {"source_file": str(path.name), "source_sha256": file_sha256(path), "rows_extracted": len(df)}
    return df, lineage
