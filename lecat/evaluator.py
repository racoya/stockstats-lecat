"""Evaluator — AST tree walker for the LECAT DSL.

Traverses an immutable AST produced by the Parser and evaluates it
against market data via the FunctionRegistry. Returns a FunctionResult
for single-bar evaluation.

Key behaviors:
  - BinaryOp (AND/OR): Short-circuit boolean logic.
  - ComparisonNode: Epsilon-aware float comparison.
  - OffsetNode (CR-001): Shifts context to a past bar via with_index().
  - FunctionCallNode: Delegates to the registry handler.
  - Identifiers: Treated as zero-arg function calls (e.g., PRICE → close).
"""

from __future__ import annotations

from lecat.ast_nodes import (
    ASTNode,
    BinaryOpNode,
    ComparisonNode,
    FunctionCallNode,
    IdentifierNode,
    LiteralNode,
    OffsetNode,
    UnaryOpNode,
)
from lecat.context import MarketContext
from lecat.errors import LECATError
from lecat.registry import FunctionRegistry, FunctionResult

# Floating-point comparison tolerance (see docs/00_Overview.md §3.4)
EPSILON = 1e-9


class EvaluationError(LECATError):
    """Raised on runtime evaluation failures."""

    def __init__(self, message: str, bar_index: int | None = None) -> None:
        self.bar_index = bar_index
        super().__init__(message)


