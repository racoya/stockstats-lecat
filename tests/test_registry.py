"""Unit tests for the LECAT FunctionRegistry."""

import unittest

from lecat.context import MarketContext
from lecat.registry import (
    FunctionMeta,
    FunctionRegistry,
    FunctionResult,
    RegistryError,
)


def _make_context() -> MarketContext:
    """Helper: minimal market context for testing."""
    return MarketContext(
        open=[10.0], high=[11.0], low=[9.0],
        close=[10.5], volume=[100.0], bar_index=0,
    )


class TestFunctionResult(unittest.TestCase):
    """Test FunctionResult factory methods."""

    def test_success(self):
        r = FunctionResult.success(42.0)
        self.assertTrue(r.is_valid)
        self.assertEqual(r.value, 42.0)
        self.assertIsNone(r.error)

    def test_insufficient_data(self):
        r = FunctionResult.insufficient_data()
        self.assertFalse(r.is_valid)
        self.assertIsNone(r.value)
        self.assertIsNotNone(r.error)

    def test_from_error(self):
        r = FunctionResult.from_error("boom")
        self.assertFalse(r.is_valid)
        self.assertEqual(r.error, "boom")


class TestRegistration(unittest.TestCase):
    """Test function registration."""

    def test_decorator_registration(self):
        reg = FunctionRegistry()

        @reg.register(name="TEST")
        def test_fn(args, ctx):
            return FunctionResult.success(1.0)

        self.assertTrue(reg.has_function("TEST"))

    def test_programmatic_registration(self):
        reg = FunctionRegistry()
        reg.register_handler(
            name="TEST",
            handler=lambda args, ctx: FunctionResult.success(1.0),
        )
        self.assertTrue(reg.has_function("TEST"))

    def test_duplicate_raises(self):
        reg = FunctionRegistry()
        reg.register_handler(name="X", handler=lambda a, c: FunctionResult.success(0.0))
        with self.assertRaises(RegistryError):
            reg.register_handler(name="X", handler=lambda a, c: FunctionResult.success(0.0))

    def test_locked_registry_rejects(self):
        reg = FunctionRegistry()
        reg.lock()
        with self.assertRaises(RegistryError):
            reg.register_handler(name="X", handler=lambda a, c: FunctionResult.success(0.0))

    def test_lock_flag(self):
        reg = FunctionRegistry()
        self.assertFalse(reg.is_locked)
        reg.lock()
        self.assertTrue(reg.is_locked)


class TestHandlerLookup(unittest.TestCase):
    """Test handler retrieval."""

    def test_get_handler(self):
        reg = FunctionRegistry()
        handler = lambda args, ctx: FunctionResult.success(99.0)
        reg.register_handler(name="MY_FN", handler=handler)
        self.assertIs(reg.get_handler("MY_FN"), handler)

    def test_unknown_handler_raises(self):
        reg = FunctionRegistry()
        with self.assertRaises(RegistryError):
            reg.get_handler("NOPE")

    def test_handler_executes(self):
        reg = FunctionRegistry()
        reg.register_handler(
            name="DOUBLE",
            handler=lambda args, ctx: FunctionResult.success(args["x"] * 2),
            arg_schema=[{"name": "x", "type": "float", "required": True}],
        )
        handler = reg.get_handler("DOUBLE")
        result = handler({"x": 5.0}, _make_context())
        self.assertEqual(result.value, 10.0)


class TestIntrospection(unittest.TestCase):
    """Test metadata and introspection API."""

    def test_get_function_meta(self):
        reg = FunctionRegistry()
        reg.register_handler(
            name="SMA",
            handler=lambda a, c: FunctionResult.success(0.0),
            description="Simple Moving Average",
            arg_schema=[{"name": "period", "type": "integer"}],
        )
        meta = reg.get_function_meta("SMA")
        self.assertIsInstance(meta, FunctionMeta)
        self.assertEqual(meta.name, "SMA")
        self.assertEqual(meta.description, "Simple Moving Average")

    def test_get_available_functions(self):
        reg = FunctionRegistry()
        reg.register_handler(name="A", handler=lambda a, c: FunctionResult.success(0.0))
        reg.register_handler(name="B", handler=lambda a, c: FunctionResult.success(0.0))
        funcs = reg.get_available_functions()
        names = [f.name for f in funcs]
        self.assertIn("A", names)
        self.assertIn("B", names)
        self.assertEqual(len(funcs), 2)

    def test_unknown_meta_raises(self):
        reg = FunctionRegistry()
        with self.assertRaises(RegistryError):
            reg.get_function_meta("NOPE")


if __name__ == "__main__":
    unittest.main()
