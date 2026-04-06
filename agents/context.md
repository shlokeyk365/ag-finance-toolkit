# ag-finance-toolkit Agent Context

## Project Summary

`ag-finance-toolkit` is intended to become a clean, credible open-source Python package for agricultural financial modeling.

Primary audience:

- Ag-finance researchers
- GitHub visitors
- future recruiters and investors

The package is meant to demonstrate domain depth in agricultural finance, production-quality software structure, and quantitative capability through financial metrics, external data connectors, and Monte Carlo risk modeling.

## Canonical Planning Docs

Read these first when starting substantive work:

1. `ag-finance-toolkit-build-plan.md`
2. `phase-1-phase-2-contract.md`
3. `usda-nass-quick-stats-implementation-plan.md`

## Current Repository State

As of 2026-04-05, the repository is partially implemented.

What exists:

- package structure under `agfin/`
- implemented schema models in `agfin/schemas/`
- implemented metrics helpers plus `calculate_all()` in `agfin/metrics/`
- executable schema and metrics tests in `tests/test_schemas.py` and `tests/test_metrics.py`
- packaging metadata in `pyproject.toml`
- dependencies declared for runtime, tests, and examples

What is still mostly placeholder:

- `agfin/connectors/nass.py`
- `agfin/connectors/weather.py`
- most of `agfin/risk/`
- `tests/test_monte_carlo.py`
- the root `README.md` is still minimal and not aligned with the implemented package

Important local note:

- the worktree contains an untracked `.superset/` directory; treat it as unrelated unless a task explicitly involves it

## Target Architecture

### `agfin.schemas`

Owns the canonical Pydantic v2 models:

- `CropMixItem`
- `FarmInputs`
- `MetricResults`
- `RiskResults`

### `agfin.metrics`

Owns finance-pure helper functions:

- liquidity metrics
- solvency metrics
- profitability metrics
- repayment metrics

Also owns `calculate_all(farm)` as the integration entrypoint.

### `agfin.connectors`

Owns external data access:

- USDA NASS Quick Stats connector
- NASA POWER weather connector

### `agfin.risk`

Owns simulation logic:

- probability distribution helpers
- vectorized Monte Carlo simulation

### `tests`

Should validate:

- schema validation behavior
- edge cases in metrics
- reproducibility and ordering properties for Monte Carlo outputs

### `examples`

Should contain an end-to-end notebook that reads like a short technical article, not just a code dump.

## Stable Interface And Contract Decisions

These names and conventions should remain stable unless deliberately changed everywhere:

- `debt_obligations`
- `interest_expense`
- `owner_draws`
- `govt_payments`
- `net_worth`
- `current_liabilities`
- `crop_mix`

Phase 1 / Phase 2 contract decisions already captured in `phase-1-phase-2-contract.md`:

- low-level metric functions stay finance-pure
- `calculate_all(farm)` performs schema-to-metric translation
- derive `current_assets` inside `calculate_all(farm)` using:

```python
current_assets = farm.working_capital + farm.current_liabilities
```

- keep `operating_expense_ratio` defined as:

```python
operating_costs / gross_revenue
```

unless the team intentionally revises that decision

## Functional Goal

When complete, the package should support:

1. validating farm financial inputs
2. calculating core agricultural finance metrics
3. pulling external yield, price, and weather data
4. running fast Monte Carlo risk simulations
5. demonstrating the workflow in a public-facing notebook and README

## Recommended Build Order

1. Implement schemas in `agfin/schemas/`
2. Implement finance-pure metric helpers in `agfin/metrics/`
3. Implement `calculate_all(farm)` integration
4. Add real tests for schemas and metrics
5. Implement data connectors
6. Implement distributions and vectorized Monte Carlo simulation
7. Expand README and notebook

## Implementation Expectations

- Keep the package standalone with no references to Samsaras, customer data, or proprietary logic
- Use Pydantic v2 idioms
- Handle divide-by-zero and missing-data cases intentionally
- Keep Monte Carlo logic vectorized with NumPy rather than looping over runs in Python
- Add tests alongside implementation, not afterward if avoidable
- Favor small, composable functions and explicit return schemas

## Definition Of Done

The repository is in good shape when:

- `pytest` passes
- the notebook runs top-to-bottom without errors
- the README explains install, quick start, modules, and data sources
- connectors work against real public APIs
- Monte Carlo output is reproducible with a fixed seed
- the repo reads as a serious public artifact, not an internal scaffold

## Immediate Next Tasks

If picking work up from the current state, the highest-value next steps are:

1. implement `agfin/connectors/nass.py` using `usda-nass-quick-stats-implementation-plan.md`
2. implement `agfin/connectors/weather.py`
3. implement the risk modules and Monte Carlo tests
4. expand the README once connectors and risk modules exist
