# A. Grammar Specification — The "Language Law"

**Standard:** EBNF (Extended Backus-Naur Form) — ISO/IEC 14977
**Parent Document:** [Overview](./00_Overview.md)

---

## 1. Design Rationale

The LECAT grammar is designed to express boolean trading conditions in a natural, readable syntax. The grammar enforces a strict **operator precedence hierarchy** to eliminate ambiguity without requiring excessive parentheses.

**Target Expression Examples:**
```
RSI(14) > 80 AND PRICE > SMA(50)
NOT (VOLUME < SMA_VOL(20)) OR MACD(12, 26, 9) > 0
EMA(10) >= EMA(50) AND RSI(14) <= 30
RSI(14)[1] > 70 AND PRICE > SMA(50)
(close > open)[1] AND VOLUME > SMA_VOL(20)
```

---

## 2. EBNF Grammar Definition

```ebnf
(* ============================================================ *)
(* LECAT DSL — Extended Backus-Naur Form Grammar                *)
(* Version: 1.1 — CR-001: Context Shifting                      *)
(* ============================================================ *)

(* --- Top-Level Rule --- *)
expression      = or_expr ;

(* --- Boolean Logic (lowest precedence) --- *)
or_expr         = and_expr , { "OR" , and_expr } ;
and_expr        = not_expr , { "AND" , not_expr } ;
not_expr        = "NOT" , not_expr
                | comparison ;

(* --- Comparison Operators --- *)
comparison      = arithmetic , [ comp_op , arithmetic ] ;
comp_op         = ">" | "<" | ">=" | "<=" | "==" | "!=" ;

(* --- Arithmetic (future extensibility) --- *)
arithmetic      = unary ;
unary           = "-" , unary
                | primary ;

(* --- Primary Expressions (with optional offset) --- *)
primary         = ( literal
                  | function_call
                  | identifier
                  | "(" , expression , ")" ) , [ offset ] ;

(* --- Context Shifting (CR-001) --- *)
offset          = "[" , int_literal , "]" ;

(* --- Function Calls --- *)
function_call   = identifier , "(" , [ arg_list ] , ")" ;
arg_list        = expression , { "," , expression } ;

(* --- Terminals --- *)
identifier      = letter , { letter | digit | "_" } ;
literal         = float_literal | int_literal | bool_literal ;

float_literal   = digit , { digit } , "." , digit , { digit } ;
int_literal     = digit , { digit } ;
bool_literal    = "TRUE" | "FALSE" ;

letter          = "A" | "B" | ... | "Z" | "a" | "b" | ... | "z" ;
digit           = "0" | "1" | ... | "9" ;
```

---

## 3. Operator Precedence Table

Precedence is from **lowest (evaluated last)** to **highest (evaluated first)**:

| Precedence | Operator(s) | Associativity | Type |
|:----------:|-------------|:-------------:|------|
| 1 (lowest) | `OR` | Left | Logical disjunction |
| 2 | `AND` | Left | Logical conjunction |
| 3 | `NOT` | Right (unary) | Logical negation |
| 4 | `>` `<` `>=` `<=` `==` `!=` | Non-associative | Comparison |
| 5 | `-` (unary) | Right (unary) | Arithmetic negation |
| 6 | `()` function calls, literals | — | Primary |
| 7 (highest) | `[]` (offset) | Left (postfix) | Context shift |

> **Non-associative comparisons** means chaining like `A > B > C` is a **syntax error**. Use `A > B AND B > C` instead.

---

## 4. Token Specification

The Lexer must recognize the following token types:

| Token Type | Pattern | Examples |
|------------|---------|----------|
| `FLOAT` | `\d+\.\d+` | `3.14`, `0.5`, `100.0` |
| `INTEGER` | `\d+` | `14`, `200`, `0` |
| `BOOL` | `TRUE \| FALSE` | `TRUE`, `FALSE` |
| `IDENTIFIER` | `[a-zA-Z][a-zA-Z0-9_]*` | `RSI`, `SMA`, `PRICE`, `my_func` |
| `AND` | `AND` | — |
| `OR` | `OR` | — |
| `NOT` | `NOT` | — |
| `COMP_OP` | `> \| < \| >= \| <= \| == \| !=` | — |
| `MINUS` | `-` | — |
| `LPAREN` | `(` | — |
| `RPAREN` | `)` | — |
| `COMMA` | `,` | — |
| `LBRACKET` | `[` | — |
| `RBRACKET` | `]` | — |
| `EOF` | End of input | — |

**Lexer Rules:**
- Whitespace is ignored (spaces, tabs) — it serves only as a separator.
- Keywords (`AND`, `OR`, `NOT`, `TRUE`, `FALSE`) are **case-sensitive** and always uppercase.
- Identifiers that match a keyword are classified as that keyword.

---

## 5. Parse Examples

### Example 1: `RSI(14) > 80 AND PRICE > SMA(50)`

**Token Stream:**
```
IDENTIFIER("RSI") LPAREN INTEGER(14) RPAREN
COMP_OP(">") INTEGER(80)
AND
IDENTIFIER("PRICE") COMP_OP(">")
IDENTIFIER("SMA") LPAREN INTEGER(50) RPAREN
```

**Parse Tree (simplified):**
```
         AND
        /    \
       >      >
      / \    / \
  RSI(14) 80  PRICE  SMA(50)
```

### Example 2: `NOT (VOLUME < SMA_VOL(20)) OR MACD(12, 26, 9) > 0`

**Token Stream:**
```
NOT LPAREN
  IDENTIFIER("VOLUME") COMP_OP("<")
  IDENTIFIER("SMA_VOL") LPAREN INTEGER(20) RPAREN
RPAREN
OR
IDENTIFIER("MACD") LPAREN INTEGER(12) COMMA INTEGER(26) COMMA INTEGER(9) RPAREN
COMP_OP(">") INTEGER(0)
```

**Parse Tree (simplified):**
```
           OR
          /    \
       NOT      >
        |      / \
        <   MACD   0
       / \  (12, 26, 9)
  VOLUME  SMA_VOL(20)
```

### Example 3: `RSI(14)[1] > 70 AND PRICE > SMA(50)` *(CR-001)*

**Token Stream:**
```
IDENTIFIER("RSI") LPAREN INTEGER(14) RPAREN
LBRACKET INTEGER(1) RBRACKET
COMP_OP(">") INTEGER(70)
AND
IDENTIFIER("PRICE") COMP_OP(">")
IDENTIFIER("SMA") LPAREN INTEGER(50) RPAREN
```

**Parse Tree (simplified):**
```
         AND
        /    \
       >      >
      / \    / \
  OFFSET  70  PRICE  SMA(50)
   |[1]
 RSI(14)
```

---

## 6. Grammar Validation Rules

| Rule ID | Requirement | Rationale |
|---------|-------------|-----------|
| G-001 | Comparison operators are non-associative | Prevents ambiguous chains like `A > B > C` |
| G-002 | Function arguments must be expressions | Allows nested calls: `SMA(RSI(14))` |
| G-003 | Empty argument lists are valid | Supports zero-arg functions: `PRICE()` or `PRICE` |
| G-004 | Parentheses override all precedence | Standard mathematical convention |
| G-005 | Maximum expression length: 4096 characters | Prevents resource exhaustion during lexing |
| G-006 | Maximum nesting depth: 256 levels | Prevents stack overflow in recursive-descent parser |
| G-007 | Offset values must be non-negative integers | Prevents look-ahead bias via negative offsets (CR-001) |
| G-008 | Offset `[0]` is a no-op (identity) | Equivalent to no offset; parser may optimize away (CR-001) |
