"""Live paper-trading engine.

Runs a background thread that periodically:
  1. pulls recent intraday bars for the ticker,
  2. computes the selected strategy's target position,
  3. executes simulated market orders (all-in / all-out) against fake cash,
  4. records the portfolio equity and every fill.

Everything is in-memory. A single active session is supported at a time,
which keeps the demo simple and predictable.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import data
from . import strategies


class PaperTrader:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._reset_state()

    def _reset_state(self) -> None:
        self.running = False
        self.ticker = ""
        self.strategy = ""
        self.params: dict = {}
        self.interval_sec = 15
        self.bar_interval = "5m"
        self.source = "yahoo"
        self.initial_cash = 10_000.0
        self.commission = 0.0005
        self.cash = 0.0
        self.shares = 0.0
        self.last_price = 0.0
        self.error: Optional[str] = None
        self.started_at: Optional[str] = None
        self.equity_history: List[Dict] = []
        self.trade_log: List[Dict] = []

