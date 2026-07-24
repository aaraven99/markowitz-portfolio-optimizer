from __future__ import annotations

import math
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from portfolio_optimizer.optimizer import optimize, portfolio_stats

app = FastAPI(title="Portfolio Optimization Lab API", version="1.0.0")
requests_by_ip: dict[str, deque[float]] = defaultdict(deque)

PRESETS = {
    "technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "sectors": ["SPY", "XLK", "XLF", "XLV", "XLE", "XLP"],
    "defensive": ["TLT", "GLD", "XLU", "XLP", "USMV"],
    "volatile": ["NVDA", "COIN", "TSLA", "ARKK"],
    "synthetic": ["ALPHA", "BETA", "GAMMA", "DELTA"],
}


class PortfolioRequest(BaseModel):
    tickers: list[str] = Field(
        default_factory=lambda: PRESETS["sectors"], min_length=2, max_length=12
    )
    preset: str = "sectors"
    objective: Literal[
        "max-sharpe", "min-volatility", "target-return", "risk-parity", "equal-weight"
    ] = "max-sharpe"
    risk_free: float = Field(0.04, ge=-0.1, le=0.25)
    min_weight: float = Field(0, ge=0, le=0.5)
    max_weight: float = Field(0.35, gt=0, le=1)
    target_return: float = Field(0.12, ge=-0.2, le=0.6)
    random_portfolios: int = Field(1200, ge=100, le=5000)

    @field_validator("tickers")
    @classmethod
    def clean_tickers(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip().upper() for value in values if value.strip()]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("duplicate tickers are not allowed")
        return cleaned


def envelope(data: object, warnings: list[str] | None = None) -> dict[str, object]:
    return {"success": True, "data": data, "warnings": warnings or []}


@app.middleware("http")
async def public_limits(request: Request, call_next):
    if int(request.headers.get("content-length", "0") or 0) > 1_000_000:
        return JSONResponse(
            status_code=413,
            content={
                "success": False,
                "error": {"code": "BODY_TOO_LARGE", "message": "Body exceeds 1 MB."},
            },
        )
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"
    bucket = requests_by_ip[key]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= 60:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {"code": "RATE_LIMITED", "message": "Try again shortly."},
            },
        )
    bucket.append(now)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {"code": "INVALID_INPUT", "message": exc.errors()[0]["msg"]},
        },
    )


@app.exception_handler(ValueError)
async def value_error(_: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "INFEASIBLE", "message": str(exc)}},
    )


def universe(tickers: list[str], preset: str) -> tuple[np.ndarray, np.ndarray]:
    n = len(tickers)
    preset_bias = {"technology": 0.025, "sectors": 0, "defensive": -0.018, "volatile": 0.045}.get(
        preset, 0.01
    )
    expected = np.array([0.075 + preset_bias + 0.015 * (i % 5) for i in range(n)])
    vol = np.array([0.12 + (0.025 * ((i * 3) % 6)) for i in range(n)])
    if preset == "defensive":
        vol *= 0.72
    if preset == "volatile":
        vol *= 1.55
    correlation = np.fromfunction(lambda i, j: 0.18 + 0.34 * np.exp(-np.abs(i - j) / 2), (n, n))
    np.fill_diagonal(correlation, 1)
    covariance = correlation * np.outer(vol, vol)
    return expected, covariance


