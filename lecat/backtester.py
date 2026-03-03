"""Backtester — Time-loop engine for LECAT strategy evaluation.

Runs an AST expression across an entire price history, producing a
boolean signal array and a BacktestResult containing basic statistics.

See docs/05_Integration_Strategy.md for the backtester design.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from lecat.ast_nodes import ASTNode, FunctionCallNode, OffsetNode
from lecat.context import MarketContext
from lecat.evaluator import Evaluator
from lecat.registry import FunctionRegistry, FunctionResult
from lecat.stats import compute_stats, StrategyStats


@dataclass(frozen=True)
class BacktestResult:
    """Result of backtesting a strategy across market data.

    Attributes:
        expression: The original expression string.
        signals: Boolean signal array (True = signal active).
        stats: Computed statistics for the signal array.
        total_bars: Total number of bars in the dataset.
        warmup_bars: Bars skipped for indicator warmup.
        elapsed_ms: Time taken in milliseconds.
    """

    expression: str
    signals: list[bool]
    stats: StrategyStats
    total_bars: int
    warmup_bars: int
    elapsed_ms: float


class Backtester:
    """Time-loop backtesting engine.

    Usage:
        registry = FunctionRegistry()
        register_std_lib(registry)
        evaluator = Evaluator(registry)
        backtester = Backtester(evaluator, registry)
        result = backtester.run(ast, context, expression_str="PRICE > 10")
    """

    def __init__(self, evaluator: Evaluator, registry: FunctionRegistry) -> None:
        self._evaluator = evaluator
        self._registry = registry

    def run(
        self,
        ast: ASTNode,
        context: MarketContext,
        expression: str = "",
    ) -> BacktestResult:
        """Run a strategy across the full price history.

        Args:
            ast: The parsed AST to evaluate.
            context: Market data (bar_index is ignored; we iterate all bars).
            expression: Original expression string (for reporting).

        Returns:
            BacktestResult with signal array and statistics.
        """
        total_bars = context.total_bars
        warmup = self._calculate_warmup(ast)

        signals: list[bool] = []
        start_time = time.perf_counter()

        for bar_idx in range(total_bars):
            if bar_idx < warmup:
                signals.append(False)
                continue

            bar_ctx = context.with_index(bar_idx)
            self._evaluator._cache.clear()
            result = self._evaluator.evaluate(ast, bar_ctx)

            if result.is_valid and result.value is not None and result.value != 0.0:
                signals.append(True)
            else:
                signals.append(False)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        stats = compute_stats(signals, warmup)

        return BacktestResult(
            expression=expression,
            signals=signals,
            stats=stats,
            total_bars=total_bars,
            warmup_bars=warmup,
            elapsed_ms=elapsed_ms,
        )

    def _calculate_warmup(self, ast: ASTNode) -> int:
        """Walk the AST to determine the maximum lookback needed.

        This considers function argument schemas (min_bars) and
        offset shift amounts for correct warmup calculation.
        """
        return self._walk_warmup(ast)

    def _walk_warmup(self, node: ASTNode) -> int:
        """Recursively calculate warmup bars from AST nodes."""
        if isinstance(node, FunctionCallNode):
            # Get min_bars from registry metadata
            fn_warmup = 0
            if self._registry.has_function(node.name):
                meta = self._registry.get_function_meta(node.name)
                # Build args dict to pass to min_bars_required
                arg_values: dict[str, float] = {}
                for i, param in enumerate(meta.arg_schema):
                    if i < len(node.arguments):
                        from lecat.ast_nodes import LiteralNode
                        arg_node = node.arguments[i]
                        if isinstance(arg_node, LiteralNode):
                            arg_values[param["name"]] = arg_node.value  # type: ignore
                        else:
                            arg_values[param["name"]] = param.get("default", 20)
                    elif "default" in param:
                        arg_values[param["name"]] = param["default"]
                try:
                    fn_warmup = meta.min_bars_required(arg_values)
                except Exception:
                    fn_warmup = 0

            # Also check child arguments for nested functions
            child_warmup = max(
                (self._walk_warmup(arg) for arg in node.arguments),
                default=0,
            )
            return max(fn_warmup, child_warmup)

        elif isinstance(node, OffsetNode):
            # Offset adds to the warmup requirement
            child_warmup = self._walk_warmup(node.child)
            return child_warmup + node.shift_amount

        elif hasattr(node, "left") and hasattr(node, "right"):
            # BinaryOp or Comparison
            left_warmup = self._walk_warmup(node.left)  # type: ignore
            right_warmup = self._walk_warmup(node.right)  # type: ignore
            return max(left_warmup, right_warmup)

        elif hasattr(node, "operand"):
            # UnaryOp
            return self._walk_warmup(node.operand)  # type: ignore

        elif hasattr(node, "child"):
            return self._walk_warmup(node.child)  # type: ignore

        # LiteralNode, IdentifierNode
        return 0
