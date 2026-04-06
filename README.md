# ag-finance-toolkit

Python package for agricultural financial modeling.

## What This Is

This repository is a lightweight toolkit for agricultural finance analysis.
It is organized around validated farm input schemas, financial metrics, risk
modeling, and thin connectors to public agricultural and weather data sources.

## Install

```bash
pip install -e .
```

For development dependencies:

```bash
pip install -e ".[dev]"
```

## Current Modules

- `agfin.schemas`: validated farm input and output models
- `agfin.metrics`: liquidity, solvency, profitability, and repayment metrics
- `agfin.connectors`: external agricultural data connectors
- `agfin.risk`: Monte Carlo risk modeling work in progress

## NASA POWER Connector

The NASA POWER connector provides normalized annual precipitation and
temperature history for a specific latitude/longitude using the official
monthly/annual point API.

```python
from agfin.connectors import (
    get_precipitation_series,
    get_temperature_series,
    get_weather_history,
)

history = get_weather_history(
    lat=42.0308,
    lon=-93.6319,
    start_year=2020,
    end_year=2022,
)

precipitation = get_precipitation_series(
    lat=42.0308,
    lon=-93.6319,
    start_year=2020,
    end_year=2022,
)

temperature = get_temperature_series(
    lat=42.0308,
    lon=-93.6319,
    start_year=2020,
    end_year=2022,
)
```

`get_weather_history(...)` returns a pandas `DataFrame` with `year`,
`precipitation`, and `temperature` columns. The helper functions return
labeled pandas `Series` indexed by year.

Behavior to expect:
- invalid year ranges raise `ValueError`
- missing usable weather data raises `ValueError`
- HTTP and network failures surface through `requests`
- repeated identical requests in one Python session reuse a simple in-memory cache

The tested metric response mode returned:
- `precipitation` as `PRECTOTCORR` in `mm/day`
- `temperature` as `T2M` in degrees Celsius

## USDA NASS Quick Stats

The USDA NASS Quick Stats connector provides annual state-level crop yield and
price lookups for the initial supported crops:

- corn
- soybeans

### API Key Setup

Request a free USDA NASS Quick Stats API key from the USDA NASS Quick Stats
service, then set:

```bash
export USDA_NASS_API_KEY="your-api-key"
```

### Example

```python
from agfin.connectors import get_crop_price, get_crop_yield, get_production_data

corn_yield = get_crop_yield("corn", "IA", 2022)
corn_price = get_crop_price("corn", "IA", 2022)
corn_snapshot = get_production_data("corn", "IA", 2022)
```

`get_production_data(...)` returns a dictionary with:

- normalized crop, state, and year
- annual yield
- annual price
- revenue per acre
- yield and price units

This product uses the NASS API but is not endorsed or certified by NASS.
