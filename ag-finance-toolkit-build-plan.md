# ag-finance-toolkit — Detailed Build Plan

**Goal:** A clean, credible open-source Python package for agricultural financial modeling.
**Audience:** YC application reviewers, GitHub visitors, future recruiters/investors.
**Time budget:** 10–15 hours across two people.
**Repo:** New, standalone GitHub repo — `ag-finance-toolkit` (no Samsaras references).

---

## Phase 0 — Repo Setup (1 hour)

**Who:** Either person, takes ~1 hour total.

### Tasks
- [ ] Create new GitHub repo: `ag-finance-toolkit`
- [ ] Initialize with `.gitignore` (Python), `MIT LICENSE`, and a stub `README.md`
- [ ] Set up project structure (see below)
- [ ] Create `pyproject.toml` with package metadata
- [ ] Set up `requirements.txt` with initial dependencies: `requests`, `pandas`, `numpy`, `scipy`, `pydantic`
- [ ] Create initial `README.md` with project description, install instructions, and usage examples (can be placeholder until modules are done)

### Repo structure to scaffold
```
ag-finance-toolkit/
├── agfin/
│   ├── __init__.py
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── nass.py
│   │   └── weather.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── liquidity.py
│   │   ├── solvency.py
│   │   ├── profitability.py
│   │   └── repayment.py
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── monte_carlo.py
│   │   └── distributions.py
│   └── schemas/
│       ├── __init__.py
│       ├── farm_inputs.py
│       └── outputs.py
├── examples/
│   └── farm_risk_demo.ipynb
├── tests/
│   ├── test_metrics.py
│   ├── test_schemas.py
│   └── test_monte_carlo.py
├── pyproject.toml
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Phase 1 — Schemas (1–1.5 hours)

**Who:** Either person. Do this first — everything else depends on it.

### `agfin/schemas/farm_inputs.py`
Define the canonical input schema using **Pydantic v2**. This is the backbone of the whole package.

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict

class CropMixItem(BaseModel):
    crop: str
    acres: float
    expected_yield: float       # bushels/unit per acre
    expected_price: float       # $ per bushel/unit

class FarmInputs(BaseModel):
    total_acres: float
    crop_mix: list[CropMixItem]
    operating_costs: float      # total annual operating costs ($)
    fixed_costs: float          # depreciation, land payments, etc. ($)
    debt_obligations: float     # total annual debt service ($)
    working_capital: float      # current assets - current liabilities ($)
    current_liabilities: float
    total_assets: float
    total_liabilities: float
    net_worth: float
    insurance_income: float = 0.0
    govt_payments: float = 0.0
    interest_expense: float = 0.0
    depreciation: float = 0.0
    owner_draws: float = 0.0
```

### `agfin/schemas/outputs.py`
Define output schemas for metrics and risk results.

```python
class MetricResults(BaseModel):
    working_capital: float
    current_ratio: float
    debt_to_asset: float
    equity_ratio: float
    operating_margin: float
    net_farm_income: float
    dscr: float
    operating_expense_ratio: float

class RiskResults(BaseModel):
    mean_income: float
    p10_income: float
    p50_income: float
    p90_income: float
    mean_dscr: float
    p10_dscr: float
    default_probability: float   # P(DSCR < 1.0)
    worst_case_shortfall: float
    simulation_runs: int
```

**Done when:** Both schemas import cleanly, Pydantic validation works for valid and invalid inputs.

---

## Phase 2 — Financial Metrics Engine (2–3 hours)

**Who:** Split by module or pair together. Most intellectually interesting part.

### `agfin/metrics/liquidity.py`
```python
def working_capital(current_assets: float, current_liabilities: float) -> float:
    return current_assets - current_liabilities

def current_ratio(current_assets: float, current_liabilities: float) -> float:
    return current_assets / current_liabilities
```

### `agfin/metrics/solvency.py`
```python
def debt_to_asset(total_liabilities: float, total_assets: float) -> float:
    return total_liabilities / total_assets

def equity_ratio(net_worth: float, total_assets: float) -> float:
    return net_worth / total_assets
```

