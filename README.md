# Autonomous Trading Bot

A full-stack trading bot that lets you **backtest** strategies on historical
stock data and run them **live in a paper-trading loop** (simulated money, no
real orders). Same strategy code powers both modes. Built with **FastAPI**,
**yfinance**, and a **Chart.js** dashboard.

> Educational project only. It does **not** place real orders and is not
> financial advice.

## Features

- **Backtesting engine** with a 1-bar execution lag (no look-ahead bias) and commissions.
- **Metrics**: total return vs. buy & hold, CAGR, Sharpe, Sortino, max drawdown, win rate, exposure, trade count.
- **Strategies**: SMA crossover, RSI mean reversion, MACD trend, Bollinger reversion, buy & hold — each with tunable parameters.
- **Live paper trading**: background thread pulls intraday bars, computes the signal, and executes simulated all-in/all-out orders while tracking equity and fills in real time.
- **Dashboard**: equity curve vs. benchmark, live portfolio chart, metric cards, and trade/fill tables.

## Architecture

```
trading-bot/
├── backend/
│   ├── main.py          # FastAPI app + endpoints, serves the dashboard
│   ├── data.py          # yfinance data access + TTL cache
│   ├── strategies.py    # strategy signal functions + registry
│   ├── backtest.py      # vectorized backtest engine + metrics
│   └── paper.py         # live paper-trading engine (threaded)
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```

## Setup

### Windows
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python backend/main.py
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python backend/main.py
```

Then open http://127.0.0.1:8000

To use a different port: set `PORT` (e.g. `PORT=8010 python backend/main.py`).

## API

| Method | Endpoint             | Body                              | Returns                         |
|--------|----------------------|-----------------------------------|---------------------------------|
| GET    | `/api/health`        | —                                 | `{"status":"ok"}`               |
| GET    | `/api/strategies`    | —                                 | strategies + default params     |
| POST   | `/api/backtest`      | ticker, strategy, period, ...     | equity curve + metrics + trades |
| POST   | `/api/paper/start`   | ticker, strategy, cash, interval  | session status                  |
| POST   | `/api/paper/stop`    | —                                 | final status                    |
| GET    | `/api/paper/status`  | —                                 | live status + equity history    |

## How the backtest works

- A strategy returns a target position series (`1` = long, `0` = flat).
- Positions are shifted forward one bar (you trade on the *next* open) to avoid look-ahead bias.
- Strategy return per bar = `position * price_return - turnover * commission`.
- Equity = cumulative product of `(1 + strategy_return) * initial_cash`.

## Data sources

Pick a source in the dashboard (or via the `source` field / `TB_DATA_SOURCE` env var):

- **`yahoo`** (default): real market data via `yfinance`. Needs internet access to Yahoo Finance.
- **`synthetic`**: realistic price data generated locally with geometric Brownian motion. Works fully offline — use it if you're on a restricted/corporate network that blocks Yahoo, or for deterministic demos.


## Notes / limitations

- **Intraday data** (paper trading) is only available during and shortly after
  US market hours. Outside those hours the price/equity line stays flat — that's
  expected, not a bug.
- Long/flat only (no shorting or leverage) to keep the logic clear.
- Data is from Yahoo Finance via `yfinance`; occasional rate limits or gaps can occur.

## Ideas to extend

- Add short selling, position sizing, and stop-losses / take-profits.
- Add walk-forward optimization and parameter grid search.
- Swap in an ML strategy (e.g. gradient-boosted classifier on engineered features).
- Persist sessions/results to SQLite; add multi-asset portfolios.
- Dockerize and deploy; wire a real broker sandbox API (e.g. Alpaca paper trading).

#Problem with deployment
Yahoo Finance actively fingerprints and blocks requests coming from datacenter/cloud IPs (Render, AWS, GCP, etc.) far more aggressively than residential IPs like my local machine's. Instead of returning stock data, Yahoo was sending back an empty or non-JSON response, which yfinance then failed to parse as JSON, producing that JSONDecodeError.
Instead modern yfinance versions actually manage their own internal session via curl_cffi, a library that can impersonate a real browser's TLS/HTTP fingerprint, which lets requests get past Yahoo's blocking.