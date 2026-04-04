"""Tests for the NASA POWER weather connector.

These tests document the Phase 3 contract for the NASA POWER integration:
- public functions should return normalized pandas objects
- invalid year ranges should raise ``ValueError``
- malformed but successful API responses should raise clear ``ValueError``
- repeated identical requests should use the module-local cache
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from agfin.connectors import weather


class DummyResponse:
    """Minimal stand-in for ``requests.Response`` used in connector tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """Simulate a successful HTTP response."""

    def json(self) -> dict[str, Any]:
        """Return the predefined JSON payload."""
        return self._payload


def make_weather_payload() -> dict[str, Any]:
    """Build a representative NASA POWER payload for parser tests.

    This mirrors the live monthly/annual API shape, where annual aggregate
    values are exposed with a ``13`` suffix such as ``202013``.
    """
    return {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {
                    "202001": 1.1,
                    "202013": 30.5,
                    "202101": 0.9,
                    "202113": 28.25,
                    "202201": 1.3,
                    "202213": 31.75,
                },
                "T2M": {
                    "202001": -2.0,
                    "202013": 11.2,
                    "202101": -1.5,
                    "202113": 10.8,
                    "202201": -0.8,
                    "202213": 12.1,
                },
            }
        }
    }


@pytest.fixture(autouse=True)
def clear_weather_cache() -> None:
    """Reset the connector cache between tests for deterministic behavior."""
    weather._CACHE.clear()


def test_get_weather_history_returns_normalized_dataframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weather history should return one normalized row per year.

    This test documents the public DataFrame contract: the connector returns a
    tidy table with ``year``, ``precipitation``, and ``temperature`` columns.
    """

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        return DummyResponse(make_weather_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    history = weather.get_weather_history(
        lat=42.0,
        lon=-93.5,
        start_year=2020,
        end_year=2022,
    )

    assert isinstance(history, pd.DataFrame)
    assert list(history.columns) == ["year", "precipitation", "temperature"]
    assert history.to_dict(orient="records") == [
        {"year": 2020, "precipitation": 30.5, "temperature": 11.2},
        {"year": 2021, "precipitation": 28.25, "temperature": 10.8},
        {"year": 2022, "precipitation": 31.75, "temperature": 12.1},
    ]


def test_get_precipitation_series_returns_labeled_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Precipitation helper should preserve year alignment and naming."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        return DummyResponse(make_weather_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    precipitation = weather.get_precipitation_series(
        lat=42.0,
        lon=-93.5,
        start_year=2020,
        end_year=2022,
    )

    assert isinstance(precipitation, pd.Series)
    assert precipitation.name == "precipitation"
    assert precipitation.index.tolist() == [2020, 2021, 2022]
    assert precipitation.tolist() == [30.5, 28.25, 31.75]


def test_get_temperature_series_returns_labeled_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Temperature helper should preserve year alignment and naming."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        return DummyResponse(make_weather_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    temperature = weather.get_temperature_series(
        lat=42.0,
        lon=-93.5,
        start_year=2020,
        end_year=2022,
    )

    assert isinstance(temperature, pd.Series)
    assert temperature.name == "temperature"
    assert temperature.index.tolist() == [2020, 2021, 2022]
    assert temperature.tolist() == [11.2, 10.8, 12.1]


def test_get_weather_history_raises_for_invalid_year_range() -> None:
    """The connector should reject year ranges where start_year is after end_year."""
    with pytest.raises(ValueError, match="start_year must be less than or equal to end_year"):
        weather.get_weather_history(
            lat=42.0,
            lon=-93.5,
            start_year=2023,
            end_year=2022,
        )


def test_get_weather_history_raises_when_parameter_block_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful responses without a parameter block should fail clearly."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        return DummyResponse({"properties": {}})

    monkeypatch.setattr(weather.requests, "get", fake_get)

    with pytest.raises(ValueError, match="missing the 'parameter' block"):
        weather.get_weather_history(
            lat=42.0,
            lon=-93.5,
            start_year=2020,
            end_year=2022,
        )


def test_get_weather_history_raises_when_precipitation_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful responses must include the precipitation parameter block."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        payload = make_weather_payload()
        del payload["properties"]["parameter"]["PRECTOTCORR"]
        return DummyResponse(payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)

    with pytest.raises(ValueError, match="missing 'PRECTOTCORR' data"):
        weather.get_weather_history(
            lat=42.0,
            lon=-93.5,
            start_year=2020,
            end_year=2022,
        )


def test_get_weather_history_raises_when_temperature_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful responses must include the temperature parameter block."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        payload = make_weather_payload()
        del payload["properties"]["parameter"]["T2M"]
        return DummyResponse(payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)

    with pytest.raises(ValueError, match="missing 'T2M' data"):
        weather.get_weather_history(
            lat=42.0,
            lon=-93.5,
            start_year=2020,
            end_year=2022,
        )


def test_get_weather_history_raises_when_years_do_not_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The connector should reject payloads without overlapping annual data."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        return DummyResponse(
            {
                "properties": {
                    "parameter": {
                        "PRECTOTCORR": {"202013": 30.5},
                        "T2M": {"202113": 10.8},
                    }
                }
            }
        )

    monkeypatch.setattr(weather.requests, "get", fake_get)

    with pytest.raises(ValueError, match="overlapping annual data"):
        weather.get_weather_history(
            lat=42.0,
            lon=-93.5,
            start_year=2020,
            end_year=2022,
        )


def test_get_weather_history_raises_when_values_are_not_numeric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-numeric parameter values should fail during normalization."""

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        payload = make_weather_payload()
        payload["properties"]["parameter"]["T2M"]["202113"] = "not-a-number"
        return DummyResponse(payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)

    with pytest.raises(ValueError, match="non-numeric temperature value for year 2021"):
        weather.get_weather_history(
            lat=42.0,
            lon=-93.5,
            start_year=2020,
            end_year=2022,
        )


def test_request_helper_uses_module_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated identical requests should reuse the cached payload.

    This test documents the lightweight in-memory caching contract for the
    connector so repeated helper calls do not trigger duplicate HTTP requests.
    """
    call_count = 0

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        nonlocal call_count
        call_count += 1
        return DummyResponse(make_weather_payload())

    monkeypatch.setattr(weather.requests, "get", fake_get)

    first = weather._request_weather_json(
        lat=42.0,
        lon=-93.5,
        start_year=2020,
        end_year=2022,
    )
    second = weather._request_weather_json(
        lat=42.0,
        lon=-93.5,
        start_year=2020,
        end_year=2022,
    )

    assert call_count == 1
    assert first == second
