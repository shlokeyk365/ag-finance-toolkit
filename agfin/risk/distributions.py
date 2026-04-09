"""Probability distribution helpers for risk simulation.

The helpers in this module return frozen SciPy distributions using the build
plan's intended shapes:

- yield: truncated normal around the mean, bounded at zero
- price: lognormal around the mean
- cost: normal around the mean
"""

from __future__ import annotations

import numpy as np
from scipy import stats


class _DeterministicDistribution:
    """Minimal frozen-distribution stand-in for degenerate cases."""

    def __init__(self, value: float) -> None:
        self.value = float(value)

    def rvs(self, size: int | tuple[int, ...] | None = None, random_state=None):
        if size is None:
            return self.value

        return np.full(size, self.value, dtype=float)


def _validate_mean_and_cv(mean: float, cv: float, *, name: str) -> None:
    """Validate the common distribution parameters.

    Args:
        mean: Central expected value for the distribution.
        cv: Coefficient of variation, expressed as a non-negative fraction.
        name: Human-readable label used in error messages.

    Raises:
        ValueError: If the parameters cannot define a valid distribution.
    """
    if mean <= 0:
        raise ValueError(f"{name} mean must be positive")

    if cv < 0:
        raise ValueError(f"{name} cv must be non-negative")


def yield_distribution(mean: float, cv: float):
    """Return a truncated normal yield distribution.

    Yield is bounded below by zero, so the implementation uses a left-truncated
    normal distribution with the requested mean and coefficient of variation.
    """
    _validate_mean_and_cv(mean, cv, name="yield")

    if cv == 0:
        return _DeterministicDistribution(mean)

    std = mean * cv
    a = -mean / std
    return stats.truncnorm(a=a, b=np.inf, loc=mean, scale=std)


def price_distribution(mean: float, cv: float):
    """Return a lognormal price distribution.

    Prices are strictly positive and commonly right-skewed, making lognormal a
    reasonable default shape for the toolkit's Monte Carlo model.
    """
    _validate_mean_and_cv(mean, cv, name="price")

    if cv == 0:
        return _DeterministicDistribution(mean)

    sigma = np.sqrt(np.log(1 + cv**2))
    mu = np.log(mean) - (sigma**2) / 2
    return stats.lognorm(s=sigma, scale=np.exp(mu))


def cost_distribution(mean: float, cv: float):
    """Return a normal cost distribution.

    The build plan models costs as symmetric variation around the expected
    value. Callers that need to enforce non-negative realized costs can clip
    sampled outputs after drawing from the distribution.
    """
    _validate_mean_and_cv(mean, cv, name="cost")

    if cv == 0:
        return _DeterministicDistribution(mean)

    return stats.norm(loc=mean, scale=mean * cv)


__all__ = ["cost_distribution", "price_distribution", "yield_distribution"]
