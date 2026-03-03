"""Unit tests for the LECAT Parser."""

import unittest

from lecat.ast_nodes import (
    BinaryOpNode,
    ComparisonNode,
    FunctionCallNode,
    IdentifierNode,
    LiteralNode,
    OffsetNode,
    UnaryOpNode,
)
from lecat.errors import ParserError
from lecat.lexer import Lexer
from lecat.parser import Parser


def parse(source: str):
    """Helper: lex and parse a source string into an AST."""
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


# ======================================================================
# Acceptance Criteria from PM Brief (Section 4)
# ======================================================================


class TestAcceptanceCriteria(unittest.TestCase):
    """Tests matching the PM's exact acceptance criteria."""

    def test_case_a_basic_logic(self):
        """Case A: RSI(14) > 80 AND PRICE > SMA(50)
        → BinaryOp(AND, Comparison(>, Call(RSI), Lit(80)),
                         Comparison(>, Id(PRICE), Call(SMA)))
        """
        ast = parse("RSI(14) > 80 AND PRICE > SMA(50)")

        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "AND")

        # Left: RSI(14) > 80
        left = ast.left
        self.assertIsInstance(left, ComparisonNode)
        self.assertEqual(left.operator, ">")
        self.assertIsInstance(left.left, FunctionCallNode)
        self.assertEqual(left.left.name, "RSI")
        self.assertEqual(len(left.left.arguments), 1)
        self.assertIsInstance(left.left.arguments[0], LiteralNode)
        self.assertEqual(left.left.arguments[0].value, 14)
        self.assertIsInstance(left.right, LiteralNode)
        self.assertEqual(left.right.value, 80)

        # Right: PRICE > SMA(50)
        right = ast.right
        self.assertIsInstance(right, ComparisonNode)
        self.assertEqual(right.operator, ">")
        self.assertIsInstance(right.left, IdentifierNode)
        self.assertEqual(right.left.name, "PRICE")
        self.assertIsInstance(right.right, FunctionCallNode)
        self.assertEqual(right.right.name, "SMA")

    def test_case_b_context_shifting(self):
        """Case B: (close > open)[1]
        → OffsetNode(shift=1, child=Comparison(>, Id(close), Id(open)))
        """
        ast = parse("(close > open)[1]")

        self.assertIsInstance(ast, OffsetNode)
        self.assertEqual(ast.shift_amount, 1)
        self.assertIsInstance(ast.child, ComparisonNode)
        self.assertEqual(ast.child.operator, ">")
        self.assertIsInstance(ast.child.left, IdentifierNode)
        self.assertEqual(ast.child.left.name, "close")
        self.assertIsInstance(ast.child.right, IdentifierNode)
        self.assertEqual(ast.child.right.name, "open")

    def test_case_c_precedence(self):
        """Case C: A OR B AND C
        → BinaryOp(OR, Id(A), BinaryOp(AND, Id(B), Id(C)))
        AND binds tighter than OR.
        """
        ast = parse("A OR B AND C")

        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "OR")
        self.assertIsInstance(ast.left, IdentifierNode)
        self.assertEqual(ast.left.name, "A")

        right = ast.right
        self.assertIsInstance(right, BinaryOpNode)
        self.assertEqual(right.operator, "AND")
        self.assertIsInstance(right.left, IdentifierNode)
        self.assertEqual(right.left.name, "B")
        self.assertIsInstance(right.right, IdentifierNode)
        self.assertEqual(right.right.name, "C")

    def test_case_d_negative_offset_error(self):
        """Case D: RSI(14)[-1]
        → Raises ParserError (Negative offset forbidden)
        """
        with self.assertRaises(ParserError) as ctx:
            parse("RSI(14)[-1]")
        self.assertIn("Negative offset", str(ctx.exception))


# ======================================================================
# Additional Parser Tests
# ======================================================================


class TestLiterals(unittest.TestCase):
    """Test parsing of literal values."""

    def test_integer(self):
        ast = parse("42")
        self.assertIsInstance(ast, LiteralNode)
        self.assertEqual(ast.value, 42)
        self.assertEqual(ast.value_type, "integer")

    def test_float(self):
        ast = parse("3.14")
        self.assertIsInstance(ast, LiteralNode)
        self.assertAlmostEqual(ast.value, 3.14)
        self.assertEqual(ast.value_type, "float")

    def test_boolean_true(self):
        ast = parse("TRUE")
        self.assertIsInstance(ast, LiteralNode)
        self.assertIs(ast.value, True)
        self.assertEqual(ast.value_type, "boolean")

    def test_boolean_false(self):
        ast = parse("FALSE")
        self.assertIsInstance(ast, LiteralNode)
        self.assertIs(ast.value, False)
        self.assertEqual(ast.value_type, "boolean")


