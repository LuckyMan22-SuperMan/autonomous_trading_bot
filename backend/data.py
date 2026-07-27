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
