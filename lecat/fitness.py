"""Fitness Calculator — Strategy performance scoring for LECAT.

Calculates PnL, Sharpe Ratio, and composite fitness from a BacktestResult
and MarketContext. Used by the optimizer to rank strategies.

Trade simulation: Buy at next open on True signal, sell at next open on
False signal (or hold until exit).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from lecat.backtester import BacktestResult
from lecat.context import MarketContext


@dataclass(frozen=True)
class FitnessResult:
    """Fitness evaluation of a strategy.

    Attributes:
        total_return_pct: Cumulative return as percentage.
        sharpe_ratio: Annualized risk-adjusted return (assuming 252 trading days).
        num_trades: Total number of completed round-trip trades.
        win_rate: Fraction of winning trades (0.0–1.0).
        max_drawdown_pct: Maximum peak-to-trough drawdown as percentage.
        fitness_score: Composite score used for ranking.
    """

    total_return_pct: float
    sharpe_ratio: float
    num_trades: int
    win_rate: float
    max_drawdown_pct: float
    fitness_score: float

    def __repr__(self) -> str:
        return (
            f"Fitness(score={self.fitness_score:.4f}, "
            f"return={self.total_return_pct:+.2f}%, "
            f"sharpe={self.sharpe_ratio:.2f}, "
            f"trades={self.num_trades}, "
            f"win={self.win_rate:.0%})"
        )


# Minimum trades to avoid overfitting penalty
MIN_TRADES_THRESHOLD = 5

# Annualization factor (trading days per year)
TRADING_DAYS_PER_YEAR = 252


def calculate_fitness(
    backtest: BacktestResult,
    context: MarketContext,
) -> FitnessResult:
    """Calculate comprehensive fitness metrics for a strategy.

    Args:
        backtest: The backtest result containing signal array.
        context: Market data for PnL calculation.

    Returns:
        FitnessResult with all metrics and composite score.
    """
    trades = _simulate_trades(backtest.signals, context)

    total_return_pct = _total_return(trades)
    sharpe = _sharpe_ratio(trades)
    num_trades = len(trades)
    win_rate = _win_rate(trades)
    max_dd = _max_drawdown(trades)

    # Composite fitness score
    fitness_score = _composite_score(
        total_return_pct=total_return_pct,
        sharpe_ratio=sharpe,
        num_trades=num_trades,
        win_rate=win_rate,
        max_drawdown_pct=max_dd,
    )

    return FitnessResult(
        total_return_pct=total_return_pct,
        sharpe_ratio=sharpe,
        num_trades=num_trades,
        win_rate=win_rate,
        max_drawdown_pct=max_dd,
        fitness_score=fitness_score,
    )


# ------------------------------------------------------------------
# Trade simulation
# ------------------------------------------------------------------


@dataclass
class Trade:
    """A completed round-trip trade."""

    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float

    @property
    def return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return ((self.exit_price - self.entry_price) / self.entry_price) * 100


def _simulate_trades(
    signals: list[bool], context: MarketContext
) -> list[Trade]:
    """Simulate buy-on-True, sell-on-False trades.

    Uses the close price for entry/exit (simplified).
    """
    trades: list[Trade] = []
    in_position = False
    entry_idx = 0
    entry_price = 0.0

    for i, sig in enumerate(signals):
        if sig and not in_position:
            # Enter position
            in_position = True
            entry_idx = i
            entry_price = float(context.close[i])
        elif not sig and in_position:
            # Exit position
            exit_price = float(context.close[i])
            trades.append(Trade(
                entry_idx=entry_idx,
                entry_price=entry_price,
                exit_idx=i,
                exit_price=exit_price,
            ))
            in_position = False

    # Close any open position at the last bar
    if in_position and len(signals) > 0:
        last_idx = len(signals) - 1
        trades.append(Trade(
            entry_idx=entry_idx,
            entry_price=entry_price,
            exit_idx=last_idx,
            exit_price=float(context.close[last_idx]),
        ))

    return trades


# ------------------------------------------------------------------
# Metric calculations
# ------------------------------------------------------------------


def _total_return(trades: list[Trade]) -> float:
    """Cumulative return from sequential trades."""
    if not trades:
        return 0.0
    equity = 1.0
    for t in trades:
        equity *= (1.0 + t.return_pct / 100.0)
    return (equity - 1.0) * 100.0


def _sharpe_ratio(trades: list[Trade]) -> float:
    """Annualized Sharpe Ratio from trade returns."""
    if len(trades) < 2:
        return 0.0

    returns = [t.return_pct / 100.0 for t in trades]
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
    std_ret = math.sqrt(variance) if variance > 0 else 0.0

    if std_ret == 0:
        return 0.0

    # Annualize: assume each trade averages ~5 days
    trades_per_year = TRADING_DAYS_PER_YEAR / max(
        sum(t.exit_idx - t.entry_idx for t in trades) / len(trades), 1
    )
    return (mean_ret / std_ret) * math.sqrt(trades_per_year)


def _win_rate(trades: list[Trade]) -> float:
    """Fraction of trades with positive return."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.return_pct > 0)
    return wins / len(trades)


def _max_drawdown(trades: list[Trade]) -> float:
    """Maximum drawdown as a percentage of peak equity."""
    if not trades:
        return 0.0

    equity = 1.0
    peak = 1.0
    max_dd = 0.0

    for t in trades:
        equity *= (1.0 + t.return_pct / 100.0)
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak * 100.0
        max_dd = max(max_dd, drawdown)

    return max_dd


def _composite_score(
    total_return_pct: float,
    sharpe_ratio: float,
    num_trades: int,
    win_rate: float,
    max_drawdown_pct: float,
) -> float:
    """Compute a composite fitness score.

    Weighting:
      - 40% Sharpe Ratio (risk-adjusted)
      - 30% Total Return (absolute performance)
      - 20% Win Rate (consistency)
      - 10% Drawdown penalty

    Penalty for too few trades (< MIN_TRADES_THRESHOLD).
    """
    # Normalize components to similar scales
    sharpe_component = sharpe_ratio * 0.4
    return_component = math.copysign(math.log1p(abs(total_return_pct)), total_return_pct) * 0.3
    win_component = (win_rate - 0.5) * 2.0 * 0.2  # Center at 0
    dd_component = -max_drawdown_pct / 100.0 * 0.1

    score = sharpe_component + return_component + win_component + dd_component

    # Penalty for insufficient trades
    if num_trades < MIN_TRADES_THRESHOLD:
        penalty = 1.0 - (num_trades / MIN_TRADES_THRESHOLD)
        score *= (1.0 - penalty * 0.8)

    return score