### `agfin/metrics/profitability.py`
```python
def gross_revenue(crop_mix: list) -> float:
    return sum(c.acres * c.expected_yield * c.expected_price for c in crop_mix)

def net_farm_income(gross_revenue, operating_costs, fixed_costs,
                    insurance_income=0, govt_payments=0) -> float:
    return gross_revenue - operating_costs - fixed_costs + insurance_income + govt_payments

def operating_margin(net_farm_income: float, gross_revenue: float) -> float:
    return net_farm_income / gross_revenue
```

### `agfin/metrics/repayment.py`
```python
def dscr(net_income: float, depreciation: float, interest: float,
         owner_draws: float, debt_service: float) -> float:
    cash_available = net_income + depreciation + interest - owner_draws
    return cash_available / debt_service
```

### `agfin/metrics/__init__.py`
Expose a single convenience function:
```python
def calculate_all(farm: FarmInputs) -> MetricResults:
    # runs all metrics and returns a MetricResults object
```

**Done when:** `calculate_all(farm)` returns a fully populated `MetricResults` from a valid `FarmInputs`.

---

## Phase 3 — Data Connectors (2–3 hours)

**Who:** One person takes this while the other does metrics, or do sequentially.

### `agfin/connectors/nass.py`
Wraps the USDA NASS Quick Stats API.

**Functions to implement:**
```python
def get_crop_yield(crop: str, state: str, year: int) -> float
def get_crop_price(crop: str, state: str, year: int) -> float
def get_production_data(crop: str, state: str, year: int) -> dict
```

**Implementation notes:**
- Base URL: `https://quickstats.nass.usda.gov/api/`
- Requires free API key from USDA (get one, document in README how to get one)
- Returns JSON; parse into clean float/dict outputs
- Add simple in-memory caching (a module-level dict) to avoid redundant API calls during a session
- Handle missing data gracefully (not all crop/state/year combos exist)

### `agfin/connectors/weather.py`
Wraps NASA POWER API (no API key required).

**Functions to implement:**
```python
def get_weather_history(lat: float, lon: float, start_year: int, end_year: int) -> pd.DataFrame
def get_precipitation_series(lat: float, lon: float, start_year: int, end_year: int) -> pd.Series
def get_temperature_series(lat: float, lon: float, start_year: int, end_year: int) -> pd.Series
```

**Implementation notes:**
- Base URL: `https://power.larc.nasa.gov/api/temporal/annual/point`
- Parameters: `PRECTOTCORR` (precipitation), `T2M` (temperature at 2m)
- Returns annual averages; return as a labeled pandas DataFrame
- No API key needed — straightforward GET requests

**Done when:** Both connectors return real data for a test call (e.g., Iowa corn yield 2022, central Iowa weather history).

---

## Phase 4 — Monte Carlo Risk Engine (2–3 hours)

**Who:** Whoever is more comfortable with numerical methods, or pair on this one.

### `agfin/risk/distributions.py`
Define the distributions used in simulation:
```python
from scipy import stats

def yield_distribution(mean: float, cv: float):
    """Truncated normal — yield can't go below zero."""
    std = mean * cv
    a = -mean / std  # lower bound in std units
    return stats.truncnorm(a=a, b=np.inf, loc=mean, scale=std)

def price_distribution(mean: float, cv: float):
    """Lognormal — prices are strictly positive and right-skewed."""
    sigma = np.sqrt(np.log(1 + cv**2))
    mu = np.log(mean) - sigma**2 / 2
    return stats.lognorm(s=sigma, scale=np.exp(mu))

def cost_distribution(mean: float, cv: float):
    """Normal — costs vary symmetrically around expected."""
    return stats.norm(loc=mean, scale=mean * cv)
```

### `agfin/risk/monte_carlo.py`
Main simulation function:
```python
def simulate_farm_risk(
    farm: FarmInputs,
    yield_cv: float = 0.12,
    price_cv: float = 0.15,
    cost_cv: float = 0.08,
    runs: int = 10_000,
    seed: int = None
) -> RiskResults:
```

