"""Trading strategies.

Each strategy is a function that takes a price DataFrame (with a 'Close'
column) and returns a pandas Series of *target positions* aligned to the
index, where 1 = fully long and 0 = flat (no shorting, for simplicity).

The backtester and the paper trader both consume this same signal, so a
strategy written once works in both modes.
"""
