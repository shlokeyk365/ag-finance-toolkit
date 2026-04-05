# USDA NASS Quick Stats Implementation Plan

## Purpose

This document turns the high-level connector notes in `ag-finance-toolkit-build-plan.md` into a repo-grounded implementation plan for `agfin/connectors/nass.py`.

The goal is to add a production-quality USDA NASS Quick Stats connector that matches the code style already established in the repository:

- strict, explicit behavior
- small composable functions
- test-first or test-alongside implementation
- minimal dependencies beyond what `pyproject.toml` already declares

## Why A Separate Plan Is Needed

The root build plan is still useful for scope, but it no longer matches the repository state closely enough to drive connector implementation on its own.

What has changed since that plan was written:

- the repo is no longer a fresh scaffold
- `agfin.schemas` and `agfin.metrics` are already implemented with meaningful validation and tests
- `agfin/connectors/nass.py` is still only a stub
- the current tests and module style favor explicit validation and predictable failure modes

The USDA connector should therefore be designed to fit the current repo, not the original 10-15 hour bootstrap plan.

## Current Repo Constraints

Relevant facts from the current codebase:

- `agfin/connectors/nass.py` currently contains only a module docstring
- `agfin/connectors/__init__.py` does not yet export connector functions
- `requests` is already a runtime dependency in `pyproject.toml`
- there is no connector test file yet
- the README is still minimal, so connector setup and usage will need documentation work as part of the task

Relevant style signals from implemented modules:

- core modules use docstrings and explicit error messages
- tests assert specific failure behavior, not just happy paths
- validation is kept intentional rather than implicit

## External API Facts To Build Around

Based on the official USDA Quick Stats API documentation:

- requests go to `https://quickstats.nass.usda.gov/api/api_GET/`
- an API key is required for all data requests
- `get_counts` is available at `https://quickstats.nass.usda.gov/api/get_counts/`
- the API returns at most 50,000 rows per request
- API filters use column names such as `commodity_desc`, `state_alpha`, `year`, `statisticcat_desc`, `domain_desc`, and `agg_level_desc`
- comparison operators such as `__GE`, `__LE`, and `__LIKE` are supported in query parameters
- returned data values live in the `Value` field and may include formatting such as commas
- NASS terms require attribution when the API is used in an application or published artifact

## Scope For This Implementation

Implement the USDA connector only. Do not change schemas, metrics, or Monte Carlo behavior as part of this task unless a connector-specific issue forces a follow-up decision.

Initial supported use cases:

- annual state-level crop yield lookup
- annual state-level crop price lookup
- combined production snapshot for one crop, one state, one year

Initial supported crop coverage should be explicit rather than pretending to be fully generic. The cleanest starting point is:

- Corn
- Soybeans

That matches the examples already used elsewhere in the repo and avoids overpromising cross-crop support before unit conventions are normalized.

## Public Interface

Keep the user-facing entrypoints aligned with the root build plan, but tighten the behavior contract.

Public functions in `agfin/connectors/nass.py`:

```python
def get_crop_yield(crop: str, state: str, year: int) -> float:
    ...


def get_crop_price(crop: str, state: str, year: int) -> float:
    ...


def get_production_data(crop: str, state: str, year: int) -> dict[str, object]:
    ...
```

Behavior contract:

- `crop` accepts a small normalized vocabulary such as `"corn"` or `"soybeans"`
- `state` accepts a two-letter state code and is normalized to uppercase
- `year` must be an integer year
- missing API credentials raise a dedicated configuration error
- no matching records raise a dedicated no-data error
- malformed or ambiguous responses raise a dedicated response error

Recommended exception hierarchy:

```python
class NassError(Exception):
    pass


class NassConfigurationError(NassError):
    pass


class NassNoDataError(NassError):
    pass


class NassResponseError(NassError):
    pass
```

This resolves a gap in the original build plan: the plan said to "handle missing data gracefully" while also specifying `float` return types. In this repo, explicit library exceptions are the cleanest version of graceful behavior.

## Internal Module Design

