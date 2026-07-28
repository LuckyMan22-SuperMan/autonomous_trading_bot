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
        self.market = "india"
        self.initial_cash = 10_000.0
        self.commission = 0.0005
        self.cash = 0.0
        self.shares = 0.0
        self.last_price = 0.0
        self.error: Optional[str] = None
        self.started_at: Optional[str] = None
        self.equity_history: List[Dict] = []
        self.trade_log: List[Dict] = []

    # ------------------------------------------------------------------ #
    def start(self, ticker: str, strategy: str, params: dict | None = None,
              initial_cash: float = 10_000.0, interval_sec: int = 15,
              bar_interval: str = "5m", source: str = "yahoo",
              market: str = "india") -> Dict:
        with self._lock:
            if self.running:
                raise RuntimeError("A paper-trading session is already running. Stop it first.")
            # Validate the ticker up front so we fail fast.
            price = data.latest_price(ticker, source=source, market=market)

            self._reset_state()
            self.running = True
            self.ticker = ticker.upper()
            self.strategy = strategy
            self.params = params or {}
            self.source = source
            self.initial_cash = float(initial_cash)
            self.cash = float(initial_cash)
            self.interval_sec = max(5, int(interval_sec))
            self.bar_interval = bar_interval
            self.market = (market or "india").lower()
            self.last_price = price
            self.started_at = _now()
            self._stop.clear()

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._record_equity()  # seed the first point
        return self.status()

    def stop(self) -> Dict:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        with self._lock:
            self.running = False
        return self.status()

    # ------------------------------------------------------------------ #
    def _log_trade(self, side: str, price: float) -> None:
        self.trade_log.append({
            "time": _now(),
            "side": side,
            "price": round(price, 4),
            "shares": round(self.shares if side == "BUY" else 0.0, 4),
            "equity": round(self._equity_value(price), 2),
        })

    def _equity_value(self, price: float) -> float:
        return self.cash + self.shares * price

    def _record_equity(self) -> None:
        with self._lock:
            eq = self._equity_value(self.last_price)
            self.equity_history.append({"time": _now(), "equity": round(eq, 2),
                                        "price": round(self.last_price, 4)})
            # Cap history to keep memory/payload bounded.
            if len(self.equity_history) > 2000:
                self.equity_history = self.equity_history[-2000:]