class Evaluator:
    """Tree-walking evaluator for LECAT AST nodes.

    Usage:
        evaluator = Evaluator(registry)
        result = evaluator.evaluate(ast, context)
    """

    def __init__(self, registry: FunctionRegistry) -> None:
        self._registry = registry
        # Cache: (function_name, args_tuple, bar_index) → FunctionResult
        self._cache: dict[tuple, FunctionResult] = {}

    def evaluate(self, ast: ASTNode, context: MarketContext) -> FunctionResult:
        """Evaluate an AST node against market data.

        Args:
            ast: The root node to evaluate.
            context: Market data and current bar position.

        Returns:
            FunctionResult with the computed value.
        """
        self._cache.clear()
        return self._visit(ast, context)

    def evaluate_series(
        self, ast: ASTNode, context: MarketContext
    ) -> list[FunctionResult]:
        """Evaluate an AST across all bars, returning a result per bar.

        Iterates bar_index from 0 to context.bar_index (inclusive),
        evaluating the expression at each bar.

        Returns:
            List of FunctionResult, one per bar.
        """
        results: list[FunctionResult] = []
        for i in range(context.bar_index + 1):
            bar_ctx = context.with_index(i)
            self._cache.clear()
            results.append(self._visit(ast, bar_ctx))
        return results

    # ------------------------------------------------------------------
    # Visitor dispatch
    # ------------------------------------------------------------------

    def _visit(self, node: ASTNode, ctx: MarketContext) -> FunctionResult:
        """Dispatch to the appropriate visit method based on node type."""
        if isinstance(node, LiteralNode):
            return self._visit_literal(node)
        elif isinstance(node, IdentifierNode):
            return self._visit_identifier(node, ctx)
        elif isinstance(node, FunctionCallNode):
            return self._visit_function_call(node, ctx)
        elif isinstance(node, UnaryOpNode):
            return self._visit_unary(node, ctx)
        elif isinstance(node, ComparisonNode):
            return self._visit_comparison(node, ctx)
        elif isinstance(node, BinaryOpNode):
            return self._visit_binary(node, ctx)
        elif isinstance(node, OffsetNode):
            return self._visit_offset(node, ctx)
        else:
            raise EvaluationError(
                f"Unknown AST node type: {type(node).__name__}",
                bar_index=ctx.bar_index,
            )

    # ------------------------------------------------------------------
    # Node visitors
    # ------------------------------------------------------------------

    def _visit_literal(self, node: LiteralNode) -> FunctionResult:
        """Evaluate a literal value."""
        if isinstance(node.value, bool):
            return FunctionResult.success(1.0 if node.value else 0.0)
        return FunctionResult.success(float(node.value))

    def _visit_identifier(
        self, node: IdentifierNode, ctx: MarketContext
    ) -> FunctionResult:
        """Evaluate an identifier — treated as a zero-arg function call."""
        # Check if the registry has this identifier as a function
        if self._registry.has_function(node.name):
            cache_key = (node.name, (), ctx.bar_index)
            if cache_key in self._cache:
                return self._cache[cache_key]

            handler = self._registry.get_handler(node.name)
            result = handler({}, ctx)
            self._cache[cache_key] = result
            return result

        # Unknown identifier
        raise EvaluationError(
            f"Unknown identifier: '{node.name}'",
            bar_index=ctx.bar_index,
        )

    def _visit_function_call(
        self, node: FunctionCallNode, ctx: MarketContext
    ) -> FunctionResult:
        """Evaluate a function call by delegating to the registry."""
        # Evaluate arguments
        arg_values: list[float] = []
        for arg_node in node.arguments:
            arg_result = self._visit(arg_node, ctx)
            if not arg_result.is_valid:
                return arg_result  # Propagate invalid results
            assert arg_result.value is not None
            arg_values.append(arg_result.value)

        # Build args dict from schema
        if not self._registry.has_function(node.name):
            raise EvaluationError(
                f"Unknown function: '{node.name}'",
                bar_index=ctx.bar_index,
            )

        meta = self._registry.get_function_meta(node.name)
        args = _build_args_dict(meta.arg_schema, arg_values)

        # Cache lookup (key includes bar_index per CR-001)
        args_tuple = tuple(sorted(args.items()))
        cache_key = (node.name, args_tuple, ctx.bar_index)
        if cache_key in self._cache:
            return self._cache[cache_key]

        handler = self._registry.get_handler(node.name)
        result = handler(args, ctx)
        self._cache[cache_key] = result
        return result

    def _visit_unary(
        self, node: UnaryOpNode, ctx: MarketContext
    ) -> FunctionResult:
        """Evaluate a unary operation (NOT or -)."""
        operand = self._visit(node.operand, ctx)
        if not operand.is_valid:
            return operand

        assert operand.value is not None

        if node.operator == "NOT":
            # Boolean negation: 0.0 → 1.0, non-zero → 0.0
            return FunctionResult.success(0.0 if operand.value != 0.0 else 1.0)
        elif node.operator == "-":
            return FunctionResult.success(-operand.value)
        else:
            raise EvaluationError(
                f"Unknown unary operator: '{node.operator}'",
                bar_index=ctx.bar_index,
            )

    def _visit_comparison(
        self, node: ComparisonNode, ctx: MarketContext
    ) -> FunctionResult:
        """Evaluate a comparison, returning 1.0 (True) or 0.0 (False).

        Uses epsilon tolerance for == and != comparisons.
        """
        left = self._visit(node.left, ctx)
        if not left.is_valid:
            return FunctionResult.success(0.0)  # Invalid → False

        right = self._visit(node.right, ctx)
        if not right.is_valid:
            return FunctionResult.success(0.0)  # Invalid → False

        assert left.value is not None and right.value is not None
        a, b = left.value, right.value

        result = _compare(node.operator, a, b)
        return FunctionResult.success(1.0 if result else 0.0)

    def _visit_binary(
        self, node: BinaryOpNode, ctx: MarketContext
    ) -> FunctionResult:
        """Evaluate AND/OR with short-circuit semantics."""
        left = self._visit(node.left, ctx)

        if node.operator == "AND":
            # Short-circuit: if left is False/invalid, skip right
            if not left.is_valid or left.value == 0.0:
                return FunctionResult.success(0.0)
            right = self._visit(node.right, ctx)
            if not right.is_valid or right.value == 0.0:
                return FunctionResult.success(0.0)
            return FunctionResult.success(1.0)

        elif node.operator == "OR":
            # Short-circuit: if left is True, skip right
            if left.is_valid and left.value is not None and left.value != 0.0:
                return FunctionResult.success(1.0)
            right = self._visit(node.right, ctx)
            if right.is_valid and right.value is not None and right.value != 0.0:
                return FunctionResult.success(1.0)
            return FunctionResult.success(0.0)

        else:
            raise EvaluationError(
                f"Unknown binary operator: '{node.operator}'",
                bar_index=ctx.bar_index,
            )

    def _visit_offset(
        self, node: OffsetNode, ctx: MarketContext
    ) -> FunctionResult:
        """Evaluate a context-shifted expression (CR-001).

        Shifts bar_index back by shift_amount and evaluates the child.
        """
        past_index = ctx.bar_index - node.shift_amount
        if past_index < 0:
            return FunctionResult.insufficient_data()

        shifted_ctx = ctx.with_index(past_index)
        return self._visit(node.child, shifted_ctx)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _build_args_dict(
    schema: list[dict], values: list[float]
) -> dict[str, float]:
    """Map positional argument values to named arguments using the schema."""
    args: dict[str, float] = {}
    for i, param in enumerate(schema):
        name = param["name"]
        if i < len(values):
            # Coerce to int if schema says integer
            if param.get("type") == "integer":
                args[name] = int(values[i])
            else:
                args[name] = values[i]
        elif "default" in param:
            args[name] = param["default"]
        elif param.get("required", False):
            raise EvaluationError(
                f"Missing required argument: '{name}'"
            )
    return args


def _compare(op: str, a: float, b: float) -> bool:
    """Perform epsilon-aware float comparison."""
    if op == ">":
        return a > b + EPSILON
    elif op == "<":
        return a < b - EPSILON
    elif op == ">=":
        return a > b - EPSILON
    elif op == "<=":
        return a < b + EPSILON
    elif op == "==":
        return abs(a - b) < EPSILON
    elif op == "!=":
        return abs(a - b) >= EPSILON
    else:
        raise EvaluationError(f"Unknown comparison operator: '{op}'")
