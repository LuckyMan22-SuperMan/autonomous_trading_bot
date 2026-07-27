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
