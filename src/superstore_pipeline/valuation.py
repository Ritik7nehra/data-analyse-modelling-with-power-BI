"""Illustrative discounted-cash-flow (DCF) valuation of the Superstore business.

This module is the single source of the default assumptions and the independent Python implementation that the
Excel model (``excel/finance/Superstore_DCF_Valuation.xlsx``) is cross-checked against in the test-suite.

IMPORTANT - what this is and is not
    * The dataset holds order-line sales and profit, not financial statements. "Profit" is used as an EBIT proxy.
      There is no balance sheet, so net debt defaults to zero and the result is an enterprise value for
      the sales business, not an investment recommendation.
    * Forecast drivers, the tax rate, capex/D&A/working-capital ratios and the cost-of-capital inputs are
      ILLUSTRATIVE placeholders chosen to demonstrate the mechanics. They are not sourced market data.
      Replace them before drawing any conclusion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FORECAST_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022)


@dataclass(frozen=True)
class Scenario:
    name: str
    growth: tuple[float, ...]          # revenue growth per forecast year
    ebit_margin: tuple[float, ...]     # EBIT proxy margin per forecast year


@dataclass(frozen=True)
class Assumptions:
    tax_rate: float = 0.25
    da_pct_sales: float = 0.02
    capex_pct_sales: float = 0.025
    nwc_pct_delta_sales: float = 0.10   # investment in working capital as a share of the change in sales
    risk_free: float = 0.0425
    equity_risk_premium: float = 0.05
    beta: float = 1.10
    pre_tax_cost_of_debt: float = 0.06
    debt_weight: float = 0.20           # D / (D + E)
    terminal_growth: float = 0.025
    net_debt: float = 0.0
    wacc_step: float = 0.01
    growth_step: float = 0.005


# Historical margin 2014-2017 was 10.2% - 12.7% (see Historicals sheet); Base holds the recent level.
SCENARIOS: dict[str, Scenario] = {
    "Base": Scenario("Base", (0.12, 0.10, 0.08, 0.06, 0.05), (0.125,) * 5),
    "Bull": Scenario("Bull", (0.16, 0.14, 0.12, 0.10, 0.08), (0.135, 0.14, 0.14, 0.14, 0.14)),
    "Bear": Scenario("Bear", (0.06, 0.04, 0.03, 0.03, 0.02), (0.11, 0.10, 0.09, 0.09, 0.09)),
}


@dataclass(frozen=True)
class YearCashFlow:
    year: int
    period: int
    revenue: float
    ebit: float
    taxes: float          # negative
    nopat: float
    da: float             # add-back, positive
    capex: float          # negative
    d_nwc: float          # negative when sales grow
    fcf: float


@dataclass(frozen=True)
class Valuation:
    scenario: str
    wacc: float
    terminal_growth: float
    flows: tuple[YearCashFlow, ...] = field(repr=False)
    pv_fcf: float = 0.0
    terminal_value: float = 0.0
    pv_terminal_value: float = 0.0
    enterprise_value: float = 0.0
    equity_value: float = 0.0

    @property
    def tv_share(self) -> float:
        return self.pv_terminal_value / self.enterprise_value

    @property
    def implied_exit_multiple(self) -> float:
        """Terminal value / final-year EBITDA (EBIT + D&A)."""
        last = self.flows[-1]
        return self.terminal_value / (last.ebit + last.da)


def wacc(a: Assumptions) -> float:
    cost_of_equity = a.risk_free + a.beta * a.equity_risk_premium
    after_tax_debt = a.pre_tax_cost_of_debt * (1 - a.tax_rate)
    return (1 - a.debt_weight) * cost_of_equity + a.debt_weight * after_tax_debt


def project(base_revenue: float, scenario: Scenario, a: Assumptions) -> tuple[YearCashFlow, ...]:
    flows: list[YearCashFlow] = []
    prev = base_revenue
    for i, year in enumerate(FORECAST_YEARS):
        revenue = prev * (1 + scenario.growth[i])
        ebit = revenue * scenario.ebit_margin[i]
        taxes = -ebit * a.tax_rate
        nopat = ebit + taxes
        da = revenue * a.da_pct_sales
        capex = -revenue * a.capex_pct_sales
        d_nwc = -(revenue - prev) * a.nwc_pct_delta_sales
        flows.append(YearCashFlow(year, i + 1, revenue, ebit, taxes, nopat, da, capex, d_nwc,
                                  nopat + da + capex + d_nwc))
        prev = revenue
    return tuple(flows)


def enterprise_value(
    fcfs: list[float] | tuple[float, ...], rate: float, growth: float
) -> tuple[float, float, float, float]:
    """Return (pv_fcf, terminal_value, pv_terminal_value, enterprise_value). End-of-year discounting."""
    if rate <= growth:
        raise ValueError(f"discount rate {rate:.4f} must exceed terminal growth {growth:.4f}")
    n = len(fcfs)
    pv_fcf = sum(f / (1 + rate) ** t for t, f in enumerate(fcfs, start=1))
    tv = fcfs[-1] * (1 + growth) / (rate - growth)
    pv_tv = tv / (1 + rate) ** n
    return pv_fcf, tv, pv_tv, pv_fcf + pv_tv


def value(base_revenue: float, scenario: Scenario, a: Assumptions | None = None, *, rate: float | None = None,
          growth: float | None = None) -> Valuation:
    a = a or Assumptions()
    rate = wacc(a) if rate is None else rate
    growth = a.terminal_growth if growth is None else growth
    flows = project(base_revenue, scenario, a)
    pv_fcf, tv, pv_tv, ev = enterprise_value([f.fcf for f in flows], rate, growth)
    return Valuation(scenario.name, rate, growth, flows, pv_fcf, tv, pv_tv, ev, ev - a.net_debt)


def sensitivity(base_revenue: float, scenario: Scenario, a: Assumptions | None = None, size: int = 5):
    """Enterprise value over a WACC x terminal-growth grid centred on the base case.

    Returns (wacc_axis, growth_axis, grid) where grid[i][j] corresponds to wacc_axis[i], growth_axis[j].
    """
    a = a or Assumptions()
    half = size // 2
    base_rate = wacc(a)
    waccs = [base_rate + (i - half) * a.wacc_step for i in range(size)]
    growths = [a.terminal_growth + (j - half) * a.growth_step for j in range(size)]
    flows = project(base_revenue, scenario, a)
    fcfs = [f.fcf for f in flows]
    grid = [[enterprise_value(fcfs, w, g)[3] for g in growths] for w in waccs]
    return waccs, growths, grid
