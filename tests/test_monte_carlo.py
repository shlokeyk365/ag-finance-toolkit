"""Tests for Monte Carlo risk simulation."""

import pytest

from agfin.risk import simulate_farm_risk
from agfin.schemas import CropMixItem, FarmInputs, RiskResults


def make_sample_farm(**overrides) -> FarmInputs:
    payload = {
        "total_acres": 500.0,
        "crop_mix": [
            CropMixItem(crop="Corn", acres=300.0, expected_yield=190.0, expected_price=4.8),
            CropMixItem(crop="Soybeans", acres=200.0, expected_yield=55.0, expected_price=12.0),
        ],
        "operating_costs": 250_000.0,
        "fixed_costs": 80_000.0,
        "debt_obligations": 60_000.0,
        "working_capital": 100_000.0,
        "current_liabilities": 40_000.0,
        "total_assets": 1_500_000.0,
        "total_liabilities": 600_000.0,
        "net_worth": 900_000.0,
        "insurance_income": 5_000.0,
        "govt_payments": 10_000.0,
        "interest_expense": 25_000.0,
        "depreciation": 45_000.0,
        "owner_draws": 30_000.0,
    }
    payload.update(overrides)
    return FarmInputs(**payload)


def test_simulate_farm_risk_returns_summary_object() -> None:
    farm = make_sample_farm()

    results = simulate_farm_risk(farm, seed=7)

    assert isinstance(results, RiskResults)
    assert results.simulation_runs == 10_000
    assert results.p10_income <= results.p50_income <= results.p90_income
    assert 0.0 <= results.default_probability <= 1.0
    assert results.worst_case_shortfall >= 0.0


def test_simulate_farm_risk_is_reproducible_with_seed() -> None:
    farm = make_sample_farm()

    first = simulate_farm_risk(farm, runs=2_000, seed=123)
    second = simulate_farm_risk(farm, runs=2_000, seed=123)

    assert first == second


def test_simulate_farm_risk_zero_variation_matches_deterministic_case() -> None:
    farm = make_sample_farm()

    results = simulate_farm_risk(
        farm,
        yield_cv=0.0,
        price_cv=0.0,
        cost_cv=0.0,
        runs=500,
        seed=1,
    )

    expected_income = 90_600.0
    expected_cash_available = expected_income + 45_000.0 + 25_000.0 - 30_000.0
    expected_dscr = expected_cash_available / 60_000.0

    assert results.mean_income == pytest.approx(expected_income)
    assert results.p10_income == pytest.approx(expected_income)
    assert results.p50_income == pytest.approx(expected_income)
    assert results.p90_income == pytest.approx(expected_income)
    assert results.mean_dscr == pytest.approx(expected_dscr)
    assert results.p10_dscr == pytest.approx(expected_dscr)
    assert results.default_probability == 0.0
    assert results.worst_case_shortfall == 0.0


def test_simulate_farm_risk_can_capture_default_risk() -> None:
    farm = make_sample_farm(
        debt_obligations=260_000.0,
        fixed_costs=140_000.0,
        owner_draws=50_000.0,
    )

    results = simulate_farm_risk(farm, runs=4_000, seed=99)

    assert 0.0 < results.default_probability < 1.0
    assert results.worst_case_shortfall > 0.0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"runs": 0}, "runs must be positive"),
        ({"yield_cv": -0.1}, "yield_cv must be non-negative"),
        ({"price_cv": -0.1}, "price_cv must be non-negative"),
        ({"cost_cv": -0.1}, "cost_cv must be non-negative"),
    ],
)
def test_simulate_farm_risk_rejects_invalid_parameters(kwargs: dict, message: str) -> None:
    farm = make_sample_farm()

    with pytest.raises(ValueError, match=message):
        simulate_farm_risk(farm, **kwargs)


def test_simulate_farm_risk_requires_non_zero_debt_service() -> None:
    farm = make_sample_farm(debt_obligations=0.0)

    with pytest.raises(ValueError, match=r"farm\.debt_obligations must be non-zero"):
        simulate_farm_risk(farm)