**Implementation steps inside the function:**
1. Draw `runs` samples of yield multiplier, price multiplier, and cost multiplier from their respective distributions
2. For each run, compute: revenue, costs, net income, DSCR
3. All vectorized with numpy (no Python loop over runs — this keeps it fast)
4. Summarize: mean, P10/P50/P90 for income and DSCR, P(DSCR < 1.0), worst-case shortfall
5. Return a `RiskResults` object

**Done when:** `simulate_farm_risk(farm)` returns a `RiskResults` in under 2 seconds for 10k runs.

---

## Phase 5 — Tests (1–1.5 hours)

**Who:** Whoever finishes their module first starts writing tests.

Write pytest tests covering:

### `tests/test_metrics.py`
- DSCR calculation with known inputs/outputs
- Working capital edge cases (negative working capital)
- Operating margin with zero revenue (should raise or return sensible value)
- `calculate_all()` returns a complete `MetricResults`

### `tests/test_schemas.py`
- Valid `FarmInputs` parses correctly
- Invalid inputs (negative acres, missing fields) raise `ValidationError`

### `tests/test_monte_carlo.py`
- `simulate_farm_risk()` runs without error
- Output `p10_income < p50_income < p90_income`
- `default_probability` is between 0 and 1
- Results are reproducible with a fixed seed

**Done when:** `pytest` passes with no failures.

---

## Phase 6 — Example Notebook + README (1–1.5 hours)

**Who:** One person. This is the public face of the project.

### `examples/farm_risk_demo.ipynb`
Walk through a realistic end-to-end scenario:

1. **Define a sample farm** — Iowa corn/soy operation, 500 acres, realistic cost structure
2. **Pull real data** from NASS (historical corn yields/prices for Iowa)
3. **Compute financial metrics** — show DSCR, liquidity, solvency
4. **Run Monte Carlo** — plot income distribution and DSCR distribution (matplotlib)
5. **Interpret results** — what does a P10 DSCR of 0.8 actually mean for a lender?

The notebook should read like a short article, not just code. Add markdown cells explaining the agriculture-domain context.

### `README.md`
Sections:
- **What this is** (2–3 sentences)
- **Install** (`pip install agfin` or clone + `pip install -e .`)
- **Quick start** (20-line code example showing metrics + simulation)
- **Modules** (brief description of each)
- **Data sources** (NASS API key instructions, NASA POWER note)
- **Contributing** (simple, welcoming)
- **License** (MIT)

**Done when:** Someone with no context can clone the repo, follow the README, and run the notebook successfully.

---

## Division of Labor (Suggested)

| Person | Modules |
|--------|---------|
| You | Schemas + Metrics Engine + Tests |
| Cofounder | Data Connectors + Monte Carlo + Notebook |

Or swap connectors and metrics based on preference. The schemas should be done first by whoever starts first, since everything depends on them.

---

## Hour-by-Hour Estimate

| Phase | Hours |
|-------|-------|
| Repo setup | 1 |
| Schemas | 1 |
| Metrics engine | 2.5 |
| Data connectors | 2.5 |
| Monte Carlo | 2.5 |
| Tests | 1.5 |
| Notebook + README | 1.5 |
| **Total** | **~13 hours** |

Fits comfortably in the 10–15 hour budget with two people working in parallel on phases 2–4.

---

## Definition of Done

The repo is done when:
- `pytest` passes
- `examples/farm_risk_demo.ipynb` runs top-to-bottom without errors
- README has install instructions, a quick-start example, and links to data sources
- GitHub repo is public under MIT license
- No references to Samsaras, customer data, or proprietary logic anywhere in the repo

---

## What Makes This Look Good on a YC Application

- **Real domain depth** — agricultural finance metrics (DSCR, FSA definitions) signal you understand the space
- **Real external APIs** — NASS and NASA POWER are actual government data sources, not toy datasets
- **Monte Carlo modeling** — signals quantitative sophistication
- **Pydantic schemas** — signals production-quality thinking, not just scripts
- **Tests** — shows engineering discipline
- **Clean notebook** — shows you can communicate technical work clearly
