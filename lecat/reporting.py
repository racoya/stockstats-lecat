"""Reporting — Equity curve visualization for LECAT backtests.

Generates equity curve charts from BacktestResult data. Uses matplotlib
if available, otherwise outputs data as CSV for external plotting.
"""

from __future__ import annotations

import os
from pathlib import Path

from lecat.backtester import BacktestResult
from lecat.context import MarketContext
from lecat.fitness import FitnessResult, _simulate_trades

# Optional matplotlib
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def plot_equity_curve(
    backtest: BacktestResult,
    context: MarketContext,
    title: str = "Strategy Equity Curve",
    output_path: str | Path = "backtest_chart.png",
    show_benchmark: bool = True,
    show_signals: bool = True,
) -> Path:
    """Generate an equity curve chart.

    Args:
        backtest: BacktestResult with signal array.
        context: MarketContext for price data.
        title: Chart title.
        output_path: Path to save the chart image.
        show_benchmark: Overlay buy-and-hold benchmark.
        show_signals: Show buy/sell markers.

    Returns:
        Path to the generated chart file.

    Raises:
        RuntimeError: If matplotlib is not available.
    """
    output_path = Path(output_path)

    if not HAS_MATPLOTLIB:
        # Fallback: save equity data as CSV
        return _save_equity_csv(backtest, context, output_path.with_suffix(".csv"))

    # Calculate equity curves
    strategy_equity = _calculate_equity_curve(backtest.signals, context)
    benchmark_equity = _calculate_benchmark_curve(context)

    # Get trade points for markers
    trades = _simulate_trades(backtest.signals, context)

    # Create figure
    if show_signals and trades:
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(14, 8), height_ratios=[3, 1],
            gridspec_kw={"hspace": 0.3},
        )
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(14, 6))
        ax2 = None

    # Style
    fig.patch.set_facecolor("#1a1a2e")
    ax1.set_facecolor("#16213e")

    # Plot equity curve
    ax1.plot(
        strategy_equity, color="#00d2ff", linewidth=1.5,
        label="Strategy", alpha=0.9,
    )

    if show_benchmark:
        ax1.plot(
            benchmark_equity, color="#ff6b6b", linewidth=1.0,
            label="Buy & Hold", alpha=0.7, linestyle="--",
        )

    # Buy/Sell markers
    if trades:
        buy_x = [t.entry_idx for t in trades]
        buy_y = [strategy_equity[i] for i in buy_x if i < len(strategy_equity)]
        sell_x = [t.exit_idx for t in trades]
        sell_y = [strategy_equity[i] for i in sell_x if i < len(strategy_equity)]

        ax1.scatter(
            buy_x[:len(buy_y)], buy_y, marker="^", color="#00ff88",
            s=40, zorder=5, label="Buy", alpha=0.8,
        )
        ax1.scatter(
            sell_x[:len(sell_y)], sell_y, marker="v", color="#ff4444",
            s=40, zorder=5, label="Sell", alpha=0.8,
        )

    ax1.set_title(title, color="white", fontsize=14, fontweight="bold", pad=15)
    ax1.set_ylabel("Cumulative Return (%)", color="white", fontsize=11)
    ax1.set_xlabel("Bar Index", color="white", fontsize=11)
    ax1.legend(
        loc="upper left", facecolor="#1a1a2e", edgecolor="#333",
        labelcolor="white", fontsize=9,
    )
    ax1.tick_params(colors="white")
    ax1.grid(True, alpha=0.15, color="white")
    ax1.axhline(y=0, color="#666", linewidth=0.5, linestyle="-")

    for spine in ax1.spines.values():
        spine.set_color("#333")

    # Signal subplot
    if ax2 is not None:
        ax2.set_facecolor("#16213e")
        signal_colors = ["#00ff88" if s else "#333" for s in backtest.signals]
        ax2.bar(
            range(len(backtest.signals)), [1] * len(backtest.signals),
            color=signal_colors, width=1.0, alpha=0.6,
        )
        ax2.set_ylabel("Signal", color="white", fontsize=9)
        ax2.set_xlabel("Bar Index", color="white", fontsize=11)
        ax2.set_yticks([])
        ax2.tick_params(colors="white")
        for spine in ax2.spines.values():
            spine.set_color("#333")

    # Save
    fig.savefig(
        output_path, dpi=150, bbox_inches="tight",
        facecolor=fig.get_facecolor(), edgecolor="none",
    )
    plt.close(fig)

    return output_path


