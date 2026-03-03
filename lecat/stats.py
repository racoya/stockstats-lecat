"""Stats — Basic performance metrics for LECAT signal arrays.

Computes signal statistics from boolean arrays produced by the Backtester.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyStats:
    """Basic statistics computed from a backtest signal array.

    Attributes:
        total_signals: Number of bars where signal is True.
        total_bars: Total bars evaluated (excluding warmup).
        signal_density: Fraction of bars with active signal (0.0–1.0).
        longest_streak: Longest consecutive True streak.
        longest_gap: Longest consecutive False streak (after warmup).
    """

    total_signals: int
    total_bars: int
    signal_density: float
    longest_streak: int
    longest_gap: int

    def __repr__(self) -> str:
        pct = self.signal_density * 100
        return (
            f"StrategyStats(signals={self.total_signals}/{self.total_bars} "
            f"({pct:.1f}%), streak={self.longest_streak}, gap={self.longest_gap})"
        )


def compute_stats(signals: list[bool], warmup: int = 0) -> StrategyStats:
    """Compute statistics from a boolean signal array.

    Args:
        signals: Full signal array (including warmup bars as False).
        warmup: Number of warmup bars at the start to exclude.

    Returns:
        StrategyStats with computed metrics.
    """
    # Only evaluate post-warmup bars
    active_signals = signals[warmup:]
    total_bars = len(active_signals)

    if total_bars == 0:
        return StrategyStats(
            total_signals=0,
            total_bars=0,
            signal_density=0.0,
            longest_streak=0,
            longest_gap=0,
        )

    total_signals = sum(active_signals)
    signal_density = total_signals / total_bars if total_bars > 0 else 0.0

    # Calculate streaks
    longest_streak = 0
    longest_gap = 0
    current_streak = 0
    current_gap = 0

    for sig in active_signals:
        if sig:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
            current_gap = 0
        else:
            current_gap += 1
            longest_gap = max(longest_gap, current_gap)
            current_streak = 0

    # Final gap check
    longest_gap = max(longest_gap, current_gap)

    return StrategyStats(
        total_signals=total_signals,
        total_bars=total_bars,
        signal_density=signal_density,
        longest_streak=longest_streak,
        longest_gap=longest_gap,
    )
