"""Dynamic Registry — Database-backed indicator registration for LECAT.

Extends FunctionRegistry to load custom indicators from the SQLite
database. Each custom indicator's formula is compiled and evaluated
at runtime using the standard LECAT pipeline (Lexer → Parser → Evaluator).

Safety: detects circular references (A calls B, B calls A) and raises
RecursionError with the dependency chain.
"""

from __future__ import annotations

import re
from typing import Any

from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry, FunctionResult
from lecat.repository import Repository


# Maximum nesting depth for composite indicators
_MAX_DEPTH = 10


class DynamicRegistry(FunctionRegistry):
    """FunctionRegistry that additionally loads custom indicators from SQLite.

    Usage:
        repo = Repository()
        registry = DynamicRegistry(repo)
        register_std_lib(registry)            # Built-in indicators
        registry.load_custom_indicators()     # DB-defined indicators
    """

    def __init__(self, repository: Repository) -> None:
        super().__init__()
        self._repository = repository
        self._custom_names: set[str] = set()

    def load_custom_indicators(self) -> int:
        """Load all custom indicators from the database.

        Returns:
            Number of custom indicators loaded.
        """
        indicators = self._repository.get_all_indicators()
        loaded = 0

        for ind in indicators:
            name = ind["name"]
            args = ind["args"]
            formula = ind["formula"]
            description = ind.get("description", "")

            # Skip if already registered (e.g., built-in with same name)
            if self.has_function(name):
                continue

            self._register_composite(name, args, formula, description)
            self._custom_names.add(name)
            loaded += 1

        # Load Python-based dynamic plugins
        from lecat.plugin_loader import load_plugins
        plugins_loaded = load_plugins(self)
        if plugins_loaded > 0:
            import logging
            logging.getLogger("lecat.registry").info(f"Loaded {plugins_loaded} Python plugins.")

        return loaded + plugins_loaded

    def reload_custom_indicators(self) -> int:
        """Unregister all custom indicators and reload from DB.

        Returns:
            Number of custom indicators loaded.
        """
        # Remove old custom handlers
        for name in list(self._custom_names):
            self._handlers.pop(name, None)
            self._metadata.pop(name, None)
        self._custom_names.clear()

        return self.load_custom_indicators()

    def _register_composite(
        self,
        name: str,
        arg_names: list[str],
        formula: str,
        description: str,
    ) -> None:
        """Register a composite indicator that evaluates a DSL formula."""

        # Build arg_schema from declared argument names
        arg_schema = []
        for arg_name in arg_names:
            arg_schema.append({
                "name": arg_name,
                "type": "float",
                "default": 0,
            })

        def make_handler(fn_name: str, fn_formula: str, fn_arg_names: list[str]):
            """Factory to capture the formula in a closure."""

            def handler(args: dict[str, Any], context: MarketContext) -> FunctionResult:
                return _evaluate_composite(
                    fn_name, fn_formula, fn_arg_names, args, context, self
                )

            return handler

        handler = make_handler(name, formula, arg_names)

        self.register_handler(
            name=name,
            handler=handler,
            description=description or f"Custom: {formula}",
            arg_schema=arg_schema,
            min_bars_required=lambda _: 1,
        )


# Thread-local recursion guard
_evaluation_stack: list[str] = []


def _evaluate_composite(
    name: str,
    formula: str,
    arg_names: list[str],
    args: dict[str, Any],
    context: MarketContext,
    registry: FunctionRegistry,
) -> FunctionResult:
    """Evaluate a composite indicator formula.

    1. Substitute argument values into the formula string.
    2. Compile (Lexer → Parser).
    3. Evaluate against the current context.

    Raises RecursionError if circular references are detected.
    """
    global _evaluation_stack

    # Circular reference detection
    if name in _evaluation_stack:
        chain = " → ".join(_evaluation_stack + [name])
        return FunctionResult.from_error(
            f"Circular reference detected: {chain}"
        )

    if len(_evaluation_stack) >= _MAX_DEPTH:
        return FunctionResult.from_error(
            f"Maximum indicator nesting depth ({_MAX_DEPTH}) exceeded"
        )

    _evaluation_stack.append(name)
    try:
        # Inject argument values into the formula
        resolved = _substitute_args(formula, arg_names, args)

        # Compile
        tokens = Lexer(resolved).tokenize()
        ast = Parser(tokens).parse()

        # Evaluate
        evaluator = Evaluator(registry)
        result = evaluator.evaluate(ast, context)

        if isinstance(result, bool):
            return FunctionResult.success(1.0 if result else 0.0)
        elif isinstance(result, (int, float)):
            return FunctionResult.success(float(result))
        else:
            return FunctionResult.success(1.0 if result else 0.0)

    except Exception as e:
        return FunctionResult.from_error(f"{type(e).__name__}: {e}")
    finally:
        _evaluation_stack.pop()


def _substitute_args(
    formula: str, arg_names: list[str], args: dict[str, Any]
) -> str:
    """Replace argument placeholders in a formula with actual values.

    E.g., formula="SMA(fast) > SMA(slow)", args={"fast": 10, "slow": 50}
    → "SMA(10) > SMA(50)"
    """
    result = formula
    for arg_name in arg_names:
        if arg_name in args:
            value = args[arg_name]
            # Replace whole-word occurrences only (avoid partial matches)
            result = re.sub(
                r'\b' + re.escape(arg_name) + r'\b',
                str(value),
                result,
            )
    return result
