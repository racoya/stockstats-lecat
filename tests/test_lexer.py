"""Unit tests for the LECAT Lexer."""

import unittest

from lecat.errors import LexerError
from lecat.lexer import Lexer
from lecat.tokens import TokenType


class TestLexerBasics(unittest.TestCase):
    """Test basic tokenization of individual token types."""

    def test_integer_literal(self):
        tokens = Lexer("42").tokenize()
        self.assertEqual(tokens[0].type, TokenType.INTEGER)
        self.assertEqual(tokens[0].value, 42)

    def test_float_literal(self):
        tokens = Lexer("3.14").tokenize()
        self.assertEqual(tokens[0].type, TokenType.FLOAT)
        self.assertAlmostEqual(tokens[0].value, 3.14)

    def test_boolean_true(self):
        tokens = Lexer("TRUE").tokenize()
        self.assertEqual(tokens[0].type, TokenType.BOOL)
        self.assertIs(tokens[0].value, True)

    def test_boolean_false(self):
        tokens = Lexer("FALSE").tokenize()
        self.assertEqual(tokens[0].type, TokenType.BOOL)
        self.assertIs(tokens[0].value, False)

    def test_identifier(self):
        tokens = Lexer("RSI").tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "RSI")

    def test_identifier_preserves_case(self):
        tokens = Lexer("myFunc_1").tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "myFunc_1")


class TestLexerKeywords(unittest.TestCase):
    """Test case-insensitive keyword recognition."""

    def test_and_keyword(self):
        tokens = Lexer("AND").tokenize()
        self.assertEqual(tokens[0].type, TokenType.AND)

    def test_or_keyword(self):
        tokens = Lexer("OR").tokenize()
        self.assertEqual(tokens[0].type, TokenType.OR)

    def test_not_keyword(self):
        tokens = Lexer("NOT").tokenize()
        self.assertEqual(tokens[0].type, TokenType.NOT)

    def test_case_insensitive_and(self):
        tokens = Lexer("and").tokenize()
        self.assertEqual(tokens[0].type, TokenType.AND)

    def test_case_insensitive_or(self):
        tokens = Lexer("Or").tokenize()
        self.assertEqual(tokens[0].type, TokenType.OR)

    def test_case_insensitive_true(self):
        tokens = Lexer("true").tokenize()
        self.assertEqual(tokens[0].type, TokenType.BOOL)
        self.assertIs(tokens[0].value, True)


class TestLexerOperators(unittest.TestCase):
    """Test comparison operator tokenization."""

    def test_gt(self):
        tokens = Lexer(">").tokenize()
        self.assertEqual(tokens[0].type, TokenType.GT)

    def test_lt(self):
        tokens = Lexer("<").tokenize()
        self.assertEqual(tokens[0].type, TokenType.LT)

    def test_gte(self):
        tokens = Lexer(">=").tokenize()
        self.assertEqual(tokens[0].type, TokenType.GTE)

    def test_lte(self):
        tokens = Lexer("<=").tokenize()
        self.assertEqual(tokens[0].type, TokenType.LTE)

    def test_eq(self):
        tokens = Lexer("==").tokenize()
        self.assertEqual(tokens[0].type, TokenType.EQ)

    def test_neq(self):
        tokens = Lexer("!=").tokenize()
        self.assertEqual(tokens[0].type, TokenType.NEQ)


class TestLexerPunctuation(unittest.TestCase):
    """Test punctuation and bracket tokens."""

    def test_parentheses(self):
        tokens = Lexer("()").tokenize()
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.RPAREN)

    def test_brackets(self):
        tokens = Lexer("[]").tokenize()
        self.assertEqual(tokens[0].type, TokenType.LBRACKET)
        self.assertEqual(tokens[1].type, TokenType.RBRACKET)

    def test_comma(self):
        tokens = Lexer(",").tokenize()
        self.assertEqual(tokens[0].type, TokenType.COMMA)

    def test_minus(self):
        tokens = Lexer("-").tokenize()
        self.assertEqual(tokens[0].type, TokenType.MINUS)


class TestLexerFullExpressions(unittest.TestCase):
    """Test tokenization of complete expressions."""

    def test_rsi_comparison(self):
        """RSI(14) > 80"""
        tokens = Lexer("RSI(14) > 80").tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(types, [
            TokenType.IDENTIFIER,  # RSI
            TokenType.LPAREN,      # (
            TokenType.INTEGER,     # 14
            TokenType.RPAREN,      # )
            TokenType.GT,          # >
            TokenType.INTEGER,     # 80
            TokenType.EOF,
        ])

    def test_compound_and(self):
        """RSI(14) > 80 AND PRICE > SMA(50)"""
        tokens = Lexer("RSI(14) > 80 AND PRICE > SMA(50)").tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(types, [
            TokenType.IDENTIFIER, TokenType.LPAREN, TokenType.INTEGER, TokenType.RPAREN,
            TokenType.GT, TokenType.INTEGER,
            TokenType.AND,
            TokenType.IDENTIFIER, TokenType.GT,
            TokenType.IDENTIFIER, TokenType.LPAREN, TokenType.INTEGER, TokenType.RPAREN,
            TokenType.EOF,
        ])

    def test_context_shifting(self):
        """RSI(14)[1] > 70"""
        tokens = Lexer("RSI(14)[1] > 70").tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(types, [
            TokenType.IDENTIFIER, TokenType.LPAREN, TokenType.INTEGER, TokenType.RPAREN,
            TokenType.LBRACKET, TokenType.INTEGER, TokenType.RBRACKET,
            TokenType.GT, TokenType.INTEGER,
            TokenType.EOF,
        ])

    def test_multi_arg_function(self):
        """MACD(12, 26, 9)"""
        tokens = Lexer("MACD(12, 26, 9)").tokenize()
        types = [t.type for t in tokens]
        self.assertEqual(types, [
            TokenType.IDENTIFIER,
            TokenType.LPAREN,
            TokenType.INTEGER, TokenType.COMMA,
            TokenType.INTEGER, TokenType.COMMA,
            TokenType.INTEGER,
            TokenType.RPAREN,
            TokenType.EOF,
        ])

    def test_whitespace_is_ignored(self):
        """Tabs and spaces should be skipped."""
        tokens_a = Lexer("RSI(14)>80").tokenize()
        tokens_b = Lexer("  RSI ( 14 )  >  80  ").tokenize()
        types_a = [t.type for t in tokens_a]
        types_b = [t.type for t in tokens_b]
        self.assertEqual(types_a, types_b)


class TestLexerErrors(unittest.TestCase):
    """Test error cases."""

    def test_unrecognized_character(self):
        with self.assertRaises(LexerError):
            Lexer("RSI(14) @ 80").tokenize()

    def test_trailing_dot(self):
        with self.assertRaises(LexerError):
            Lexer("3.").tokenize()

    def test_max_length_exceeded(self):
        with self.assertRaises(LexerError):
            Lexer("A" * 4097).tokenize()

    def test_eof_always_appended(self):
        tokens = Lexer("").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)


if __name__ == "__main__":
    unittest.main()
