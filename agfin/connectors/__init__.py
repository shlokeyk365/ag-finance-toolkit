"""Data connector modules for external agricultural datasets.

This package exposes thin wrappers around external public data sources used by
the toolkit. Connector modules are intentionally focused on request handling,
response normalization, and clear error behavior.
"""

from agfin.connectors.nass import (
    NassConfigurationError,
    NassError,
    NassNoDataError,
    NassResponseError,
    get_crop_price,
    get_crop_yield,
    get_production_data,
)
from agfin.connectors.weather import (
    get_precipitation_series,
    get_temperature_series,
    get_weather_history,
)

__all__ = [
    "NassConfigurationError",
    "NassError",
    "NassNoDataError",
    "NassResponseError",
    "get_crop_price",
    "get_crop_yield",
    "get_production_data",
    "get_weather_history",
    "get_precipitation_series",
    "get_temperature_series",
]
