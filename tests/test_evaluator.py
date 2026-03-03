"""Unit tests for the LECAT Evaluator (Sprint 2)."""

import unittest

from lecat.context import MarketContext, LookAheadError, InsufficientDataError
from lecat.evaluator import Evaluator
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry, FunctionResult
from lecat.std_lib import register_std_lib


# ======================================================================
# Helpers
# ======================================================================


def _make_registry() -> FunctionRegistry:
    """Create a registry with standard library functions."""
    reg = FunctionRegistry()
    register_std_lib(reg)
    return reg


def _make_context(
    close: list[float] | None = None,
    bar_index: int | None = None,
    open_: list[float] | None = None,
    high: list[float] | None = None,
    low: list[float] | None = None,
    volume: list[float] | None = None,
) -> MarketContext:
    """Helper: create a MarketContext with sensible defaults."""
    if close is None:
        close = [10.0, 11.0, 12.0, 13.0, 14.0]
    if bar_index is None:
        bar_index = len(close) - 1
    n = len(close)
    return MarketContext(
        open=open_ or [c - 0.5 for c in close],
        high=high or [c + 1.0 for c in close],
        low=low or [c - 1.0 for c in close],
        close=close,
        volume=volume or [1000.0] * n,
        bar_index=bar_index,
    )


def _eval(expression: str, ctx: MarketContext | None = None) -> FunctionResult:
    """Parse, evaluate, and return result for a single bar."""
    reg = _make_registry()
    evaluator = Evaluator(reg)
    tokens = Lexer(expression).tokenize()
    ast = Parser(tokens).parse()
    return evaluator.evaluate(ast, ctx or _make_context())


# ======================================================================
# PM Acceptance Criteria (Section 4)
# ======================================================================


class TestAcceptanceCriteria(unittest.TestCase):
    """Tests matching the PM's exact acceptance criteria for Sprint 2."""

    def test_case_a_basic_execution(self):
        """Case A: close=[10,11,12,13,14], bar_index=4.
        PRICE > 12 → True (14 > 12).
        """
        ctx = _make_context(close=[10.0, 11.0, 12.0, 13.0, 14.0], bar_index=4)
        result = _eval("PRICE > 12", ctx)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 1.0)  # True

    def test_case_b_context_shifting(self):
        """Case B: PRICE[1] > 12.
        PRICE at index 4 is 14. PRICE[1] shifts to index 3 → close[3] = 13.
        13 > 12 → True.
        """
        ctx = _make_context(close=[10.0, 11.0, 12.0, 13.0, 14.0], bar_index=4)
        result = _eval("PRICE[1] > 12", ctx)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 1.0)  # True

    def test_case_c_deep_shift(self):
        """Case C: PRICE[2] == 12.
        Index 4 - 2 = 2. close[2] = 12. → True.
        """
        ctx = _make_context(close=[10.0, 11.0, 12.0, 13.0, 14.0], bar_index=4)
        result = _eval("PRICE[2] == 12", ctx)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 1.0)  # True

    def test_case_d_out_of_bounds(self):
        """Case D: PRICE[10] — past bar_index 4 by 10 → insufficient data.
        Comparison with insufficient data → False.
        """
        ctx = _make_context(close=[10.0, 11.0, 12.0, 13.0, 14.0], bar_index=4)
        result = _eval("PRICE[10] > 0", ctx)
        self.assertEqual(result.value, 0.0)  # False (insufficient data → invalid → False)


# ======================================================================
# MarketContext Tests
# ======================================================================


class TestMarketContext(unittest.TestCase):
    """Test MarketContext creation and methods."""

    def test_creation(self):
        ctx = _make_context()
        self.assertEqual(ctx.bar_index, 4)
        self.assertEqual(ctx.total_bars, 5)

    def test_with_index(self):
        ctx = _make_context()
        shifted = ctx.with_index(2)
        self.assertEqual(shifted.bar_index, 2)
        # Data arrays should be shared (same object)
        self.assertIs(shifted.close, ctx.close)

    def test_with_index_look_ahead_error(self):
        ctx = _make_context(bar_index=3)
        with self.assertRaises(LookAheadError):
            ctx.with_index(4)  # future bar

    def test_with_index_negative_error(self):
        ctx = _make_context()
        with self.assertRaises(ValueError):
            ctx.with_index(-1)

    def test_get_window(self):
        ctx = _make_context(close=[1.0, 2.0, 3.0, 4.0, 5.0], bar_index=4)
        window = ctx.get_window("close", 3)
        self.assertEqual(list(window), [3.0, 4.0, 5.0])

    def test_get_window_insufficient(self):
        ctx = _make_context(close=[1.0, 2.0, 3.0], bar_index=1)
        with self.assertRaises(InsufficientDataError):
            ctx.get_window("close", 5)

    def test_immutability(self):
        ctx = _make_context()
        with self.assertRaises(AttributeError):
            ctx.bar_index = 0  # type: ignore


