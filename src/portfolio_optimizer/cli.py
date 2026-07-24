import argparse
import json

import yfinance as yf

from .optimizer import optimize, portfolio_stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=["AAPL", "MSFT", "NVDA"])
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--objective", default="max-sharpe")
    parser.add_argument("--max-weight", type=float, default=0.5)
    args = parser.parse_args()
    prices = yf.download(args.tickers, start=args.start, auto_adjust=True, progress=False)[
        "Close"
    ].dropna()
    returns = prices.pct_change().dropna()
    weights = optimize(
        (returns.mean() * 252).values, (returns.cov() * 252).values, args.objective, args.max_weight
    )
    print(
        json.dumps(
            {
                "weights": dict(zip(args.tickers, weights.round(4))),
                **portfolio_stats(
                    weights, (returns.mean() * 252).values, (returns.cov() * 252).values
                ),
            },
            indent=2,
        )
    )
