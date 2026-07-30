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


def _extract_trades(close: pd.Series, pos: pd.Series) -> List[Dict]:
    """Reconstruct round-trip trades from position changes."""
    trades: List[Dict] = []
    entry_price = None
    entry_date = None
    prev = 0.0
    for date, p in pos.items():
        price = float(close.loc[date])
        if prev == 0.0 and p > 0.0:  # entered long
            entry_price = price
            entry_date = date
        elif prev > 0.0 and p == 0.0 and entry_price is not None:  # exited
            ret = (price - entry_price) / entry_price
            trades.append({
                "entry_date": entry_date.isoformat(),
                "exit_date": date.isoformat(),
                "entry_price": round(entry_price, 4),
                "exit_price": round(price, 4),
                "return_pct": round(ret * 100, 2),
            })
            entry_price = None
        prev = p
    # Close any open position at the last bar (mark-to-market).
    if entry_price is not None:
        last_date = close.index[-1]
        price = float(close.iloc[-1])
        ret = (price - entry_price) / entry_price
        trades.append({
            "entry_date": entry_date.isoformat(),
            "exit_date": last_date.isoformat(),
            "entry_price": round(entry_price, 4),
            "exit_price": round(price, 4),
            "return_pct": round(ret * 100, 2),
            "open": True,
        })
    return trades


def _max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    return float(drawdown.min())


def _metrics(equity: pd.Series, returns: pd.Series, trades: List[Dict],
             periods_per_year: int, initial_cash: float,
             bench_equity: pd.Series) -> Dict:
    total_return = equity.iloc[-1] / initial_cash - 1.0
    bench_return = bench_equity.iloc[-1] / initial_cash - 1.0
    n = len(returns)
    years = max(n / periods_per_year, 1e-9)
    cagr = (equity.iloc[-1] / initial_cash) ** (1 / years) - 1.0

    std = returns.std()
    sharpe = (returns.mean() / std * np.sqrt(periods_per_year)) if std > 0 else 0.0

    downside = returns[returns < 0].std()
    sortino = (returns.mean() / downside * np.sqrt(periods_per_year)) if downside > 0 else 0.0

    wins = [t for t in trades if t["return_pct"] > 0]
    win_rate = (len(wins) / len(trades)) if trades else 0.0
    avg_trade = np.mean([t["return_pct"] for t in trades]) if trades else 0.0
    exposure = float((returns != 0).mean())

    return {
        "total_return_pct": round(total_return * 100, 2),
        "benchmark_return_pct": round(bench_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(float(sharpe), 2),
        "sortino": round(float(sortino), 2),
        "max_drawdown_pct": round(_max_drawdown(equity) * 100, 2),
        "num_trades": len(trades),
        "win_rate_pct": round(win_rate * 100, 1),
        "avg_trade_pct": round(float(avg_trade), 2),
        "final_equity": round(float(equity.iloc[-1]), 2),
        "exposure_pct": round(exposure * 100, 1),
    }
