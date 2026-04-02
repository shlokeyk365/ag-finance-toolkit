# AG Finance Toolkit: Phase 1 / Phase 2 Working Contract

## Purpose

This document defines the shared interface between Phase 1 (schemas) and Phase 2 (metrics engine) so both can be built in parallel and integrated cleanly later.

## High-Level Agreement

We are using **Option A**:

- Low-level metric functions stay finance-pure.
- `calculate_all(farm)` will derive any needed finance inputs from schema fields.

This means the individual metric functions should use standard financial formulas, while the schema-to-metric translation happens inside `calculate_all()`.

## Schema Contract

Phase 2 assumes Phase 1 will expose the following models and field names exactly.

### `CropMixItem`

```python
class CropMixItem(BaseModel):
    crop: str
    acres: float
    expected_yield: float
    expected_price: float
```

### `FarmInputs`

```python
class FarmInputs(BaseModel):
    total_acres: float
    crop_mix: list[CropMixItem]
    operating_costs: float
    fixed_costs: float
    debt_obligations: float
    working_capital: float
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

### `MetricResults`

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
```

## Derived Field Rule

Phase 2 will derive `current_assets` inside `calculate_all(farm)` using:

```python
current_assets = farm.working_capital + farm.current_liabilities
```

Because of this, Phase 1 does **not** need to add a `current_assets` field unless both people later agree to change the contract.

## Metric Function Contract

Phase 2 will implement these helper functions independently of Pydantic:

```python
working_capital(current_assets: float, current_liabilities: float) -> float
current_ratio(current_assets: float, current_liabilities: float) -> float
debt_to_asset(total_liabilities: float, total_assets: float) -> float
equity_ratio(net_worth: float, total_assets: float) -> float
gross_revenue(crop_mix: list) -> float
net_farm_income(
    gross_revenue: float,
    operating_costs: float,
    fixed_costs: float,
    insurance_income: float = 0.0,
    govt_payments: float = 0.0,
) -> float
operating_margin(net_farm_income: float, gross_revenue: float) -> float
dscr(
    net_income: float,
    depreciation: float,
    interest: float,
    owner_draws: float,
    debt_service: float,
) -> float
```

## Integration Contract for `calculate_all(farm)`

Phase 2 assumes:

- `farm.crop_mix` is iterable.
- Each item in `crop_mix` exposes:
  - `acres`
  - `expected_yield`
  - `expected_price`

`calculate_all(farm)` will:

1. derive `current_assets`
2. compute `gross_revenue`
3. compute `net_farm_income`
4. compute all remaining financial metrics
5. return a `MetricResults` object

## Naming Agreement

Please keep these field names exactly as written:

- `debt_obligations`
- `interest_expense`
- `owner_draws`
- `govt_payments`
- `net_worth`
- `current_liabilities`
- `crop_mix`

Phase 2 will wire directly against these names.

## Validation Assumptions

Phase 2 assumes Phase 1 will validate:

- required fields are present
- `crop_mix` items have numeric `acres`, `expected_yield`, and `expected_price`
- clearly invalid values like negative acres can be rejected if strict validation is desired

Phase 2 will separately handle mathematical edge cases such as divide-by-zero.

## Open Decision: Operating Expense Ratio

Both people should agree now whether `operating_expense_ratio` is:

```python
operating_costs / gross_revenue
```

or

```python
(operating_costs + fixed_costs) / gross_revenue
```

### Recommended choice

```python
operating_costs / gross_revenue
```

This is the cleaner and more standard interpretation of an operating expense ratio.

## Final Working Agreement

- Phase 1 builds the schemas above.
- Phase 2 builds finance-pure metric functions.
- `calculate_all(farm)` will be the integration layer.
- `current_assets` will be derived, not stored.
- Field names should stay stable to avoid rework during integration.
