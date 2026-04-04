"""Financial metrics package entry points.

This module provides the integration layer between the Phase 1 schemas and the
finance-pure helper functions implemented across the metrics submodules.
"""

from agfin.metrics.liquidity import current_ratio, working_capital
from agfin.metrics.profitability import (
    gross_revenue,
    net_farm_income,
    operating_expense_ratio,
    operating_margin,
)
from agfin.metrics.repayment import dscr
from agfin.metrics.solvency import debt_to_asset, equity_ratio
from agfin.schemas import FarmInputs, MetricResults


def calculate_all(farm: FarmInputs) -> MetricResults:
    """Calculate all core financial metrics for a validated farm input.

    This function is the schema-aware integration layer for Phase 2. It keeps
    the underlying metric helpers finance-pure while handling the few derived
    values needed to translate ``FarmInputs`` into ``MetricResults``.

    In particular, this function applies the team's agreed Option A policy:
    ``current_assets`` is derived from schema fields rather than stored
    directly.

    Args:
        farm: Validated farm financial inputs.

    Returns:
        A populated ``MetricResults`` object containing liquidity, solvency,
        profitability, and repayment metrics.
    """
    current_assets = farm.working_capital + farm.current_liabilities
    total_gross_revenue = gross_revenue(farm.crop_mix)
    total_net_farm_income = net_farm_income(
        gross_revenue=total_gross_revenue,
        operating_costs=farm.operating_costs,
        fixed_costs=farm.fixed_costs,
        insurance_income=farm.insurance_income,
        govt_payments=farm.govt_payments,
    )

    return MetricResults(
        working_capital=working_capital(current_assets, farm.current_liabilities),
        current_ratio=current_ratio(current_assets, farm.current_liabilities),
        debt_to_asset=debt_to_asset(farm.total_liabilities, farm.total_assets),
        equity_ratio=equity_ratio(farm.net_worth, farm.total_assets),
        operating_margin=operating_margin(total_net_farm_income, total_gross_revenue),
        net_farm_income=total_net_farm_income,
        dscr=dscr(
            net_income=total_net_farm_income,
            depreciation=farm.depreciation,
            interest=farm.interest_expense,
            owner_draws=farm.owner_draws,
            debt_service=farm.debt_obligations,
        ),
        operating_expense_ratio=operating_expense_ratio(
            farm.operating_costs,
            total_gross_revenue,
        ),
    )


__all__ = [
    "calculate_all",
    "current_ratio",
    "debt_to_asset",
    "dscr",
    "equity_ratio",
    "gross_revenue",
    "net_farm_income",
    "operating_expense_ratio",
    "operating_margin",
    "working_capital",
]
