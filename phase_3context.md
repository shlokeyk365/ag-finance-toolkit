# AG Finance Toolkit: Phase 3 Connector Context

## Purpose

This document defines the shared implementation contract for Phase 3 so two people can build the USDA NASS and NASA POWER connectors in parallel and merge them cleanly later.

This is the Phase 3 equivalent of the Phase 1 / Phase 2 contract:

- one person owns `agfin/connectors/nass.py`
- one person owns `agfin/connectors/weather.py`
- both implementations should follow the same conventions for inputs, outputs, request handling, error behavior, and documentation

## Scope Split

### Partner A: USDA NASS

Owns:

- [agfin/connectors/nass.py](/Users/aaravkenchiah/ag%20python%20lib/ag-finance-toolkit/agfin/connectors/nass.py)

Functions to implement:

```python
def get_crop_yield(crop: str, state: str, year: int) -> float
def get_crop_price(crop: str, state: str, year: int) -> float
def get_production_data(crop: str, state: str, year: int) -> dict
```

### Partner B: NASA POWER

Owns:

- [agfin/connectors/weather.py](/Users/aaravkenchiah/ag%20python%20lib/ag-finance-toolkit/agfin/connectors/weather.py)

Functions to implement:

```python
def get_weather_history(lat: float, lon: float, start_year: int, end_year: int) -> pd.DataFrame
def get_precipitation_series(lat: float, lon: float, start_year: int, end_year: int) -> pd.Series
def get_temperature_series(lat: float, lon: float, start_year: int, end_year: int) -> pd.Series
```

## Shared Design Rules

Both connectors should follow these repo-wide rules.

### 1. Keep connectors thin

These modules should:

- make HTTP requests
- validate and normalize response data
- return clean Python objects

These modules should not:

- contain business logic from Phase 2
- contain notebook-specific formatting
- silently swallow broken responses

### 2. Use `requests`

The repo already includes `requests` as a dependency. Both connectors should use it consistently.

Recommended pattern:

- module-level base URL constant
- small helper to perform requests
- explicit timeout
- `response.raise_for_status()`

### 3. Normalize outputs

The public connector functions should return stable, predictable outputs:

- USDA yield: `float`
- USDA price: `float`
- USDA production summary: `dict`
- NASA weather history: `pandas.DataFrame`
- NASA precipitation series: `pandas.Series`
- NASA temperature series: `pandas.Series`

Avoid returning raw API payloads from the public functions unless the function is specifically documented to do that.

### 4. Be explicit about missing data

If a crop/state/year or lat/lon/year range does not return usable data, the connector should raise a clear exception rather than return junk values.

Recommended default:

- raise `ValueError` for valid requests that return no usable data
- let `requests` HTTP errors surface via `raise_for_status()`

This is consistent with the strictness used in Phase 2.

### 5. Add module-level caching

Both connectors should use simple in-memory caching to avoid duplicate requests in a single Python session.

Recommended pattern:

```python
_CACHE: dict[tuple, object] = {}
```

Cache key guidance:

- USDA: function name + crop + state + year
- NASA: function name + lat + lon + start_year + end_year

The cache should be:

- module-local
- simple
- transparent

Do not add Redis, disk persistence, or anything heavy.

### 6. Document units

Every public function docstring should say what the returned values mean and what units are expected.

Examples:

- crop yield: bushels or units per acre, depending on the NASS series returned
- crop price: dollars per bushel or unit
- precipitation: annual precipitation series from NASA POWER
- temperature: annual average temperature at 2m from NASA POWER

If the API source uses units in the payload metadata, prefer to preserve that interpretation in comments or docstrings.

## Shared Error-Handling Contract

Both connector modules should follow the same error style.

### Raise `ValueError` when:

- input year ranges are invalid
- no usable records are returned for an otherwise valid query
- required fields are missing from an otherwise successful API response

### Let `requests` raise when:

- the network fails
- the API returns a bad HTTP status
- timeouts occur

### Do not:

- return `None` silently
- return empty DataFrames or empty Series without documentation
- bury important failures in print statements

## NASA POWER Contract

Owner:

- weather connector owner

File:

- [agfin/connectors/weather.py](/Users/aaravkenchiah/ag%20python%20lib/ag-finance-toolkit/agfin/connectors/weather.py)

### Official API context

The current build plan points to:

- base URL family: `https://power.larc.nasa.gov/api/temporal/annual/point`
- parameters of interest:
  - `PRECTOTCORR`
  - `T2M`

NASA POWER documentation also indicates:

- temporal APIs support JSON and CSV output
- point requests are built around a single latitude/longitude
- validation and rate-limit failures use standard HTTP codes like `422` and `429`

### Implementation contract

`get_weather_history(...)` should:

- validate `start_year <= end_year`
- request both `PRECTOTCORR` and `T2M`
- return a `DataFrame` indexed by year or containing a clear year column
- include normalized columns for precipitation and temperature

Recommended columns:

- `year`
- `precipitation`
- `temperature`