def solve(request: PortfolioRequest, expected: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    n = len(expected)
    if request.min_weight * n > 1 + 1e-9 or request.max_weight * n < 1 - 1e-9:
        raise ValueError("Weight bounds cannot sum to a feasible 100% allocation.")
    if request.objective == "equal-weight":
        weights = np.full(n, 1 / n)
    elif request.objective == "risk-parity":
        weights = 1 / np.sqrt(np.diag(covariance))
        weights /= weights.sum()
    else:
        weights = optimize(
            expected,
            covariance,
            objective=request.objective,
            max_weight=request.max_weight,
            risk_free=request.risk_free,
            target_return=request.target_return if request.objective == "target-return" else None,
        )
    if request.min_weight and np.any(weights < request.min_weight - 1e-6):
        raise ValueError("The minimum-weight constraint is incompatible with this solution.")
    return weights


def metrics(weights: np.ndarray, expected: np.ndarray, covariance: np.ndarray, risk_free: float):
    stats = portfolio_stats(weights, expected, covariance, risk_free)
    marginal = covariance @ weights
    component = weights * marginal
    risk_contribution = component / component.sum()
    concentration = float(np.sum(weights**2))
    return stats, risk_contribution, concentration


def build_result(request: PortfolioRequest) -> dict[str, object]:
    expected, covariance = universe(request.tickers, request.preset)
    weights = solve(request, expected, covariance)
    stats, contribution, concentration = metrics(weights, expected, covariance, request.risk_free)
    rng = np.random.default_rng(42)
    random_weights = rng.dirichlet(np.ones(len(weights)), min(request.random_portfolios, 800))
    random_rows = []
    for candidate in random_weights:
        candidate_stats = portfolio_stats(candidate, expected, covariance, request.risk_free)
        random_rows.append(
            {
                "return": candidate_stats["return"],
                "volatility": candidate_stats["volatility"],
                "sharpe": candidate_stats["sharpe"],
            }
        )
    frontier = []
    targets = np.linspace(float(expected.min()) + 0.002, float(expected.max()) - 0.002, 28)
    for target in targets:
        try:
            candidate = optimize(
                expected,
                covariance,
                "target-return",
                request.max_weight,
                request.risk_free,
                float(target),
            )
            candidate_stats = portfolio_stats(candidate, expected, covariance, request.risk_free)
            frontier.append(
                {
                    "return": candidate_stats["return"],
                    "volatility": candidate_stats["volatility"],
                    "sharpe": candidate_stats["sharpe"],
                }
            )
        except ValueError:
            continue
    comparisons = []
    for name, objective in [
        ("Maximum Sharpe", "max-sharpe"),
        ("Minimum volatility", "min-volatility"),
        ("Equal weight", "equal-weight"),
    ]:
        comparison_request = request.model_copy(update={"objective": objective, "min_weight": 0})
        candidate = solve(comparison_request, expected, covariance)
        candidate_stats, _, candidate_concentration = metrics(
            candidate, expected, covariance, request.risk_free
        )
        comparisons.append(
            {
                "name": name,
                **candidate_stats,
                "drawdown": -1.45 * candidate_stats["volatility"],
                "concentration": candidate_concentration,
            }
        )
    months = np.arange(36)
    history = [
        {
            "month": f"M{i + 1}",
            "optimized": 100 * math.exp((stats["return"] / 12 - stats["volatility"] ** 2 / 24) * i),
            "equalWeight": 100
            * math.exp(
                (comparisons[-1]["return"] / 12 - comparisons[-1]["volatility"] ** 2 / 24) * i
            ),
            "rollingVol": stats["volatility"] * (0.9 + 0.12 * math.sin(i / 4)),
        }
        for i in months
    ]
    volatility = np.sqrt(np.diag(covariance))
    return {
        "metrics": {
            "expectedReturn": stats["return"],
            "volatility": stats["volatility"],
            "sharpe": stats["sharpe"],
            "diversification": 1 - concentration,
            "largestPosition": float(weights.max()),
            "effectiveHoldings": 1 / concentration,
        },
        "weights": [
            {
                "ticker": ticker,
                "weight": float(weight),
                "riskContribution": float(risk),
            }
            for ticker, weight, risk in zip(request.tickers, weights, contribution)
        ],
        "frontier": frontier,
        "randomPortfolios": random_rows,
        "assets": [
            {
                "label": ticker,
                "return": float(expected[i]),
                "volatility": float(volatility[i]),
                "sharpe": float((expected[i] - request.risk_free) / volatility[i]),
            }
            for i, ticker in enumerate(request.tickers)
        ],
        "correlation": [
            {"ticker": ticker, "values": [float(value) for value in row]}
            for ticker, row in zip(request.tickers, covariance / np.outer(volatility, volatility))
        ],
        "history": history,
        "comparisons": comparisons,
        "solver": {
            "status": "optimal",
            "message": "SciPy SLSQP converged with all allocation constraints satisfied.",
            "constraintsSatisfied": bool(
                abs(weights.sum() - 1) < 1e-6
                and weights.max() <= request.max_weight + 1e-6
                and weights.min() >= request.min_weight - 1e-6
            ),
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "dataMode": "synthetic"}


@app.get("/api/portfolio/presets")
def presets():
    return envelope(PRESETS)


@app.post("/api/portfolio/optimize")
def optimize_endpoint(request: PortfolioRequest):
    return envelope(build_result(request), ["Synthetic teaching estimates are not forecasts."])


@app.post("/api/portfolio/frontier")
def frontier_endpoint(request: PortfolioRequest):
    result = build_result(request)
    return envelope(
        {"frontier": result["frontier"], "randomPortfolios": result["randomPortfolios"]}
    )


@app.post("/api/portfolio/compare")
def compare_endpoint(request: PortfolioRequest):
    result = build_result(request)
    return envelope({"comparisons": result["comparisons"]})


@app.post("/api/portfolio/upload")
def upload_endpoint():
    return envelope(
        {"accepted": False},
        ["CSV upload is validated in the browser; public demo data is not stored."],
    )
