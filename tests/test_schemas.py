import pytest
from pydantic import ValidationError

from agfin.schemas import CropMixItem, FarmInputs, RiskResults


def make_valid_farm_inputs(**overrides) -> FarmInputs:
    payload = {
        "total_acres": 500.0,
        "crop_mix": [
            CropMixItem(
                crop="Corn",
                acres=300.0,
                expected_yield=190.0,
                expected_price=4.8,
            ),
            CropMixItem(
                crop="Soybeans",
                acres=200.0,
                expected_yield=55.0,
                expected_price=12.0,
            ),
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


def test_valid_farm_inputs_parse_correctly() -> None:
    farm = make_valid_farm_inputs()

    assert farm.total_acres == 500.0
    assert len(farm.crop_mix) == 2
    assert farm.net_worth == 900_000.0


def test_negative_acres_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CropMixItem(
            crop="Corn",
            acres=-10.0,
            expected_yield=190.0,
            expected_price=4.8,
        )


def test_crop_mix_cannot_exceed_total_acres() -> None:
    with pytest.raises(ValidationError):
        make_valid_farm_inputs(
            total_acres=400.0,
            crop_mix=[
                CropMixItem(
                    crop="Corn",
                    acres=300.0,
                    expected_yield=190.0,
                    expected_price=4.8,
                ),
                CropMixItem(
                    crop="Soybeans",
                    acres=200.0,
                    expected_yield=55.0,
                    expected_price=12.0,
                ),
            ],
        )


def test_net_worth_must_match_assets_minus_liabilities() -> None:
    with pytest.raises(ValidationError):
        make_valid_farm_inputs(net_worth=850_000.0)


def test_working_capital_cannot_imply_negative_current_assets() -> None:
    with pytest.raises(ValidationError):
        make_valid_farm_inputs(working_capital=-50_000.0, current_liabilities=40_000.0)


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        FarmInputs(
            **make_valid_farm_inputs().model_dump(),
            current_assets=140_000.0,
        )


def test_risk_results_require_ordered_income_percentiles() -> None:
    with pytest.raises(ValidationError):
        RiskResults(
            mean_income=80_000.0,
            p10_income=100_000.0,
            p50_income=90_000.0,
            p90_income=120_000.0,
            mean_dscr=1.25,
            p10_dscr=0.95,
            default_probability=0.18,
            worst_case_shortfall=35_000.0,
            simulation_runs=10_000,
        )


def test_risk_results_validate_probability_bounds() -> None:
    with pytest.raises(ValidationError):
        RiskResults(
            mean_income=80_000.0,
            p10_income=50_000.0,
            p50_income=80_000.0,
            p90_income=120_000.0,
            mean_dscr=1.25,
            p10_dscr=0.95,
            default_probability=1.2,
            worst_case_shortfall=35_000.0,
            simulation_runs=10_000,
        )