class TestIdentifiers(unittest.TestCase):
    """Test parsing of identifiers."""

    def test_simple_identifier(self):
        ast = parse("PRICE")
        self.assertIsInstance(ast, IdentifierNode)
        self.assertEqual(ast.name, "PRICE")

    def test_identifier_preserves_case(self):
        ast = parse("myIndicator")
        self.assertIsInstance(ast, IdentifierNode)
        self.assertEqual(ast.name, "myIndicator")


class TestFunctionCalls(unittest.TestCase):
    """Test parsing of function calls."""

    def test_single_arg(self):
        ast = parse("RSI(14)")
        self.assertIsInstance(ast, FunctionCallNode)
        self.assertEqual(ast.name, "RSI")
        self.assertEqual(len(ast.arguments), 1)
        self.assertIsInstance(ast.arguments[0], LiteralNode)
        self.assertEqual(ast.arguments[0].value, 14)

    def test_multiple_args(self):
        ast = parse("MACD(12, 26, 9)")
        self.assertIsInstance(ast, FunctionCallNode)
        self.assertEqual(ast.name, "MACD")
        self.assertEqual(len(ast.arguments), 3)
        self.assertEqual(ast.arguments[0].value, 12)
        self.assertEqual(ast.arguments[1].value, 26)
        self.assertEqual(ast.arguments[2].value, 9)

    def test_no_args(self):
        ast = parse("PRICE()")
        self.assertIsInstance(ast, FunctionCallNode)
        self.assertEqual(ast.name, "PRICE")
        self.assertEqual(len(ast.arguments), 0)

    def test_nested_function_call(self):
        """SMA(RSI(14)) — function as argument."""
        ast = parse("SMA(RSI(14))")
        self.assertIsInstance(ast, FunctionCallNode)
        self.assertEqual(ast.name, "SMA")
        self.assertEqual(len(ast.arguments), 1)
        inner = ast.arguments[0]
        self.assertIsInstance(inner, FunctionCallNode)
        self.assertEqual(inner.name, "RSI")


class TestUnaryOperators(unittest.TestCase):
    """Test NOT and unary minus."""

    def test_not(self):
        ast = parse("NOT TRUE")
        self.assertIsInstance(ast, UnaryOpNode)
        self.assertEqual(ast.operator, "NOT")
        self.assertIsInstance(ast.operand, LiteralNode)

    def test_double_not(self):
        ast = parse("NOT NOT A")
        self.assertIsInstance(ast, UnaryOpNode)
        self.assertIsInstance(ast.operand, UnaryOpNode)
        self.assertIsInstance(ast.operand.operand, IdentifierNode)

    def test_unary_minus(self):
        ast = parse("-42")
        self.assertIsInstance(ast, UnaryOpNode)
        self.assertEqual(ast.operator, "-")
        self.assertIsInstance(ast.operand, LiteralNode)
        self.assertEqual(ast.operand.value, 42)


class TestComparisons(unittest.TestCase):
    """Test comparison operators."""

    def test_all_operators(self):
        for op in [">", "<", ">=", "<=", "==", "!="]:
            ast = parse(f"A {op} B")
            self.assertIsInstance(ast, ComparisonNode)
            self.assertEqual(ast.operator, op)

    def test_chained_comparison_error(self):
        """A > B > C should raise ParserError (non-associative)."""
        with self.assertRaises(ParserError) as ctx:
            parse("A > B > C")
        self.assertIn("non-associative", str(ctx.exception).lower())


class TestBinaryOperators(unittest.TestCase):
    """Test AND and OR with correct precedence."""

    def test_and(self):
        ast = parse("A AND B")
        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "AND")

    def test_or(self):
        ast = parse("A OR B")
        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "OR")

    def test_and_binds_tighter_than_or(self):
        """A OR B AND C → OR(A, AND(B, C))"""
        ast = parse("A OR B AND C")
        self.assertEqual(ast.operator, "OR")
        self.assertEqual(ast.right.operator, "AND")

    def test_parentheses_override_precedence(self):
        """(A OR B) AND C → AND(OR(A, B), C)"""
        ast = parse("(A OR B) AND C")
        self.assertEqual(ast.operator, "AND")
        self.assertEqual(ast.left.operator, "OR")

    def test_chained_and(self):
        """A AND B AND C → AND(AND(A, B), C) (left-associative)"""
        ast = parse("A AND B AND C")
        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "AND")
        self.assertIsInstance(ast.left, BinaryOpNode)
        self.assertEqual(ast.left.operator, "AND")


