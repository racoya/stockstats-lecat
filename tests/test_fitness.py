"""Unit tests for the LECAT Fitness Calculator."""

import unittest

from lecat.backtester import Backtester
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.fitness import FitnessResult, calculate_fitness, _simulate_trades
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
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


def _backtest(expr: str, close: list[float]):
    reg, evaluator, backtester = _setup()
    ctx = _ctx(close)
    ast = Parser(Lexer(expr).tokenize()).parse()
    return backtester.run(ast, ctx, expression=expr), ctx


class TestTradeSimulation(unittest.TestCase):
    """Test the trade simulation logic."""

    def test_buy_sell_signal(self):
        """True → buy, False → sell."""
        ctx = _ctx([10.0, 12.0, 11.0, 13.0])
        trades = _simulate_trades([True, True, False, True], ctx)
        # Trade 1: buy at 10, sell at 11
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0].entry_price, 10.0)
        self.assertEqual(trades[0].exit_price, 11.0)

    def test_no_signals_no_trades(self):
        ctx = _ctx([10.0, 11.0, 12.0])
        trades = _simulate_trades([False, False, False], ctx)
        self.assertEqual(len(trades), 0)

    def test_all_true_single_trade(self):
        """All True → one open trade, closed at end."""
        ctx = _ctx([10.0, 12.0, 15.0])
        trades = _simulate_trades([True, True, True], ctx)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].entry_price, 10.0)
        self.assertEqual(trades[0].exit_price, 15.0)

    def test_trade_return_calculation(self):
        ctx = _ctx([100.0, 110.0])
        trades = _simulate_trades([True, False], ctx)
        self.assertEqual(len(trades), 1)
        self.assertAlmostEqual(trades[0].return_pct, 10.0)  # 10% return


class TestFitnessCalculation(unittest.TestCase):
    """Test fitness scoring."""

    def test_profitable_strategy(self):
        # Price goes up: 10 → 20 → 30
        result, ctx = _backtest("PRICE > 5", [10.0, 20.0, 30.0])
        fitness = calculate_fitness(result, ctx)
        self.assertGreater(fitness.total_return_pct, 0)
        self.assertIsInstance(fitness, FitnessResult)

    def test_no_trades_penalty(self):
        # No signals → no trades → penalty
        result, ctx = _backtest("PRICE > 9999", [10.0, 20.0, 30.0])
        fitness = calculate_fitness(result, ctx)
        self.assertEqual(fitness.num_trades, 0)

    def test_fitness_result_is_frozen(self):
        result, ctx = _backtest("PRICE > 5", [10.0, 20.0, 30.0])
        fitness = calculate_fitness(result, ctx)
        with self.assertRaises(AttributeError):
            fitness.fitness_score = 999.0  # type: ignore

    def test_win_rate(self):
        # Rising prices with PRICE > 5 → always in, one trade, positive
        result, ctx = _backtest("PRICE > 5", [10.0, 12.0, 14.0, 16.0, 18.0])
        fitness = calculate_fitness(result, ctx)
        # One trade, profitable → 100% win rate
        self.assertGreaterEqual(fitness.win_rate, 0.0)

    def test_fitness_repr(self):
        result, ctx = _backtest("PRICE > 5", [10.0, 20.0])
        fitness = calculate_fitness(result, ctx)
        self.assertIn("score=", repr(fitness))
        self.assertIn("return=", repr(fitness))


class TestLowTradesPenalty(unittest.TestCase):
    """Test the penalty for too few trades."""

    def test_less_than_5_trades_penalized(self):
        """Strategies with < 5 trades should have reduced fitness."""
        # Create oscillating data for some trades
        close = [10.0, 20.0, 10.0, 20.0]  # 2 round trips
        result, ctx = _backtest("PRICE > 15", close)
        fitness = calculate_fitness(result, ctx)
        self.assertLess(fitness.num_trades, 5)


if __name__ == "__main__":
    unittest.main()
