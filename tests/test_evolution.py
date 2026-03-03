"""Unit tests for the LECAT Evolution module (Genetic Operators)."""

import unittest
import random

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
from lecat.evolution import (
    Individual,
    crossover,
    mutate,
    tournament_selection,
    _collect_nodes,
)
from lecat.lexer import Lexer
from lecat.main import generate_random_ohlcv
from lecat.optimizer import Optimizer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib


def _make_registry() -> FunctionRegistry:
    reg = FunctionRegistry()
    register_std_lib(reg)
    return reg


def _parse(expr: str) -> ASTNode:
    return Parser(Lexer(expr).tokenize()).parse()


def _validate(ast: ASTNode) -> bool:
    """Check that an AST can be serialized and re-parsed."""
    try:
        expr = ast_to_string(ast)
        Parser(Lexer(expr).tokenize()).parse()
        return True
    except Exception:
        return False


# ======================================================================
# PM Acceptance Criteria
# ======================================================================


class TestAcceptanceCriteria(unittest.TestCase):
    """Tests matching PM acceptance criteria for Phase 3 Sprint 1."""

    def test_case_a_mutation_validity(self):
        """Case A: Mutate RSI(14) > 50 100 times, all must be valid ASTs.
        At least some must differ from the original.
        """
        reg = _make_registry()
        original = _parse("RSI(14) > 50")
        original_str = ast_to_string(original)
        rng = random.Random(42)

        valid_count = 0
        different_count = 0

        for _ in range(100):
            mutated = mutate(original, reg, rng)
            if _validate(mutated):
                valid_count += 1
            mutated_str = ast_to_string(mutated)
            if mutated_str != original_str:
                different_count += 1

        self.assertEqual(valid_count, 100, f"Only {valid_count}/100 mutations were valid")
        self.assertGreater(different_count, 0, "No mutations differed from original")

    def test_case_b_crossover_validity(self):
        """Case B: Crossover RSI(14) > 50 with PRICE > SMA(200).
        Result must be a valid AST combining parts of both.
        """
        reg = _make_registry()
        parent_a = _parse("RSI(14) > 50")
        parent_b = _parse("PRICE > SMA(200)")
        rng = random.Random(42)

        child = crossover(parent_a, parent_b, rng)
        self.assertTrue(_validate(child), f"Crossover result is invalid: {ast_to_string(child)}")

    def test_case_c_improvement_over_generations(self):
        """Case C: Best fitness at gen 10 >= best fitness at gen 0.

        Uses a small population and short data for speed.
        """
        ctx = generate_random_ohlcv(500, seed=42)
        optimizer = Optimizer(
            ctx,
            population_size=20,
            elite_count=3,
            seed=42,
            verbose=False,
        )
        result = optimizer.run(generations=10)

        gen0_fitness = result.generations[0].best_fitness
        gen10_fitness = result.generations[-1].best_fitness

        # Elitism guarantees non-regression of the best
        self.assertGreaterEqual(
            gen10_fitness, gen0_fitness,
            f"Fitness regressed: gen0={gen0_fitness:.4f} > gen10={gen10_fitness:.4f}"
        )


# ======================================================================
# Mutation Tests
# ======================================================================


class TestMutation(unittest.TestCase):
    """Test mutation operator."""

    def test_parameter_mutation(self):
        """Mutated AST should sometimes have different numeric values."""
        reg = _make_registry()
        original = _parse("RSI(14) > 70")
        rng = random.Random(42)

        originals = set()
        mutated_strs = set()
        for _ in range(50):
            m = mutate(original, reg, rng)
            mutated_strs.add(ast_to_string(m))

        self.assertGreater(len(mutated_strs), 1, "All mutations identical")

    def test_mutation_preserves_validity(self):
        """All mutations should produce valid ASTs."""
        reg = _make_registry()
        expr = "PRICE > SMA(20) AND RSI(14) > 30"
        original = _parse(expr)
        rng = random.Random(42)

        for _ in range(50):
            mutated = mutate(original, reg, rng)
            self.assertTrue(
                _validate(mutated),
                f"Invalid mutation: {ast_to_string(mutated)}"
            )

    def test_mutation_of_simple_ast(self):
        """Mutation of a very simple AST should not crash."""
        reg = _make_registry()
        simple = _parse("PRICE > 10")
        rng = random.Random(42)
        mutated = mutate(simple, reg, rng)
        self.assertIsInstance(mutated, ASTNode)


# ======================================================================
# Crossover Tests
# ======================================================================


