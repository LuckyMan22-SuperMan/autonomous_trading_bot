"""Vectorized backtesting engine + performance metrics.

The engine takes a price frame and a target-position series (0/1), applies a
1-bar execution lag (you trade on the *next* bar to avoid look-ahead bias),
deducts a per-trade commission, and produces an equity curve plus a set of
standard performance metrics.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def run_backtest(df: pd.DataFrame, positions: pd.Series,
                 initial_cash: float = 10_000.0,
                 commission: float = 0.0005,
                 periods_per_year: int = TRADING_DAYS) -> Dict:
    """Run a long/flat backtest and return equity curve, trades and metrics."""
    close = df["Close"].astype(float)
    # Execute on the next bar: shift the target position forward by one.
    pos = positions.reindex(close.index).fillna(0.0).shift(1).fillna(0.0)

    bar_returns = close.pct_change().fillna(0.0)
    # Commission charged whenever the position changes (a trade).
    turnover = pos.diff().abs().fillna(pos.abs())
    strat_returns = pos * bar_returns - turnover * commission

    equity = (1.0 + strat_returns).cumprod() * initial_cash
    bench_equity = (1.0 + bar_returns).cumprod() * initial_cash

    trades = _extract_trades(close, pos)
    metrics = _metrics(equity, strat_returns, trades, periods_per_year,
                        initial_cash, bench_equity)

    return {
        "dates": [d.isoformat() for d in equity.index],
        "equity": [round(float(v), 2) for v in equity.values],
        "benchmark": [round(float(v), 2) for v in bench_equity.values],
        "price": [round(float(v), 4) for v in close.values],
        "trades": trades,
        "metrics": metrics,
    }