If you prefer the year as the index, be consistent and document it.

`get_precipitation_series(...)` should:

- call `get_weather_history(...)` or reuse the same parsing logic
- return a labeled `Series`
- preserve year alignment
- name the series clearly, for example `precipitation`

`get_temperature_series(...)` should:

- mirror the precipitation-series behavior
- return a labeled `Series`
- preserve year alignment

### NASA-specific implementation notes

- use one internal request/parsing helper if it keeps the file cleaner
- prefer a single request that fetches both `PRECTOTCORR` and `T2M`
- parse the response into a normalized tabular structure once
- make the two series helpers thin wrappers around the DataFrame-returning function

### NASA-specific edge cases to handle

- invalid year range
- malformed JSON or missing expected parameter blocks
- partial responses where one requested parameter is missing
- empty usable year range in the response

## USDA NASS Contract

Owner:

- NASS connector owner

File:

- [agfin/connectors/nass.py](/Users/aaravkenchiah/ag%20python%20lib/ag-finance-toolkit/agfin/connectors/nass.py)

### Official API context

The current build plan points to:

- Quick Stats API
- base URL family: `https://quickstats.nass.usda.gov/api/`
- API key required

The official Quick Stats API documentation also notes:

- an API key is required
- the API returns a maximum of 50,000 records per request
- query filters determine the exact record set returned

### Implementation contract

`get_crop_yield(...)` should:

- query the NASS API for a crop/state/year yield value
- return a single `float`
- raise `ValueError` if no usable value is found

`get_crop_price(...)` should:

- query the NASS API for a crop/state/year price value
- return a single `float`
- raise `ValueError` if no usable value is found

`get_production_data(...)` should:

- return a small normalized dictionary rather than a raw payload dump

Recommended dictionary fields:

```python
{
    "crop": ...,
    "state": ...,
    "year": ...,
    "yield": ...,
    "price": ...,
}
```

If the implementation later needs extra fields, add them deliberately and document them.

### USDA-specific implementation notes

- use an environment variable for the API key
- document the exact env var name in the file docstring and later in the README
- use a small internal helper for common request code
- normalize crop and state inputs consistently before building requests

Recommended env var:

```python
NASS_API_KEY
```

### USDA-specific edge cases to handle

- missing API key
- empty `data` response list
- multiple records returned when a single value is expected
- string-formatted numeric values that need cleaning before conversion

If multiple records are returned, do not silently average them. Either:

- tighten the query so one record is returned
- or raise `ValueError` explaining the ambiguity

## Cross-Connector Consistency Rules

To merge cleanly, both connector modules should share the same style in these areas.

### Naming

Use:

- clear base URL constants
- uppercase cache constant names
- small private helpers prefixed with `_`

### Function behavior

Public functions should:

- have precise return types
- use docstrings
- raise explicit errors on invalid or missing data

### Internal helpers

Private helpers are encouraged if they reduce repeated code, for example:

- `_request_json(...)`
- `_parse_weather_payload(...)`
- `_clean_numeric_value(...)`

### Testing expectations

Even if Phase 3 tests are written later, both implementations should be designed to be testable now.

That means:

- separate request logic from parsing logic where reasonable
- avoid hard-coding environment-dependent behavior deep inside the function body
- make it easy to mock `requests.get`

## Merge Checklist

Before either branch is merged, both people should confirm:

1. Public function names match the build plan exactly.
2. Return types match the contract exactly.
3. Missing-data behavior is explicit and documented.
4. Caching exists and is module-local.
5. API keys are handled only where needed.
6. NASA code does not depend on USDA code.
7. USDA code does not depend on NASA code.
8. Docstrings explain units and return values.

## Recommended Division of Labor

To reduce merge friction:

- NASA owner should edit only `weather.py`
- USDA owner should edit only `nass.py`
- if shared connector exports are later added in `agfin/connectors/__init__.py`, do that in a small follow-up commit after both modules are stable

This avoids overlapping edits during development.

## Suggested Implementation Order

### NASA owner

1. Add base URL, cache, and request helper
2. Implement `get_weather_history(...)`
3. Implement `get_precipitation_series(...)`
4. Implement `get_temperature_series(...)`
5. Add docstrings and edge-case handling

### USDA owner

1. Add base URL, API key handling, cache, and request helper
2. Implement `get_crop_yield(...)`
3. Implement `get_crop_price(...)`
4. Implement `get_production_data(...)`
5. Add docstrings and ambiguity handling

## Key Decisions Already Locked In

- Keep the connectors thin
- Raise explicit errors for missing usable data
- Use simple in-memory caching
- Use `operating_expense_ratio = operating_costs / gross_revenue`
- Keep Phase 3 independent from Phase 2 business logic

## Helpful Official References

- NASA POWER Temporal APIs:
  - https://power.larc.nasa.gov/docs/services/api/temporal/
  - https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- USDA NASS Quick Stats API:
  - https://quickstats.nass.usda.gov/api
  - https://www.nass.usda.gov/Quick_Stats/
