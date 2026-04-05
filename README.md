# ag-finance-toolkit

Python package for agricultural financial modeling.

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
