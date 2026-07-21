from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def portfolio_stats(
    weights: np.ndarray, expected: np.ndarray, covariance: np.ndarray, risk_free: float = 0
) -> dict[str, float]:
    annual_return = float(weights @ expected)
    volatility = float(np.sqrt(weights @ covariance @ weights))
    return {
        "return": annual_return,
        "volatility": volatility,
        "sharpe": (annual_return - risk_free) / volatility if volatility else 0.0,
    }


def optimize(
    expected: np.ndarray,
    covariance: np.ndarray,
    objective: str = "max-sharpe",
    max_weight: float = 1.0,
    risk_free: float = 0,
    target_return: float | None = None,
) -> np.ndarray:
    expected, covariance = np.asarray(expected, float), np.asarray(covariance, float)
    if covariance.shape != (len(expected), len(expected)) or not 0 < max_weight <= 1:
        raise ValueError("invalid covariance or bounds")
    covariance = (covariance + covariance.T) / 2 + np.eye(len(expected)) * 1e-10
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    if objective == "target-return":
        if target_return is None:
            raise ValueError("target return is required")
        constraints.append({"type": "eq", "fun": lambda w: w @ expected - target_return})
    if objective not in {"max-sharpe", "min-volatility", "target-return"}:
        raise ValueError("unknown objective")
    fun = lambda w: (
        -(w @ expected - risk_free) / np.sqrt(w @ covariance @ w)
        if objective == "max-sharpe"
        else np.sqrt(w @ covariance @ w)
    )
    result = minimize(
        fun,
        np.full(len(expected), 1 / len(expected)),
        bounds=[(0, max_weight)] * len(expected),
        constraints=constraints,
        method="SLSQP",
    )
    if not result.success:
        raise ValueError(f"optimization failed: {result.message}")
    return result.x
