"""Unit tests for the LECAT Extended Indicators."""

import unittest

from lecat.context import MarketContext
from lecat.indicators import register_extended_indicators, _calc_ema, _ema_of_values
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib


def _make_registry() -> FunctionRegistry:
    reg = FunctionRegistry()
    register_std_lib(reg)
    register_extended_indicators(reg)
    return reg


def _ctx(
    close: list[float],
    high: list[float] | None = None,
    low: list[float] | None = None,
) -> MarketContext:
    n = len(close)
    if high is None:
        high = [c + 1.0 for c in close]
    if low is None:
        low = [c - 1.0 for c in close]
    return MarketContext(
        open=[c - 0.5 for c in close],
        high=high,
        low=low,
        close=close,
        volume=[1000.0] * n,
        bar_index=n - 1,
    )


class TestMACDIndicator(unittest.TestCase):
    """Case B: Test MACD correctness against manual calculation."""

    def test_macd_returns_value(self):
        """MACD should return a numeric value with sufficient data."""
        reg = _make_registry()
        # Need slow(26) + signal(9) = 35 bars minimum
        close = [100.0 + i * 0.5 for i in range(50)]
        ctx = _ctx(close)

        handler = reg.get_handler("MACD")
        result = handler({"fast": 12, "slow": 26, "signal": 9}, ctx)
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.value)

    def test_macd_insufficient_data(self):
        """MACD should return insufficient data with too few bars."""
        reg = _make_registry()
        close = [100.0 + i for i in range(10)]  # Only 10 bars
        ctx = _ctx(close)

        handler = reg.get_handler("MACD")
        result = handler({"fast": 12, "slow": 26, "signal": 9}, ctx)
        self.assertFalse(result.is_valid)

    def test_macd_manual_calculation(self):
        """MACD histogram should match manual EMA computation within tolerance."""
        # Create 50 bars of data
        close = [100.0 + i * 0.3 + (i % 5) * 0.1 for i in range(50)]
        idx = len(close) - 1

        # Manual calculation
        fast_ema = _calc_ema(close, 12, idx)
        slow_ema = _calc_ema(close, 26, idx)
        macd_line = fast_ema - slow_ema

        # Calculate signal from MACD values
        macd_values = []
        for i in range(idx - 8, idx + 1):  # signal period = 9
            f = _calc_ema(close, 12, i)
            s = _calc_ema(close, 26, i)
            macd_values.append(f - s)
        signal = _ema_of_values(macd_values, 9)

        expected_histogram = macd_line - signal

        # Test via handler
        reg = _make_registry()
        ctx = _ctx(close)
        handler = reg.get_handler("MACD")
        result = handler({"fast": 12, "slow": 26, "signal": 9}, ctx)

        self.assertAlmostEqual(result.value, expected_histogram, places=5)


class TestBollingerBands(unittest.TestCase):
    """Test BB_UPPER and BB_LOWER."""

    def test_bb_upper_above_sma(self):
        """Upper band should be above the simple moving average."""
        reg = _make_registry()
        close = [100.0 + i for i in range(25)]
        ctx = _ctx(close)

        handler = reg.get_handler("BB_UPPER")
        result = handler({"period": 20, "std_dev": 2.0}, ctx)
        self.assertTrue(result.is_valid)

        # SMA(20) of last 20 bars
        sma = sum(close[-20:]) / 20
        self.assertGreater(result.value, sma)

    def test_bb_lower_below_sma(self):
        """Lower band should be below the simple moving average."""
        reg = _make_registry()
        close = [100.0 + i for i in range(25)]
        ctx = _ctx(close)

        handler = reg.get_handler("BB_LOWER")
        result = handler({"period": 20, "std_dev": 2.0}, ctx)
        self.assertTrue(result.is_valid)

        sma = sum(close[-20:]) / 20
        self.assertLess(result.value, sma)

    def test_bb_symmetry(self):
        """Upper - SMA should equal SMA - Lower."""
        reg = _make_registry()
        close = [100.0 + i * 0.5 for i in range(25)]
        ctx = _ctx(close)

        upper = reg.get_handler("BB_UPPER")({"period": 20, "std_dev": 2.0}, ctx)
        lower = reg.get_handler("BB_LOWER")({"period": 20, "std_dev": 2.0}, ctx)
        sma = sum(close[-20:]) / 20

        self.assertAlmostEqual(
            upper.value - sma, sma - lower.value, places=5
        )

    def test_bb_insufficient_data(self):
        reg = _make_registry()
        close = [100.0 + i for i in range(10)]
        ctx = _ctx(close)

        result = reg.get_handler("BB_UPPER")({"period": 20, "std_dev": 2.0}, ctx)
        self.assertFalse(result.is_valid)


class TestStochastic(unittest.TestCase):
    """Test Stochastic Oscillator."""

    def test_stoch_in_range(self):
        """Stochastic should be between 0 and 100."""
        reg = _make_registry()
        close = [100.0 + i * 0.5 for i in range(30)]
        high = [c + 2.0 for c in close]
        low = [c - 2.0 for c in close]
        ctx = _ctx(close, high, low)

        result = reg.get_handler("STOCH")({"k_period": 14, "d_period": 3}, ctx)
        self.assertTrue(result.is_valid)
        self.assertGreaterEqual(result.value, 0.0)
        self.assertLessEqual(result.value, 100.0)

    def test_stoch_insufficient_data(self):
        reg = _make_registry()
        close = [100.0 + i for i in range(5)]
        ctx = _ctx(close)

        result = reg.get_handler("STOCH")({"k_period": 14, "d_period": 3}, ctx)
        self.assertFalse(result.is_valid)


class TestEMAHelpers(unittest.TestCase):
    """Test internal EMA calculation functions."""

    def test_ema_matches_sma_for_first_period(self):
        """EMA starting value should equal SMA of first period."""
        data = [10.0, 11.0, 12.0, 13.0, 14.0]
        # EMA(5) at index 4 should start from SMA
        ema = _calc_ema(data, 5, 4)
        sma = sum(data[:5]) / 5
        self.assertAlmostEqual(ema, sma, places=5)

    def test_ema_of_values(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _ema_of_values(values, 3)
        self.assertIsInstance(result, float)


class TestIndicatorRegistration(unittest.TestCase):
    """Test that all indicators register correctly."""

    def test_all_indicators_registered(self):
        reg = _make_registry()
        names = [f.name for f in reg.get_available_functions()]
        for expected in ["MACD", "BB_UPPER", "BB_LOWER", "STOCH"]:
            self.assertIn(expected, names, f"{expected} not registered")

    def test_indicators_work_in_evaluator(self):
        """Indicators should work through the full evaluate pipeline."""
        from lecat.evaluator import Evaluator
        from lecat.lexer import Lexer
        from lecat.parser import Parser

        reg = _make_registry()
        evaluator = Evaluator(reg)

        close = [100.0 + i * 0.5 for i in range(50)]
        ctx = _ctx(close)

        ast = Parser(Lexer("BB_UPPER(20, 2.0) > 100").tokenize()).parse()
        result = evaluator.evaluate(ast, ctx)
        self.assertTrue(result.is_valid)


if __name__ == "__main__":
    unittest.main()
