"""Tests for financial metric calculations.

These tests document the intended behavior of the finance-pure metric helper
functions. They are meant to serve both as regression coverage and as a clear
statement of the business rules we have chosen for the toolkit.
"""

import pytest

from agfin.metrics.liquidity import current_ratio, working_capital
from agfin.metrics.solvency import debt_to_asset, equity_ratio


def test_working_capital_returns_positive_liquidity_buffer() -> None:
    """Working capital should equal current assets minus liabilities.

    This case documents the standard scenario where current assets exceed
    current liabilities and the farm has a positive short-term liquidity
    cushion.
    """
    assert working_capital(100.0, 40.0) == 60.0


def test_working_capital_allows_negative_result() -> None:
    """Working capital may be negative when liabilities exceed assets.

    The pure function should not reject this case, because negative working
    capital is a meaningful financial outcome rather than an invalid input.
    """
    assert working_capital(40.0, 100.0) == -60.0


def test_current_ratio_returns_standard_liquidity_ratio() -> None:
    """Current ratio should divide current assets by current liabilities."""
    assert current_ratio(100.0, 50.0) == 2.0


def test_current_ratio_raises_for_zero_current_liabilities() -> None:
    """Current ratio is undefined when current liabilities are zero.

    The toolkit's policy is to raise ``ValueError`` rather than return a
    sentinel value such as infinity. This keeps the core math layer strict and
    makes the special-case interpretation the caller's responsibility.
    """
    with pytest.raises(ValueError, match="current_liabilities must be non-zero"):
        current_ratio(100.0, 0.0)


def test_debt_to_asset_returns_standard_leverage_ratio() -> None:
    """Debt-to-asset should measure liabilities as a share of assets.

    This case documents the standard solvency interpretation where a farm with
    40 of liabilities and 100 of assets has a leverage ratio of 0.4.
    """
    assert debt_to_asset(40.0, 100.0) == 0.4


def test_equity_ratio_returns_standard_equity_share() -> None:
    """Equity ratio should measure net worth as a share of assets.

    This case documents the standard solvency interpretation where a farm with
    60 of net worth and 100 of assets has an equity ratio of 0.6.
    """
    assert equity_ratio(60.0, 100.0) == 0.6


def test_debt_to_asset_raises_for_zero_total_assets() -> None:
    """Debt-to-asset is undefined when total assets are zero.

    The toolkit's policy is to raise ``ValueError`` for undefined denominator-
    based solvency ratios rather than return a placeholder value.
    """
    with pytest.raises(ValueError, match="total_assets must be non-zero"):
        debt_to_asset(40.0, 0.0)


def test_equity_ratio_raises_for_zero_total_assets() -> None:
    """Equity ratio is undefined when total assets are zero.

    This mirrors the debt-to-asset policy so the solvency module handles zero
    denominators consistently across its finance-pure helper functions.
    """
    with pytest.raises(ValueError, match="total_assets must be non-zero"):
        equity_ratio(60.0, 0.0)
