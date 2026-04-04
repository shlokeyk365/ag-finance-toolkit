"""Tests for financial metric calculations.

These tests document the intended behavior of the finance-pure metric helper
functions. They are meant to serve both as regression coverage and as a clear
statement of the business rules we have chosen for the toolkit.
"""

import pytest

from agfin.metrics import calculate_all
from agfin.metrics.liquidity import current_ratio, working_capital
from agfin.metrics.profitability import (
    gross_revenue,
    net_farm_income,
    operating_expense_ratio,
    operating_margin,
)
from agfin.metrics.repayment import dscr
from agfin.metrics.solvency import debt_to_asset, equity_ratio
from agfin.schemas import CropMixItem, FarmInputs, MetricResults


def make_sample_farm() -> dict:
    """Build a reusable validated farm payload for metric integration tests."""
    return {
        "total_acres": 150.0,
        "crop_mix": [
            CropMixItem(crop="Corn", acres=100.0, expected_yield=180.0, expected_price=5.0),
            CropMixItem(crop="Soybeans", acres=50.0, expected_yield=60.0, expected_price=12.0),
        ],
        "operating_costs": 70_000.0,
        "fixed_costs": 20_000.0,
        "debt_obligations": 20_000.0,
        "working_capital": 60_000.0,
        "current_liabilities": 40_000.0,
        "total_assets": 500_000.0,
        "total_liabilities": 200_000.0,
        "net_worth": 300_000.0,
        "insurance_income": 5_000.0,
        "govt_payments": 4_000.0,
        "interest_expense": 5_000.0,
        "depreciation": 10_000.0,
        "owner_draws": 15_000.0,
    }


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


def test_gross_revenue_sums_expected_crop_sales() -> None:
    """Gross revenue should sum acreage, yield, and price across crops.

    This case documents the core revenue formula used throughout the
    profitability module.
    """
    crop_mix = [
        CropMixItem(crop="Corn", acres=100.0, expected_yield=180.0, expected_price=5.0),
        CropMixItem(crop="Soybeans", acres=50.0, expected_yield=60.0, expected_price=12.0),
    ]

    assert gross_revenue(crop_mix) == 126_000.0


def test_net_farm_income_uses_project_profitability_formula() -> None:
    """Net farm income should follow the simplified project definition.

    The project formula subtracts operating and fixed costs, then adds
    insurance income and government payments.
    """
    assert net_farm_income(
        gross_revenue=126_000.0,
        operating_costs=70_000.0,
        fixed_costs=20_000.0,
        insurance_income=5_000.0,
        govt_payments=4_000.0,
    ) == 45_000.0


def test_operating_margin_returns_profitability_share_of_revenue() -> None:
    """Operating margin should divide net farm income by gross revenue."""
    assert operating_margin(45_000.0, 126_000.0) == pytest.approx(0.3571428571)


def test_operating_expense_ratio_uses_operating_costs_only() -> None:
    """Operating expense ratio excludes fixed costs by project agreement.

    This test documents the shared contract decision that the ratio uses
    operating costs only, divided by gross revenue.
    """
    assert operating_expense_ratio(70_000.0, 126_000.0) == pytest.approx(0.5555555556)


def test_operating_margin_raises_for_zero_gross_revenue() -> None:
    """Operating margin is undefined when gross revenue is zero.

    The toolkit's policy is to raise ``ValueError`` rather than return a
    placeholder ratio for denominator-based profitability metrics.
    """
    with pytest.raises(ValueError, match="gross_revenue must be non-zero"):
        operating_margin(10_000.0, 0.0)


def test_operating_expense_ratio_raises_for_zero_gross_revenue() -> None:
    """Operating expense ratio is undefined when gross revenue is zero.

    This mirrors the operating-margin policy so profitability ratios handle
    zero denominators consistently.
    """
    with pytest.raises(ValueError, match="gross_revenue must be non-zero"):
        operating_expense_ratio(10_000.0, 0.0)


def test_dscr_returns_standard_repayment_coverage_ratio() -> None:
    """DSCR should divide available cash by annual debt service.

    This test documents the project's simplified cash-available formula:
    net income plus depreciation and interest, minus owner draws.
    """
    assert dscr(
        net_income=45_000.0,
        depreciation=10_000.0,
        interest=5_000.0,
        owner_draws=15_000.0,
        debt_service=20_000.0,
    ) == pytest.approx(2.25)


def test_dscr_raises_for_zero_debt_service() -> None:
    """DSCR is undefined when annual debt service is zero.

    The toolkit's policy is to raise ``ValueError`` for undefined denominator-
    based repayment metrics rather than return a placeholder value.
    """
    with pytest.raises(ValueError, match="debt_service must be non-zero"):
        dscr(
            net_income=45_000.0,
            depreciation=10_000.0,
            interest=5_000.0,
            owner_draws=15_000.0,
            debt_service=0.0,
        )


def test_calculate_all_returns_metric_results_for_valid_farm() -> None:
    """calculate_all should return a fully populated MetricResults object.

    This test verifies that the integration layer correctly bridges the Phase 1
    ``FarmInputs`` schema to the finance-pure Phase 2 helper functions.
    """
    farm = FarmInputs(**make_sample_farm())

    results = calculate_all(farm)

    assert isinstance(results, MetricResults)
    assert results.working_capital == 60_000.0
    assert results.current_ratio == 2.5
    assert results.debt_to_asset == 0.4
    assert results.equity_ratio == 0.6
    assert results.net_farm_income == 45_000.0
    assert results.operating_margin == pytest.approx(0.3571428571)
    assert results.operating_expense_ratio == pytest.approx(0.5555555556)
    assert results.dscr == pytest.approx(2.25)


def test_calculate_all_uses_option_a_current_assets_derivation() -> None:
    """calculate_all should derive current assets from schema fields.

    The project agreed on Option A: keep low-level metric helpers finance-pure
    and derive ``current_assets`` inside ``calculate_all()`` as:

    ``working_capital + current_liabilities``
    """
    farm = FarmInputs(**make_sample_farm())

    results = calculate_all(farm)

    assert results.working_capital == 60_000.0
    assert results.current_ratio == 2.5


def test_calculate_all_raises_when_current_liabilities_are_zero() -> None:
    """calculate_all should surface current-ratio denominator errors.

    This integration case verifies that Option A still respects the liquidity
    module's strict rule that current liabilities must be non-zero for
    ``current_ratio`` to be defined.
    """
    payload = make_sample_farm()
    payload["working_capital"] = 100_000.0
    payload["current_liabilities"] = 0.0
    farm = FarmInputs(**payload)

    with pytest.raises(ValueError, match="current_liabilities must be non-zero"):
        calculate_all(farm)


def test_calculate_all_raises_when_debt_obligations_are_zero() -> None:
    """calculate_all should surface DSCR denominator errors.

    This integration case verifies that the repayment module's strict zero-
    denominator policy propagates through the schema-aware integration layer.
    """
    payload = make_sample_farm()
    payload["debt_obligations"] = 0.0
    farm = FarmInputs(**payload)

    with pytest.raises(ValueError, match="debt_service must be non-zero"):
        calculate_all(farm)