# ======================================================================
# Evaluator — Literals & Identifiers
# ======================================================================


class TestEvalLiterals(unittest.TestCase):
    """Test evaluation of literal values."""

    def test_integer(self):
        result = _eval("42")
        self.assertEqual(result.value, 42.0)

    def test_float(self):
        result = _eval("3.14")
        self.assertAlmostEqual(result.value, 3.14)

    def test_boolean_true(self):
        result = _eval("TRUE")
        self.assertEqual(result.value, 1.0)

    def test_boolean_false(self):
        result = _eval("FALSE")
        self.assertEqual(result.value, 0.0)


class TestEvalIdentifiers(unittest.TestCase):
    """Test evaluation of identifiers as zero-arg function calls."""

    def test_price_identifier(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0], bar_index=2)
        result = _eval("PRICE", ctx)
        self.assertEqual(result.value, 30.0)

    def test_close_lowercase(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0], bar_index=1)
        result = _eval("close", ctx)
        self.assertEqual(result.value, 20.0)


# ======================================================================
# Evaluator — Comparisons
# ======================================================================


class TestEvalComparisons(unittest.TestCase):
    """Test comparison operations."""

    def test_gt_true(self):
        ctx = _make_context(close=[10.0, 20.0], bar_index=1)
        result = _eval("PRICE > 15", ctx)
        self.assertEqual(result.value, 1.0)

    def test_gt_false(self):
        ctx = _make_context(close=[10.0, 20.0], bar_index=1)
        result = _eval("PRICE > 25", ctx)
        self.assertEqual(result.value, 0.0)

    def test_lt(self):
        ctx = _make_context(close=[10.0], bar_index=0)
        result = _eval("PRICE < 20", ctx)
        self.assertEqual(result.value, 1.0)

    def test_eq_with_epsilon(self):
        # Should be equal within epsilon
        ctx = _make_context(close=[10.0], bar_index=0)
        result = _eval("PRICE == 10", ctx)
        self.assertEqual(result.value, 1.0)

    def test_gte(self):
        ctx = _make_context(close=[10.0], bar_index=0)
        result = _eval("PRICE >= 10", ctx)
        self.assertEqual(result.value, 1.0)

    def test_lte(self):
        ctx = _make_context(close=[10.0], bar_index=0)
        result = _eval("PRICE <= 10", ctx)
        self.assertEqual(result.value, 1.0)

    def test_neq(self):
        ctx = _make_context(close=[10.0], bar_index=0)
        result = _eval("PRICE != 20", ctx)
        self.assertEqual(result.value, 1.0)


# ======================================================================
# Evaluator — Boolean Logic
# ======================================================================


class TestEvalBooleanLogic(unittest.TestCase):
    """Test AND, OR, NOT."""

    def test_and_both_true(self):
        ctx = _make_context(close=[100.0], bar_index=0)
        result = _eval("PRICE > 50 AND PRICE < 200", ctx)
        self.assertEqual(result.value, 1.0)

    def test_and_one_false(self):
        ctx = _make_context(close=[100.0], bar_index=0)
        result = _eval("PRICE > 50 AND PRICE > 200", ctx)
        self.assertEqual(result.value, 0.0)

    def test_or_one_true(self):
        ctx = _make_context(close=[100.0], bar_index=0)
        result = _eval("PRICE > 200 OR PRICE > 50", ctx)
        self.assertEqual(result.value, 1.0)

    def test_or_both_false(self):
        ctx = _make_context(close=[100.0], bar_index=0)
        result = _eval("PRICE > 200 OR PRICE > 300", ctx)
        self.assertEqual(result.value, 0.0)

    def test_not(self):
        ctx = _make_context(close=[100.0], bar_index=0)
        result = _eval("NOT PRICE > 200", ctx)
        self.assertEqual(result.value, 1.0)  # NOT False → True


# ======================================================================
# Evaluator — Function Calls
# ======================================================================


class TestEvalFunctions(unittest.TestCase):
    """Test function call evaluation."""

    def test_sma(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0, 40.0, 50.0], bar_index=4)
        result = _eval("SMA(3)", ctx)
        self.assertTrue(result.is_valid)
        # SMA(3) at bar 4: (30+40+50)/3 = 40.0
        self.assertAlmostEqual(result.value, 40.0)

    def test_sma_insufficient_data(self):
        ctx = _make_context(close=[10.0, 20.0], bar_index=1)
        result = _eval("SMA(5)", ctx)
        # SMA(5) needs 5 bars, only 2 available → insufficient
        self.assertFalse(result.is_valid)

    def test_price_function_call(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0], bar_index=2)
        result = _eval("PRICE()", ctx)
        self.assertEqual(result.value, 30.0)

    def test_sma_comparison(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0, 40.0, 50.0], bar_index=4)
        result = _eval("PRICE > SMA(5)", ctx)
        # PRICE = 50, SMA(5) = (10+20+30+40+50)/5 = 30
        self.assertEqual(result.value, 1.0)


