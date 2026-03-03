"""LECAT CLI — Main entry point for running a full generation + backtest cycle.

Generates random OHLCV data, creates random strategies, compiles and
backtests them, and prints results.

Usage:
    python3 -m lecat.main
    python3 -m lecat.main --strategies 20 --bars 10000 --depth 3
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time

from lecat.backtester import Backtester
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.generator import ExpressionGenerator
from lecat.indicators import register_extended_indicators
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib


def generate_random_ohlcv(
    num_bars: int, seed: int | None = None
) -> MarketContext:
    """Generate synthetic OHLCV data with random-walk prices.

    Args:
        num_bars: Number of bars to generate.
        seed: Random seed for reproducibility.

    Returns:
        MarketContext with generated data, bar_index at last bar.
    """
    rng = random.Random(seed)

    price = 100.0
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[float] = []

    for _ in range(num_bars):
        # Random walk with slight upward drift
        change_pct = rng.gauss(0.0002, 0.02)
        open_price = price
        close_price = price * (1 + change_pct)

        # Ensure positive prices
        close_price = max(close_price, 0.01)

        # High/Low within the bar
        bar_range = abs(close_price - open_price) + rng.uniform(0.1, 2.0)
        high_price = max(open_price, close_price) + rng.uniform(0, bar_range)
        low_price = min(open_price, close_price) - rng.uniform(0, bar_range)
        low_price = max(low_price, 0.01)

        volume = rng.uniform(100, 10000)

        opens.append(round(open_price, 4))
        highs.append(round(high_price, 4))
        lows.append(round(low_price, 4))
        closes.append(round(close_price, 4))
        volumes.append(round(volume, 2))

        price = close_price

    return MarketContext(
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        volume=volumes,
        bar_index=num_bars - 1,
    )


def run_cycle(
    num_strategies: int = 10,
    num_bars: int = 1000,
    max_depth: int = 3,
    seed: int | None = None,
) -> None:
    """Run a full generation → compile → backtest cycle.

    Args:
        num_strategies: Number of strategies to generate and test.
        num_bars: Number of bars to generate for testing.
        max_depth: Maximum depth for generated expressions.
        seed: Random seed for reproducibility.
    """
    # Initialize
    registry = FunctionRegistry()
    register_std_lib(registry)
    register_extended_indicators(registry)
    evaluator = Evaluator(registry)
    backtester = Backtester(evaluator, registry)
    generator = ExpressionGenerator(registry, max_depth=max_depth, seed=seed)

    # Generate market data
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  LECAT — Strategy Generation & Backtest Engine")
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  Bars: {num_bars:,}  |  Strategies: {num_strategies}  |  Depth: {max_depth}")
    print(f"═══════════════════════════════════════════════════════════════\n")

    context = generate_random_ohlcv(num_bars, seed=seed)

    print(f"  Market Data: {num_bars:,} bars generated")
    print(f"  Price Range: {min(context.close):.2f} — {max(context.close):.2f}\n")
    print(f"{'─' * 80}")
    print(f"  {'#':<3} {'Signals':>8} {'Density':>8} {'Time':>8}  {'Strategy'}")
    print(f"{'─' * 80}")

    total_time = 0.0
    compile_errors = 0

    for i in range(num_strategies):
        expr = generator.generate(max_depth)

        try:
            tokens = Lexer(expr).tokenize()
            ast = Parser(tokens).parse()
            result = backtester.run(ast, context, expression=expr)

            total_time += result.elapsed_ms
            density_pct = result.stats.signal_density * 100

            # Truncate long expressions
            display_expr = expr if len(expr) <= 50 else expr[:47] + "..."

            print(
                f"  {i + 1:<3} {result.stats.total_signals:>8} "
                f"{density_pct:>7.1f}% "
                f"{result.elapsed_ms:>6.1f}ms  "
                f"{display_expr}"
            )
        except Exception as e:
            compile_errors += 1
            display_expr = expr if len(expr) <= 50 else expr[:47] + "..."
            print(f"  {i + 1:<3} {'ERROR':>8} {'—':>8} {'—':>8}  {display_expr}")
            print(f"       └─ {type(e).__name__}: {e}")

    print(f"{'─' * 80}")
    print(f"\n  Summary:")
    print(f"    Total time:     {total_time:.1f}ms")
    print(f"    Avg per test:   {total_time / max(num_strategies - compile_errors, 1):.1f}ms")
    if compile_errors:
        print(f"    Compile errors: {compile_errors}/{num_strategies}")
    print()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="lecat",
        description="LECAT — Strategy Generation & Backtest Engine",
    )
    parser.add_argument(
        "--strategies", "-n",
        type=int, default=10,
        help="Number of strategies to generate and test (default: 10)",
    )
    parser.add_argument(
        "--bars", "-b",
        type=int, default=1000,
        help="Number of bars to generate (default: 1000)",
    )
    parser.add_argument(
        "--depth", "-d",
        type=int, default=3,
        help="Max expression depth (default: 3)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int, default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--cores", "-c",
        type=int, default=1,
        help="Number of CPU workers for parallel evaluation (default: 1)",
    )
    parser.add_argument(
        "--generations", "-g",
        type=int, default=0,
        help="Run optimizer for N generations instead of simple backtest (default: 0 = off)",
    )

    args = parser.parse_args()

    if args.generations > 0:
        # Run optimizer mode
        from lecat.optimizer import Optimizer
        context = generate_random_ohlcv(args.bars, seed=args.seed)
        optimizer = Optimizer(
            context,
            population_size=args.strategies,
            seed=args.seed,
            use_parallel=args.cores > 1,
            max_workers=args.cores if args.cores > 1 else None,
        )
        optimizer.run(generations=args.generations)
    else:
        run_cycle(
            num_strategies=args.strategies,
            num_bars=args.bars,
            max_depth=args.depth,
            seed=args.seed,
        )


if __name__ == "__main__":
    main()
