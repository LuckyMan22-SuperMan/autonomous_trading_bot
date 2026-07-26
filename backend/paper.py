"""Live paper-trading engine.

Runs a background thread that periodically:
  1. pulls recent intraday bars for the ticker,
  2. computes the selected strategy's target position,
  3. executes simulated market orders (all-in / all-out) against fake cash,
  4. records the portfolio equity and every fill.

Everything is in-memory. A single active session is supported at a time,
which keeps the demo simple and predictable.
"""
