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


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def ast_to_string(node: ASTNode) -> str:
    """Serialize an AST back to a LECAT expression string.

    This is the inverse of parsing — needed by the evolution module
    to convert mutated/crossover ASTs back to string form.
    """
    if isinstance(node, LiteralNode):
        if isinstance(node.value, bool):
            return "TRUE" if node.value else "FALSE"
        if isinstance(node.value, float) and node.value == int(node.value):
            return str(int(node.value))
        return str(node.value)

    elif isinstance(node, IdentifierNode):
        return node.name

    elif isinstance(node, FunctionCallNode):
        args = ", ".join(ast_to_string(a) for a in node.arguments)
        return f"{node.name}({args})"

    elif isinstance(node, UnaryOpNode):
        operand_str = ast_to_string(node.operand)
        if node.operator == "NOT":
            # Wrap in parens if operand is composite
            if isinstance(node.operand, (BinaryOpNode, ComparisonNode)):
                return f"NOT ({operand_str})"
            return f"NOT {operand_str}"
        return f"-{operand_str}"

    elif isinstance(node, ComparisonNode):
        left = ast_to_string(node.left)
        right = ast_to_string(node.right)
        return f"{left} {node.operator} {right}"

    elif isinstance(node, BinaryOpNode):
        left = ast_to_string(node.left)
        right = ast_to_string(node.right)
        # Wrap in parens if needed for precedence
        if isinstance(node.left, BinaryOpNode) and node.left.operator != node.operator:
            left = f"({left})"
        if isinstance(node.right, BinaryOpNode) and node.right.operator != node.operator:
            right = f"({right})"
        return f"{left} {node.operator} {right}"

    elif isinstance(node, OffsetNode):
        child_str = ast_to_string(node.child)
        # Wrap composite children in parens
        if isinstance(node.child, (BinaryOpNode, ComparisonNode, UnaryOpNode)):
            child_str = f"({child_str})"
        return f"{child_str}[{node.shift_amount}]"

    raise ValueError(f"Unknown node type: {type(node).__name__}")

