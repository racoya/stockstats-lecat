"""Custom exception classes for the LECAT compiler pipeline."""

from __future__ import annotations


class LECATError(Exception):
    """Base exception for all LECAT errors."""

    def __init__(self, message: str, position: int | None = None) -> None:
        self.position = position
        super().__init__(message)


class LexerError(LECATError):
    """Raised when the Lexer encounters an invalid character or token.

    Severity: S1 — Fatal (compile-time).
    """

    def __init__(self, message: str, position: int) -> None:
        self.position = position
        super().__init__(f"LexerError at position {position}: {message}", position)


class ParserError(LECATError):
    """Raised when the Parser encounters a syntax violation.

    Severity: S1 — Fatal (compile-time).
    """

    def __init__(self, message: str, position: int | None = None) -> None:
        prefix = f"ParserError at position {position}" if position is not None else "ParserError"
        super().__init__(f"{prefix}: {message}", position)
