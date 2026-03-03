"""Unit tests for the LECAT Backtester."""

import unittest
import time

from lecat.backtester import Backtester, BacktestResult
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.generator import ExpressionGenerator
from lecat.lexer import Lexer
from lecat.main import generate_random_ohlcv
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib
from lecat.stats import compute_stats, StrategyStats


# ======================================================================
# Helpers
# ======================================================================


def _setup() -> tuple[FunctionRegistry, Evaluator, Backtester]:
    reg = FunctionRegistry()
    register_std_lib(reg)
    evaluator = Evaluator(reg)
    backtester = Backtester(evaluator, reg)
    return reg, evaluator, backtester


def _parse(expr: str):
    return Parser(Lexer(expr).tokenize()).parse()


def _make_context(close: list[float], **kw) -> MarketContext:
    n = len(close)
    return MarketContext(
        open=kw.get("open_", [c - 0.5 for c in close]),
        high=kw.get("high", [c + 1.0 for c in close]),
        low=kw.get("low", [c - 1.0 for c in close]),
        close=close,
        volume=kw.get("volume", [1000.0] * n),
        bar_index=n - 1,
    )


# ======================================================================
# PM Acceptance Criteria
# ======================================================================


class TestAcceptanceCriteria(unittest.TestCase):
    """Tests matching PM acceptance criteria for Sprint 3."""

    def test_case_b_backtest_consistency(self):
        """Case B: PRICE > 10 with [11, 9, 12, 8, 15]
        Expected: [True, False, True, False, True]
        """
        reg, evaluator, backtester = _setup()
        ctx = _make_context([11.0, 9.0, 12.0, 8.0, 15.0])
        ast = _parse("PRICE > 10")

        result = backtester.run(ast, ctx, expression="PRICE > 10")

        self.assertEqual(result.signals, [True, False, True, False, True])
        self.assertEqual(result.stats.total_signals, 3)
        self.assertEqual(result.total_bars, 5)

    def test_case_c_performance_benchmark(self):
        """Case C: Complex strategy over 10,000 bars under 1.0 second."""
        reg, evaluator, backtester = _setup()
        ctx = generate_random_ohlcv(10000, seed=42)
        ast = _parse("PRICE > SMA(20) AND RSI(14) > 30")

        start = time.perf_counter()
        result = backtester.run(ast, ctx)
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 1.0, f"Backtest took {elapsed:.3f}s — exceeds 1.0s target")
        self.assertEqual(len(result.signals), 10000)


# ======================================================================
# Backtester Tests
# ======================================================================


class TestBacktester(unittest.TestCase):
    """Test backtester behavior."""

    def test_all_bars_evaluated(self):
        reg, evaluator, backtester = _setup()
        ctx = _make_context([10.0, 20.0, 30.0, 40.0, 50.0])
        ast = _parse("PRICE > 0")
        result = backtester.run(ast, ctx)
        self.assertEqual(len(result.signals), 5)

    def test_warmup_handling(self):
        """SMA(3) needs 3 bars warmup — first 2 bars should be False."""
        reg, evaluator, backtester = _setup()
        ctx = _make_context([100.0, 200.0, 300.0, 400.0, 500.0])
        ast = _parse("SMA(3) > 0")
        result = backtester.run(ast, ctx)

        # First 2 bars (0,1) are warmup → False
        # Bars 2,3,4 have sufficient data
        self.assertFalse(result.signals[0])
        self.assertFalse(result.signals[1])
        self.assertTrue(result.warmup_bars >= 2)

    def test_result_contains_timing(self):
        reg, evaluator, backtester = _setup()
        ctx = _make_context([10.0, 20.0, 30.0])
        ast = _parse("PRICE > 0")
        result = backtester.run(ast, ctx)
        self.assertGreater(result.elapsed_ms, 0.0)

    def test_result_contains_expression(self):
        reg, evaluator, backtester = _setup()
        ctx = _make_context([10.0])
        ast = _parse("PRICE > 5")
        result = backtester.run(ast, ctx, expression="PRICE > 5")
        self.assertEqual(result.expression, "PRICE > 5")

    def test_context_shifting_in_backtest(self):
        """PRICE[1] should access previous bar during backtest."""
        reg, evaluator, backtester = _setup()
        # close: [10, 20, 30] → PRICE[1] at bar 2 = 20
        ctx = _make_context([10.0, 20.0, 30.0])
        ast = _parse("PRICE[1] > 15")
        result = backtester.run(ast, ctx)

        # Bar 0: warmup (shift of 1), bar 1: PRICE[1]=10 > 15? False
        # Bar 2: PRICE[1]=20 > 15? True
        self.assertTrue(result.signals[2])

    def test_backtest_result_is_frozen(self):
        reg, evaluator, backtester = _setup()
        ctx = _make_context([10.0])
        ast = _parse("PRICE > 5")
        result = backtester.run(ast, ctx)
        with self.assertRaises(AttributeError):
            result.expression = "hacked"  # type: ignore


# ======================================================================
# Stats Tests
# ======================================================================


class TestStats(unittest.TestCase):
    """Test signal statistics computation."""

    def test_all_true(self):
        stats = compute_stats([True, True, True, True, True])
        self.assertEqual(stats.total_signals, 5)
        self.assertAlmostEqual(stats.signal_density, 1.0)
        self.assertEqual(stats.longest_streak, 5)
        self.assertEqual(stats.longest_gap, 0)

    def test_all_false(self):
        stats = compute_stats([False, False, False])
        self.assertEqual(stats.total_signals, 0)
        self.assertAlmostEqual(stats.signal_density, 0.0)
        self.assertEqual(stats.longest_streak, 0)
        self.assertEqual(stats.longest_gap, 3)

    def test_mixed(self):
        stats = compute_stats([True, True, False, True, False])
        self.assertEqual(stats.total_signals, 3)
        self.assertAlmostEqual(stats.signal_density, 0.6)
        self.assertEqual(stats.longest_streak, 2)
        self.assertEqual(stats.longest_gap, 1)

    def test_warmup_excluded(self):
        # 3 warmup bars (False), then 2 active bars (True)
        stats = compute_stats([False, False, False, True, True], warmup=3)
        self.assertEqual(stats.total_bars, 2)
        self.assertEqual(stats.total_signals, 2)
        self.assertAlmostEqual(stats.signal_density, 1.0)

    def test_empty(self):
        stats = compute_stats([])
        self.assertEqual(stats.total_signals, 0)
        self.assertEqual(stats.total_bars, 0)

    def test_repr(self):
        stats = compute_stats([True, False, True])
        self.assertIn("signals=", repr(stats))


# ======================================================================
# Integration Test
# ======================================================================


class TestIntegration(unittest.TestCase):
    """End-to-end integration: generate → compile → backtest."""

    def test_generated_strategy_backtests(self):
        """Generate 10 strategies, compile and backtest each."""
        reg, evaluator, backtester = _setup()
        gen = ExpressionGenerator(reg, seed=42)
        ctx = generate_random_ohlcv(500, seed=42)

        for i in range(10):
            expr = gen.generate()
            ast = _parse(expr)
            result = backtester.run(ast, ctx, expression=expr)
            self.assertEqual(len(result.signals), 500)
            self.assertIsInstance(result.stats, StrategyStats)


if __name__ == "__main__":
    unittest.main()
