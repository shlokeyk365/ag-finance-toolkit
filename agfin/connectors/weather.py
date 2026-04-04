"""NASA POWER weather connector.

This module provides a thin wrapper around the NASA POWER monthly/annual point
API for historical weather summaries at a specific latitude/longitude.

The connector exposes annual precipitation and temperature summaries through a
small, documented public API. It hides the less intuitive details of the NASA
response format, including the annual aggregate key convention used by the
monthly/annual endpoint.

Phase 3 contract notes:
- use ``requests`` for HTTP calls
- keep connector logic thin and focused on transport + parsing
- return normalized Python data structures rather than raw payloads
- raise ``ValueError`` when a successful response does not contain usable data
- use simple module-local in-memory caching to avoid duplicate requests during
  a single Python session

The public API for this module will eventually expose:
- ``get_weather_history(...)`` returning a normalized pandas ``DataFrame``
- ``get_precipitation_series(...)`` returning a precipitation ``Series``
- ``get_temperature_series(...)`` returning a temperature ``Series``

Units:
- ``PRECTOTCORR`` is returned by NASA POWER in millimeters per day in the
  tested metric response mode
- ``T2M`` is returned in degrees Celsius in the tested metric response mode

Error behavior:
- invalid year ranges raise ``ValueError``
- successful responses without usable weather data raise ``ValueError``
- network and HTTP failures are allowed to surface through ``requests``
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import requests

BASE_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
"""NASA POWER monthly/annual point endpoint used for historical weather summaries."""

_CACHE: dict[tuple, object] = {}
"""Simple in-memory cache keyed by request identity.

