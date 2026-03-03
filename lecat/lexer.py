"""Lexer (Tokenizer) for the LECAT DSL.

Converts a raw source string into an ordered list of Token objects.
Implements the token specification from docs/01_Grammar_Specification.md.
"""

from __future__ import annotations

from lecat.errors import LexerError
from lecat.tokens import (
    COMPARISON_OPS,
    KEYWORDS,
    SINGLE_CHAR_TOKENS,
    Token,
    TokenType,
)

# Maximum allowed expression length (Grammar rule G-005)
MAX_EXPRESSION_LENGTH = 4096


class Lexer:
    """Converts a source string into a stream of tokens.

    Usage:
        tokens = Lexer("RSI(14) > 80").tokenize()
    """

    def __init__(self, source: str) -> None:
        if len(source) > MAX_EXPRESSION_LENGTH:
            raise LexerError(
                f"Expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters",
                position=0,
            )
        self._source = source
        self._pos = 0
        self._tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        """Tokenize the entire source string.

        Returns:
            Ordered list of Token objects, ending with an EOF token.

        Raises:
            LexerError: On unrecognized characters or invalid tokens.
        """
        while self._pos < len(self._source):
            self._skip_whitespace()
            if self._pos >= len(self._source):
                break

            char = self._source[self._pos]

            # --- Comparison operators (check multi-char first) ---
            if self._try_comparison_op():
                continue

            # --- Single-character tokens ---
            if char in SINGLE_CHAR_TOKENS:
                self._tokens.append(
                    Token(SINGLE_CHAR_TOKENS[char], char, self._pos)
                )
                self._pos += 1
                continue

            # --- Numbers (integer or float) ---
            if char.isdigit():
                self._read_number()
                continue

            # --- Identifiers and keywords ---
            if char.isalpha() or char == "_":
                self._read_identifier()
                continue

            # --- Unrecognized character ---
            raise LexerError(f"Unexpected character '{char}'", self._pos)

        # Append EOF
        self._tokens.append(Token(TokenType.EOF, "", self._pos))
        return self._tokens

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _skip_whitespace(self) -> None:
        """Advance past spaces and tabs."""
        while self._pos < len(self._source) and self._source[self._pos] in (" ", "\t"):
            self._pos += 1

    def _try_comparison_op(self) -> bool:
        """Try to match a comparison operator at the current position.

        Returns True if a match was found and consumed.
        """
        for op_str, op_type in COMPARISON_OPS:
            if self._source[self._pos:self._pos + len(op_str)] == op_str:
                self._tokens.append(Token(op_type, op_str, self._pos))
                self._pos += len(op_str)
                return True
        return False

    def _read_number(self) -> None:
        """Read an integer or float literal starting at current position."""
        start = self._pos
        has_dot = False

        while self._pos < len(self._source):
            char = self._source[self._pos]
            if char.isdigit():
                self._pos += 1
            elif char == "." and not has_dot:
                # Check that there's a digit after the dot
                if self._pos + 1 < len(self._source) and self._source[self._pos + 1].isdigit():
                    has_dot = True
                    self._pos += 1
                else:
                    raise LexerError(
                        "Invalid number literal (trailing dot)",
                        start,
                    )
            else:
                break

        text = self._source[start:self._pos]

        if has_dot:
            self._tokens.append(Token(TokenType.FLOAT, float(text), start))
        else:
            self._tokens.append(Token(TokenType.INTEGER, int(text), start))

    def _read_identifier(self) -> None:
        """Read an identifier or keyword starting at current position."""
        start = self._pos

        while self._pos < len(self._source) and (
            self._source[self._pos].isalnum() or self._source[self._pos] == "_"
        ):
            self._pos += 1

        text = self._source[start:self._pos]
        upper = text.upper()

        # Check if it's a keyword (case-insensitive)
        if upper in KEYWORDS:
            token_type = KEYWORDS[upper]
            # For BOOL tokens, store the actual boolean value
            if token_type == TokenType.BOOL:
                self._tokens.append(Token(token_type, upper == "TRUE", start))
            else:
                self._tokens.append(Token(token_type, upper, start))
        else:
            # Regular identifier — preserve original case
            self._tokens.append(Token(TokenType.IDENTIFIER, text, start))
