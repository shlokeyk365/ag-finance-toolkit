"""Repayment metric calculations.

This module contains finance-pure helper functions for evaluating repayment
capacity. The helpers here use the simplified project-level debt service
coverage ratio formula and leave schema translation or presentation-specific
interpretation to higher layers.

Policy decisions:
- ``dscr`` is defined using the project's simplified formula for cash
  available for debt service.
- If ``debt_service == 0``, ``dscr`` raises ``ValueError`` rather than return
  a sentinel value. This keeps denominator-based repayment metrics strict and
  explicit.
"""


def dscr(
    net_income: float,
    depreciation: float,
    interest: float,
    owner_draws: float,
    debt_service: float,
) -> float:
    """Calculate debt service coverage ratio using the project formula.

    The simplified cash-available formula for this project is:

    ``net_income + depreciation + interest - owner_draws``

    DSCR is then calculated as cash available divided by annual debt service.

    Args:
        net_income: Net farm income under the project's simplified model.
        depreciation: Annual depreciation expense.
        interest: Annual interest expense.
        owner_draws: Owner withdrawals that reduce cash available for debt
            service.
        debt_service: Annual debt obligations.

    Returns:
        The debt service coverage ratio.

    Raises:
        ValueError: If debt_service is zero, since the ratio would be
            undefined.

    Notes:
        This helper keeps the core repayment math layer strict. Special-case
        interpretation of zero debt service should be handled by the caller
        rather than converted into a placeholder value such as infinity.
    """
    if debt_service == 0:
        raise ValueError("debt_service must be non-zero")

    cash_available = net_income + depreciation + interest - owner_draws
    return cash_available / debt_service
