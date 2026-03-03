# LECAT — System Design Document (SDD) & Software Requirements Specification (SRS)

**Project:** Logical Expression Compiler for Algorithmic Trading (LECAT)
**Version:** 2.0
**Date:** March 3, 2026
**Phase:** 4 — Interface & Deployment
**Standards:** IEEE 830 (SRS), EBNF (Grammar), C4 Model (Architecture)

---

## 1. Executive Summary

LECAT is a high-performance **Domain-Specific Language (DSL) Compiler** designed to evaluate boolean logical expressions for financial markets. The system parses text-based trading strategies, resolves dynamic indicator functions from an expandable registry, and executes logic against historical market data.

**Primary Use Case:** Serve as the fitness function for a Genetic Programming / Neural Network optimization loop — requiring extreme performance, determinism, and safety guarantees.

**Example Expression:**
```
RSI(14) > 80 AND PRICE > SMA(50)
```

---

## 2. Document Index

This documentation suite is organized into the following files:

| # | Document | Description |
|---|----------|-------------|
| 00 | [Overview](./00_Overview.md) | This file — project summary, glossary, and constraints |
| 01 | [Grammar Specification](./01_Grammar_Specification.md) | EBNF grammar definition for the DSL |
| 02 | [System Architecture](./02_System_Architecture.md) | Component diagrams, AST node schemas, data flow |
| 03 | [Function Registry API](./03_Function_Registry_API.md) | Plugin registration contract and context passing |
| 04 | [Error Handling](./04_Error_Handling.md) | Error taxonomy, edge cases, and safety guarantees |
| 05 | [Integration Strategy](./05_Integration_Strategy.md) | Optimizer hook interface and BacktestResult schema |
| 06 | [Operations Manual](./06_Operations_Manual.md) | Installation, CLI usage, dashboard, and deployment |

---

## 3. Technical Constraints & Guiding Principles

These constraints apply across all components and are **non-negotiable**.

### 3.1 Immutability
The AST **must be immutable** once created by the Parser. No component downstream may mutate AST nodes. This guarantees safe concurrent evaluation and repeatable results.

### 3.2 Idempotency
Evaluating the same expression on the same dataset must **always** yield the same result, regardless of execution count, thread, or time of invocation.

### 3.3 Performance
- The Evaluator must operate at **O(n)** complexity relative to AST depth (single tree walk).
- **Recursion depth limit:** Maximum AST depth of **256 nodes** to prevent stack overflow.
- Function results should be **cached per bar** during a single evaluation pass to avoid redundant computation (e.g., `SMA(50)` referenced twice should compute once).

### 3.4 Floating-Point Precision
All floating-point comparisons must use an **epsilon tolerance**:
```
EPSILON = 1e-9

def float_eq(a: float, b: float) -> bool:
    return abs(a - b) < EPSILON
```
This applies to `==`, `<=`, and `>=` operators within the Evaluator.

### 3.5 Determinism
No randomness, no external I/O, no side effects during evaluation. The compiler pipeline is a **pure function**: `f(expression, data) → result`.

---

## 4. Glossary

| Term | Definition |
|------|------------|
| **AST** | Abstract Syntax Tree — the in-memory tree representation of a parsed expression |
| **Bar** | A single time-period data point containing OHLCV values |
| **BNF/EBNF** | (Extended) Backus-Naur Form — a formal notation for describing language grammar |
| **DSL** | Domain-Specific Language — a language designed for a particular application domain |
| **Evaluator** | The component that walks the AST and computes the final boolean result per bar |
| **Lexer** | The component that converts a raw string into a stream of tokens |
| **OHLCV** | Open, High, Low, Close, Volume — standard market data fields |
| **Parser** | The component that converts a token stream into an AST |
| **Registry** | The plugin system that maps function names to their implementations |
| **SDD** | System Design Document |
| **SRS** | Software Requirements Specification |
| **Token** | A classified unit of the source string (e.g., `NUMBER`, `OPERATOR`, `IDENTIFIER`) |

---

## 5. Scope Boundaries

### Implemented
- Grammar definition and formal specification
- Architecture design with component interfaces
- Function registry plugin pattern (standard + extended indicators)
- Error handling taxonomy
- Optimizer integration interface
- Full compiler pipeline (Lexer → Parser → AST → Evaluator)
- Context Shifting (CR-001)
- Backtesting engine with signal statistics
- Random expression generator
- Genetic Algorithm optimizer with walk-forward validation
- CSV data loader with column alias resolution
- Equity curve reporting (matplotlib + Plotly)
- Multi-core parallel evaluation
- Extended indicators (MACD, BB_UPPER, BB_LOWER, STOCH)
- Interactive web dashboard (Streamlit)

### Out of Scope
- Live data feeds / real-time streaming
- Order execution / broker integration
- Multi-asset portfolio optimization
- Neural network strategy generation
