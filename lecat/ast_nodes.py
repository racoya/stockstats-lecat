"""Immutable AST node definitions for the LECAT compiler.

All nodes use frozen dataclasses to guarantee immutability after construction.
Node types correspond to the schemas defined in docs/02_System_Architecture.md.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ASTNode:
    """Abstract base for all AST nodes."""


# ---------------------------------------------------------------------------
# Leaf nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LiteralNode(ASTNode):
    """A literal value: integer, float, or boolean.

    Examples: 80, 3.14, TRUE
    """

    value: int | float | bool
    value_type: str  # "integer", "float", or "boolean"


@dataclass(frozen=True)
class IdentifierNode(ASTNode):
    """A bare identifier, resolved via the Function Registry as a zero-arg function.

    Examples: PRICE, VOLUME, close
    """

    name: str


# ---------------------------------------------------------------------------
# Composite nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FunctionCallNode(ASTNode):
    """A function call with arguments.

    Examples: RSI(14), SMA(50), MACD(12, 26, 9)
    """

    name: str
    arguments: tuple[ASTNode, ...]


@dataclass(frozen=True)
class UnaryOpNode(ASTNode):
    """A unary operation: NOT (logical) or - (arithmetic negation).

    Examples: NOT condition, -value
    """

    operator: str  # "NOT" or "-"
    operand: ASTNode


@dataclass(frozen=True)
class ComparisonNode(ASTNode):
    """A comparison between two expressions.

    Operators: >, <, >=, <=, ==, !=
    """

    operator: str
    left: ASTNode
    right: ASTNode


@dataclass(frozen=True)
class BinaryOpNode(ASTNode):
    """A binary logical operation: AND or OR.

    Examples: A AND B, X OR Y
    """

    operator: str  # "AND" or "OR"
    left: ASTNode
    right: ASTNode


@dataclass(frozen=True)
class OffsetNode(ASTNode):
    """A time-shifted evaluation (Context Shifting — CR-001).

    Wraps a child expression to be evaluated at bar_index - shift_amount.

    Examples: RSI(14)[1], (close > open)[1]
    """

    shift_amount: int
    child: ASTNode
