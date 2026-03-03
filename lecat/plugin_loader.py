"""Dynamic Plugin Loader for LECAT.

Scans the `lecat_plugins/` directory for Python files and dynamically loads them
to register user-defined custom math and indicators.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Union

from lecat.registry import FunctionRegistry

logger = logging.getLogger("lecat.plugins")

# Default plugins directory relative to the project root
DEFAULT_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "lecat_plugins"


def load_plugins(registry: FunctionRegistry, plugins_dir: Union[str, Path, None] = None) -> int:
    """Scan and load all Python plugins in the designated directory.

    Each plugin file must define a `register_plugin(registry: FunctionRegistry)`
    function.

    Args:
        registry: The FunctionRegistry to register plugins into.
        plugins_dir: Path to the plugins directory. Defaults to `lecat_plugins/`.

    Returns:
        Number of plugins successfully loaded.
    """
    plugins_path = Path(plugins_dir) if plugins_dir else DEFAULT_PLUGINS_DIR

    if not plugins_path.exists() or not plugins_path.is_dir():
        logger.warning(f"Plugins directory not found: {plugins_path}")
        return 0

    count = 0
    for file_path in plugins_path.glob("*.py"):
        if file_path.name.startswith("_"):
            continue

        module_name = f"lecat_plugins.{file_path.stem}"
        try:
            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec is None or spec.loader is None:
                logger.error(f"Cannot load plugin specification for {file_path}")
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Check for the required entry point
            if hasattr(module, "register_plugin"):
                module.register_plugin(registry)
                logger.debug(f"Successfully loaded plugin: {file_path.name}")
                count += 1
            else:
                logger.warning(f"Plugin {file_path.name} missing `register_plugin(registry)` function.")

        except Exception as e:
            logger.error(f"Failed to load plugin {file_path.name}: {e}")

    return count
