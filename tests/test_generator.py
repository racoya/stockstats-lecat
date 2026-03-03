"""Unit tests for the LECAT ExpressionGenerator."""

import unittest

from lecat.errors import LexerError, ParserError
from lecat.generator import ExpressionGenerator
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib


def _make_registry() -> FunctionRegistry:
    reg = FunctionRegistry()
    register_std_lib(reg)
    return reg


class TestGeneratorValidity(unittest.TestCase):
    """PM Case A: Every generated string must compile without errors."""

    def test_100_random_strategies_compile(self):
        """Generate 100 strategies; all must parse successfully."""
        reg = _make_registry()
        gen = ExpressionGenerator(reg, seed=42)

        errors: list[tuple[str, str]] = []
        for i in range(100):
            expr = gen.generate()
            try:
                tokens = Lexer(expr).tokenize()
                Parser(tokens).parse()
            except (LexerError, ParserError) as e:
                errors.append((expr, str(e)))

        if errors:
            msg = "\n".join(f"  [{i}] {expr!r}: {err}" for i, (expr, err) in enumerate(errors))
            self.fail(f"{len(errors)} expressions failed to compile:\n{msg}")

    def test_depth_1(self):
        """Low depth should produce simple expressions."""
        reg = _make_registry()
        gen = ExpressionGenerator(reg, max_depth=1, seed=99)

        for _ in range(50):
            expr = gen.generate()
            tokens = Lexer(expr).tokenize()
            Parser(tokens).parse()  # Should not raise

    def test_depth_4(self):
        """High depth should still produce valid expressions."""
        reg = _make_registry()
        gen = ExpressionGenerator(reg, max_depth=4, seed=77)

        for _ in range(50):
            expr = gen.generate()
            tokens = Lexer(expr).tokenize()
            Parser(tokens).parse()


class TestGeneratorFeatures(unittest.TestCase):
    """Test generator features and configuration."""

    def test_seed_reproducibility(self):
        """Same seed should produce identical expressions."""
        reg = _make_registry()
        gen1 = ExpressionGenerator(reg, seed=123)
        gen2 = ExpressionGenerator(reg, seed=123)

        for _ in range(20):
            self.assertEqual(gen1.generate(), gen2.generate())

    def test_different_seeds_differ(self):
        """Different seeds should produce different expressions."""
        reg = _make_registry()
        gen1 = ExpressionGenerator(reg, seed=1)
        gen2 = ExpressionGenerator(reg, seed=2)

        exprs1 = [gen1.generate() for _ in range(10)]
        exprs2 = [gen2.generate() for _ in range(10)]
        self.assertNotEqual(exprs1, exprs2)

    def test_batch_generation(self):
        """generate_batch produces unique expressions."""
        reg = _make_registry()
        gen = ExpressionGenerator(reg, seed=42)
        batch = gen.generate_batch(10)
        self.assertEqual(len(batch), 10)
        self.assertEqual(len(set(batch)), 10)  # All unique

    def test_contains_offsets(self):
        """With offset_probability > 0, some expressions should contain [n]."""
        reg = _make_registry()
        gen = ExpressionGenerator(reg, offset_probability=0.5, seed=42)
        exprs = [gen.generate() for _ in range(50)]
        has_offset = any("[" in e for e in exprs)
        self.assertTrue(has_offset, "No offsets generated with 50% probability")

    def test_zero_offset_probability(self):
        """With offset_probability=0, no offsets should appear."""
        reg = _make_registry()
        gen = ExpressionGenerator(reg, offset_probability=0.0, seed=42)
        exprs = [gen.generate() for _ in range(50)]
        has_offset = any("[" in e for e in exprs)
        self.assertFalse(has_offset, "Offsets generated with 0% probability")

    def test_output_is_string(self):
        reg = _make_registry()
        gen = ExpressionGenerator(reg, seed=42)
        expr = gen.generate()
        self.assertIsInstance(expr, str)
        self.assertTrue(len(expr) > 0)


if __name__ == "__main__":
    unittest.main()
