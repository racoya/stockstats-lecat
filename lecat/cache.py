"""Context Cache — Shared memoization for indicator calculations.

In a population of 1000 strategies, RSI(14) might appear 500 times.
Since MarketContext is immutable for a given generation, we can cache
the full indicator array and look up individual bar values.

This cache persists across evaluations within a single backtest run,
dramatically reducing redundant computation.
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from lecat.context import MarketContext
from lecat.registry import FunctionResult


class IndicatorCache:
    """Cross-bar indicator cache for a single MarketContext.

    Caches full indicator arrays keyed by (function_name, args_tuple).
    Automatically invalidated when the MarketContext changes (different id).

    Usage:
        cache = IndicatorCache()
        cache.get_or_compute("RSI", (14,), ctx, rsi_compute_fn)
    """

    def __init__(self) -> None:
        self._cache: dict[tuple, list[float | None]] = {}
        self._context_id: int | None = None
        self._hits = 0
        self._misses = 0

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        self._context_id = None

    def get_or_compute(
        self,
        func_name: str,
        args_tuple: tuple,
        bar_index: int,
        compute_fn: Callable[[], FunctionResult],
    ) -> FunctionResult:
        """Get a cached value or compute and cache it.

        Args:
            func_name: Function identifier (e.g., "RSI").
            args_tuple: Tuple of argument values.
            bar_index: Current bar index.
            compute_fn: Callable returning FunctionResult if not cached.

        Returns:
            Cached or freshly computed FunctionResult.
        """
        key = (func_name, args_tuple)

        # Check if we have this function+args cached
        if key in self._cache:
            cached_array = self._cache[key]
            if bar_index < len(cached_array) and cached_array[bar_index] is not None:
                self._hits += 1
                return FunctionResult.success(cached_array[bar_index])

        # Compute
        self._misses += 1
        result = compute_fn()

        if result.is_valid and result.value is not None:
            # Store in cache
            if key not in self._cache:
                self._cache[key] = [None] * (bar_index + 1)
            # Extend if needed
            while len(self._cache[key]) <= bar_index:
                self._cache[key].append(None)
            self._cache[key][bar_index] = result.value

        return result

    @property
    def stats(self) -> dict[str, int]:
        """Cache hit/miss statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "entries": len(self._cache),
        }

    def __repr__(self) -> str:
        total = self._hits + self._misses
        rate = (self._hits / total * 100) if total > 0 else 0
        return f"IndicatorCache(entries={len(self._cache)}, hits={self._hits}, misses={self._misses}, rate={rate:.0f}%)"