class TestContextShifting(unittest.TestCase):
    """Test CR-001 offset syntax."""

    def test_function_offset(self):
        """RSI(14)[1] → OffsetNode wrapping FunctionCallNode"""
        ast = parse("RSI(14)[1]")
        self.assertIsInstance(ast, OffsetNode)
        self.assertEqual(ast.shift_amount, 1)
        self.assertIsInstance(ast.child, FunctionCallNode)
        self.assertEqual(ast.child.name, "RSI")

    def test_identifier_offset(self):
        """PRICE[5] → OffsetNode wrapping IdentifierNode"""
        ast = parse("PRICE[5]")
        self.assertIsInstance(ast, OffsetNode)
        self.assertEqual(ast.shift_amount, 5)
        self.assertIsInstance(ast.child, IdentifierNode)
        self.assertEqual(ast.child.name, "PRICE")

    def test_grouped_expression_offset(self):
        """(close > open)[1]"""
        ast = parse("(close > open)[1]")
        self.assertIsInstance(ast, OffsetNode)
        self.assertEqual(ast.shift_amount, 1)
        self.assertIsInstance(ast.child, ComparisonNode)

    def test_zero_offset(self):
        """RSI(14)[0] — no-op, but valid"""
        ast = parse("RSI(14)[0]")
        self.assertIsInstance(ast, OffsetNode)
        self.assertEqual(ast.shift_amount, 0)

    def test_negative_offset_error(self):
        with self.assertRaises(ParserError):
            parse("RSI(14)[-1]")

    def test_float_offset_error(self):
        with self.assertRaises(ParserError):
            parse("RSI(14)[1.5]")

    def test_offset_in_larger_expression(self):
        """RSI(14)[1] > 70 AND PRICE > SMA(50)"""
        ast = parse("RSI(14)[1] > 70 AND PRICE > SMA(50)")
        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "AND")
        left = ast.left
        self.assertIsInstance(left, ComparisonNode)
        self.assertIsInstance(left.left, OffsetNode)
        self.assertEqual(left.left.shift_amount, 1)


class TestParserErrors(unittest.TestCase):
    """Test error handling."""

    def test_empty_expression(self):
        with self.assertRaises(ParserError):
            parse("")

    def test_unmatched_lparen(self):
        with self.assertRaises(ParserError):
            parse("RSI(14")

    def test_unmatched_rparen(self):
        with self.assertRaises(ParserError):
            parse("RSI 14)")

    def test_trailing_tokens(self):
        with self.assertRaises(ParserError):
            parse("RSI(14) > 80 extra")

    def test_unexpected_token(self):
        with self.assertRaises(ParserError):
            parse("> > 80")


class TestComplexExpressions(unittest.TestCase):
    """Test realistic multi-feature expressions."""

    def test_full_strategy(self):
        """NOT (VOLUME < SMA_VOL(20)) OR MACD(12, 26, 9) > 0"""
        ast = parse("NOT (VOLUME < SMA_VOL(20)) OR MACD(12, 26, 9) > 0")
        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "OR")
        # Left: NOT (...)
        self.assertIsInstance(ast.left, UnaryOpNode)
        self.assertEqual(ast.left.operator, "NOT")
        # Right: MACD(...) > 0
        self.assertIsInstance(ast.right, ComparisonNode)

    def test_ema_crossover_with_offset(self):
        """EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]"""
        ast = parse("EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]")
        self.assertIsInstance(ast, BinaryOpNode)
        self.assertEqual(ast.operator, "AND")
        # Right side should have offsets
        right = ast.right
        self.assertIsInstance(right, ComparisonNode)
        self.assertIsInstance(right.left, OffsetNode)
        self.assertIsInstance(right.right, OffsetNode)

    def test_immutability(self):
        """AST nodes must be immutable (frozen=True)."""
        ast = parse("RSI(14)")
        with self.assertRaises(AttributeError):
            ast.name = "SMA"  # type: ignore


if __name__ == "__main__":
    unittest.main()
