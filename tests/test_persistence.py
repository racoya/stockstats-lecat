"""Unit tests for the LECAT Exporter and Logger modules."""

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path

from lecat.exporter import (
    ENGINE_VERSION,
    load_strategy,
    load_strategies_batch,
    save_strategy,
    save_strategies_batch,
    strategy_to_json_string,
    _auto_name,
)
from lecat.logger import get_logger, setup_logging


class TestSaveStrategy(unittest.TestCase):
    """Test strategy save/load cycle (Case B)."""

    def test_save_creates_file(self):
        """save_strategy should create a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test_strategy.json"
            result = save_strategy("RSI(14) > 70", filepath=filepath)
            self.assertTrue(result.exists())

    def test_save_load_roundtrip(self):
        """Saved strategy should load back with same expression."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "roundtrip.json"
            save_strategy("PRICE > SMA(50)", name="Golden Cross", filepath=filepath)
            loaded = load_strategy(filepath)

            self.assertEqual(loaded["expression"], "PRICE > SMA(50)")
            self.assertEqual(loaded["name"], "Golden Cross")
            self.assertEqual(loaded["engine_version"], ENGINE_VERSION)
            self.assertIn("timestamp", loaded)

    def test_save_with_metrics_dict(self):
        """Metrics dict should be preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "metrics.json"
            metrics = {"sharpe": 1.5, "return": 25.4}
            save_strategy("RSI(14) > 70", metrics=metrics, filepath=filepath)
            loaded = load_strategy(filepath)
            self.assertEqual(loaded["metrics"]["sharpe"], 1.5)
            self.assertEqual(loaded["metrics"]["return"], 25.4)

    def test_save_creates_parent_dirs(self):
        """Should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nested" / "dir" / "strategy.json"
            save_strategy("PRICE > 100", filepath=filepath)
            self.assertTrue(filepath.exists())

    def test_auto_name(self):
        """Auto-generated name should use first tokens."""
        name = _auto_name("RSI(14) > 70 AND PRICE > SMA(50)")
        self.assertIn("RSI", name)


class TestLoadStrategy(unittest.TestCase):
    """Test strategy loading edge cases."""

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing files."""
        with self.assertRaises(FileNotFoundError):
            load_strategy("/nonexistent/path.json")

    def test_invalid_json(self):
        """Should raise ValueError for invalid JSON."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("not valid json")
            f.flush()
            with self.assertRaises(ValueError):
                load_strategy(f.name)
            os.unlink(f.name)

    def test_missing_expression_field(self):
        """Should raise ValueError if expression key is missing."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"name": "test"}, f)
            f.flush()
            with self.assertRaises(ValueError):
                load_strategy(f.name)
            os.unlink(f.name)


class TestBatchExport(unittest.TestCase):
    """Test batch strategy export/import."""

    def test_batch_roundtrip(self):
        strategies = [
            {"expression": "RSI(14) > 70", "name": "Strategy 1"},
            {"expression": "PRICE > SMA(50)", "name": "Strategy 2"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "batch.json"
            save_strategies_batch(strategies, filepath=filepath)
            loaded = load_strategies_batch(filepath)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["expression"], "RSI(14) > 70")


class TestJsonString(unittest.TestCase):
    """Test JSON string generation."""

    def test_json_string_output(self):
        result = strategy_to_json_string("PRICE > 100", name="Test")
        data = json.loads(result)
        self.assertEqual(data["expression"], "PRICE > 100")
        self.assertEqual(data["name"], "Test")


class TestLogger(unittest.TestCase):
    """Test the logging system (Case C)."""

    def test_get_logger(self):
        """get_logger should return a Logger instance."""
        log = get_logger("test.module")
        self.assertIsInstance(log, logging.Logger)

    def test_logger_name(self):
        """Logger name should match the module path."""
        log = get_logger("lecat.test")
        self.assertEqual(log.name, "lecat.test")

    def test_log_to_file(self):
        """Logger should write to file handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Reset logging state for isolated test
            import lecat.logger
            lecat.logger._configured = False
            root = logging.getLogger("lecat")
            root.handlers.clear()

            setup_logging(log_dir=tmpdir, log_file="test.log")
            log = get_logger("lecat.test_file")
            log.info("Test message for file handler")

            # Force flush
            for handler in logging.getLogger("lecat").handlers:
                handler.flush()

            log_file = Path(tmpdir) / "test.log"
            self.assertTrue(log_file.exists())

            content = log_file.read_text()
            self.assertIn("Test message for file handler", content)

            # Clean up
            lecat.logger._configured = False
            root.handlers.clear()


class TestConfig(unittest.TestCase):
    """Test configuration loading."""

    def test_get_config(self):
        from lecat import get_config
        config = get_config()
        self.assertIsInstance(config, dict)
        self.assertIn("initial_capital", config)
        self.assertEqual(config["initial_capital"], 10000)

    def test_config_has_optimizer_section(self):
        from lecat import get_config
        config = get_config()
        self.assertIn("optimizer", config)
        self.assertEqual(config["optimizer"]["population_size"], 100)


if __name__ == "__main__":
    unittest.main()
