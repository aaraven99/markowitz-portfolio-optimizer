import pytest
from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)


def test_health_and_valid_optimization() -> None:
    assert client.get("/api/health").json()["dataMode"] == "synthetic"
    response = client.post(
        "/api/portfolio/optimize",
        json={
            "tickers": ["SPY", "XLK", "XLF", "XLV"],
            "preset": "sectors",
            "max_weight": 0.4,
            "random_portfolios": 150,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert sum(row["weight"] for row in data["weights"]) == pytest.approx(1)
    assert max(row["weight"] for row in data["weights"]) <= 0.4 + 1e-6
    assert data["solver"]["constraintsSatisfied"] is True
    assert len(data["frontier"]) > 5


def test_duplicate_and_infeasible_bounds() -> None:
    duplicate = client.post("/api/portfolio/optimize", json={"tickers": ["SPY", "SPY"]})
    assert duplicate.status_code == 422
    infeasible = client.post(
        "/api/portfolio/optimize",
        json={"tickers": ["A", "B", "C"], "max_weight": 0.2},
    )
    assert infeasible.status_code == 422
    assert infeasible.json()["error"]["code"] == "INFEASIBLE"


def test_presets_and_compare() -> None:
    assert "technology" in client.get("/api/portfolio/presets").json()["data"]
    response = client.post(
        "/api/portfolio/compare",
        json={"tickers": ["A", "B", "C", "D"], "max_weight": 0.5},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["comparisons"]) == 3
