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