Implement `agfin/connectors/nass.py` as one public layer plus a small internal helper layer.

### 1. Configuration and constants

Add module-level constants for:

- `BASE_URL`
- `DEFAULT_TIMEOUT_SECONDS`
- supported crops and their USDA query metadata

Recommended environment variable:

- `USDA_NASS_API_KEY`

Do not hardcode keys in code, tests, or notebook artifacts.

### 2. API key loader

Add a helper such as:

```python
def _get_api_key(api_key: str | None = None) -> str:
    ...
```

Behavior:

- explicit argument wins if later internal helpers ever pass one
- otherwise read `USDA_NASS_API_KEY`
- raise `NassConfigurationError` with a clear setup message if absent

### 3. Query normalization helpers

Add small helpers to keep public functions simple:

- `_normalize_crop(crop: str) -> str`
- `_normalize_state(state: str) -> str`
- `_validate_year(year: int) -> int`

These should reject unsupported crops and malformed state codes early, before any HTTP request is made.

### 4. Low-level HTTP helper

Add one request helper responsible for:

- injecting the API key
- adding `format=JSON`
- issuing `requests.get(...)`
- applying a timeout
- surfacing request failures as `NassResponseError`
- validating that the JSON body contains a `data` field when using `api_GET`

Suggested signature:

```python
def _api_get(params: dict[str, str]) -> list[dict[str, str]]:
    ...
```

Optional follow-up helper:

```python
def _get_count(params: dict[str, str]) -> int:
    ...
```

For the initial crop/state/year lookup functions, `get_counts` is not required for correctness, but it is useful as a guardrail if a query template turns out broader than expected.

### 5. Caching

Use stdlib caching, not a hand-rolled mutable dict.

Recommended approach:

```python
from functools import lru_cache
```

Cache the normalized query helper rather than raw HTTP calls. This keeps the implementation simple and still satisfies the original plan's in-memory caching goal.

### 6. Value parsing

The API returns published values as strings in `Value`, often with commas.

Add:

```python
def _parse_numeric_value(raw_value: str) -> float:
    ...
```

This helper should:

- strip commas and whitespace
- convert plain numeric strings to `float`
- reject suppression or non-numeric codes with `NassNoDataError` or `NassResponseError`

This is one of the highest-risk parts of the connector because external APIs often look structurally correct while still returning non-numeric published values.

### 7. Record selection

Even for a narrow crop/state/year query, the API can return multiple rows if filters are too broad.

Add a helper such as:

```python
def _select_single_record(records: list[dict[str, str]], *, context: str) -> dict[str, str]:
    ...
```

Selection rules should be explicit:

- prefer `agg_level_desc == "STATE"`
- require `freq_desc == "ANNUAL"`
- prefer `reference_period_desc == "YEAR"` when present
- prefer `domain_desc == "TOTAL"`
- if more than one record still matches, raise `NassResponseError` instead of silently picking one

This matches the repo's existing preference for deterministic behavior over hidden guesswork.

## Query Templates

The implementation should not rely on open-ended free-form queries for the first version. It should use curated query templates backed by a small crop configuration map.

Recommended internal crop config shape:

```python
CROP_QUERY_CONFIG = {
    "corn": {
        "commodity_desc": "CORN",
        "yield_unit_desc": "BU / ACRE",
        "price_unit_desc": "$ / BU",
    },
    "soybeans": {
        "commodity_desc": "SOYBEANS",
        "yield_unit_desc": "BU / ACRE",
        "price_unit_desc": "$ / BU",
    },
}
```

Recommended query shape for `get_crop_yield(...)`:

- `commodity_desc`
- `state_alpha`
- `year`
- `agg_level_desc=STATE`
- `freq_desc=ANNUAL`
- `reference_period_desc=YEAR`
- `domain_desc=TOTAL`
- `statisticcat_desc=YIELD`
- `unit_desc` from crop config

Recommended query shape for `get_crop_price(...)`:

- `commodity_desc`
- `state_alpha`
- `year`
- `agg_level_desc=STATE`
- `freq_desc=ANNUAL`
- `domain_desc=TOTAL`
- `statisticcat_desc=PRICE RECEIVED`
- `unit_desc` from crop config

