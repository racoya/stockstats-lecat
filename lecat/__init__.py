# LECAT - Logical Expression Compiler for Algorithmic Trading

from __future__ import annotations

import os
from pathlib import Path

# Package version
__version__ = "2.0.0"

# Default config path (relative to package root)
_CONFIG_PATH = Path(__file__).parent / "config.yaml"

# Global config singleton
_config: dict | None = None


def get_config() -> dict:
    """Load and return the LECAT configuration.

    Loads from lecat/config.yaml on first call, caches thereafter.
    Falls back to defaults if yaml is unavailable or file missing.
    """
    global _config
    if _config is not None:
        return _config

    defaults = {
        "initial_capital": 10000,
        "chart_theme": "plotly_dark",
        "log_dir": "logs",
        "strategies_dir": "strategies",
        "optimizer": {
            "population_size": 100,
            "generations": 10,
            "elite_count": 5,
            "mutation_rate": 0.3,
            "crossover_rate": 0.7,
            "tournament_k": 3,
            "max_depth": 3,
        },
        "dashboard": {
            "port": 8501,
            "theme": "dark",
        },
    }

    try:
        import yaml  # type: ignore

        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH) as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                defaults.update(loaded)
    except ImportError:
        pass  # PyYAML not installed; use defaults

    _config = defaults
    return _config
