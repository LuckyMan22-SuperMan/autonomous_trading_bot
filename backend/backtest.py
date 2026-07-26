"""Vectorized backtesting engine + performance metrics.

The engine takes a price frame and a target-position series (0/1), applies a
1-bar execution lag (you trade on the *next* bar to avoid look-ahead bias),
deducts a per-trade commission, and produces an equity curve plus a set of
standard performance metrics.
"""
