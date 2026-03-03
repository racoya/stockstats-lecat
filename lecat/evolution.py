"""Genetic Operators — Mutation, Crossover, and Selection for LECAT.

Operates directly on immutable AST nodes, producing new ASTs by:
  - Mutation: Tweak parameters, flip operators, or replace subtrees.
  - Crossover: Swap subtrees between two parent ASTs.
  - Selection: Tournament selection for breeding.

All operators preserve AST validity — output is always compilable.
Type-aware grafting prevents invalid structures like chained comparisons.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from lecat.ast_nodes import (
    ASTNode,
    BinaryOpNode,
    ComparisonNode,
    FunctionCallNode,
    IdentifierNode,
    LiteralNode,
    OffsetNode,
    UnaryOpNode,
    ast_to_string,
)
from lecat.generator import ExpressionGenerator
from lecat.registry import FunctionRegistry


# ------------------------------------------------------------------
# Type classification helpers
# ------------------------------------------------------------------


def _is_value_node(node: ASTNode) -> bool:
    """True for nodes that produce a numeric value (not boolean logic)."""
    return isinstance(node, (LiteralNode, IdentifierNode, FunctionCallNode, OffsetNode))


def _is_logic_node(node: ASTNode) -> bool:
    """True for nodes that produce a boolean value."""
    return isinstance(node, (ComparisonNode, BinaryOpNode, UnaryOpNode))


def _node_is_inside_comparison(node: ASTNode, path: list) -> bool:
    """Check if this node is a direct child of a ComparisonNode."""
    # Path entries are like ("left",) or ("right",) etc.
    # We check based on the path structure - this is a simplified check
    return False  # We use type-aware replacement instead


# ------------------------------------------------------------------
# AST Traversal helpers
# ------------------------------------------------------------------


def _collect_nodes_with_parent(
    node: ASTNode, parent: ASTNode | None = None
) -> list[tuple[ASTNode, ASTNode | None, str]]:
    """Collect all nodes with their parent and the field name they occupy.

    Returns: list of (node, parent, field_name)
    """
    results: list[tuple[ASTNode, ASTNode | None, str]] = [(node, parent, "root")]

    if isinstance(node, BinaryOpNode):
        results.extend(_collect_nodes_with_parent(node.left, node))
        results.extend(_collect_nodes_with_parent(node.right, node))
    elif isinstance(node, ComparisonNode):
        results.extend(_collect_nodes_with_parent(node.left, node))
        results.extend(_collect_nodes_with_parent(node.right, node))
    elif isinstance(node, UnaryOpNode):
        results.extend(_collect_nodes_with_parent(node.operand, node))
    elif isinstance(node, OffsetNode):
        results.extend(_collect_nodes_with_parent(node.child, node))
    elif isinstance(node, FunctionCallNode):
        for arg in node.arguments:
            results.extend(_collect_nodes_with_parent(arg, node))

    return results


def _collect_nodes(node: ASTNode) -> list[tuple[ASTNode, list]]:
    """Collect all nodes in the AST with their path (for selection).

    Returns a list of (node, path) where path is a list of tuples.
    """
    results: list[tuple[ASTNode, list]] = [(node, [])]

    if isinstance(node, BinaryOpNode):
        for child, path in _collect_nodes(node.left):
            results.append((child, [("left",)] + path))
        for child, path in _collect_nodes(node.right):
            results.append((child, [("right",)] + path))
    elif isinstance(node, ComparisonNode):
        for child, path in _collect_nodes(node.left):
            results.append((child, [("left",)] + path))
        for child, path in _collect_nodes(node.right):
            results.append((child, [("right",)] + path))
    elif isinstance(node, UnaryOpNode):
        for child, path in _collect_nodes(node.operand):
            results.append((child, [("operand",)] + path))
    elif isinstance(node, OffsetNode):
        for child, path in _collect_nodes(node.child):
            results.append((child, [("child",)] + path))
    elif isinstance(node, FunctionCallNode):
        for i, arg in enumerate(node.arguments):
            for child, path in _collect_nodes(arg):
                results.append((child, [("arguments", i)] + path))

    return results


def _replace_subtree(root: ASTNode, target: ASTNode, replacement: ASTNode) -> ASTNode:
    """Replace a specific subtree in the AST with a new subtree.

    Since nodes are frozen, this rebuilds the path from root to target.
    """
    if root is target:
        return replacement

    if isinstance(root, BinaryOpNode):
        new_left = _replace_subtree(root.left, target, replacement)
        new_right = _replace_subtree(root.right, target, replacement)
        if new_left is not root.left or new_right is not root.right:
            return BinaryOpNode(operator=root.operator, left=new_left, right=new_right)
        return root

    elif isinstance(root, ComparisonNode):
        new_left = _replace_subtree(root.left, target, replacement)
        new_right = _replace_subtree(root.right, target, replacement)
        if new_left is not root.left or new_right is not root.right:
            return ComparisonNode(operator=root.operator, left=new_left, right=new_right)
        return root

    elif isinstance(root, UnaryOpNode):
        new_operand = _replace_subtree(root.operand, target, replacement)
        if new_operand is not root.operand:
            return UnaryOpNode(operator=root.operator, operand=new_operand)
        return root

    elif isinstance(root, OffsetNode):
        new_child = _replace_subtree(root.child, target, replacement)
        if new_child is not root.child:
            return OffsetNode(shift_amount=root.shift_amount, child=new_child)
        return root

    elif isinstance(root, FunctionCallNode):
        new_args = []
        changed = False
        for arg in root.arguments:
            new_arg = _replace_subtree(arg, target, replacement)
            new_args.append(new_arg)
            if new_arg is not arg:
                changed = True
        if changed:
            return FunctionCallNode(name=root.name, arguments=tuple(new_args))
        return root

    return root


def _safe_replace(
    root: ASTNode,
    target: ASTNode,
    donor: ASTNode,
    target_parent: ASTNode | None,
) -> ASTNode | None:
    """Type-aware replacement that avoids creating invalid structures.

    Returns None if the replacement would create an invalid AST
    (e.g., chained comparison).
    """
    # Rule: Don't place a boolean/comparison node inside a comparison's operand
    if isinstance(target_parent, ComparisonNode) and _is_logic_node(donor):
        return None

    # Rule: Don't place a boolean/comparison node inside a function arg
    if isinstance(target_parent, FunctionCallNode) and _is_logic_node(donor):
        return None

    return _replace_subtree(root, target, donor)


def _validate_ast(ast: ASTNode) -> bool:
    """Verify an AST can be serialized and re-parsed without errors."""
    try:
        from lecat.lexer import Lexer
        from lecat.parser import Parser
        expr = ast_to_string(ast)
        Parser(Lexer(expr).tokenize()).parse()
        return True
    except Exception:
        return False


# ------------------------------------------------------------------
# Mutation
# ------------------------------------------------------------------

# Operator pools for random flips
_COMP_OPS = [">", "<", ">=", "<=", "==", "!="]
_LOGIC_OPS = ["AND", "OR"]


def mutate(
    ast: ASTNode,
    registry: FunctionRegistry,
    rng: random.Random | None = None,
    generator: ExpressionGenerator | None = None,
) -> ASTNode:
    """Apply a random mutation to an AST.

    Mutation types:
      1. Parameter tweak: Change a numeric literal ±20%
      2. Operator flip: Change > to <, AND to OR, etc.
      3. Subtree replacement: Replace a random subtree with a new random one

    All mutations are validated before returning. If validation fails,
    the original AST is returned unchanged.

    Args:
        ast: The AST to mutate.
        registry: For generating valid replacement subtrees.
        rng: Random number generator.
        generator: For creating replacement subtrees.

    Returns:
        A new, valid AST with one mutation applied.
    """
    if rng is None:
        rng = random.Random()
    if generator is None:
        generator = ExpressionGenerator(registry, max_depth=2, seed=None)
        generator._rng = rng

    nodes = _collect_nodes(ast)
    if len(nodes) <= 1:
        return ast

    # Choose mutation strategy
    choice = rng.random()

    if choice < 0.4:
        result = _mutate_parameter(ast, nodes, rng)
    elif choice < 0.75:
        result = _mutate_operator(ast, nodes, rng)
    else:
        result = _mutate_subtree(ast, nodes, rng, generator)

    # Validate the result — fall back to original if invalid
    if _validate_ast(result):
        return result
    return ast


def _mutate_parameter(
    ast: ASTNode,
    nodes: list[tuple[ASTNode, list]],
    rng: random.Random,
) -> ASTNode:
    """Tweak a numeric literal by ±20%."""
    literals = [(n, p) for n, p in nodes if isinstance(n, LiteralNode) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
    if not literals:
        return ast

    target, _ = rng.choice(literals)
    assert isinstance(target, LiteralNode)

    if isinstance(target.value, int):
        delta = max(1, int(abs(target.value) * 0.2))
        new_val = target.value + rng.randint(-delta, delta)
        new_val = max(1, new_val)  # Keep positive for periods
        new_node = LiteralNode(value=new_val, value_type="integer")
    else:
        delta = abs(target.value) * 0.2
        new_val = target.value + rng.uniform(-delta, delta)
        new_node = LiteralNode(value=round(new_val, 2), value_type="float")

    return _replace_subtree(ast, target, new_node)


def _mutate_operator(
    ast: ASTNode,
    nodes: list[tuple[ASTNode, list]],
    rng: random.Random,
) -> ASTNode:
    """Flip a comparison or logical operator."""
    comps = [(n, p) for n, p in nodes if isinstance(n, ComparisonNode)]
    bools = [(n, p) for n, p in nodes if isinstance(n, BinaryOpNode)]

    candidates = comps + bools
    if not candidates:
        return ast

    target, _ = rng.choice(candidates)

    if isinstance(target, ComparisonNode):
        new_op = rng.choice([op for op in _COMP_OPS if op != target.operator])
        new_node = ComparisonNode(operator=new_op, left=target.left, right=target.right)
    elif isinstance(target, BinaryOpNode):
        new_op = "OR" if target.operator == "AND" else "AND"
        new_node = BinaryOpNode(operator=new_op, left=target.left, right=target.right)
    else:
        return ast

    return _replace_subtree(ast, target, new_node)


def _mutate_subtree(
    ast: ASTNode,
    nodes: list[tuple[ASTNode, list]],
    rng: random.Random,
    generator: ExpressionGenerator,
) -> ASTNode:
    """Replace a random subtree with a type-compatible replacement."""
    from lecat.lexer import Lexer
    from lecat.parser import Parser

    # Collect nodes with parent info for type-safe replacement
    nodes_with_parent = _collect_nodes_with_parent(ast)
    # Skip root
    non_root = [(n, parent, field) for n, parent, field in nodes_with_parent if parent is not None]
    if not non_root:
        return ast

    target, parent, _ = rng.choice(non_root)

    # Determine what type of node is safe to graft here
    if isinstance(parent, ComparisonNode):
        # Inside a comparison: only value nodes are safe
        replacement = _gen_value_node(generator, rng)
    elif isinstance(parent, FunctionCallNode):
        # Inside a function arg: only value/literal nodes
        replacement = _gen_value_node(generator, rng)
    else:
        # Anywhere else: generate freely
        try:
            expr_str = generator.generate(max_depth=1)
            tokens = Lexer(expr_str).tokenize()
            replacement = Parser(tokens).parse()
        except Exception:
            return ast

    return _replace_subtree(ast, target, replacement)


def _gen_value_node(generator: ExpressionGenerator, rng: random.Random) -> ASTNode:
    """Generate a value-producing node (identifier, function call, or literal)."""
    # Use the generator's internals to produce a value-level node
    primary = generator._gen_function_or_identifier()
    from lecat.lexer import Lexer
    from lecat.parser import Parser
    try:
        tokens = Lexer(primary).tokenize()
        return Parser(tokens).parse()
    except Exception:
        return LiteralNode(value=50, value_type="integer")


# ------------------------------------------------------------------
# Crossover
# ------------------------------------------------------------------


def crossover(
    parent_a: ASTNode,
    parent_b: ASTNode,
    rng: random.Random | None = None,
) -> ASTNode:
    """Swap subtrees between two parent ASTs to produce a child.

    Type-aware: ensures that grafted subtrees are compatible with their
    new position (e.g., no comparison inside a comparison).

    Args:
        parent_a: First parent AST.
        parent_b: Second parent AST.
        rng: Random number generator.

    Returns:
        A new child AST combining parts of both parents.
    """
    if rng is None:
        rng = random.Random()

    nodes_b = _collect_nodes(parent_b)
    nodes_a_with_parent = _collect_nodes_with_parent(parent_a)

    # Filter to non-root nodes in parent_a
    non_root_a = [(n, parent) for n, parent, field in nodes_a_with_parent if parent is not None]
    if not non_root_a:
        return parent_b if rng.random() < 0.5 else parent_a

    # Try multiple times to find a compatible graft
    for _ in range(10):
        target, target_parent = rng.choice(non_root_a)
        donor, _ = rng.choice(nodes_b)

        result = _safe_replace(parent_a, target, donor, target_parent)
        if result is not None and _validate_ast(result):
            return result

    # All attempts failed — return parent_a unchanged
    return parent_a


# ------------------------------------------------------------------
# Selection
# ------------------------------------------------------------------


@dataclass
class Individual:
    """A strategy individual in the population.

    Attributes:
        ast: The parsed AST.
        expression: The original expression string.
        fitness: Fitness score (higher is better).
    """

    ast: ASTNode
    expression: str
    fitness: float = 0.0


def tournament_selection(
    population: list[Individual],
    k: int = 3,
    rng: random.Random | None = None,
) -> Individual:
    """Select the best individual from k random candidates.

    Args:
        population: List of individuals to select from.
        k: Tournament size (default: 3).
        rng: Random number generator.

    Returns:
        The individual with the highest fitness among k candidates.
    """
    if rng is None:
        rng = random.Random()

    candidates = rng.sample(population, min(k, len(population)))
    return max(candidates, key=lambda ind: ind.fitness)
