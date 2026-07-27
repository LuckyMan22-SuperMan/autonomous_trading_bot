"""Trading strategies.

Each strategy is a function that takes a price DataFrame (with a 'Close'
column) and returns a pandas Series of *target positions* aligned to the
index, where 1 = fully long and 0 = flat (no shorting, for simplicity).

The backtester and the paper trader both consume this same signal, so a
strategy written once works in both modes.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np
import pandas as pd


def sma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """Long when fast SMA is above slow SMA."""
    close = df["Close"]
    fast_ma = close.rolling(fast).mean()
    slow_ma = close.rolling(slow).mean()
    pos = (fast_ma > slow_ma).astype(float)
    return pos.fillna(0.0)


def rsi_reversion(df: pd.DataFrame, period: int = 14,
                  oversold: float = 30, overbought: float = 70) -> pd.Series:
    """Buy when RSI crosses up out of oversold, exit above overbought."""
    close = df["Close"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    pos = pd.Series(index=close.index, dtype=float)
    holding = 0.0
    for i in range(len(close)):
        r = rsi.iloc[i]
        if np.isnan(r):
            pos.iloc[i] = 0.0
            continue
        if holding == 0.0 and r < oversold:
            holding = 1.0
        elif holding == 1.0 and r > overbought:
            holding = 0.0
        pos.iloc[i] = holding
    return pos

# Registry: name -> (function, default_params, human label)
STRATEGIES: Dict[str, Dict] = {
    "sma_crossover": {
        "fn": sma_crossover,
        "label": "SMA Crossover",
        "params": {"fast": 20, "slow": 50},
    },
    "rsi_reversion": {
        "fn": rsi_reversion,
        "label": "RSI Mean Reversion",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
    },
    "macd_trend": {
        "fn": macd_trend,
        "label": "MACD Trend",
        "params": {"fast": 12, "slow": 26, "signal": 9},
    },
    "bollinger_reversion": {
        "fn": bollinger_reversion,
        "label": "Bollinger Reversion",
        "params": {"period": 20, "num_std": 2.0},
    },
    "buy_and_hold": {
        "fn": buy_and_hold,
        "label": "Buy & Hold",
        "params": {},
    },
}
