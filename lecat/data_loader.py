"""Data Loader — CSV and DataFrame ingestion for LECAT.

Loads financial time-series data from CSV files into MarketContext.
Supports standard OHLCV format with date parsing, missing value handling,
and data validation.

Optional numpy support: uses float32 arrays if numpy is available,
falls back to standard Python lists otherwise.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from lecat.context import MarketContext

# Try numpy for efficient arrays, fall back to lists
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# Known column name mappings (case-insensitive)
_COLUMN_ALIASES = {
    "open": ["open", "o", "open_price"],
    "high": ["high", "h", "high_price"],
    "low": ["low", "l", "low_price"],
    "close": ["close", "c", "close_price", "adj close", "adj_close"],
    "volume": ["volume", "vol", "v"],
    "date": ["date", "datetime", "time", "timestamp"],
}


def load_from_csv(
    filepath: str | Path,
    symbol: str = "",
    timeframe: str = "",
) -> MarketContext:
    """Load OHLCV data from a CSV file into a MarketContext.

    Args:
        filepath: Path to the CSV file.
        symbol: Optional ticker symbol (e.g., "AAPL").
        timeframe: Optional candle timeframe (e.g., "1D").

    Returns:
        MarketContext with loaded and validated data.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        ValueError: If required columns are missing or data is invalid.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")

        # Map CSV columns to standard OHLCV names
        col_map = _resolve_columns(reader.fieldnames)

        rows: list[dict[str, str]] = list(reader)

    if not rows:
        raise ValueError("CSV file contains no data rows")

    # Extract and convert columns
    opens = _extract_column(rows, col_map["open"])
    highs = _extract_column(rows, col_map["high"])
    lows = _extract_column(rows, col_map["low"])
    closes = _extract_column(rows, col_map["close"])
    volumes = _extract_column(rows, col_map["volume"])

    # Forward-fill missing values
    opens = _forward_fill(opens)
    highs = _forward_fill(highs)
    lows = _forward_fill(lows)
    closes = _forward_fill(closes)
    volumes = _forward_fill(volumes)

    # Convert to efficient arrays if numpy available
    if HAS_NUMPY:
        opens = np.array(opens, dtype=np.float32).tolist()
        highs = np.array(highs, dtype=np.float32).tolist()
        lows = np.array(lows, dtype=np.float32).tolist()
        closes = np.array(closes, dtype=np.float32).tolist()
        volumes = np.array(volumes, dtype=np.float32).tolist()

    # Validate data integrity
    _validate_data(opens, highs, lows, closes, volumes)

    return MarketContext(
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        volume=volumes,
        bar_index=len(closes) - 1,
        symbol=symbol,
        timeframe=timeframe,
    )


def load_from_lists(
    open_prices: list[float],
    high_prices: list[float],
    low_prices: list[float],
    close_prices: list[float],
    volumes: list[float],
    symbol: str = "",
    timeframe: str = "",
) -> MarketContext:
    """Create a MarketContext from raw Python lists.

    Convenience function for programmatic data loading.
    """
    n = len(close_prices)
    if not (len(open_prices) == len(high_prices) == len(low_prices) == n == len(volumes)):
        raise ValueError("All price arrays must have the same length")
    if n == 0:
        raise ValueError("Price arrays must not be empty")

    return MarketContext(
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        volume=volumes,
        bar_index=n - 1,
        symbol=symbol,
        timeframe=timeframe,
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    """Map CSV column names to standard OHLCV field names."""
    col_map: dict[str, str] = {}
    lower_fields = {f.lower().strip(): f for f in fieldnames}

    for standard_name, aliases in _COLUMN_ALIASES.items():
        if standard_name == "date":
            continue  # Date is optional
        found = False
        for alias in aliases:
            if alias in lower_fields:
                col_map[standard_name] = lower_fields[alias]
                found = True
                break
        if not found:
            raise ValueError(
                f"Required column '{standard_name}' not found. "
                f"Available columns: {fieldnames}"
            )

    return col_map


def _extract_column(rows: list[dict[str, str]], col_name: str) -> list[float]:
    """Extract a column as floats, handling empty/invalid values as NaN."""
    result: list[float] = []
    for row in rows:
        raw = row.get(col_name, "").strip()
        if raw == "" or raw.lower() == "nan" or raw.lower() == "null":
            result.append(float("nan"))
        else:
            try:
                result.append(float(raw))
            except ValueError:
                result.append(float("nan"))
    return result


def _forward_fill(data: list[float]) -> list[float]:
    """Forward-fill NaN values with the last known good value."""
    import math

    result = data.copy()
    last_valid = 0.0

    for i, val in enumerate(result):
        if math.isnan(val):
            result[i] = last_valid
        else:
            last_valid = val

    return result


def _validate_data(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
) -> None:
    """Validate basic data integrity."""
    import math

    n = len(closes)
    if n == 0:
        raise ValueError("No data rows after processing")

    # Check for remaining NaN values
    for name, data in [("open", opens), ("high", highs), ("low", lows),
                       ("close", closes), ("volume", volumes)]:
        nan_count = sum(1 for v in data if math.isnan(v))
        if nan_count > 0:
            raise ValueError(f"Column '{name}' has {nan_count} NaN values after forward fill")

    # Check for negative prices
    for i in range(n):
        if closes[i] < 0 or opens[i] < 0:
            raise ValueError(f"Negative price at row {i}")
