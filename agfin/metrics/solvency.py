"""Solvency metric calculations.

This module contains finance-pure helper functions for evaluating overall
balance-sheet strength. These helpers intentionally focus on canonical
financial formulas and leave schema translation or presentation-specific
interpretation to higher layers.

Policy decisions:
- ``debt_to_asset`` is defined as total liabilities divided by total assets.
- ``equity_ratio`` is defined as net worth divided by total assets.
- If ``total_assets == 0``, both functions raise ``ValueError`` rather than
  return a sentinel value. This keeps undefined balance-sheet ratios explicit.
"""


def debt_to_asset(total_liabilities: float, total_assets: float) -> float:
    """Calculate the debt-to-asset ratio.

    The debt-to-asset ratio measures what share of the farm's asset base is
    financed by debt. Higher values generally indicate greater leverage and
    less balance-sheet flexibility.

    Args:
        total_liabilities: Total farm liabilities.
        total_assets: Total farm assets.

    Returns:
        The debt-to-asset ratio.

    Raises:
        ValueError: If total_assets is zero, since the ratio would be
            undefined.

    Notes:
        This function does not try to validate whether the inputs describe a
        realistic balance sheet. Negative values are allowed at the pure-math
        layer so that higher-level validation can remain separate.
    """
    if total_assets == 0:
        raise ValueError("total_assets must be non-zero")

    return total_liabilities / total_assets


def equity_ratio(net_worth: float, total_assets: float) -> float:
    """Calculate the equity ratio as net worth divided by total assets.

    The equity ratio measures what share of the farm's asset base is financed
    by owner equity rather than debt. Higher values generally indicate a
    stronger ownership position.

    Args:
        net_worth: Total farm net worth.
        total_assets: Total farm assets.

    Returns:
        The equity ratio.

    Raises:
        ValueError: If total_assets is zero, since the ratio would be
            undefined.

    Notes:
        This function keeps the core solvency math layer strict. Undefined
        ratios should be handled explicitly by the caller rather than converted
        into special placeholder values.
    """
    if total_assets == 0:
        raise ValueError("total_assets must be non-zero")

    return net_worth / total_assets
