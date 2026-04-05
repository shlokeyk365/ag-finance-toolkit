"""USDA NASS Quick Stats connector.

This module provides a narrow, explicit wrapper around the USDA NASS Quick
Stats API for annual state-level crop yield and price lookups.

The initial implementation intentionally supports a small normalized crop
vocabulary so the package can offer reliable, testable behavior before trying
to generalize across the full Quick Stats surface area.
"""

from __future__ import annotations

import os
from functools import lru_cache

import requests

BASE_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
DEFAULT_TIMEOUT_SECONDS = 10
API_KEY_ENV_VAR = "USDA_NASS_API_KEY"

_CROP_ALIASES = {
    "corn": "corn",
    "soybean": "soybeans",
    "soybeans": "soybeans",
}

_CROP_QUERY_CONFIG = {
    "corn": {
        "commodity_desc": "CORN",
        "yield_unit_desc": "BU / ACRE",
        "price_unit_desc": "$ / BU",
        "yield_extra_params": {
            "util_practice_desc": "GRAIN",
            "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        },
        "price_extra_params": {
            "util_practice_desc": "GRAIN",
        },
    },
    "soybeans": {
        "commodity_desc": "SOYBEANS",
        "yield_unit_desc": "BU / ACRE",
        "price_unit_desc": "$ / BU",
        "yield_extra_params": {
            "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        },
        "price_extra_params": {},
    },
}

_STAT_KIND_CONFIG = {
    "yield": {
        "statisticcat_desc": "YIELD",
        "unit_key": "yield_unit_desc",
        "reference_period_desc": "YEAR",
        "extra_params_key": "yield_extra_params",
    },
    "price": {
        "statisticcat_desc": "PRICE RECEIVED",
        "unit_key": "price_unit_desc",
        "reference_period_desc": "MARKETING YEAR",
        "extra_params_key": "price_extra_params",
    },
}


class NassError(Exception):
    """Base exception for USDA NASS connector failures."""


class NassConfigurationError(NassError):
    """Raised when USDA NASS credentials are missing."""


class NassNoDataError(NassError):
    """Raised when a query succeeds but no usable data is returned."""


class NassResponseError(NassError):
    """Raised when the USDA NASS response is malformed or ambiguous."""


def _get_api_key(api_key: str | None = None) -> str:
    """Resolve the USDA NASS API key from an argument or environment."""
    resolved_key = api_key or os.getenv(API_KEY_ENV_VAR)
    if resolved_key:
        return resolved_key

    raise NassConfigurationError(
        f"USDA NASS API key is required. Set {API_KEY_ENV_VAR} before using this connector."
    )


def _normalize_crop(crop: str) -> str:
    """Normalize a crop name to the connector's supported vocabulary."""
    normalized = crop.strip().lower()
    try:
        return _CROP_ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_CROP_QUERY_CONFIG))
        raise ValueError(
            f"Unsupported crop {crop!r}. Supported crops: {supported}."
        ) from exc


def _normalize_state(state: str) -> str:
    """Normalize and validate a two-letter state code."""
    normalized = state.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("state must be a two-letter alphabetic state code")

    return normalized


def _validate_year(year: int) -> int:
    """Validate a numeric year input."""
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError("year must be an integer")
    if year <= 0:
        raise ValueError("year must be positive")

    return year


def _build_query_params(crop_key: str, state: str, year: int, stat_kind: str) -> dict[str, str]:
    """Build a USDA NASS query for one crop, state, year, and statistic kind."""
    crop_config = _CROP_QUERY_CONFIG[crop_key]
    stat_config = _STAT_KIND_CONFIG[stat_kind]

    return {
        "commodity_desc": crop_config["commodity_desc"],
        "state_alpha": state,
        "year": str(year),
        "agg_level_desc": "STATE",
        "freq_desc": "ANNUAL",
        "reference_period_desc": stat_config["reference_period_desc"],
        "domain_desc": "TOTAL",
        "statisticcat_desc": stat_config["statisticcat_desc"],
        "unit_desc": crop_config[stat_config["unit_key"]],
        **crop_config[stat_config["extra_params_key"]],
    }