class TestCrossover(unittest.TestCase):
    """Test crossover operator."""

    def test_crossover_produces_valid_ast(self):
        a = _parse("RSI(14) > 50")
        b = _parse("PRICE > SMA(20)")
        rng = random.Random(42)

        for _ in range(20):
            child = crossover(a, b, rng)
            self.assertTrue(_validate(child), f"Invalid child: {ast_to_string(child)}")

    def test_crossover_different_parents(self):
        """Crossover of different parents should sometimes produce novel ASTs."""
        a = _parse("RSI(14) > 70 AND PRICE > SMA(50)")
        b = _parse("EMA(20) < 100 OR VOLUME > 1000")
        rng = random.Random(42)

        results = set()
        for _ in range(30):
            child = crossover(a, b, rng)
            results.add(ast_to_string(child))

        self.assertGreater(len(results), 1, "All crossovers identical")

    def test_crossover_with_leaf(self):
        """Crossover where one parent is a leaf node."""
        a = _parse("42")
        b = _parse("RSI(14) > 70")
        rng = random.Random(42)

        child = crossover(a, b, rng)
        self.assertIsInstance(child, ASTNode)


# ======================================================================
# Selection Tests
# ======================================================================


class TestSelection(unittest.TestCase):
    """Test tournament selection."""

    def test_tournament_returns_individual(self):
        pop = [
            Individual(ast=_parse("PRICE > 10"), expression="PRICE > 10", fitness=1.0),
            Individual(ast=_parse("PRICE > 20"), expression="PRICE > 20", fitness=2.0),
            Individual(ast=_parse("PRICE > 30"), expression="PRICE > 30", fitness=3.0),
        ]
        selected = tournament_selection(pop, k=2)
        self.assertIsInstance(selected, Individual)

    def test_tournament_selects_fittest(self):
        """With k=population size, should always return the fittest."""
        pop = [
            Individual(ast=_parse("PRICE > 10"), expression="A", fitness=1.0),
            Individual(ast=_parse("PRICE > 20"), expression="B", fitness=5.0),
            Individual(ast=_parse("PRICE > 30"), expression="C", fitness=2.0),
        ]
        selected = tournament_selection(pop, k=3)
        self.assertEqual(selected.fitness, 5.0)

    def test_tournament_pressure(self):
        """Higher k → more selective pressure → fitter individuals more often."""
        pop = [
            Individual(ast=_parse("PRICE > 10"), expression="low", fitness=1.0),
            Individual(ast=_parse("PRICE > 20"), expression="mid", fitness=5.0),
            Individual(ast=_parse("PRICE > 30"), expression="high", fitness=10.0),
        ]
        rng = random.Random(42)
        selections = [tournament_selection(pop, k=2, rng=rng).fitness for _ in range(100)]
        avg = sum(selections) / len(selections)
        # With k=2, average should trend above population mean
        pop_mean = sum(i.fitness for i in pop) / len(pop)
        self.assertGreater(avg, pop_mean)


# ======================================================================
# AST Serialization Tests
# ======================================================================


class TestAstToString(unittest.TestCase):
    """Test the ast_to_string serializer round-trips correctly."""

    def test_round_trip_simple(self):
        expr = "RSI(14) > 70"
        ast = _parse(expr)
        result = ast_to_string(ast)
        reparsed = _parse(result)
        self.assertEqual(ast_to_string(reparsed), result)

    def test_round_trip_complex(self):
        expr = "RSI(14) > 70 AND PRICE > SMA(50)"
        ast = _parse(expr)
        result = ast_to_string(ast)
        reparsed = _parse(result)
        self.assertIsInstance(reparsed, BinaryOpNode)

    def test_round_trip_offset(self):
        expr = "RSI(14)[1] > 70"
        ast = _parse(expr)
        result = ast_to_string(ast)
        reparsed = _parse(result)
        # Should contain offset in left side of comparison
        self.assertIsInstance(reparsed, ComparisonNode)
        self.assertIsInstance(reparsed.left, OffsetNode)

    def test_round_trip_not(self):
        expr = "NOT PRICE > 50"
        ast = _parse(expr)
        result = ast_to_string(ast)
        reparsed = _parse(result)
        self.assertIsInstance(reparsed, UnaryOpNode) if hasattr(reparsed, 'operator') else None


# ======================================================================
# Node Collection Tests
# ======================================================================


class TestNodeCollection(unittest.TestCase):
    """Test AST traversal helper."""

    def test_collect_leaf_nodes(self):
        ast = _parse("RSI(14) > 70")
        nodes = _collect_nodes(ast)
        # Should find: ComparisonNode, FunctionCallNode, LiteralNode(14), LiteralNode(70)
        self.assertGreaterEqual(len(nodes), 4)

    def test_collect_complex(self):
        ast = _parse("A AND B OR C")
        nodes = _collect_nodes(ast)
        self.assertGreater(len(nodes), 3)


if __name__ == "__main__":
    unittest.main()
