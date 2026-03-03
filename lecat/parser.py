"""Recursive Descent Parser for the LECAT DSL.

Consumes a token stream produced by the Lexer and builds an immutable AST.
Implements the EBNF grammar from docs/01_Grammar_Specification.md (v1.1).

Grammar (precedence low → high):
    expression  = or_expr
    or_expr     = and_expr { "OR" and_expr }
    and_expr    = not_expr { "AND" not_expr }
    not_expr    = "NOT" not_expr | comparison
    comparison  = arithmetic [ comp_op arithmetic ]
    arithmetic  = unary
    unary       = "-" unary | primary
    primary     = ( literal | function_call | identifier | "(" expr ")" ) [ offset ]
    offset      = "[" int_literal "]"
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
from lecat.errors import ParserError
from lecat.tokens import Token, TokenType

# Maximum nesting depth (Grammar rule G-006)
MAX_NESTING_DEPTH = 256

# Comparison token types for matching
_COMP_OPS = frozenset({
    TokenType.GT, TokenType.LT,
    TokenType.GTE, TokenType.LTE,
    TokenType.EQ, TokenType.NEQ,
})


class Parser:
    """Recursive Descent Parser that builds an immutable AST from tokens.

    Usage:
        tokens = Lexer("RSI(14) > 80 AND PRICE > SMA(50)").tokenize()
        ast = Parser(tokens).parse()
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._depth = 0

    def parse(self) -> ASTNode:
        """Parse the full token stream into an AST.

        Returns:
            The root ASTNode of the parsed expression.

        Raises:
            ParserError: On syntax violations.
        """
        if self._current().type == TokenType.EOF:
            raise ParserError("Empty expression", position=0)

        node = self._expression()

        # Ensure all tokens were consumed
        if self._current().type != TokenType.EOF:
            tok = self._current()
            raise ParserError(
                f"Unexpected token '{tok.value}' after expression end",
                position=tok.position,
            )

        return node

    # ------------------------------------------------------------------
    # Grammar rules (ordered by ascending precedence)
    # ------------------------------------------------------------------

    def _expression(self) -> ASTNode:
        """expression = or_expr"""
        return self._or_expr()

    def _or_expr(self) -> ASTNode:
        """or_expr = and_expr { "OR" and_expr }"""
        left = self._and_expr()

        while self._current().type == TokenType.OR:
            self._advance()  # consume OR
            right = self._and_expr()
            left = BinaryOpNode(operator="OR", left=left, right=right)

        return left

    def _and_expr(self) -> ASTNode:
        """and_expr = not_expr { "AND" not_expr }"""
        left = self._not_expr()

        while self._current().type == TokenType.AND:
            self._advance()  # consume AND
            right = self._not_expr()
            left = BinaryOpNode(operator="AND", left=left, right=right)

        return left

    def _not_expr(self) -> ASTNode:
        """not_expr = "NOT" not_expr | comparison"""
        if self._current().type == TokenType.NOT:
            self._advance()  # consume NOT
            operand = self._not_expr()
            return UnaryOpNode(operator="NOT", operand=operand)

        return self._comparison()

    def _comparison(self) -> ASTNode:
        """comparison = arithmetic [ comp_op arithmetic ]

        Non-associative: A > B > C is a syntax error.
        """
        left = self._arithmetic()

        if self._current().type in _COMP_OPS:
            op_token = self._current()
            self._advance()  # consume operator
            right = self._arithmetic()
            node = ComparisonNode(
                operator=op_token.value,
                left=left,
                right=right,
            )

            # Non-associative check: reject chained comparisons
            if self._current().type in _COMP_OPS:
                raise ParserError(
                    "Comparison operators are non-associative. "
                    "Use 'A > B AND B > C' instead of 'A > B > C'",
                    position=self._current().position,
                )

            return node

        return left

    def _arithmetic(self) -> ASTNode:
        """arithmetic = unary (future extensibility for +, *, etc.)"""
        return self._unary()

    def _unary(self) -> ASTNode:
        """unary = "-" unary | primary"""
        if self._current().type == TokenType.MINUS:
            self._advance()  # consume -
            operand = self._unary()
            return UnaryOpNode(operator="-", operand=operand)

        return self._primary()

    def _primary(self) -> ASTNode:
        """primary = ( literal | function_call | identifier | "(" expr ")" ) [ offset ]"""
        self._check_depth()
        self._depth += 1

        try:
            token = self._current()

            # --- Parenthesized expression ---
            if token.type == TokenType.LPAREN:
                node = self._parenthesized_expr()

            # --- Boolean literal ---
            elif token.type == TokenType.BOOL:
                self._advance()
                node = LiteralNode(value=token.value, value_type="boolean")

            # --- Numeric literals ---
            elif token.type == TokenType.INTEGER:
                self._advance()
                node = LiteralNode(value=token.value, value_type="integer")

            elif token.type == TokenType.FLOAT:
                self._advance()
                node = LiteralNode(value=token.value, value_type="float")

            # --- Identifier or function call ---
            elif token.type == TokenType.IDENTIFIER:
                node = self._identifier_or_call()

            else:
                raise ParserError(
                    f"Expected expression, found '{token.value}' ({token.type.name})",
                    position=token.position,
                )

            # --- Optional offset suffix [n] (CR-001) ---
            if self._current().type == TokenType.LBRACKET:
                node = self._offset(node)

            return node
        finally:
            self._depth -= 1

    # ------------------------------------------------------------------
    # Sub-rules
    # ------------------------------------------------------------------

    def _parenthesized_expr(self) -> ASTNode:
        """Parse "(" expression ")" """
        self._advance()  # consume (
        node = self._expression()

        if self._current().type != TokenType.RPAREN:
            raise ParserError(
                f"Expected ')' but found '{self._current().value}'",
                position=self._current().position,
            )
        self._advance()  # consume )
        return node

    def _identifier_or_call(self) -> ASTNode:
        """Parse identifier or function_call = identifier "(" [arg_list] ")" """
        name_token = self._current()
        self._advance()  # consume identifier

        # Check if this is a function call
        if self._current().type == TokenType.LPAREN:
            return self._function_call(name_token)

        # Plain identifier
        return IdentifierNode(name=name_token.value)

    def _function_call(self, name_token: Token) -> FunctionCallNode:
        """Parse function call arguments: "(" [arg_list] ")" """
        self._advance()  # consume (

        args: list[ASTNode] = []

        if self._current().type != TokenType.RPAREN:
            # Read first argument
            args.append(self._expression())

            # Read remaining arguments
            while self._current().type == TokenType.COMMA:
                self._advance()  # consume ,
                args.append(self._expression())

        if self._current().type != TokenType.RPAREN:
            raise ParserError(
                f"Expected ')' or ',' in function call, found '{self._current().value}'",
                position=self._current().position,
            )
        self._advance()  # consume )

        return FunctionCallNode(name=name_token.value, arguments=tuple(args))

    def _offset(self, child: ASTNode) -> OffsetNode:
        """Parse offset suffix: "[" int_literal "]" (CR-001)"""
        bracket_pos = self._current().position
        self._advance()  # consume [

        tok = self._current()

        # Must be a non-negative integer
        if tok.type == TokenType.MINUS:
            raise ParserError(
                "Negative offset forbidden. Offsets must be non-negative integers "
                "(look-ahead bias prevention)",
                position=tok.position,
            )

        if tok.type != TokenType.INTEGER:
            raise ParserError(
                f"Offset must be a non-negative integer, found '{tok.value}' ({tok.type.name})",
                position=tok.position,
            )

        shift = tok.value
        assert isinstance(shift, int)
        self._advance()  # consume integer

        if self._current().type != TokenType.RBRACKET:
            raise ParserError(
                f"Expected ']' after offset value, found '{self._current().value}'",
                position=self._current().position,
            )
        self._advance()  # consume ]

        return OffsetNode(shift_amount=shift, child=child)

    # ------------------------------------------------------------------
    # Token navigation
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        """Return the current token without advancing."""
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        """Consume the current token and return it."""
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _check_depth(self) -> None:
        """Enforce maximum nesting depth (Grammar rule G-006)."""
        if self._depth >= MAX_NESTING_DEPTH:
            raise ParserError(
                f"Maximum nesting depth of {MAX_NESTING_DEPTH} exceeded",
                position=self._current().position,
            )
