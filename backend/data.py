"""Market data access via yfinance, with a small in-memory cache.

Provides two access patterns:
  * get_history()  -> daily OHLCV over a period (used for backtesting)
  * get_intraday() -> recent 1m/5m bars (used for live paper trading)

Two data sources are supported via the `source` argument:
  * "yahoo"     -> real market data from Yahoo Finance (needs internet)
  * "synthetic" -> locally generated realistic price data (works offline;
                   useful on restricted/corporate networks that block Yahoo)
"""
