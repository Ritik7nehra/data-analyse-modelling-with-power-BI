"""Collect every number the executive deck shows, straight from the pipeline marts and the DCF module.

    python reports/deck/build_deck_data.py     # writes build/deck_data.json

The deck script (build_deck.js) only formats these values, so nothing on a slide is typed in by hand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from superstore_pipeline import valuation as val  # noqa: E402

MARTS = ROOT / "reports" / "marts"
OUT = ROOT / "build" / "deck_data.json"


def main() -> None:
    kpi = pd.read_csv(MARTS / "mart_executive_kpis.csv")
    years = kpi[kpi["period"] != "All years"].copy()
    total = kpi[kpi["period"] == "All years"].iloc[0]
    flat = pd.read_csv(MARTS / "mart_sales_flat.csv", usecols=["category", "sales", "profit", "month_number", "year"])
    cat = flat.groupby("category").agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
    cat["margin"] = cat["profit"] / cat["sales"]
    cat["sales_share"] = cat["sales"] / cat["sales"].sum()
    cat["profit_share"] = cat["profit"] / cat["profit"].sum()
    prod = pd.read_csv(MARTS / "mart_product_profitability.csv")
    losers = prod[prod["profit"] < 0].sort_values("profit")[["sub_category", "profit"]]
    disc = pd.read_csv(MARTS / "mart_discount_impact.csv")
    deep = disc[disc["discount_band"].isin(["2. 21-40%", "3. Over 40%"])]
    wi = pd.read_csv(MARTS / "mart_discount_what_if.csv")
    rfm = pd.read_csv(MARTS / "mart_customer_rfm.csv")
    seg = rfm.groupby("rfm_segment").agg(customers=("customer_id", "count"), sales=("monetary", "sum")).reset_index()
    seg = seg.sort_values("sales", ascending=False)
    base_rev = float(flat.loc[flat["year"] == int(years["period"].iloc[-1]), "sales"].sum())
    scen = {name: val.value(base_rev, s) for name, s in val.SCENARIOS.items()}
    nd = flat.assign(nd=flat["month_number"].isin([11, 12]))
    nov_dec = float(nd[nd["nd"]]["sales"].sum() / nd["sales"].sum())

    data = {
        "kpi": {k: float(total[k]) for k in ("sales", "profit", "margin", "orders", "customers")},
        "years": years[["period", "sales", "profit", "margin"]].to_dict("records"),
        "growth_total": float(years["sales"].iloc[-1] / years["sales"].iloc[0] - 1),
        "dip_2015": float(years["sales"].iloc[1] / years["sales"].iloc[0] - 1),
        "category": cat.to_dict("records"),
        "losing_subcats": losers.to_dict("records"),
        "discount": disc.to_dict("records"),
        "deep_line_share": float(deep["share_of_lines"].sum()),
        "deep_loss_share": float(deep["share_of_all_losses"].sum()),
        "deep_lines": int(deep["order_lines"].sum()),
        "deep_baseline_profit": float(deep["profit"].sum()),
        "loss_lines_total": float(disc["total_losses"].sum()),
        "what_if": wi[wi["volume_retention"].isin([1.0, 0.6, 0.0])][
            ["discount_cap", "volume_retention", "affected_lines", "baseline_profit_affected", "profit_delta"]
        ].to_dict("records"),
        "rfm": seg.to_dict("records"),
        "rfm_total_customers": int(seg["customers"].sum()),
        "rfm_total_sales": float(seg["sales"].sum()),
        "valuation": {
            "wacc": scen["Base"].wacc, "terminal_growth": scen["Base"].terminal_growth,
            "ev": {k: v.enterprise_value for k, v in scen.items()},
            "tv_share": scen["Base"].tv_share, "exit_multiple": scen["Base"].implied_exit_multiple,
        },
        "nov_dec_share": nov_dec,
        "control": {"rows": 9994, "sales": 2297200.86, "profit": 286397.02},
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, default=float))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
