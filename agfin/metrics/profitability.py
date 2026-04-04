"""Profitability metric calculations.

This module contains finance-pure helper functions for evaluating operating
performance and earnings capacity. The helpers here use canonical formulas and
leave schema translation or presentation-specific interpretation to higher
layers.

Policy decisions:
- ``gross_revenue`` is defined as the sum of expected crop revenue across the
  crop mix.
- ``net_farm_income`` is defined using the simplified project formula:
  gross revenue minus operating and fixed costs, plus insurance income and
  government payments.
- ``operating_margin`` is defined as net farm income divided by gross revenue.
- ``operating_expense_ratio`` is defined as operating costs divided by gross
  revenue.
- If ``gross_revenue == 0``, denominator-based profitability ratios raise
  ``ValueError`` rather than return a sentinel value. This keeps undefined
  ratios explicit and consistent with the rest of the metrics package.
"""


def gross_revenue(crop_mix: list) -> float:
    """Calculate gross crop revenue from the expected crop mix.

    Gross revenue is the top-line revenue estimate before deducting operating
    or fixed costs. Each crop contributes acreage multiplied by expected yield
    and expected price.

    Args:
        crop_mix: Iterable of crop entries exposing ``acres``,
            ``expected_yield``, and ``expected_price`` attributes.

    Returns:
        The total expected gross crop revenue.

    Notes:
        This helper assumes each crop item provides the required numeric
        attributes. Schema-level validation belongs in higher layers.
    """
    return sum(item.acres * item.expected_yield * item.expected_price for item in crop_mix)


def net_farm_income(
    gross_revenue: float,
    operating_costs: float,
    fixed_costs: float,
    insurance_income: float = 0.0,
    govt_payments: float = 0.0,
) -> float:
    """Calculate simplified net farm income for the project.

    This project uses a deliberately simple profitability definition:
    gross revenue minus operating costs and fixed costs, plus insurance income
    and government payments.

    Args:
        gross_revenue: Total expected gross revenue.
        operating_costs: Annual operating costs.
        fixed_costs: Annual fixed costs.
        insurance_income: Insurance proceeds included in annual income.
        govt_payments: Government support payments included in annual income.

    Returns:
        The simplified net farm income value.

    Notes:
        This is a project-level modeling simplification rather than a complete
        farm accounting statement.
    """
    return (
        gross_revenue
        - operating_costs
        - fixed_costs
        + insurance_income
        + govt_payments
    )


def operating_margin(net_farm_income: float, gross_revenue: float) -> float:
    """Calculate operating margin as net farm income divided by revenue.

    Operating margin measures what share of each revenue dollar remains after
    accounting for the modeled costs and support income in this project.

    Args:
        net_farm_income: Net farm income under the project's simplified model.
        gross_revenue: Total expected gross revenue.

    Returns:
        The operating margin ratio.

    Raises:
        ValueError: If gross_revenue is zero, since the ratio would be
            undefined.

    Notes:
        This helper keeps denominator-based profitability metrics strict.
        Special-case interpretation of zero revenue should be handled by the
        caller rather than converted into a placeholder value.
    """
    if gross_revenue == 0:
        raise ValueError("gross_revenue must be non-zero")

    return net_farm_income / gross_revenue


def operating_expense_ratio(operating_costs: float, gross_revenue: float) -> float:
    """Calculate operating expense ratio as operating costs over revenue.

    This project defines operating expense ratio using operating costs only,
    excluding fixed costs. That choice is part of the shared Phase 1 / Phase 2
    contract for the repository.

    Args:
        operating_costs: Annual operating costs.
        gross_revenue: Total expected gross revenue.

    Returns:
        The operating expense ratio.

    Raises:
        ValueError: If gross_revenue is zero, since the ratio would be
            undefined.

    Notes:
        This helper mirrors the zero-denominator policy used by
        ``operating_margin`` so profitability ratios behave consistently.
    """
    if gross_revenue == 0:
        raise ValueError("gross_revenue must be non-zero")

    return operating_costs / gross_revenue
