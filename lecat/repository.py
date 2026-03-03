"""Repository — SQLite CRUD wrapper for LECAT persistence.

Centralizes all database operations: market data ingestion,
custom indicator management, and optimization result logging.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Path to schema file
_SCHEMA_PATH = Path(__file__).parent / "data" / "schema.sql"

# Default database location
DEFAULT_DB_PATH = Path(__file__).parent.parent / "lecat.db"


class Repository:
    """SQLite repository for LECAT data persistence.

    Usage:
        repo = Repository()                    # Uses default lecat.db
        repo = Repository("path/to/my.db")     # Custom location

        repo.save_market_data(rows, "BTC_USD")
        ctx_data = repo.get_market_data("BTC_USD")
    """

    def __init__(self, db_path: Union[str, Path, None] = None) -> None:
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database with the schema."""
        with self._connect() as conn:
            if _SCHEMA_PATH.exists():
                conn.executescript(_SCHEMA_PATH.read_text())
            else:
                # Inline fallback if schema file is missing
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS market_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL DEFAULT '1D',
                        timestamp DATETIME NOT NULL,
                        open REAL, high REAL, low REAL, close REAL, volume REAL,
                        UNIQUE(symbol, timeframe, timestamp)
                    );
                    CREATE TABLE IF NOT EXISTS indicators (
                        name TEXT PRIMARY KEY,
                        args TEXT NOT NULL DEFAULT '[]',
                        formula TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS strategy_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        expression TEXT NOT NULL,
                        metrics TEXT NOT NULL,
                        dataset_symbol TEXT DEFAULT '',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """)

    def _connect(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    def save_market_data(
        self,
        rows: list[dict[str, Any]],
        symbol: str,
        timeframe: str = "1D",
    ) -> int:
        """Bulk insert market data rows.

        Args:
            rows: List of dicts with keys: timestamp, open, high, low, close, volume.
            symbol: Ticker symbol (e.g., "BTC_USD").
            timeframe: Candle timeframe (default "1D").

        Returns:
            Number of rows inserted.
        """
        with self._connect() as conn:
            inserted = 0
            for row in rows:
                try:
                    conn.execute(
                        """INSERT OR REPLACE INTO market_data
                           (symbol, timeframe, timestamp, open, high, low, close, volume)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            symbol,
                            timeframe,
                            row.get("timestamp", ""),
                            row.get("open", 0.0),
                            row.get("high", 0.0),
                            row.get("low", 0.0),
                            row.get("close", 0.0),
                            row.get("volume", 0.0),
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
        return inserted

    def get_market_data(
        self, symbol: str, timeframe: str = "1D"
    ) -> list[dict[str, Any]]:
        """Retrieve market data for a symbol.

        Returns:
            List of dicts with OHLCV + timestamp data, ordered by timestamp.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """SELECT timestamp, open, high, low, close, volume
                   FROM market_data
                   WHERE symbol = ? AND timeframe = ?
                   ORDER BY timestamp ASC""",
                (symbol, timeframe),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_symbols(self) -> list[str]:
        """Return all unique symbols in the database."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
            )
            return [row["symbol"] for row in cursor.fetchall()]

    def delete_market_data(self, symbol: str, timeframe: str = "1D") -> int:
        """Delete all market data for a symbol. Returns rows deleted."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM market_data WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe),
            )
            conn.commit()
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Custom Indicators
    # ------------------------------------------------------------------

    def save_indicator(
        self,
        name: str,
        args: list[str],
        formula: str,
        description: str = "",
    ) -> None:
        """Insert or update a custom indicator.

        Args:
            name: Unique indicator name (e.g., "AVG_PRICE").
            args: List of argument names (e.g., ["fast", "slow"]).
            formula: DSL expression (e.g., "(HIGH + LOW) / 2").
            description: Human-readable description.
        """
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO indicators (name, args, formula, description)
                   VALUES (?, ?, ?, ?)""",
                (name.upper(), json.dumps(args), formula, description),
            )
            conn.commit()

    def delete_indicator(self, name: str) -> bool:
        """Delete a custom indicator. Returns True if deleted."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM indicators WHERE name = ?", (name.upper(),)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_all_indicators(self) -> list[dict[str, Any]]:
        """Return all custom indicators as a list of dicts.

        Each dict has keys: name, args (list), formula, description, created_at.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT name, args, formula, description, created_at FROM indicators ORDER BY name"
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "name": row["name"],
                    "args": json.loads(row["args"]),
                    "formula": row["formula"],
                    "description": row["description"],
                    "created_at": row["created_at"],
                })
            return results

    def get_indicator(self, name: str) -> dict[str, Any] | None:
        """Return a single indicator by name, or None if not found."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT name, args, formula, description, created_at FROM indicators WHERE name = ?",
                (name.upper(),),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "name": row["name"],
                "args": json.loads(row["args"]),
                "formula": row["formula"],
                "description": row["description"],
                "created_at": row["created_at"],
            }

    # ------------------------------------------------------------------
    # Strategy Results
    # ------------------------------------------------------------------

    def save_result(
        self,
        expression: str,
        metrics: dict[str, Any],
        dataset_symbol: str = "",
    ) -> int:
        """Log a backtest/optimization result.

        Returns:
            The row ID of the inserted result.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO strategy_results (expression, metrics, dataset_symbol)
                   VALUES (?, ?, ?)""",
                (expression, json.dumps(metrics), dataset_symbol),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_results(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent strategy results, most recent first."""
        with self._connect() as conn:
            cursor = conn.execute(
                """SELECT id, expression, metrics, dataset_symbol, timestamp
                   FROM strategy_results
                   ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "expression": row["expression"],
                    "metrics": json.loads(row["metrics"]),
                    "dataset_symbol": row["dataset_symbol"],
                    "timestamp": row["timestamp"],
                })
            return results

    def clear_results(self) -> int:
        """Delete all strategy results. Returns rows deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM strategy_results")
            conn.commit()
            return cursor.rowcount
