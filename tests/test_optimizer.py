import numpy as np
import pytest

from portfolio_optimizer.optimizer import optimize, portfolio_stats


def test_weights_and_stats() -> None:
    weights = optimize(np.array([0.1, 0.2]), np.array([[0.04, 0.01], [0.01, 0.09]]), max_weight=0.8)
    assert weights.sum() == pytest.approx(1) and (weights <= 0.8 + 1e-8).all()
    assert portfolio_stats(weights, np.array([0.1, 0.2]), np.eye(2))["volatility"] > 0


def test_infeasible_target() -> None:
    with pytest.raises(ValueError):
        optimize(np.array([0.1, 0.2]), np.eye(2), "target-return", target_return=2)
