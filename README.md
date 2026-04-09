# ag-finance-toolkit

`ag-finance-toolkit` is a lightweight Python package for agricultural
financial modeling. It combines validated farm input schemas, core ag-finance
metrics, public data connectors, and Monte Carlo risk simulation in a single
package that is easy to inspect, test, and extend.

## What This Is

The toolkit is meant to be a credible public artifact for agricultural finance
work, not just a notebook dump. It focuses on a few clear building blocks:

- validated farm financial inputs with Pydantic
- finance-pure metric calculations for liquidity, solvency, profitability, and repayment
- thin connectors to USDA NASS Quick Stats and NASA POWER
- vectorized Monte Carlo simulation for income and DSCR risk

## Current Status

Implemented today:

- `agfin.schemas` for canonical farm input and output models
- `agfin.metrics` including `calculate_all(...)`
- `agfin.connectors.nass` for annual crop yield and price lookups
- `agfin.connectors.weather` for annual precipitation and temperature history
- `agfin.risk.simulate_farm_risk(...)` for vectorized Monte Carlo risk summaries
- automated test coverage across schemas, metrics, connectors, and risk

Also included:

- a polished end-to-end walkthrough notebook in `examples/farm_risk_demo.ipynb`

## Install

Clone the repository and install it in editable mode:

```bash
pip install -e .
```

For local development tools:

```bash
pip install -e ".[dev]"
```

For notebook and plotting dependencies:

```bash
pip install -e ".[examples]"
```

## Quick Start

```python
from agfin import calculate_all, simulate_farm_risk
from agfin.schemas import CropMixItem, FarmInputs

farm = FarmInputs(
    total_acres=500.0,
    crop_mix=[
        CropMixItem(crop="Corn", acres=300.0, expected_yield=190.0, expected_price=4.8),
        CropMixItem(crop="Soybeans", acres=200.0, expected_yield=55.0, expected_price=12.0),
    ],
    operating_costs=250_000.0,
    fixed_costs=80_000.0,
    debt_obligations=60_000.0,
    working_capital=100_000.0,
    current_liabilities=40_000.0,
    total_assets=1_500_000.0,
    total_liabilities=600_000.0,
    net_worth=900_000.0,
    insurance_income=5_000.0,
    govt_payments=10_000.0,
    interest_expense=25_000.0,
    depreciation=45_000.0,
    owner_draws=30_000.0,
)

metrics = calculate_all(farm)
risk = simulate_farm_risk(farm, runs=10_000, seed=42)

print(metrics.net_farm_income)
print(metrics.dscr)
print(risk.p10_income)
print(risk.default_probability)
```

## Modules

### `agfin.schemas`

Pydantic v2 models for:

- `CropMixItem`
- `FarmInputs`
- `MetricResults`
- `RiskResults`

These models enforce core structural rules such as crop acreage totals and net
worth consistency.

### `agfin.metrics`

Finance-pure helper functions plus the schema-aware `calculate_all(...)`
integration entrypoint. The current metric surface includes:

- working capital
- current ratio
- debt-to-asset ratio
- equity ratio
- net farm income
- operating margin
- operating expense ratio
- DSCR

### `agfin.connectors`

Public-data access for external agricultural inputs:

- USDA NASS Quick Stats for annual state-level crop yield and price data
- NASA POWER for annual precipitation and temperature history at a point

Connector behavior is intentionally strict:

- invalid inputs raise `ValueError`
- missing usable data raises a connector-specific exception or `ValueError`
- HTTP/network failures surface through `requests`
- repeated identical requests reuse in-memory caching within a session

### `agfin.risk`

Monte Carlo simulation built around multiplicative shocks to:

- yield
- price
- operating costs

The public entrypoint is:

```python
from agfin.risk import simulate_farm_risk
```

It returns a `RiskResults` object with:

- mean income
- P10, P50, and P90 income
- mean DSCR
- P10 DSCR
- default probability, defined as `P(DSCR < 1.0)`
- worst-case debt-service shortfall

## Data Sources

### USDA NASS Quick Stats

The USDA connector currently supports normalized annual state-level lookups for:

- corn
- soybeans

Set a USDA API key before using the NASS connector:

```bash
export USDA_NASS_API_KEY="your-api-key"
```

Example:

```python
from agfin.connectors import get_crop_price, get_crop_yield, get_production_data

corn_yield = get_crop_yield("corn", "IA", 2022)
corn_price = get_crop_price("corn", "IA", 2022)
corn_snapshot = get_production_data("corn", "IA", 2022)
```

### NASA POWER

The weather connector does not require an API key.

```python
from agfin.connectors import get_weather_history

history = get_weather_history(
    lat=42.0308,
    lon=-93.6319,
    start_year=2020,
    end_year=2022,
)
```

`get_weather_history(...)` returns a pandas `DataFrame` with `year`,
`precipitation`, and `temperature` columns. The helper functions
`get_precipitation_series(...)` and `get_temperature_series(...)` return
year-indexed pandas `Series`.

## Testing

Run the full test suite with:

```bash
pytest -q
```

The current suite covers:

- schema validation behavior
- metric formulas and denominator edge cases
- USDA NASS connector normalization and failure handling
- NASA POWER response parsing and output shaping
- Monte Carlo reproducibility, percentile ordering, and default-risk behavior

## Contributing

Contributions are welcome. Small focused improvements are especially helpful:

- README and docs polish
- broader connector coverage
- richer simulation assumptions
- example notebook improvements

## License

MIT