def plot_optimization_progress(
    generations: list,
    title: str = "Optimization Progress",
    output_path: str | Path = "optimization_progress.png",
) -> Path:
    """Plot fitness progression across generations.

    Args:
        generations: List of GenerationReport objects.
        title: Chart title.
        output_path: Output path for the chart.

    Returns:
        Path to the generated chart file.
    """
    output_path = Path(output_path)

    if not HAS_MATPLOTLIB:
        return _save_progress_csv(generations, output_path.with_suffix(".csv"))

    gens = [r.generation for r in generations]
    best = [r.best_fitness for r in generations]
    avg = [r.avg_fitness for r in generations]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    ax.plot(gens, best, color="#00d2ff", linewidth=2, label="Best Fitness", marker="o", markersize=4)
    ax.plot(gens, avg, color="#ff6b6b", linewidth=1.5, label="Avg Fitness", linestyle="--", alpha=0.7)

    ax.set_title(title, color="white", fontsize=14, fontweight="bold")
    ax.set_xlabel("Generation", color="white")
    ax.set_ylabel("Fitness Score", color="white")
    ax.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="white")
    ax.tick_params(colors="white")
    ax.grid(True, alpha=0.15, color="white")
    for spine in ax.spines.values():
        spine.set_color("#333")

    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return output_path


def generate_report_text(
    backtest: BacktestResult,
    context: MarketContext,
    fitness: FitnessResult,
    label: str = "Strategy",
) -> str:
    """Generate a text summary of a backtest result.

    Args:
        backtest: BacktestResult data.
        context: MarketContext for reference.
        fitness: FitnessResult with metrics.
        label: Label for the report section.

    Returns:
        Formatted text report.
    """
    lines = [
        f"═══ {label} Report ═══",
        f"  Expression: {backtest.expression}",
        f"  Bars:       {backtest.total_bars:,} (warmup: {backtest.warmup_bars})",
        f"  Signals:    {backtest.stats.total_signals:,} ({backtest.stats.signal_density:.1%})",
        f"  Trades:     {fitness.num_trades}",
        f"  Return:     {fitness.total_return_pct:+.2f}%",
        f"  Sharpe:     {fitness.sharpe_ratio:.3f}",
        f"  Win Rate:   {fitness.win_rate:.1%}",
        f"  Max DD:     {fitness.max_drawdown_pct:.2f}%",
        f"  Fitness:    {fitness.fitness_score:.4f}",
        f"  Time:       {backtest.elapsed_ms:.1f}ms",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _calculate_equity_curve(signals: list[bool], context: MarketContext) -> list[float]:
    """Calculate cumulative return curve for the strategy."""
    equity = [0.0]
    in_position = False
    entry_price = 0.0

    for i in range(len(signals)):
        if signals[i] and not in_position:
            in_position = True
            entry_price = float(context.close[i])
            equity.append(equity[-1])
        elif not signals[i] and in_position:
            exit_price = float(context.close[i])
            trade_return = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            equity.append(equity[-1] + trade_return)
            in_position = False
        elif in_position:
            # Mark-to-market: show unrealized PnL
            current_price = float(context.close[i])
            unrealized = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            equity.append(equity[-1] + unrealized - (equity[-1] - equity[-2] if len(equity) > 1 else 0))
        else:
            equity.append(equity[-1])

    return equity[1:]  # Remove initial 0


def _calculate_benchmark_curve(context: MarketContext) -> list[float]:
    """Calculate buy-and-hold benchmark curve."""
    initial = float(context.close[0])
    if initial == 0:
        return [0.0] * len(context.close)
    return [((float(p) - initial) / initial) * 100 for p in context.close]


def _save_equity_csv(
    backtest: BacktestResult,
    context: MarketContext,
    output_path: Path,
) -> Path:
    """Fallback: save equity data as CSV when matplotlib unavailable."""
    import csv as csv_mod

    equity = _calculate_equity_curve(backtest.signals, context)
    with open(output_path, "w", newline="") as f:
        writer = csv_mod.writer(f)
        writer.writerow(["bar_index", "signal", "equity_pct", "close"])
        for i in range(min(len(equity), len(backtest.signals))):
            writer.writerow([
                i,
                int(backtest.signals[i]),
                round(equity[i], 4),
                context.close[i],
            ])
    return output_path


def _save_progress_csv(generations: list, output_path: Path) -> Path:
    """Fallback: save generation data as CSV."""
    import csv as csv_mod

    with open(output_path, "w", newline="") as f:
        writer = csv_mod.writer(f)
        writer.writerow(["generation", "best_fitness", "avg_fitness", "best_expression"])
        for r in generations:
            writer.writerow([r.generation, r.best_fitness, r.avg_fitness, r.best_expression])
    return output_path
