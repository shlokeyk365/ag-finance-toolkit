"""Liquidity metric calculations.

This module contains finance-pure helper functions for short-term liquidity
analysis. The functions here intentionally keep the math layer simple and
explicit so that schema translation and presentation-specific handling can live
elsewhere.

Policy decisions:
- ``working_capital`` is always defined as current assets minus current
  liabilities.
- ``current_ratio`` is defined as current assets divided by current
  liabilities.
- If ``current_liabilities == 0``, ``current_ratio`` raises ``ValueError``
  rather than returning a sentinel value such as infinity. This keeps the core
  metrics layer strict and predictable.
"""


def working_capital(current_assets: float, current_liabilities: float) -> float:
    """Calculate working capital as current assets minus current liabilities.

    Working capital is a dollar-based liquidity measure that represents the
    amount of short-term financial cushion available after covering current
    obligations.

    Args:
        current_assets: Total current assets.
        current_liabilities: Total current liabilities.

    Returns:
        The farm's working capital.

    Notes:
        This function does not validate whether the inputs are economically
        realistic. Negative values are allowed at the pure-math layer.
    """
    return current_assets - current_liabilities


def current_ratio(current_assets: float, current_liabilities: float) -> float:
    """Calculate the current ratio as current assets divided by liabilities.

    The current ratio is a standard liquidity metric used to assess whether a
    farm can cover its short-term obligations using short-term assets.

    Args:
        current_assets: Total current assets.
        current_liabilities: Total current liabilities.

    Returns:
        The farm's current ratio.

    Raises:
        ValueError: If current_liabilities is zero, since the ratio would be
            undefined.

    Notes:
        This function keeps the core math layer strict. Special-case
        interpretation of zero current liabilities should be handled by the
        caller rather than converted into a sentinel value such as infinity.
    """
    if current_liabilities == 0:
        raise ValueError("current_liabilities must be non-zero")

    return current_assets / current_liabilities
