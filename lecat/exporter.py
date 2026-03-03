"""Strategy Exporter — Save and load LECAT strategies as JSON.

Enables strategy persistence: users can save their best strategies
from the optimizer or lab, and reload them later.

Schema:
    {
        "name": "Strategy Name",
        "expression": "RSI(14) > 70 AND PRICE > SMA(50)",
        "metrics": {"sharpe": 1.5, "return": 25.4, ...},
        "timestamp": "2026-03-03T12:00:00",
        "engine_version": "2.0"
    }
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lecat.fitness import FitnessResult

ENGINE_VERSION = "2.0"


def save_strategy(
    expression: str,
    metrics: dict[str, float] | FitnessResult | None = None,
    name: str = "",
    filepath: str | Path = "strategy.json",
) -> Path:
    """Save a strategy to a JSON file.

    Args:
        expression: LECAT expression string.
        metrics: Performance metrics (dict or FitnessResult).
        name: Human-readable strategy name.
        filepath: Output file path.

    Returns:
        Path to the saved file.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Convert FitnessResult to dict
    if isinstance(metrics, FitnessResult):
        metrics_dict = {
            "sharpe": round(metrics.sharpe_ratio, 4),
            "return": round(metrics.total_return_pct, 4),
            "win_rate": round(metrics.win_rate, 4),
            "trades": metrics.num_trades,
            "max_drawdown": round(metrics.max_drawdown_pct, 4),
            "fitness": round(metrics.fitness_score, 4),
        }
    elif metrics is not None:
        metrics_dict = metrics
    else:
        metrics_dict = {}

    strategy_data = {
        "name": name or _auto_name(expression),
        "expression": expression,
        "metrics": metrics_dict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
    }

    with open(filepath, "w") as f:
        json.dump(strategy_data, f, indent=2)

    return filepath


def load_strategy(filepath: str | Path) -> dict[str, Any]:
    """Load a strategy from a JSON file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        Strategy data dict with 'expression', 'name', 'metrics', etc.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If JSON is invalid or missing required fields.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Strategy file not found: {filepath}")

    with open(filepath, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")

    if "expression" not in data:
        raise ValueError(f"Strategy file missing 'expression' field: {filepath}")

    return data


def save_strategies_batch(
    strategies: list[dict],
    filepath: str | Path = "strategies.json",
) -> Path:
    """Save multiple strategies to a single JSON file.

    Args:
        strategies: List of strategy dicts.
        filepath: Output file path.

    Returns:
        Path to the saved file.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    batch = {
        "strategies": strategies,
        "count": len(strategies),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
    }

    with open(filepath, "w") as f:
        json.dump(batch, f, indent=2)

    return filepath


def load_strategies_batch(filepath: str | Path) -> list[dict]:
    """Load multiple strategies from a batch JSON file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        List of strategy dicts.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Strategies file not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    if "strategies" in data:
        return data["strategies"]
    elif isinstance(data, list):
        return data
    else:
        # Single strategy file
        return [data]


def strategy_to_json_string(
    expression: str,
    metrics: dict[str, float] | FitnessResult | None = None,
    name: str = "",
) -> str:
    """Convert a strategy to a JSON string (for dashboard download).

    Args:
        expression: LECAT expression string.
        metrics: Performance metrics.
        name: Strategy name.

    Returns:
        JSON string.
    """
    if isinstance(metrics, FitnessResult):
        metrics_dict = {
            "sharpe": round(metrics.sharpe_ratio, 4),
            "return": round(metrics.total_return_pct, 4),
            "win_rate": round(metrics.win_rate, 4),
            "trades": metrics.num_trades,
            "max_drawdown": round(metrics.max_drawdown_pct, 4),
            "fitness": round(metrics.fitness_score, 4),
        }
    elif metrics is not None:
        metrics_dict = metrics
    else:
        metrics_dict = {}

    data = {
        "name": name or _auto_name(expression),
        "expression": expression,
        "metrics": metrics_dict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
    }

    return json.dumps(data, indent=2)


def _auto_name(expression: str) -> str:
    """Generate a name from the expression."""
    # Take first few tokens as name
    clean = expression.replace("(", " ").replace(")", " ").replace(",", " ")
    tokens = clean.split()[:4]
    return " ".join(tokens) if tokens else "Unnamed Strategy"
