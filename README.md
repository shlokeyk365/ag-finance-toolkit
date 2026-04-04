# ag-finance-toolkit

Python package for agricultural financial modeling.

## What This Is

This repository is a lightweight toolkit for agricultural finance analysis.
It is organized around validated farm input schemas, financial metrics, risk
modeling, and thin connectors to public agricultural and weather data sources.

The NASA POWER connector is part of Phase 3 and provides normalized annual
weather summaries that can feed later financial or risk workflows.

## NASA POWER Connector Example

The Phase 3 NASA POWER connector provides normalized annual precipitation and
temperature history for a specific latitude/longitude.

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

print(history)

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
`precipitation`, and `temperature` columns. The two helper functions return
labeled pandas `Series` indexed by year.

## NASA POWER Notes

The connector currently requests `PRECTOTCORR` and `T2M` from the official
NASA POWER monthly/annual point API and normalizes the annual aggregate values
into one row per year.

Behavior to expect:
- invalid year ranges raise `ValueError`
- missing usable weather data raises `ValueError`
- HTTP and network failures surface through `requests`
- repeated identical requests in one Python session reuse a simple in-memory cache

The tested metric response mode returned:
- `precipitation` as `PRECTOTCORR` in `mm/day`
- `temperature` as `T2M` in degrees Celsius
