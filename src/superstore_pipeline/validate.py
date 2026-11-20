"""Data-quality gates.

Each check returns a `Check` with a severity. `error` checks stop the pipeline; `warn` checks are
reported but let it continue. Results are persisted so a failed run can be diagnosed afterwards.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from .extract import EXPECTED_COLUMNS

DOMAINS = {
    "Ship Mode": {"Standard Class", "Second Class", "First Class", "Same Day"},
    "Segment": {"Consumer", "Corporate", "Home Office"},
    "Region": {"West", "East", "Central", "South"},
    "Category": {"Furniture", "Office Supplies", "Technology"},
}
ORDER_ID_PATTERN = r"^[A-Z]{2}-\d{4}-\d+$"
CUSTOMER_ID_PATTERN = r"^[A-Za-z]{2}-\d+$"        # structure only; casing is checked separately (warning)
CUSTOMER_ID_UPPER_PATTERN = r"^[A-Z]{2}-\d+$"
MAX_REASONABLE_SHIP_DAYS = 14


@dataclass
class Check:
    name: str
    severity: str            # "error" or "warn"
    passed: bool
    failed_rows: int
    description: str


@dataclass
class QualityReport:
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, severity: str, bad: pd.Series | int, description: str) -> None:
        failed = int(bad.sum()) if isinstance(bad, pd.Series) else int(bad)
        self.checks.append(Check(name, severity, failed == 0, failed, description))

    @property
    def errors(self) -> list[Check]:
        return [c for c in self.checks if c.severity == "error" and not c.passed]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.severity == "warn" and not c.passed]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checks_total": len(self.checks),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "checks": [asdict(c) for c in self.checks],
        }

    def summary(self) -> str:
        return (f"{len(self.checks)} checks: {len(self.checks) - len(self.errors) - len(self.warnings)} passed, "
                f"{len(self.warnings)} warnings, {len(self.errors)} errors")


class DataQualityError(RuntimeError):
    """Raised when one or more error-severity checks fail."""

    def __init__(self, report: QualityReport):
        names = ", ".join(f"{c.name} ({c.failed_rows} rows)" for c in report.errors)
        super().__init__(f"data quality gate failed: {names}")
        self.report = report


def run_checks(df: pd.DataFrame) -> QualityReport:
    """Validate the raw orders frame (before masking)."""
    rep = QualityReport()

    # --- schema -------------------------------------------------------------------------------
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    rep.add("schema_required_columns", "error", len(missing),
            f"all {len(EXPECTED_COLUMNS)} expected columns present" + (f" (missing: {missing})" if missing else ""))
    if missing:                       # nothing else can be evaluated safely
        return rep

    # --- completeness -------------------------------------------------------------------------
    null_cells = int(df[EXPECTED_COLUMNS].isna().sum().sum())
    rep.add("no_null_values", "error", null_cells, "no missing values in any column")

    # --- validity -----------------------------------------------------------------------------
    rep.add("sales_positive", "error", df["Sales"] <= 0, "Sales > 0")
    rep.add("quantity_positive", "error", df["Quantity"] <= 0, "Quantity > 0")
    rep.add("discount_in_range", "error", ~df["Discount"].between(0, 1), "0 <= Discount <= 1")
    rep.add("profit_not_above_sales", "error", df["Profit"] > df["Sales"], "Profit <= Sales (cost cannot be negative)")
    rep.add("ship_not_before_order", "error", df["Ship Date"] < df["Order Date"], "Ship Date >= Order Date")
    rep.add("order_id_format", "error", ~df["Order ID"].astype(str).str.match(ORDER_ID_PATTERN),
            "Order ID matches XX-YYYY-NNNNNN")
    rep.add("customer_id_format", "error", ~df["Customer ID"].astype(str).str.match(CUSTOMER_ID_PATTERN),
            "Customer ID matches XX-NNNNN (any letter case)")
    for col, allowed in DOMAINS.items():
        rep.add(f"domain_{col.lower().replace(' ', '_')}", "error", ~df[col].isin(allowed),
                f"{col} in {sorted(allowed)}")

    # --- consistency --------------------------------------------------------------------------
    id_year = pd.to_numeric(df["Order ID"].astype(str).str.slice(3, 7), errors="coerce")   # malformed IDs -> NaN
    rep.add("order_id_year_matches_order_date", "warn", id_year != df["Order Date"].dt.year,
            "year embedded in Order ID equals the Order Date year")
    ids = df["Customer ID"].astype(str)
    rep.add("customer_id_uppercase", "warn", ~ids.str.match(CUSTOMER_ID_UPPER_PATTERN),
            "Customer ID letters are upper case (a few source IDs are not; they are kept as-is)")
    distinct_ids = ids.drop_duplicates()
    rep.add("customer_id_case_collisions", "error", int(distinct_ids.str.upper().duplicated().sum()),
            "no two distinct Customer IDs differ only by letter case (would create duplicate customers)")
    seg_per_customer = df.groupby("Customer ID")["Segment"].nunique()
    rep.add("one_segment_per_customer", "error", int((seg_per_customer > 1).sum()),
            "each customer belongs to exactly one segment (required for dim_customer)")
    region_per_state = df.groupby("State")["Region"].nunique()
    rep.add("one_region_per_state", "error", int((region_per_state > 1).sum()),
            "each state belongs to exactly one region (required for dim_geography)")

    # --- uniqueness / plausibility (warnings) ---------------------------------------------------
    rep.add("no_duplicate_rows", "warn", int(df.duplicated().sum()), "no fully duplicated order lines")
    ship_days = (df["Ship Date"] - df["Order Date"]).dt.days
    rep.add("ship_days_plausible", "warn", ship_days > MAX_REASONABLE_SHIP_DAYS,
            f"shipping takes at most {MAX_REASONABLE_SHIP_DAYS} days")
    rep.add("order_not_in_future", "warn", df["Order Date"] > pd.Timestamp.today().normalize(),
            "no order dated in the future")
    return rep


def reconcile(actual: dict, expected: dict) -> list[str]:
    """Compare loaded totals with source control totals; return a list of mismatch messages."""
    tol = float(expected.get("tolerance", 0.01))
    problems = []
    if "row_count" in expected and actual["row_count"] != expected["row_count"]:
        problems.append(f"row_count {actual['row_count']} != {expected['row_count']}")
    for key in ("sales", "profit"):
        if key in expected and abs(actual[key] - expected[key]) > tol:
            problems.append(f"{key} {actual[key]:,.2f} != {expected[key]:,.2f}")
    return problems
