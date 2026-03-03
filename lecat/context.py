"""MarketContext — The read-only data layer for LECAT evaluation.

Provides OHLCV market data and bar position to the Evaluator and
registered indicator functions. Immutable after construction.

Design notes:
  - Uses `Sequence[float]` for data arrays, compatible with both plain
    Python lists and numpy arrays.
  - `with_index()` is O(1) — creates a shallow copy with a different
    bar_index. Data array references are shared, not copied (CR-001).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence


@dataclass(frozen=True)
class MarketContext:
    """Read-only market data for expression evaluation.

    Attributes:
        open:      Open prices for each bar.
        high:      High prices for each bar.
        low:       Low prices for each bar.
        close:     Close prices for each bar.
        volume:    Volume for each bar.
        bar_index: Current bar being evaluated (0-indexed).
        symbol:    Ticker symbol (e.g., "BTCUSD").
        timeframe: Candle timeframe (e.g., "1D", "4H").
    """

    open: Sequence[float]
    high: Sequence[float]
    low: Sequence[float]
    close: Sequence[float]
    volume: Sequence[float]
    bar_index: int
    symbol: str = ""
    timeframe: str = ""

    def __post_init__(self) -> None:
        if self.bar_index < 0:
            raise ValueError(f"bar_index must be >= 0, got {self.bar_index}")
        if self.bar_index >= len(self.close):
            raise ValueError(
                f"bar_index {self.bar_index} out of range for data of length {len(self.close)}"
            )

    @property
    def total_bars(self) -> int:
        """Total number of bars in the dataset."""
        return len(self.close)

    def with_index(self, new_index: int) -> MarketContext:
        """Return a lightweight copy pointing to a different bar.

        This is the core mechanism for Context Shifting (CR-001).
        O(1) — only bar_index changes; data arrays are shared.

        Args:
            new_index: Target bar index (must be >= 0 and <= bar_index).

        Returns:
            New MarketContext with bar_index = new_index.

        Raises:
            ValueError: If new_index < 0.
            LookAheadError: If new_index > current bar_index.
        """
        if new_index < 0:
            raise ValueError(f"new_index must be >= 0, got {new_index}")
        if new_index > self.bar_index:
            raise LookAheadError(
                f"Cannot shift to bar {new_index} from bar {self.bar_index}. "
                f"Look-ahead bias detected."
            )
        return replace(self, bar_index=new_index)

    def get_window(self, field: str, lookback: int) -> Sequence[float]:
        """Get a lookback window of data ending at bar_index (inclusive).

        Args:
            field: One of "open", "high", "low", "close", "volume".
            lookback: Number of bars to include.

        Returns:
            Slice of the requested field of length `lookback`.

        Raises:
            InsufficientDataError: If not enough bars available.
            ValueError: If field name is invalid.
        """
        data = self._get_field(field)
        start = self.bar_index - lookback + 1
        if start < 0:
            raise InsufficientDataError(
                f"Need {lookback} bars for {field}, but only {self.bar_index + 1} available"
            )
        return data[start : self.bar_index + 1]

    def _get_field(self, field: str) -> Sequence[float]:
        """Resolve a field name to its data array."""
        fields = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        if field not in fields:
            raise ValueError(
                f"Unknown field '{field}'. Valid fields: {list(fields.keys())}"
            )
        return fields[field]


class LookAheadError(Exception):
    """Raised when an operation attempts to access future bar data."""


class InsufficientDataError(Exception):
    """Raised when not enough historical bars are available for a calculation."""
