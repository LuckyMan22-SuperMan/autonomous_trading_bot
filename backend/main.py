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