Recommended `get_production_data(...)` behavior:

- call `get_crop_yield(...)`
- call `get_crop_price(...)`
- return a structured dict containing:

```python
{
    "crop": ...,
    "state": ...,
    "year": ...,
    "yield": ...,
    "price": ...,
    "revenue_per_acre": ...,
    "yield_unit": ...,
    "price_unit": ...,
}
```

For the first implementation, this is better than trying to support every possible production statistic from Quick Stats. It is directly useful to the rest of the repo and easy to test.

## File-Level Work Plan

### `agfin/connectors/nass.py`

Implement:

- exception classes
- normalization helpers
- API request helper
- numeric parsing helper
- record selection helper
- `get_crop_yield`
- `get_crop_price`
- `get_production_data`

### `agfin/connectors/__init__.py`

Export:

- `get_crop_yield`
- `get_crop_price`
- `get_production_data`
- connector exception classes

### `tests/test_connectors_nass.py`

Add unit tests for:

- missing API key raises `NassConfigurationError`
- unsupported crop raises `ValueError`
- malformed state raises `ValueError`
- numeric parsing removes commas correctly
- suppression or missing `Value` content raises a connector error
- yield query builds the expected parameters
- price query builds the expected parameters
- empty result sets raise `NassNoDataError`
- multiple unresolved result rows raise `NassResponseError`
- `get_production_data` combines yield and price into the expected dict

Testing strategy:

- mock `requests.get`
- do not depend on live USDA availability in unit tests
- if a live smoke test is desired later, gate it behind `USDA_NASS_API_KEY`

### `README.md`

Add a connector setup section that covers:

- what USDA Quick Stats is
- how to request an API key
- required environment variable: `USDA_NASS_API_KEY`
- a minimal usage example
- attribution language required by the NASS API terms

Suggested README note:

`This product uses the NASS API but is not endorsed or certified by NASS.`

## Implementation Sequence

Recommended order of execution:

1. Add failing tests for normalization, numeric parsing, and error handling.
2. Implement connector exceptions and input normalization.
3. Implement low-level request and response parsing helpers.
4. Implement `get_crop_yield`.
5. Implement `get_crop_price`.
6. Implement `get_production_data`.
7. Export public connector symbols from `agfin/connectors/__init__.py`.
8. Expand `README.md` with key setup and usage.
9. Optionally run one manual live smoke test with a real API key.

## Acceptance Criteria

This connector work is done when:

- `tests/test_connectors_nass.py` exists and passes
- public USDA connector functions are importable from `agfin.connectors`
- USDA credentials are documented in the README
- connector failures surface as clear domain-specific exceptions
- at least one supported crop can retrieve annual state yield and price cleanly
- the implementation does not add new third-party dependencies

## Risks And Decisions To Lock Early

### Crop support breadth

Risk:

- Quick Stats is broad, but units and query semantics vary by commodity

Decision:

- start with explicit support for Corn and Soybeans
- expand the crop map only after tests prove the pattern

### Missing or suppressed values

Risk:

- some otherwise valid API rows may contain non-numeric published values

Decision:

- raise explicit connector errors instead of returning fake numeric defaults

### Ambiguous result sets

Risk:

- overly broad filters may return multiple records that look plausible

Decision:

- fail loudly unless record selection rules narrow the result set to one row

### Live API reliance in CI

Risk:

- live HTTP tests are flaky and require credentials

Decision:

- keep default tests mocked
- treat live checks as optional smoke validation

## Follow-On Work After This Connector

Once USDA NASS Quick Stats is implemented, the next logical follow-ons are:

- expand supported crops if needed
- add helper functions for multi-year series retrieval
- feed observed yield and price history into the Monte Carlo assumptions layer
- pair the USDA connector with the NASA POWER connector for richer farm scenario inputs

## References

- USDA NASS Quick Stats API documentation:
  `https://quickstats.nass.usda.gov/api`
- USDA NASS main site:
  `https://www.nass.usda.gov/`
