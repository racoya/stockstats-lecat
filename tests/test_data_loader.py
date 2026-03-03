"""Unit tests for the LECAT Data Loader."""

import csv
import math
import os
import tempfile
import unittest

from lecat.context import MarketContext
from lecat.data_loader import load_from_csv, load_from_lists


class TestLoadFromCSV(unittest.TestCase):
    """Test CSV loading into MarketContext."""

    def _write_csv(self, rows: list[dict], path: str) -> None:
        """Helper: write a list of dicts to CSV."""
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_basic_load(self):
        """Case A: Load a standard OHLCV CSV."""
        rows = [
            {"Date": "2024-01-01", "Open": "100", "High": "110", "Low": "90", "Close": "105", "Volume": "1000"},
            {"Date": "2024-01-02", "Open": "105", "High": "115", "Low": "95", "Close": "110", "Volume": "1200"},
            {"Date": "2024-01-03", "Open": "110", "High": "120", "Low": "100", "Close": "115", "Volume": "800"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            self._write_csv(rows, path)
            ctx = load_from_csv(path, symbol="TEST", timeframe="1D")

            self.assertEqual(ctx.total_bars, 3)
            self.assertEqual(ctx.bar_index, 2)
            self.assertAlmostEqual(ctx.close[0], 105.0, places=0)
            self.assertAlmostEqual(ctx.close[-1], 115.0, places=0)
            self.assertEqual(ctx.symbol, "TEST")
            self.assertEqual(ctx.timeframe, "1D")
        finally:
            os.unlink(path)

    def test_column_aliases(self):
        """Handles alternative column names (e.g., 'adj close')."""
        rows = [
            {"date": "2024-01-01", "open": "100", "high": "110", "low": "90", "adj close": "105", "vol": "1000"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            self._write_csv(rows, path)
            ctx = load_from_csv(path)
            self.assertEqual(ctx.total_bars, 1)
            self.assertAlmostEqual(ctx.close[0], 105.0, places=0)
        finally:
            os.unlink(path)

    def test_forward_fill(self):
        """NaN/missing values should be forward-filled."""
        rows = [
            {"Date": "2024-01-01", "Open": "100", "High": "110", "Low": "90", "Close": "105", "Volume": "1000"},
            {"Date": "2024-01-02", "Open": "105", "High": "115", "Low": "95", "Close": "", "Volume": ""},
            {"Date": "2024-01-03", "Open": "110", "High": "120", "Low": "100", "Close": "115", "Volume": "800"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            self._write_csv(rows, path)
            ctx = load_from_csv(path)
            # Row 2 close was empty, should be forward-filled from row 1
            self.assertAlmostEqual(ctx.close[1], 105.0, places=0)
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_from_csv("/nonexistent/path.csv")

    def test_missing_column_error(self):
        """Missing required column raises ValueError."""
        rows = [{"Date": "2024-01-01", "Open": "100", "High": "110"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            self._write_csv(rows, path)
            with self.assertRaises(ValueError):
                load_from_csv(path)
        finally:
            os.unlink(path)

    def test_last_index_access(self):
        """Accessing close[-1] returns the last price."""
        rows = [
            {"Date": "2024-01-01", "Open": "100", "High": "110", "Low": "90", "Close": "105", "Volume": "1000"},
            {"Date": "2024-01-02", "Open": "105", "High": "115", "Low": "95", "Close": "200", "Volume": "1200"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            self._write_csv(rows, path)
            ctx = load_from_csv(path)
            self.assertAlmostEqual(ctx.close[-1], 200.0, places=0)
        finally:
            os.unlink(path)


class TestLoadFromLists(unittest.TestCase):
    """Test programmatic loading."""

    def test_basic(self):
        ctx = load_from_lists(
            [10.0, 20.0], [12.0, 22.0], [8.0, 18.0],
            [11.0, 21.0], [100.0, 200.0],
        )
        self.assertEqual(ctx.total_bars, 2)
        self.assertEqual(ctx.close[1], 21.0)

    def test_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            load_from_lists([10.0], [12.0], [8.0], [11.0, 21.0], [100.0])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            load_from_lists([], [], [], [], [])


class TestContextSplit(unittest.TestCase):
    """Test MarketContext.split() for walk-forward validation."""

    def test_split_ratio(self):
        ctx = MarketContext(
            open=[1.0] * 10, high=[2.0] * 10, low=[0.5] * 10,
            close=list(range(1, 11)), volume=[100.0] * 10,  # type: ignore
            bar_index=9,
        )
        train, test = ctx.split(0.7)
        self.assertEqual(train.total_bars, 7)
        self.assertEqual(test.total_bars, 3)

    def test_split_50_50(self):
        close = list(map(float, range(1, 11)))
        ctx = MarketContext(
            open=[1.0] * 10, high=[2.0] * 10, low=[0.5] * 10,
            close=close, volume=[100.0] * 10,
            bar_index=9,
        )
        train, test = ctx.split(0.5)
        self.assertEqual(train.total_bars, 5)
        self.assertEqual(test.total_bars, 5)
        # No data overlap
        self.assertEqual(list(train.close), close[:5])
        self.assertEqual(list(test.close), close[5:])

    def test_split_invalid_ratio(self):
        ctx = MarketContext(
            open=[1.0], high=[2.0], low=[0.5],
            close=[1.0], volume=[100.0], bar_index=0,
        )
        with self.assertRaises(ValueError):
            ctx.split(0.0)
        with self.assertRaises(ValueError):
            ctx.split(1.0)


if __name__ == "__main__":
    unittest.main()
