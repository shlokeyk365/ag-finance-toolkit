from unittest.mock import Mock, patch

import pytest

from agfin.connectors import nass
from agfin.connectors.nass import (
    NassConfigurationError,
    NassNoDataError,
    NassResponseError,
    get_crop_price,
    get_crop_yield,
    get_production_data,
)


@pytest.fixture(autouse=True)
def clear_nass_caches() -> None:
    nass._lookup_stat_value.cache_clear()


def make_response(payload: dict) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_get_api_key_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("USDA_NASS_API_KEY", raising=False)

    with pytest.raises(NassConfigurationError, match="USDA_NASS_API_KEY"):
        nass._get_api_key()


def test_normalize_crop_rejects_unsupported_crop() -> None:
    with pytest.raises(ValueError, match="Unsupported crop"):
        nass._normalize_crop("wheat")


def test_normalize_state_rejects_malformed_state_code() -> None:
    with pytest.raises(ValueError, match="two-letter"):
        nass._normalize_state("Iowa")


def test_parse_numeric_value_removes_commas() -> None:
    assert nass._parse_numeric_value("1,234.5") == 1234.5


def test_parse_numeric_value_rejects_suppressed_values() -> None:
    with pytest.raises(NassNoDataError, match="non-numeric"):
        nass._parse_numeric_value("(D)")


def test_get_crop_yield_builds_expected_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USDA_NASS_API_KEY", "test-key")
    payload = {
        "data": [
            {
                "Value": "203.4",
                "agg_level_desc": "STATE",
                "freq_desc": "ANNUAL",
                "reference_period_desc": "YEAR",
                "domain_desc": "TOTAL",
            }
        ]
    }

    with patch("agfin.connectors.nass.requests.get", return_value=make_response(payload)) as mock_get:
        result = get_crop_yield("Corn", "ia", 2022)

    assert result == 203.4

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["key"] == "test-key"
    assert called_params["format"] == "JSON"
    assert called_params["commodity_desc"] == "CORN"
    assert called_params["state_alpha"] == "IA"
    assert called_params["year"] == "2022"
    assert called_params["agg_level_desc"] == "STATE"
    assert called_params["freq_desc"] == "ANNUAL"
    assert called_params["reference_period_desc"] == "YEAR"
    assert called_params["domain_desc"] == "TOTAL"
    assert called_params["statisticcat_desc"] == "YIELD"
    assert called_params["unit_desc"] == "BU / ACRE"
    assert called_params["util_practice_desc"] == "GRAIN"
    assert called_params["prodn_practice_desc"] == "ALL PRODUCTION PRACTICES"


def test_get_crop_price_builds_expected_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USDA_NASS_API_KEY", "test-key")
    payload = {
        "data": [
            {
                "Value": "4.75",
                "agg_level_desc": "STATE",
                "freq_desc": "ANNUAL",
                "reference_period_desc": "YEAR",
                "domain_desc": "TOTAL",
            }
        ]
    }

    with patch("agfin.connectors.nass.requests.get", return_value=make_response(payload)) as mock_get:
        result = get_crop_price("soybean", "il", 2022)

    assert result == 4.75

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["commodity_desc"] == "SOYBEANS"
    assert called_params["state_alpha"] == "IL"
    assert called_params["year"] == "2022"
    assert called_params["reference_period_desc"] == "MARKETING YEAR"
    assert called_params["statisticcat_desc"] == "PRICE RECEIVED"
    assert called_params["unit_desc"] == "$ / BU"


def test_get_crop_yield_raises_for_empty_result_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USDA_NASS_API_KEY", "test-key")

    with patch(
        "agfin.connectors.nass.requests.get",
        return_value=make_response({"data": []}),
    ):
        with pytest.raises(NassNoDataError, match="No USDA NASS data found"):
            get_crop_yield("corn", "IA", 2022)


def test_get_crop_yield_raises_for_ambiguous_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USDA_NASS_API_KEY", "test-key")
    payload = {
        "data": [
            {
                "Value": "200.0",
                "agg_level_desc": "STATE",
                "freq_desc": "ANNUAL",
                "reference_period_desc": "YEAR",
                "domain_desc": "TOTAL",
                "source_desc": "SURVEY",
            },
            {
                "Value": "201.0",
                "agg_level_desc": "STATE",
                "freq_desc": "ANNUAL",
                "reference_period_desc": "YEAR",
                "domain_desc": "TOTAL",
                "source_desc": "CENSUS",
            },
        ]
    }

    with patch("agfin.connectors.nass.requests.get", return_value=make_response(payload)):
        with pytest.raises(NassResponseError, match="Ambiguous USDA NASS response"):
            get_crop_yield("corn", "IA", 2022)


def test_get_production_data_combines_yield_and_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USDA_NASS_API_KEY", "test-key")
    responses = [
        make_response(
            {
                "data": [
                    {
                        "Value": "210.0",
                        "agg_level_desc": "STATE",
                        "freq_desc": "ANNUAL",
                        "reference_period_desc": "YEAR",
                        "domain_desc": "TOTAL",
                    }
                ]
            }
        ),
        make_response(
            {
                "data": [
                    {
                        "Value": "4.50",
                        "agg_level_desc": "STATE",
                        "freq_desc": "ANNUAL",
                        "reference_period_desc": "YEAR",
                        "domain_desc": "TOTAL",
                    }
                ]
            }
        ),
    ]

    with patch("agfin.connectors.nass.requests.get", side_effect=responses):
        result = get_production_data("corn", "IA", 2022)

    assert result == {
        "crop": "corn",
        "state": "IA",
        "year": 2022,
        "yield": 210.0,
        "price": 4.5,
        "revenue_per_acre": 945.0,
        "yield_unit": "BU / ACRE",
        "price_unit": "$ / BU",
    }


def test_lookup_stat_value_uses_in_memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USDA_NASS_API_KEY", "test-key")
    payload = {
        "data": [
            {
                "Value": "200.0",
                "agg_level_desc": "STATE",
                "freq_desc": "ANNUAL",
                "reference_period_desc": "YEAR",
                "domain_desc": "TOTAL",
            }
        ]
    }

    with patch("agfin.connectors.nass.requests.get", return_value=make_response(payload)) as mock_get:
        first = get_crop_yield("corn", "IA", 2022)
        second = get_crop_yield("corn", "IA", 2022)

    assert first == 200.0
    assert second == 200.0
    assert mock_get.call_count == 1
