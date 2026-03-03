import unittest
from pathlib import Path
import tempfile
import sys
import os

from lecat.registry import FunctionRegistry
from lecat.plugin_loader import load_plugins

class TestPluginLoader(unittest.TestCase):
    def setUp(self):
        self.registry = FunctionRegistry()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.plugins_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_valid_plugin(self):
        # Create a valid plugin file
        plugin_code = """
from lecat.registry import FunctionRegistry, FunctionResult

def register_plugin(registry: FunctionRegistry) -> None:
    @registry.register(name="TEST_MATH", description="Test math", arg_schema=[], min_bars_required=lambda _: 1)
    def test_handler(args, ctx):
        return FunctionResult.success(42.0)
"""
        with open(self.plugins_path / "valid_plugin.py", "w") as f:
            f.write(plugin_code)

        count = load_plugins(self.registry, self.plugins_path)
        self.assertEqual(count, 1)
        self.assertTrue(self.registry.has_function("TEST_MATH"))

    def test_load_plugin_missing_register(self):
        # Create a plugin missing register_plugin
        plugin_code = """
def some_other_function():
    pass
"""
        with open(self.plugins_path / "invalid_plugin.py", "w") as f:
            f.write(plugin_code)

        count = load_plugins(self.registry, self.plugins_path)
        self.assertEqual(count, 0)

    def test_ignore_underscore_files(self):
        # Create a valid plugin but prefixed with _
        plugin_code = """
def register_plugin(registry):
    pass
"""
        with open(self.plugins_path / "_hidden_plugin.py", "w") as f:
            f.write(plugin_code)

        count = load_plugins(self.registry, self.plugins_path)
        self.assertEqual(count, 0)
