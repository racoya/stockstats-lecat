"""ExpressionGenerator — Random strategy creator for LECAT.

Generates syntactically valid LECAT expressions by recursively building
AST-like structures and serializing them to strings. Uses the
FunctionRegistry for smart argument generation within valid ranges.

See docs/05_Integration_Strategy.md for the generator design.
"""

from __future__ import annotations

import random
from typing import Any

from lecat.registry import FunctionRegistry


# Default configuration
DEFAULT_MAX_DEPTH = 3
OFFSET_PROBABILITY = 0.10  # 10% chance of appending [n] offset
MAX_OFFSET_VALUE = 10


class ExpressionGenerator:
    """Generates random, syntactically valid LECAT expression strings.

    Usage:
        registry = FunctionRegistry()
        register_std_lib(registry)
        gen = ExpressionGenerator(registry)
        expr = gen.generate()  # e.g., "RSI(14) > 70 AND PRICE > SMA(50)"
    """

    def __init__(
        self,
        registry: FunctionRegistry,
        max_depth: int = DEFAULT_MAX_DEPTH,
        offset_probability: float = OFFSET_PROBABILITY,
        seed: int | None = None,
    ) -> None:
        self._registry = registry
        self._max_depth = max_depth
        self._offset_probability = offset_probability
        self._rng = random.Random(seed)

        # Collect available functions from registry
        self._functions = registry.get_available_functions()
        self._indicator_fns = [f for f in self._functions if f.arg_schema]
        self._accessor_fns = [f for f in self._functions if not f.arg_schema]

    def generate(self, max_depth: int | None = None) -> str:
        """Generate a random, valid LECAT expression string.

        Args:
            max_depth: Override the default max recursion depth.

        Returns:
            A syntactically valid LECAT expression string.
        """
        depth = max_depth if max_depth is not None else self._max_depth
        return self._gen_expression(depth)

    # ------------------------------------------------------------------
    # Recursive builders
    # ------------------------------------------------------------------

    def _gen_expression(self, depth: int) -> str:
        """Generate an expression at the given depth level."""
        if depth <= 0:
            return self._gen_comparison(0)

        # Choose between: binary op (AND/OR) or comparison
        choice = self._rng.random()
        if choice < 0.5 and depth > 1:
            # Binary operation: left OP right
            op = self._rng.choice(["AND", "OR"])
            left = self._gen_expression(depth - 1)
            right = self._gen_expression(depth - 1)
            return f"{left} {op} {right}"
        elif choice < 0.8:
            # NOT expression (less frequent)
            if depth > 1 and self._rng.random() < 0.2:
                inner = self._gen_comparison(depth - 1)
                return f"NOT ({inner})"
            return self._gen_comparison(depth - 1)
        else:
            return self._gen_comparison(depth - 1)

    def _gen_comparison(self, depth: int) -> str:
        """Generate a comparison: left op right."""
        op = self._rng.choice([">", "<", ">=", "<=", "==", "!="])
        left = self._gen_primary(depth)
        right = self._gen_primary_or_literal(depth)
        return f"{left} {op} {right}"

    def _gen_primary(self, depth: int) -> str:
        """Generate a primary expression (function call or identifier)."""
        node = self._gen_function_or_identifier()

        # Maybe add offset
        if self._rng.random() < self._offset_probability:
            offset = self._rng.randint(1, MAX_OFFSET_VALUE)
            node = f"{node}[{offset}]"

        return node

    def _gen_primary_or_literal(self, depth: int) -> str:
        """Generate either a primary expression or a numeric literal."""
        if self._rng.random() < 0.5:
            return self._gen_primary(depth)
        return self._gen_literal()

    def _gen_function_or_identifier(self) -> str:
        """Generate a function call with valid args, or a bare identifier."""
        if self._indicator_fns and self._rng.random() < 0.6:
            # Function call with arguments
            fn = self._rng.choice(self._indicator_fns)
            args = self._gen_arguments(fn.arg_schema)
            args_str = ", ".join(str(a) for a in args)
            return f"{fn.name}({args_str})"
        elif self._accessor_fns:
            # Bare identifier (zero-arg accessor)
            fn = self._rng.choice(self._accessor_fns)
            return fn.name
        else:
            return "PRICE"

    def _gen_arguments(self, schema: list[dict[str, Any]]) -> list[int | float]:
        """Generate valid arguments based on the function's arg_schema."""
        args: list[int | float] = []
        for param in schema:
            param_type = param.get("type", "float")
            min_val = param.get("min", 1)
            max_val = param.get("max", 100)
            default = param.get("default")

            if param_type == "integer":
                # Use default occasionally, otherwise random in range
                if default is not None and self._rng.random() < 0.3:
                    args.append(int(default))
                else:
                    args.append(self._rng.randint(int(min_val), int(max_val)))
            else:
                if default is not None and self._rng.random() < 0.3:
                    args.append(float(default))
                else:
                    args.append(round(self._rng.uniform(float(min_val), float(max_val)), 2))

        return args

    def _gen_literal(self) -> str:
        """Generate a numeric literal value."""
        if self._rng.random() < 0.7:
            # Integer literal (common for thresholds like 70, 80, etc.)
            return str(self._rng.choice([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]))
        else:
            # Float literal
            return str(round(self._rng.uniform(0, 100), 2))

    # ------------------------------------------------------------------
    # Batch generation
    # ------------------------------------------------------------------

    def generate_batch(self, count: int, max_depth: int | None = None) -> list[str]:
        """Generate multiple unique expressions.

        Args:
            count: Number of expressions to generate.
            max_depth: Override the default max depth.

        Returns:
            List of unique expression strings.
        """
        expressions: set[str] = set()
        attempts = 0
        max_attempts = count * 10  # Avoid infinite loops

        while len(expressions) < count and attempts < max_attempts:
            expr = self.generate(max_depth)
            expressions.add(expr)
            attempts += 1

        return list(expressions)
