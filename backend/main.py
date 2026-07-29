"""FastAPI backend for the Autonomous Trading Bot.

Endpoints:
    GET  /api/strategies        -> available strategies + default params
    POST /api/backtest          -> run a backtest, return equity curve + metrics
    POST /api/paper/start       -> start a live paper-trading session
    POST /api/paper/stop        -> stop the session
    GET  /api/paper/status      -> current session status + equity history
    GET  /api/health            -> health check

Serves the static dashboard from ../static at "/".
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import backtest as bt
from . import data
from . import strategies
from .paper import trader

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Autonomous Trading Bot", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class BacktestRequest(BaseModel):
    ticker: str = "RELIANCE.NS"
    strategy: str = "sma_crossover"
    period: str = "2y"
    interval: str = "1d"
    initial_cash: float = 10_000.0
    commission: float = 0.0005
    source: str = "yahoo"
    market: str = "india"
    params: dict | None = None


class PaperStartRequest(BaseModel):
    ticker: str = "RELIANCE.NS"
    strategy: str = "sma_crossover"
    initial_cash: float = 10_000.0
    interval_sec: int = 15
    bar_interval: str = "5m"
    source: str = "yahoo"
    market: str = "india"
    params: dict | None = None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/strategies")
def list_strategies() -> dict:
    return {
        name: {"label": spec["label"], "params": spec["params"]}
        for name, spec in strategies.STRATEGIES.items()
    }


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest) -> dict:
    try:
        df = data.get_history(req.ticker, period=req.period, interval=req.interval,
                              source=req.source, market=req.market)
        signal = strategies.get_signal(req.strategy, df, req.params)
        ppy = 252 if req.interval == "1d" else 252 * 6
        result = bt.run_backtest(
            df, signal,
            initial_cash=req.initial_cash,
            commission=req.commission,
            periods_per_year=ppy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}")
    result["ticker"] = req.ticker.upper()
    result["strategy"] = req.strategy
    return result


@app.post("/api/paper/start")
def paper_start(req: PaperStartRequest) -> dict:
    try:
        return trader.start(
            ticker=req.ticker,
            strategy=req.strategy,
            params=req.params,
            initial_cash=req.initial_cash,
            interval_sec=req.interval_sec,
            bar_interval=req.bar_interval,
            source=req.source,
            market=req.market,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/paper/stop")
def paper_stop() -> dict:
    return trader.stop()


@app.get("/api/paper/status")
def paper_status() -> dict:
    return trader.status()