Cache entries are intentionally module-local and session-scoped. This keeps the
implementation lightweight while preventing redundant API calls when the same
weather query is requested multiple times in one Python process.
"""


def _request_weather_json(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    """Fetch NASA POWER monthly/annual weather data as JSON.

    The request is intentionally narrow and predictable:
    - one point location identified by ``lat`` and ``lon``
    - one inclusive year range from ``start_year`` to ``end_year``
    - the two Phase 3 parameters required by the project contract:
      precipitation (``PRECTOTCORR``) and temperature at 2m (``T2M``)

    NASA POWER serves annual summaries through its monthly/annual endpoint. In
    the JSON payload, annual aggregate values are represented with keys such as
    ``202013`` rather than plain ``2020``. The parser helper below extracts one
    annual value per requested year from that response shape.

    Results are cached in-memory so repeated calls with the same inputs do not
    issue another network request during the current Python session.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        start_year: First year in the inclusive request window.
        end_year: Last year in the inclusive request window.

    Returns:
        Parsed JSON payload from the NASA POWER API.

    Raises:
        requests.RequestException: If the HTTP request fails, times out, or the
            API returns a non-success status code.
        ValueError: If the response body is not valid JSON.
    """
    cache_key = ("weather_json", lat, lon, start_year, end_year)
    if cache_key in _CACHE:
        return _CACHE[cache_key]  # type: ignore[return-value]

    params = {
        "parameters": "PRECTOTCORR,T2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_year,
        "end": end_year,
        "format": "JSON",
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("NASA POWER returned a non-JSON response.") from exc

    _CACHE[cache_key] = payload
    return payload


def _extract_annual_parameter_values(
    parameter_values: dict[str, Any],
    parameter_name: str,
) -> dict[int, float]:
    """Extract annual aggregate values from one NASA POWER parameter series.

    The monthly/annual API encodes annual aggregate values using a ``13``
    suffix, for example ``202013`` for the annual value associated with 2020.
    This helper normalizes that representation into a simpler ``{year: value}``
    mapping for downstream parsing.

    For resilience in tests and future payload variations, plain four-digit
    year keys are also accepted and treated as already-normalized annual data.

    Args:
        parameter_values: Raw yearly/monthly mapping for one NASA parameter.
        parameter_name: Human-readable parameter name used in error messages.

    Returns:
        A mapping from calendar year to annual aggregate value.

    Raises:
        ValueError: If an annual value is present but cannot be converted to a
            float.
    """
    annual_values: dict[int, float] = {}

    for raw_key, raw_value in parameter_values.items():
        year_key = str(raw_key)

        if len(year_key) == 4 and year_key.isdigit():
            normalized_year = int(year_key)
        elif len(year_key) == 6 and year_key[:4].isdigit() and year_key.endswith("13"):
            normalized_year = int(year_key[:4])
        else:
            continue

        if raw_value is None:
            continue

        try:
            annual_values[normalized_year] = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"NASA POWER response contains a non-numeric {parameter_name} value "
                f"for year {normalized_year}."
            ) from exc

    return annual_values


def _parse_weather_payload(payload: dict[str, Any]) -> list[dict[str, float | int]]:
    """Normalize a NASA POWER payload into per-year weather rows.

    The NASA POWER response nests parameter values inside
    ``properties -> parameter``. This helper extracts the two required Phase 3
    series and converts them into a simple list of yearly records that later
    public functions can turn into pandas objects.

    Each returned row uses a stable schema:
    - ``year``: observation year
    - ``precipitation``: annual NASA POWER value from ``PRECTOTCORR``
    - ``temperature``: annual NASA POWER value from ``T2M``

    Args:
        payload: Parsed NASA POWER JSON response.

    Returns:
        A list of normalized annual weather records.

    Raises:
        ValueError: If the expected parameter blocks are missing, if the two
            parameter series do not line up by year, or if no usable annual
            records can be extracted.
    """
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("NASA POWER response is missing the 'properties' block.")

    parameter_block = properties.get("parameter")
    if not isinstance(parameter_block, dict):
        raise ValueError("NASA POWER response is missing the 'parameter' block.")

    precipitation_data = parameter_block.get("PRECTOTCORR")
    temperature_data = parameter_block.get("T2M")

    if not isinstance(precipitation_data, dict):
        raise ValueError("NASA POWER response is missing 'PRECTOTCORR' data.")
    if not isinstance(temperature_data, dict):
        raise ValueError("NASA POWER response is missing 'T2M' data.")

    precipitation_by_year = _extract_annual_parameter_values(
        precipitation_data,
        parameter_name="precipitation",
    )
    temperature_by_year = _extract_annual_parameter_values(
        temperature_data,
        parameter_name="temperature",
    )

    years = sorted(set(precipitation_by_year) & set(temperature_by_year))
    if not years:
        raise ValueError("NASA POWER response did not contain overlapping annual data.")

    rows: list[dict[str, float | int]] = []
    for year in years:
        row = {
            "year": year,
            "precipitation": precipitation_by_year[year],
            "temperature": temperature_by_year[year],
        }

        rows.append(row)

    if not rows:
        raise ValueError("NASA POWER response did not contain any usable annual records.")

    return rows


def get_weather_history(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """Return annual precipitation and temperature history for one location.

    This is the primary public entry point for the NASA POWER connector. It
    validates the requested year range, fetches the raw API payload, normalizes
    the response into a tabular structure, and returns a tidy pandas
    ``DataFrame`` that higher-level code can use directly.

    The returned frame uses a stable schema:
    - ``year``: calendar year of the observation
    - ``precipitation``: annual NASA POWER value from ``PRECTOTCORR``. In the
      tested metric response mode this is reported in ``mm/day``.
    - ``temperature``: annual NASA POWER value from ``T2M``. In the tested
      metric response mode this is reported in degrees Celsius.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        start_year: First year in the inclusive request window.
        end_year: Last year in the inclusive request window.

    Returns:
        A pandas ``DataFrame`` with one annual row per year and three
        normalized columns: ``year``, ``precipitation``, and ``temperature``.

    Raises:
        ValueError: If the year range is invalid or if NASA POWER returns a
            successful response without the required usable weather data.
        requests.RequestException: If the underlying HTTP request fails.
    """
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year.")

    payload = _request_weather_json(
        lat=lat,
        lon=lon,
        start_year=start_year,
        end_year=end_year,
    )
    rows = _parse_weather_payload(payload)

    weather_history = pd.DataFrame(rows, columns=["year", "precipitation", "temperature"])
    if weather_history.empty:
        raise ValueError("NASA POWER response did not produce any weather history rows.")

    return weather_history


def get_precipitation_series(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
) -> pd.Series:
    """Return annual precipitation as a labeled pandas Series.

    This is a thin convenience wrapper around ``get_weather_history(...)``. It
    reuses the normalized weather table and extracts only the precipitation
    column while preserving year alignment for downstream analysis.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        start_year: First year in the inclusive request window.
        end_year: Last year in the inclusive request window.

    Returns:
        A pandas ``Series`` named ``precipitation`` with one value per year.
        The Series index is the corresponding calendar year. In the tested
        metric response mode, values are reported in ``mm/day``.

    Raises:
        ValueError: If the year range is invalid or if NASA POWER returns a
            successful response without usable precipitation data.
        requests.RequestException: If the underlying HTTP request fails.
    """
    weather_history = get_weather_history(
        lat=lat,
        lon=lon,
        start_year=start_year,
        end_year=end_year,
    )
    precipitation = weather_history.set_index("year")["precipitation"]
    precipitation.name = "precipitation"
    return precipitation


def get_temperature_series(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
) -> pd.Series:
    """Return annual average temperature as a labeled pandas Series.

    This is a thin convenience wrapper around ``get_weather_history(...)``. It
    reuses the normalized weather table and extracts only the temperature
    column while preserving year alignment for downstream analysis.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        start_year: First year in the inclusive request window.
        end_year: Last year in the inclusive request window.

    Returns:
        A pandas ``Series`` named ``temperature`` with one value per year. The
        Series index is the corresponding calendar year. In the tested metric
        response mode, values are reported in degrees Celsius.

    Raises:
        ValueError: If the year range is invalid or if NASA POWER returns a
            successful response without usable temperature data.
        requests.RequestException: If the underlying HTTP request fails.
    """
    weather_history = get_weather_history(
        lat=lat,
        lon=lon,
        start_year=start_year,
        end_year=end_year,
    )
    temperature = weather_history.set_index("year")["temperature"]
    temperature.name = "temperature"
    return temperature
