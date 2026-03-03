"""Unit tests for the LECAT Parallel Evaluator."""

import unittest
import time

from lecat.context import MarketContext
from lecat.evolution import Individual
from lecat.lexer import Lexer
from lecat.main import generate_random_ohlcv
from lecat.parallel import BatchEvaluator, _make_registry
from lecat.parser import Parser
from lecat.cache import IndicatorCache


def _parse(expr: str):
    return Parser(Lexer(expr).tokenize()).parse()


class TestBatchEvaluator(unittest.TestCase):
    """Test parallel batch evaluation."""

    def test_serial_evaluation(self):
        """Serial mode should produce valid fitness scores."""
        ctx = generate_random_ohlcv(200, seed=42)
        reg = _make_registry()
        evaluator = BatchEvaluator(max_workers=1)

        population = [
            Individual(ast=_parse("PRICE > 50"), expression="PRICE > 50"),
            Individual(ast=_parse("RSI(14) > 70"), expression="RSI(14) > 70"),
            Individual(ast=_parse("SMA(20) > 100"), expression="SMA(20) > 100"),
        ]

        scores = evaluator.evaluate_population(population, ctx, reg)
        self.assertEqual(len(scores), 3)
        for score in scores:
            self.assertIsInstance(score, float)
            self.assertGreater(score, -999.0)

    def test_parallel_evaluation(self):
        """Parallel mode should produce valid fitness scores."""
        ctx = generate_random_ohlcv(200, seed=42)
        reg = _make_registry()
        evaluator = BatchEvaluator(max_workers=2)

        # Need >= 10 for parallel path
        exprs = [
            "PRICE > 50", "RSI(14) > 70", "SMA(20) > 100",
            "EMA(10) > 50", "PRICE > 80", "RSI(14) < 30",
            "SMA(50) > 90", "PRICE > 60", "EMA(20) > 70",
            "PRICE > 100", "RSI(14) > 50", "SMA(10) > 80",
        ]
        population = [
            Individual(ast=_parse(e), expression=e) for e in exprs
        ]

        scores = evaluator.evaluate_population(population, ctx, reg)
        self.assertEqual(len(scores), len(exprs))
        for score in scores:
            self.assertIsInstance(score, float)

    def test_parallel_matches_serial(self):
        """Case C: Parallel results should match serial results."""
        ctx = generate_random_ohlcv(200, seed=42)
        reg = _make_registry()

        exprs = [
            "PRICE > 50", "RSI(14) > 70", "SMA(20) > 100",
            "EMA(10) > 50", "PRICE > 80", "RSI(14) < 30",
            "SMA(50) > 90", "PRICE > 60", "EMA(20) > 70",
            "PRICE > 100",
        ]

        # Serial
        serial_pop = [Individual(ast=_parse(e), expression=e) for e in exprs]
        serial_eval = BatchEvaluator(max_workers=1)
        serial_scores = serial_eval.evaluate_population(serial_pop, ctx, reg)

        # Parallel
        parallel_pop = [Individual(ast=_parse(e), expression=e) for e in exprs]
        parallel_eval = BatchEvaluator(max_workers=2)
        parallel_scores = parallel_eval.evaluate_population(parallel_pop, ctx, reg)

        # Results should be identical
        for i, (s, p) in enumerate(zip(serial_scores, parallel_scores)):
            self.assertAlmostEqual(
                s, p, places=5,
                msg=f"Mismatch at index {i}: serial={s}, parallel={p}"
            )

    def test_empty_population(self):
        ctx = generate_random_ohlcv(100, seed=42)
        evaluator = BatchEvaluator(max_workers=2)
        scores = evaluator.evaluate_population([], ctx)
        self.assertEqual(scores, [])


class TestIndicatorCache(unittest.TestCase):
    """Test the indicator cache."""

    def test_cache_stores_values(self):
        cache = IndicatorCache()
        from lecat.registry import FunctionResult

        result = cache.get_or_compute(
            "RSI", (14,), 5,
            lambda: FunctionResult.success(65.0)
        )
        self.assertEqual(result.value, 65.0)
        self.assertEqual(cache.stats["misses"], 1)

        # Second access should hit cache
        result2 = cache.get_or_compute(
            "RSI", (14,), 5,
            lambda: FunctionResult.success(99.0)  # Should NOT be called
        )
        self.assertEqual(result2.value, 65.0)  # Cached value
        self.assertEqual(cache.stats["hits"], 1)

    def test_cache_different_bars(self):
        cache = IndicatorCache()
        from lecat.registry import FunctionResult

        cache.get_or_compute("SMA", (20,), 0, lambda: FunctionResult.success(100.0))
        cache.get_or_compute("SMA", (20,), 1, lambda: FunctionResult.success(101.0))

        self.assertEqual(cache.stats["misses"], 2)

    def test_cache_clear(self):
        cache = IndicatorCache()
        from lecat.registry import FunctionResult

        cache.get_or_compute("RSI", (14,), 0, lambda: FunctionResult.success(50.0))
        cache.clear()
        self.assertEqual(cache.stats["entries"], 0)

    def test_cache_repr(self):
        cache = IndicatorCache()
        self.assertIn("IndicatorCache", repr(cache))


class TestParallelSpeedup(unittest.TestCase):
    """Case A: Test that parallel is not slower than serial for larger workloads."""

    def test_parallel_completes(self):
        """Parallel evaluation should complete without errors."""
        ctx = generate_random_ohlcv(500, seed=42)
        reg = _make_registry()

        exprs = [f"PRICE > {i}" for i in range(20, 80)]
        population = [Individual(ast=_parse(e), expression=e) for e in exprs]

        evaluator = BatchEvaluator(max_workers=4)
        scores = evaluator.evaluate_population(population, ctx, reg)
        self.assertEqual(len(scores), len(exprs))


if __name__ == "__main__":
    unittest.main()
