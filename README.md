# Markowitz Portfolio Optimizer

![Generated constrained portfolio demonstration](assets/portfolio-preview.png)

Constrained mean-variance allocation with explicit return, risk, and concentration assumptions.

```bash
pip install -e . pytest ruff
portfolio-optimizer --tickers AAPL MSFT NVDA --objective max-sharpe --max-weight .35
pytest && ruff check . && ruff format --check .
```

The optimizer symmetrizes and lightly stabilizes the covariance matrix but cannot make an infeasible target return feasible. Historical parameters are uncertain.

This project is intended for educational and research purposes only. It does not provide investment advice, and its outputs should not be used as the sole basis for financial decisions. Historical performance and simulated results do not guarantee future performance.

MIT License. Author: Aarav Shah.
