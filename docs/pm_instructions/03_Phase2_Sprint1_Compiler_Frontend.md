
# Phase 2: Core Implementation — Sprint 1 (Compiler Frontend)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 2 — Implementation
**Goal:** Build the Lexer, AST definitions, and Recursive Descent Parser.

---

## 1. Objective
Translate the approved **EBNF Grammar** and **AST Schemas** into working Python code.
By the end of this sprint, we must be able to input a string like `RSI(14)[1] > 80` and receive a validated, immutable AST object structure.

**Constraints:**
* **Language:** Python 3.10+ (Use `dataclasses` and type hinting).
* **Dependencies:** Standard library only (no external parser generators like `ply` or `antlr` yet — we want a lightweight, custom recursive descent parser for maximum control).
* **Testing:** proper unit tests must be included.

---

## 2. Required File Structure
Please initialize the project with the following structure:

```text
lecat/
├── __init__.py
├── errors.py          # Custom Exception classes (LexerError, ParserError)
├── tokens.py          # Token definitions and Enum
├── ast_nodes.py       # Dataclasses matching the JSON schema
├── lexer.py           # The Tokenizer implementation
└── parser.py          # The Recursive Descent Parser implementation
tests/
├── test_lexer.py
└── test_parser.py

```

---

## 3. Implementation Tasks

### Task 1: AST Definitions (`ast_nodes.py`)

Implement the AST nodes defined in `02_System_Architecture.md` as Python `dataclasses`.

* **Requirement:** All fields must be immutable (`frozen=True`).
* **Nodes:** `BinaryOpNode`, `UnaryOpNode`, `ComparisonNode`, `FunctionCallNode`, `LiteralNode`, `IdentifierNode`, and the new `OffsetNode`.

### Task 2: The Lexer (`lexer.py`)

Implement the tokenizer based on `01_Grammar_Specification.md`.

* **Token Types:** `AND`, `OR`, `NOT`, `IDENTIFIER`, `NUMBER` (Float/Int), `LPAREN`, `RPAREN`, `LBRACKET`, `RBRACKET` (for offsets), `COMMA`, `OPERATOR` (>, <, ==, etc).
* **Behavior:**
* Skip whitespace.
* Case-insensitive for keywords (normalize `and` -> `AND`), but identifiers should preserve case (convention is UPPER).
* Raise `LexerError` with position info for invalid characters.



### Task 3: The Parser (`parser.py`)

Implement a **Recursive Descent Parser** that consumes tokens and builds the AST.

* **Precedence:** You must strictly follow the Precedence Table in `01_Grammar_Specification.md`.
* *Hint:* Structure your methods as `expression()`, `or_expr()`, `and_expr()`, `comparison()`, `primary()`.


* **Context Shifting:** Ensure `primary()` handles the optional `[offset]` suffix and wraps the node in an `OffsetNode`.
* **Validation:**
* Ensure `offset` contains only positive integers.
* Check for unbalanced parentheses.



---

## 4. Acceptance Criteria (Test Cases)

Your code must pass the following scenarios (please include them in `tests/`):

**Case A: Basic Logic**
Input: `RSI(14) > 80 AND PRICE > SMA(50)`
Output: `BinaryOp(AND, Comparison(>, Call(RSI), Lit(80)), Comparison(>, Id(PRICE), Call(SMA)))`

**Case B: Context Shifting (The new feature)**
Input: `(close > open)[1]`
Output: `OffsetNode(shift=1, child=Comparison(>, Id(close), Id(open)))`

**Case C: Precedence Check**
Input: `A OR B AND C`
Output: `BinaryOp(OR, Id(A), BinaryOp(AND, Id(B), Id(C)))` (AND binds tighter)

**Case D: Error Handling**
Input: `RSI(14)[-1]`
Output: Raises `ParserError` (Negative offset forbidden)

---

**Action:** Generate the Python code for `tokens.py`, `ast_nodes.py`, `lexer.py`, and `parser.py`.

