"""Market data access via yfinance, with a small in-memory cache.

Provides two access patterns:
  * get_history()  -> daily OHLCV over a period (used for backtesting)
  * get_intraday() -> recent 1m/5m bars (used for live paper trading)

Two data sources are supported via the `source` argument:
  * "yahoo"     -> real market data from Yahoo Finance (needs internet)
  * "synthetic" -> locally generated realistic price data (works offline;
                   useful on restricted/corporate networks that block Yahoo)
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# Simple TTL cache: {(key): (timestamp, dataframe)}
_CACHE: dict[str, Tuple[float, pd.DataFrame]] = {}


def _build_session() -> Optional[requests.Session]:
    """Return a requests session.

    On corporate networks that intercept TLS with a self-signed root CA,
    certificate verification fails. Set TB_INSECURE_SSL=1 to disable
    verification (demo/dev convenience only — never do this in production).
    Alternatively point REQUESTS_CA_BUNDLE at your corporate CA bundle.
    """
    if os.environ.get("TB_INSECURE_SSL", "").lower() in ("1", "true", "yes"):
        session = requests.Session()
        session.verify = False
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:  # noqa: BLE001
            pass
        return session
    return None  # let yfinance use its default (secure) session


_SESSION = _build_session()


def _cache_get(key: str, ttl: float) -> pd.DataFrame | None:
    hit = _CACHE.get(key)
    if hit and (time.time() - hit[0]) < ttl:
        return hit[1].copy()
    return None


def _cache_set(key: str, df: pd.DataFrame) -> None:
    _CACHE[key] = (time.time(), df.copy())


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance columns and keep a clean OHLCV frame."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].dropna()
    df.index = pd.to_datetime(df.index)
    return df


# Default data source/market; can be overridden per-call or via env vars.
DEFAULT_SOURCE = os.environ.get("TB_DATA_SOURCE", "yahoo").lower()
DEFAULT_MARKET = os.environ.get("TB_MARKET", "india").lower()

_PERIOD_TO_DAYS = {
    "6mo": 126, "1y": 252, "2y": 504, "5y": 1260, "10y": 2520,
}
_INTRADAY_MINUTES = {"1m": 1, "5m": 5, "15m": 15}


def _resolve_source(source: Optional[str]) -> str:
    return (source or DEFAULT_SOURCE).lower()


def _resolve_market(market: Optional[str]) -> str:
    return (market or DEFAULT_MARKET).lower()


def _normalize_ticker(ticker: str, market: Optional[str] = None) -> str:
    """Normalize ticker symbols for the selected market."""
    market_key = _resolve_market(market)
    if market_key not in {"india", "us"}:
        raise ValueError(f"Unsupported market '{market_key}'. Use 'india' or 'us'.")

    symbol = (ticker or "").strip()
    if not symbol:
        raise ValueError("Ticker cannot be empty.")

    if market_key == "india":
        upper = symbol.upper()
        if "." in upper:
            return upper
        return f"{upper}.NS"
    return symbol.upper()


def get_history(ticker: str, period: str = "2y", interval: str = "1d",
                ttl: float = 3600, source: Optional[str] = None,
                market: Optional[str] = None) -> pd.DataFrame:
    """Daily (or given interval) history for backtesting."""
    src = _resolve_source(source)
    market_key = _resolve_market(market)
    ticker = _normalize_ticker(ticker, market=market_key)
    key = f"hist:{src}:{market_key}:{ticker}:{period}:{interval}"
    cached = _cache_get(key, ttl)
    if cached is not None:
        return cached
    if src == "synthetic":
        df = _synthetic_history(ticker, period, interval)
    else:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False, session=_SESSION)
        if df is None or df.empty:
            raise ValueError(f"No data returned for '{ticker}'. Check the symbol "
                             f"or switch the data source to 'synthetic'.")
        df = _normalize(df)
    _cache_set(key, df)
    return df
