"""Export the data embedded in the Power BI reports to CSV files in data/.

The .pbix files carry their own copy of the data (the original Excel / web sources are not in this
repo), so this script makes the notebooks reproducible without Power BI Desktop.

    pip install pbixray pandas
    python scripts/export_pbix_data.py

Outputs
    data/superstore_orders.csv          Orders joined to Customers, Geography and Products (one row per order line)
    data/nigeria_covid19_by_state.csv   Covid-19 cases by state (snapshot embedded in the dashboard)

Customer names are intentionally not exported; Customer ID is enough for the analysis.
"""
from pathlib import Path

import pandas as pd
from pbixray import PBIXRay

ROOT = Path(__file__).resolve().parents[1]
PBIX_DIR = ROOT / "powerbi"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def export_sales() -> None:
    model = PBIXRay(str(PBIX_DIR / "sales-report-data-modelling.pbix"))
    orders = model.get_table("Orders")
    customers = model.get_table("Customers").drop(columns=["Customer Name"])
    geography = model.get_table("Geography")
    products = model.get_table("Products")

    # Same keys as the relationships in the Power BI model (Orders -> dimension, many-to-one).
    df = (
        orders
        .merge(customers, on="Customer ID", how="left", validate="m:1")
        .merge(geography.drop(columns=["Country"]), on="GeographyKey", how="left", validate="m:1")
        .merge(products.drop(columns=["Product ID"]), on="ProductKey", how="left", validate="m:1")
    )
    assert len(df) == len(orders), "join changed the row count"
    for col in ["Segment", "Region", "Category"]:
        assert df[col].notna().all(), f"unmatched dimension keys in {col}"

    df = df.drop(columns=["GeographyKey", "ProductKey"])
    df[["Sales", "Profit"]] = df[["Sales", "Profit"]].round(4)   # remove float noise (e.g. 1044.6299999999999)
    for col in ["Order Date", "Ship Date"]:
        df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
    out = DATA_DIR / "superstore_orders.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out.relative_to(ROOT)}  {df.shape}")


def export_covid() -> None:
    model = PBIXRay(str(PBIX_DIR / "nigeria-covid19-dashboard.pbix"))
    df = model.get_table("Covid")
    out = DATA_DIR / "nigeria_covid19_by_state.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out.relative_to(ROOT)}  {df.shape}")


if __name__ == "__main__":
    export_sales()
    export_covid()