def _api_get(params: dict[str, str], api_key: str) -> list[dict[str, str]]:
    """Issue a USDA NASS request and return the raw record list."""
    request_params = {
        **params,
        "key": api_key,
        "format": "JSON",
    }

    try:
        response = requests.get(
            BASE_URL,
            params=request_params,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise NassResponseError("USDA NASS request failed") from exc
    except ValueError as exc:
        raise NassResponseError("USDA NASS returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise NassResponseError("USDA NASS response body must be a JSON object")

    if "error" in payload:
        raise NassResponseError(f"USDA NASS API error: {payload['error']}")

    records = payload.get("data")
    if not isinstance(records, list):
        raise NassResponseError("USDA NASS response did not include a valid data list")

    return records


def _parse_numeric_value(raw_value: str) -> float:
    """Parse the numeric USDA NASS ``Value`` field into a float."""
    cleaned = raw_value.strip()
    if not cleaned:
        raise NassNoDataError("USDA NASS returned an empty Value field")

    normalized = cleaned.replace(",", "")
    try:
        return float(normalized)
    except ValueError as exc:
        raise NassNoDataError(
            f"USDA NASS returned a non-numeric Value field: {raw_value!r}"
        ) from exc


def _select_single_record(records: list[dict[str, str]], *, context: str) -> dict[str, str]:
    """Select a single record or raise a domain-specific error."""
    if not records:
        raise NassNoDataError(f"No USDA NASS data found for {context}")

    candidates = records
    for field, expected_value in (
        ("agg_level_desc", "STATE"),
        ("freq_desc", "ANNUAL"),
        ("domain_desc", "TOTAL"),
    ):
        filtered = [
            record
            for record in candidates
            if str(record.get(field, "")).strip().upper() == expected_value
        ]
        if filtered:
            candidates = filtered

    if len(candidates) != 1:
        raise NassResponseError(
            f"Ambiguous USDA NASS response for {context}: expected 1 record, got {len(candidates)}."
        )

    return candidates[0]


@lru_cache(maxsize=128)
def _lookup_stat_value(
    crop_key: str,
    state: str,
    year: int,
    stat_kind: str,
    api_key: str,
) -> float:
    """Fetch and cache one numeric statistic from USDA NASS."""
    params = _build_query_params(crop_key, state, year, stat_kind)
    records = _api_get(params, api_key=api_key)
    record = _select_single_record(
        records,
        context=f"{crop_key} {stat_kind} in {state} for {year}",
    )

    try:
        raw_value = record["Value"]
    except KeyError as exc:
        raise NassResponseError("USDA NASS record did not include a Value field") from exc

    return _parse_numeric_value(raw_value)


def get_crop_yield(crop: str, state: str, year: int) -> float:
    """Return annual state-level crop yield from USDA NASS Quick Stats."""
    crop_key = _normalize_crop(crop)
    state_code = _normalize_state(state)
    year_value = _validate_year(year)
    api_key = _get_api_key()

    return _lookup_stat_value(crop_key, state_code, year_value, "yield", api_key)


def get_crop_price(crop: str, state: str, year: int) -> float:
    """Return annual state-level crop price received from USDA NASS."""
    crop_key = _normalize_crop(crop)
    state_code = _normalize_state(state)
    year_value = _validate_year(year)
    api_key = _get_api_key()

    return _lookup_stat_value(crop_key, state_code, year_value, "price", api_key)


def get_production_data(crop: str, state: str, year: int) -> dict[str, object]:
    """Return a combined crop production snapshot for one state-year."""
    crop_key = _normalize_crop(crop)
    state_code = _normalize_state(state)
    year_value = _validate_year(year)

    crop_yield = get_crop_yield(crop_key, state_code, year_value)
    crop_price = get_crop_price(crop_key, state_code, year_value)
    crop_config = _CROP_QUERY_CONFIG[crop_key]

    return {
        "crop": crop_key,
        "state": state_code,
        "year": year_value,
        "yield": crop_yield,
        "price": crop_price,
        "revenue_per_acre": crop_yield * crop_price,
        "yield_unit": crop_config["yield_unit_desc"],
        "price_unit": crop_config["price_unit_desc"],
    }


__all__ = [
    "API_KEY_ENV_VAR",
    "BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "NassConfigurationError",
    "NassError",
    "NassNoDataError",
    "NassResponseError",
    "get_crop_price",
    "get_crop_yield",
    "get_production_data",
]
