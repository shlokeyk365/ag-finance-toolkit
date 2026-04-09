"""Monte Carlo risk simulation engine."""

from __future__ import annotations

import numpy as np

from agfin.risk.distributions import (
    cost_distribution,
    price_distribution,
    yield_distribution,
)
from agfin.schemas import FarmInputs, RiskResults


def _draw_samples(distribution_factory, cv: float, runs: int, rng: np.random.Generator) -> np.ndarray:
    """Draw multiplicative samples around a unit mean.

    The public simulation API expresses uncertainty as a coefficient of
    variation around the base farm assumptions. This helper keeps the Monte
    Carlo layer vectorized while handling the deterministic ``cv == 0`` case
    cleanly.
    """
    if cv == 0:
        return np.ones(runs, dtype=float)

    distribution = distribution_factory(1.0, cv)
    return np.asarray(distribution.rvs(size=runs, random_state=rng), dtype=float)


def simulate_farm_risk(
    farm: FarmInputs,
    yield_cv: float = 0.12,
    price_cv: float = 0.15,
    cost_cv: float = 0.08,
    runs: int = 10_000,
    seed: int | None = None,
) -> RiskResults:
    """Simulate farm income and repayment risk using vectorized Monte Carlo.

    The simulation treats the farm's expected crop revenue and operating costs
    as baseline assumptions, then perturbs them with multiplicative shocks for
    yield, price, and cost. Fixed costs and support income remain deterministic
    in this first-pass model.

    Args:
        farm: Validated farm financial inputs.
        yield_cv: Coefficient of variation for the yield multiplier.
        price_cv: Coefficient of variation for the price multiplier.
        cost_cv: Coefficient of variation for the operating-cost multiplier.
        runs: Number of simulation draws to generate.
        seed: Optional NumPy random seed for reproducibility.

    Returns:
        A ``RiskResults`` summary object containing income and DSCR statistics.

    Raises:
        ValueError: If the simulation parameters are invalid or debt service is
            zero.
    """
    if runs <= 0:
        raise ValueError("runs must be positive")

    if yield_cv < 0:
        raise ValueError("yield_cv must be non-negative")

    if price_cv < 0:
        raise ValueError("price_cv must be non-negative")

    if cost_cv < 0:
        raise ValueError("cost_cv must be non-negative")

    if farm.debt_obligations == 0:
        raise ValueError("farm.debt_obligations must be non-zero")

    rng = np.random.default_rng(seed)

    base_gross_revenue = sum(
        item.acres * item.expected_yield * item.expected_price for item in farm.crop_mix
    )

    yield_multiplier = _draw_samples(yield_distribution, yield_cv, runs, rng)
    price_multiplier = _draw_samples(price_distribution, price_cv, runs, rng)
    cost_multiplier = np.maximum(_draw_samples(cost_distribution, cost_cv, runs, rng), 0.0)

    revenues = base_gross_revenue * yield_multiplier * price_multiplier
    operating_costs = farm.operating_costs * cost_multiplier
    incomes = (
        revenues
        - operating_costs
        - farm.fixed_costs
        + farm.insurance_income
        + farm.govt_payments
    )

    cash_available = incomes + farm.depreciation + farm.interest_expense - farm.owner_draws
    dscr_values = cash_available / farm.debt_obligations
    shortfalls = np.maximum(farm.debt_obligations - cash_available, 0.0)

    return RiskResults(
        mean_income=float(np.mean(incomes)),
        p10_income=float(np.percentile(incomes, 10)),
        p50_income=float(np.percentile(incomes, 50)),
        p90_income=float(np.percentile(incomes, 90)),
        mean_dscr=float(np.mean(dscr_values)),
        p10_dscr=float(np.percentile(dscr_values, 10)),
        default_probability=float(np.mean(dscr_values < 1.0)),
        worst_case_shortfall=float(np.max(shortfalls)),
        simulation_runs=runs,
    )


__all__ = ["simulate_farm_risk"]
