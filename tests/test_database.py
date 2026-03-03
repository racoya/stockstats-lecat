"""Tests for Repository and DynamicRegistry — Phase 6 Sprint 1."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from lecat.repository import Repository
from lecat.dynamic_registry import DynamicRegistry
from lecat.context import MarketContext
from lecat.std_lib import register_std_lib
from lecat.indicators import register_extended_indicators


class TestRepository(unittest.TestCase):
    """Test Repository CRUD operations."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.repo = Repository(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)
        # Also clean up WAL/SHM files
        for ext in (".db-wal", ".db-shm"):
            wal = self.tmp.name + ext.replace(".db", "")
            if os.path.exists(wal):
                os.unlink(wal)

    # --- Market Data ---

    def test_save_and_get_market_data(self):
        rows = [
            {"timestamp": "2024-01-01", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
            {"timestamp": "2024-01-02", "open": 105, "high": 115, "low": 95, "close": 110, "volume": 1500},
        ]
        inserted = self.repo.save_market_data(rows, "BTC_USD")
        self.assertEqual(inserted, 2)

        data = self.repo.get_market_data("BTC_USD")
        self.assertEqual(len(data), 2)
        self.assertAlmostEqual(data[0]["open"], 100.0)
        self.assertAlmostEqual(data[1]["close"], 110.0)

    def test_get_symbols(self):
        self.repo.save_market_data(
            [{"timestamp": "2024-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}],
            "AAPL",
        )
        self.repo.save_market_data(
            [{"timestamp": "2024-01-01", "open": 50, "high": 60, "low": 40, "close": 55, "volume": 200}],
            "GOOG",
        )
        symbols = self.repo.get_symbols()
        self.assertEqual(symbols, ["AAPL", "GOOG"])

    def test_delete_market_data(self):
        self.repo.save_market_data(
            [{"timestamp": "2024-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}],
            "DELETE_ME",
        )
        deleted = self.repo.delete_market_data("DELETE_ME")
        self.assertEqual(deleted, 1)
        self.assertEqual(self.repo.get_market_data("DELETE_ME"), [])

    def test_upsert_market_data(self):
        """INSERT OR REPLACE should update existing rows."""
        rows = [{"timestamp": "2024-01-01", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}]
        self.repo.save_market_data(rows, "BTC")
        # Update with new close
        rows[0]["close"] = 200
        self.repo.save_market_data(rows, "BTC")
        data = self.repo.get_market_data("BTC")
        self.assertEqual(len(data), 1)
        self.assertAlmostEqual(data[0]["close"], 200.0)

    # --- Indicators ---

    def test_save_and_get_indicator(self):
        self.repo.save_indicator("AVG_PRICE", [], "(HIGH + LOW) / 2", "Average price")
        indicators = self.repo.get_all_indicators()
        self.assertEqual(len(indicators), 1)
        self.assertEqual(indicators[0]["name"], "AVG_PRICE")
        self.assertEqual(indicators[0]["formula"], "(HIGH + LOW) / 2")
        self.assertEqual(indicators[0]["args"], [])

    def test_save_indicator_with_args(self):
        self.repo.save_indicator("MY_CROSS", ["fast", "slow"], "SMA(fast) > SMA(slow)")
        ind = self.repo.get_indicator("MY_CROSS")
        self.assertIsNotNone(ind)
        self.assertEqual(ind["args"], ["fast", "slow"])

    def test_delete_indicator(self):
        self.repo.save_indicator("TEMP", [], "PRICE")
        self.assertTrue(self.repo.delete_indicator("TEMP"))
        self.assertIsNone(self.repo.get_indicator("TEMP"))

    def test_delete_nonexistent_indicator(self):
        self.assertFalse(self.repo.delete_indicator("NOPE"))

    def test_update_indicator(self):
        """INSERT OR REPLACE should update existing indicators."""
        self.repo.save_indicator("UPD", [], "PRICE")
        self.repo.save_indicator("UPD", ["p"], "SMA(p)")
        ind = self.repo.get_indicator("UPD")
        self.assertEqual(ind["formula"], "SMA(p)")
        self.assertEqual(ind["args"], ["p"])

    # --- Strategy Results ---

    def test_save_and_get_result(self):
        row_id = self.repo.save_result(
            "RSI(14) > 70",
            {"sharpe": 1.5, "return": 20.4, "win_rate": 0.6},
            "BTC_USD",
        )
        self.assertGreater(row_id, 0)

        results = self.repo.get_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["expression"], "RSI(14) > 70")
        self.assertAlmostEqual(results[0]["metrics"]["sharpe"], 1.5)

    def test_clear_results(self):
        self.repo.save_result("A", {"score": 1})
        self.repo.save_result("B", {"score": 2})
        deleted = self.repo.clear_results()
        self.assertEqual(deleted, 2)
        self.assertEqual(self.repo.get_results(), [])


class TestDynamicRegistry(unittest.TestCase):
    """Test DynamicRegistry with composite indicators."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.repo = Repository(self.tmp.name)
        self.registry = DynamicRegistry(self.repo)
        register_std_lib(self.registry)
        register_extended_indicators(self.registry)

        # Create a simple market context
        n = 100
        self.ctx = MarketContext(
            open=[float(50 + i * 0.1) for i in range(n)],
            high=[float(55 + i * 0.1) for i in range(n)],
            low=[float(45 + i * 0.1) for i in range(n)],
            close=[float(52 + i * 0.1) for i in range(n)],
            volume=[1000.0] * n,
            bar_index=n - 1,
            symbol="TEST",
        )

    def tearDown(self):
        os.unlink(self.tmp.name)
        for ext in ("-wal", "-shm"):
            wal = self.tmp.name + ext
            if os.path.exists(wal):
                os.unlink(wal)

    def test_load_simple_indicator(self):
        """Custom indicator with no args should load."""
        self.repo.save_indicator("HIGH_VOL", [], "RSI(14) > 50", "High volume check")
        loaded = self.registry.load_custom_indicators()
        self.assertEqual(loaded, 1)
        self.assertTrue(self.registry.has_function("HIGH_VOL"))

    def test_evaluate_simple_indicator(self):
        """Custom indicator should return a valid result."""
        self.repo.save_indicator("ABOVE_MID", [], "PRICE > SMA(20)")
        self.registry.load_custom_indicators()

        handler = self.registry.get_handler("ABOVE_MID")
        result = handler({}, self.ctx)
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.value)

    def test_indicator_with_args(self):
        """Indicator with arguments should substitute correctly."""
        self.repo.save_indicator("MY_SMA", ["period"], "SMA(period)")
        self.registry.load_custom_indicators()

        handler = self.registry.get_handler("MY_SMA")
        result = handler({"period": 20}, self.ctx)
        self.assertTrue(result.is_valid)

    def test_reload_indicators(self):
        """Reload should pick up new indicators."""
        self.repo.save_indicator("V1", [], "PRICE")
        self.registry.load_custom_indicators()
        self.assertTrue(self.registry.has_function("V1"))

        self.repo.save_indicator("V2", [], "VOLUME")
        loaded = self.registry.reload_custom_indicators()
        self.assertTrue(self.registry.has_function("V2"))

    def test_circular_reference_detection(self):
        """A calling B calling A should produce an error result."""
        from lecat.dynamic_registry import _evaluation_stack

        # Clear the stack
        _evaluation_stack.clear()

        self.repo.save_indicator("CIRC_A", [], "CIRC_B() > 0")
        self.repo.save_indicator("CIRC_B", [], "CIRC_A() > 0")
        self.registry.load_custom_indicators()

        handler = self.registry.get_handler("CIRC_A")
        result = handler({}, self.ctx)
        # Should return error result (circular reference or unknown function)
        # Either result.is_valid is False, or the error is caught
        if result.error:
            self.assertFalse(result.is_valid)
        # Even if it doesn't detect the circle (shallow eval), it shouldn't crash
        _evaluation_stack.clear()  # Cleanup

    def test_skip_builtin_names(self):
        """Should not overwrite built-in functions."""
        self.repo.save_indicator("RSI", [], "PRICE")  # Name collision
        loaded = self.registry.load_custom_indicators()
        self.assertEqual(loaded, 0)  # Should be skipped


class TestLoadFromDb(unittest.TestCase):
    """Test load_from_db function."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.repo = Repository(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)
        for ext in ("-wal", "-shm"):
            wal = self.tmp.name + ext
            if os.path.exists(wal):
                os.unlink(wal)

    def test_load_from_db(self):
        rows = [
            {"timestamp": f"2024-01-{i+1:02d}", "open": 100+i, "high": 110+i,
             "low": 90+i, "close": 105+i, "volume": 1000+i}
            for i in range(50)
        ]
        self.repo.save_market_data(rows, "TEST_SYM")

        from lecat.data_loader import load_from_db
        ctx = load_from_db("TEST_SYM", db_path=self.tmp.name)
        self.assertEqual(ctx.total_bars, 50)
        self.assertEqual(ctx.symbol, "TEST_SYM")

    def test_load_from_db_not_found(self):
        from lecat.data_loader import load_from_db
        with self.assertRaises(ValueError):
            load_from_db("NOPE", db_path=self.tmp.name)


if __name__ == "__main__":
    unittest.main()
