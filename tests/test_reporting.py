"""Unit tests for the LECAT Reporting module."""

import os
import tempfile
import unittest
from pathlib import Path

from lecat.backtester import Backtester
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.fitness import calculate_fitness
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.reporting import (
    generate_report_text,
    plot_equity_curve,
    _calculate_equity_curve,
    _calculate_benchmark_curve,
)
from lecat.std_lib import register_std_lib


def _setup():
    reg = FunctionRegistry()
    register_std_lib(reg)
    evaluator = Evaluator(reg)
    backtester = Backtester(evaluator, reg)
    return reg, evaluator, backtester


def _ctx(close: list[float]) -> MarketContext:
    n = len(close)
    return MarketContext(
        open=[c - 0.5 for c in close],
        high=[c + 1.0 for c in close],
        low=[c - 1.0 for c in close],
        close=close,
        volume=[1000.0] * n,
        bar_index=n - 1,
    )


class TestEquityCurve(unittest.TestCase):
    """Test equity curve calculation."""

    def test_equity_length(self):
        ctx = _ctx([10.0, 11.0, 12.0, 13.0, 14.0])
        signals = [True, True, True, False, True]
        equity = _calculate_equity_curve(signals, ctx)
        self.assertEqual(len(equity), len(signals))

    def test_no_trades_flat(self):
        ctx = _ctx([10.0, 11.0, 12.0])
        signals = [False, False, False]
        equity = _calculate_equity_curve(signals, ctx)
        self.assertEqual(equity[-1], 0.0)  # No change


class TestBenchmarkCurve(unittest.TestCase):
    """Test buy-and-hold benchmark."""

    def test_benchmark_starts_at_zero(self):
        ctx = _ctx([100.0, 110.0, 120.0])
        benchmark = _calculate_benchmark_curve(ctx)
        self.assertAlmostEqual(benchmark[0], 0.0)

    def test_benchmark_end(self):
        ctx = _ctx([100.0, 110.0, 120.0])
        benchmark = _calculate_benchmark_curve(ctx)
        # 120/100 - 1 = 20%
        self.assertAlmostEqual(benchmark[-1], 20.0)


class TestPlotGeneration(unittest.TestCase):
    """Case C: Test chart file generation."""

    def test_plot_generates_file(self):
        """An image or CSV file should be generated."""
        reg, evaluator, backtester = _setup()
        ctx = _ctx([10.0, 12.0, 11.0, 14.0, 13.0])
        ast = Parser(Lexer("PRICE > 11").tokenize()).parse()
        result = backtester.run(ast, ctx, expression="PRICE > 11")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            output = plot_equity_curve(result, ctx, output_path=path)
            self.assertTrue(Path(output).exists())
            self.assertGreater(os.path.getsize(output), 0)
        finally:
            if os.path.exists(path):
                os.unlink(path)
            # Also remove CSV fallback if created
            csv_path = path.replace(".png", ".csv")
            if os.path.exists(csv_path):
                os.unlink(csv_path)


class TestReportText(unittest.TestCase):
    """Test text report generation."""

    def test_report_contains_metrics(self):
        reg, evaluator, backtester = _setup()
        ctx = _ctx([10.0, 12.0, 11.0, 14.0, 13.0])
        ast = Parser(Lexer("PRICE > 11").tokenize()).parse()
        result = backtester.run(ast, ctx, expression="PRICE > 11")
        fitness = calculate_fitness(result, ctx)

        report = generate_report_text(result, ctx, fitness)
        self.assertIn("PRICE > 11", report)
        self.assertIn("Return:", report)
        self.assertIn("Sharpe:", report)
        self.assertIn("Trades:", report)


class TestWalkForwardSplit(unittest.TestCase):
    """Case B: Test walk-forward split enforcement."""

    def test_optimizer_split_produces_results(self):
        """Running optimizer with split_ratio should produce WalkForwardResult."""
        from lecat.main import generate_random_ohlcv
        from lecat.optimizer import Optimizer

        ctx = generate_random_ohlcv(200, seed=42)
        optimizer = Optimizer(ctx, population_size=10, elite_count=2, seed=42, verbose=False)
        result = optimizer.run(generations=3, split_ratio=0.7)

        self.assertIsNotNone(result.walk_forward)
        wf = result.walk_forward
        self.assertEqual(wf.train_bars, 140)
        self.assertEqual(wf.test_bars, 60)

    def test_no_split_no_walkforward(self):
        """Without split_ratio, walk_forward should be None."""
        from lecat.main import generate_random_ohlcv
        from lecat.optimizer import Optimizer

        ctx = generate_random_ohlcv(100, seed=42)
        optimizer = Optimizer(ctx, population_size=10, elite_count=2, seed=42, verbose=False)
        result = optimizer.run(generations=2)

        self.assertIsNone(result.walk_forward)


if __name__ == "__main__":
    unittest.main()
