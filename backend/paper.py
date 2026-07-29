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
    def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self.error = str(exc)
            self._stop.wait(self.interval_sec)

    def _tick(self) -> None:
        df = data.get_intraday(self.ticker, period="5d",
                               interval=self.bar_interval, ttl=self.interval_sec,
                               source=self.source, market=self.market)
        signal = strategies.get_signal(self.strategy, df, self.params)
        target = float(signal.iloc[-1]) if len(signal) else 0.0
        price = float(df["Close"].iloc[-1])

        with self._lock:
            self.last_price = price
            self.error = None
            holding = self.shares > 0

            if target >= 0.5 and not holding and self.cash > 0:
                # Go all-in.
                spend = self.cash * (1 - self.commission)
                self.shares = spend / price
                self.cash = 0.0
                self._log_trade("BUY", price)
            elif target < 0.5 and holding:
                # Exit fully.
                proceeds = self.shares * price * (1 - self.commission)
                self.cash += proceeds
                self.shares = 0.0
                self._log_trade("SELL", price)

        self._record_equity()

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

    # ------------------------------------------------------------------ #
    def status(self) -> Dict:
        with self._lock:
            equity = self._equity_value(self.last_price)
            pnl = equity - self.initial_cash
            pnl_pct = (pnl / self.initial_cash * 100) if self.initial_cash else 0.0
            return {
                "running": self.running,
                "ticker": self.ticker,
                "strategy": self.strategy,
                "started_at": self.started_at,
                "interval_sec": self.interval_sec,
                "bar_interval": self.bar_interval,
                "market": self.market,
                "cash": round(self.cash, 2),
                "shares": round(self.shares, 4),
                "last_price": round(self.last_price, 4),
                "position": "LONG" if self.shares > 0 else "FLAT",
                "equity": round(equity, 2),
                "initial_cash": round(self.initial_cash, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "num_trades": len(self.trade_log),
                "error": self.error,
                "equity_history": self.equity_history[-500:],
                "trade_log": self.trade_log[-100:],
            }


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


# Module-level singleton used by the API.
trader = PaperTrader()