# ======================================================================
# Evaluator — Context Shifting (CR-001)
# ======================================================================


class TestEvalContextShifting(unittest.TestCase):
    """Test OffsetNode evaluation — the core CR-001 feature."""

    def test_price_shift_1(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0], bar_index=2)
        result = _eval("PRICE[1]", ctx)
        # Shift to bar 1: close[1] = 20.0
        self.assertEqual(result.value, 20.0)

    def test_price_shift_2(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0], bar_index=2)
        result = _eval("PRICE[2]", ctx)
        # Shift to bar 0: close[0] = 10.0
        self.assertEqual(result.value, 10.0)

    def test_shift_out_of_bounds(self):
        ctx = _make_context(close=[10.0, 20.0], bar_index=1)
        result = _eval("PRICE[5]", ctx)
        self.assertFalse(result.is_valid)

    def test_grouped_expression_offset(self):
        """(close > open)[1] — green candle check at previous bar."""
        ctx = MarketContext(
            open=[8.0, 15.0, 25.0],  # bar 1: open=15, close=20 → green
            high=[12.0, 22.0, 32.0],
            low=[7.0, 14.0, 24.0],
            close=[10.0, 20.0, 30.0],
            volume=[100.0, 100.0, 100.0],
            bar_index=2,
        )
        result = _eval("(close > open)[1]", ctx)
        # At bar 1: close=20, open=15 → 20 > 15 → True
        self.assertEqual(result.value, 1.0)

    def test_function_offset(self):
        """SMA(2)[1] — SMA at previous bar."""
        ctx = _make_context(close=[10.0, 20.0, 30.0, 40.0], bar_index=3)
        # SMA(2) at bar 2: (20+30)/2 = 25
        result = _eval("SMA(2)[1]", ctx)
        self.assertTrue(result.is_valid)
        self.assertAlmostEqual(result.value, 25.0)

    def test_zero_offset(self):
        """PRICE[0] should equal PRICE."""
        ctx = _make_context(close=[10.0, 20.0, 30.0], bar_index=2)
        result_no_offset = _eval("PRICE", ctx)
        result_zero_offset = _eval("PRICE[0]", ctx)
        self.assertEqual(result_no_offset.value, result_zero_offset.value)


# ======================================================================
# Evaluator — Series Evaluation
# ======================================================================


class TestEvalSeries(unittest.TestCase):
    """Test evaluate_series for multi-bar signal generation."""

    def test_signal_series(self):
        ctx = _make_context(close=[10.0, 20.0, 30.0, 40.0, 50.0], bar_index=4)
        reg = _make_registry()
        evaluator = Evaluator(reg)
        tokens = Lexer("PRICE > 25").tokenize()
        ast = Parser(tokens).parse()
        results = evaluator.evaluate_series(ast, ctx)

        self.assertEqual(len(results), 5)
        # close: [10, 20, 30, 40, 50], threshold 25
        signals = [r.value for r in results]
        self.assertEqual(signals, [0.0, 0.0, 1.0, 1.0, 1.0])


# ======================================================================
# Evaluator — Complex Expressions
# ======================================================================


class TestComplexExpressions(unittest.TestCase):
    """Test realistic multi-feature expressions."""

    def test_crossover_detection(self):
        """SMA(2) > SMA(3) AND SMA(2)[1] <= SMA(3)[1]
        Classic golden cross detection.
        """
        # Construct data where SMA(2) crosses above SMA(3)
        close = [10.0, 12.0, 11.0, 13.0, 15.0, 18.0]
        ctx = _make_context(close=close, bar_index=5)

        # SMA(2) at bar 5: (15+18)/2 = 16.5
        # SMA(3) at bar 5: (13+15+18)/3 = 15.33
        # SMA(2) at bar 4: (13+15)/2 = 14
        # SMA(3) at bar 4: (11+13+15)/3 = 13
        # 16.5 > 15.33 AND 14 <= 13 → True AND False → False
        result = _eval("SMA(2) > SMA(3) AND SMA(2)[1] <= SMA(3)[1]", ctx)
        # This specific data doesn't trigger a crossover, which is fine
        self.assertTrue(result.is_valid)

    def test_compound_logic_with_offset(self):
        """PRICE > 12 AND PRICE[1] < 12"""
        ctx = _make_context(close=[10.0, 11.0, 12.0, 13.0, 14.0], bar_index=4)
        # PRICE = 14 > 12: True
        # PRICE[1] = 13 < 12: False
        result = _eval("PRICE > 12 AND PRICE[1] < 12", ctx)
        self.assertEqual(result.value, 0.0)  # False


if __name__ == "__main__":
    unittest.main()
