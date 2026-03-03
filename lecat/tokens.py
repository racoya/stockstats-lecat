"""Token type definitions for the LECAT lexer."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """All token types recognized by the LECAT lexer."""

    # Literals
    INTEGER = auto()
    FLOAT = auto()
    BOOL = auto()

    # Identifiers & Keywords
    IDENTIFIER = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    # Comparison operators
    GT = auto()       # >
    LT = auto()       # <
    GTE = auto()      # >=
    LTE = auto()      # <=
    EQ = auto()       # ==
    NEQ = auto()      # !=

    # Punctuation
    LPAREN = auto()   # (
    RPAREN = auto()   # )
    LBRACKET = auto() # [
    RBRACKET = auto() # ]
    COMMA = auto()    # ,
    MINUS = auto()    # -

    # Control
    EOF = auto()


# Keywords are case-insensitive and normalized to uppercase
KEYWORDS: dict[str, TokenType] = {
    "AND": TokenType.AND,
    "OR": TokenType.OR,
    "NOT": TokenType.NOT,
    "TRUE": TokenType.BOOL,
    "FALSE": TokenType.BOOL,
}

# Single-character tokens (excluding operators that can be multi-char)
SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    "-": TokenType.MINUS,
}

# Comparison operators (checked in order: longest match first)
COMPARISON_OPS: list[tuple[str, TokenType]] = [
    (">=", TokenType.GTE),
    ("<=", TokenType.LTE),
    ("==", TokenType.EQ),
    ("!=", TokenType.NEQ),
    (">", TokenType.GT),
    ("<", TokenType.LT),
]


@dataclass(frozen=True)
class Token:
    """A single token produced by the Lexer.

    Attributes:
        type: The classification of this token.
        value: The parsed value (str for identifiers, int/float for numbers,
               bool for TRUE/FALSE, str for operators).
        position: Character offset in the source string (0-indexed).
    """

    type: TokenType
    value: str | int | float | bool
    position: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, pos={self.position})"
