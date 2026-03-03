# Project Brief: Logical Expression Compiler for Algorithmic Trading (LECAT)

**To:** Lead AI Developer / Systems Architect
**From:** Project Manager
**Date:** October 26, 2023
**Phase:** 1 - Requirements & Specification
**Priority:** Critical

## 1. Executive Summary
We are building a high-performance **Domain-Specific Language (DSL) Compiler** designed to evaluate boolean logical expressions for financial markets. The system must parse text-based strategies (e.g., `RSI(14) > 80 AND PRICE > SMA(50)`), resolve dynamic functions from an expandable registry, and execute logic against historical data.

**Core Goal:** Create a modular, safe, and incredibly fast evaluation engine that can be used as the fitness function for a Genetic Programming / Neural Network optimization loop.

---

## 2. Assignment Objectives
You are required to produce a comprehensive **System Design Document (SDD)** and **Software Requirements Specification (SRS)**. Do not write implementation code yet. Focus on architecture, interfaces, and data contracts.

Your output must adhere to the following industry standards:
* **IEEE 830** for Requirements Specification.
* **BNF / EBNF** (Extended Backus-Naur Form) for Grammar definition.
* **C4 Model** for Architecture diagrams.

---

## 3. Required Deliverables (Documentation)

Please generate the following distinct documentation sections:

### A. The Grammar Specification (The "Language Law")
Define the syntax of our DSL rigorously.
* **Requirement:** Create an **EBNF (Extended Backus-Naur Form)** representation of the language.
* **Scope:** Must handle:
    * Unary operators (`NOT`, `-`)
    * Binary operators (`AND`, `OR`, `>`, `<`, `==`, `<=`, `>=`)
    * Function calls with variable arguments (`FUNC(arg1, arg2)`)
    * Operator precedence (e.g., `AND` binds tighter than `OR`)
    * Literals (Integers, Floats, Booleans)

### B. System Architecture Design
Define how the components interact. We need a "Plugin Architecture" for the Function Registry.
* **Diagrams Required (MermaidJS format):**
    1.  **Component Diagram:** Showing the flow from `Source String` -> `Lexer` -> `Parser` -> `AST` -> `Evaluator`.
    2.  **Registry Pattern:** How the `Evaluator` requests a function handle from the `Registry` without knowing the implementation details.
* **Data Structures:** Define the JSON/Object structure of the **Abstract Syntax Tree (AST)** nodes.

### C. The Function Registry Interface API
Define the contract for how new indicators are added. This makes the system "expandable."
* **Specification:**
    * How does a function register itself? (Decorator pattern? Config file?)
    * Input/Output contract: All functions must return a standard type (e.g., `Result<Float, Error>`)?
    * **Context Passing:** How is the "Market Data" (OHLCV array) passed to the function during evaluation?

### D. Error Handling & Edge Cases (The "Safety Net")
In financial trading, a crash is expensive.
* Define behavior for:
    * **Division by Zero** inside an indicator.
    * **Look-ahead bias:** Trying to access index `i+1`.
    * **Insufficient Data:** Calculating `SMA(200)` on the 50th bar.
    * **Type Mismatch:** Comparing `Boolean` AND `Float`.

### E. Integration Strategy (The "Optimizer Hook")
Describe the interface for the Genetic/Neural generator.
* How does the Generator request a list of available functions to build a random tree?
* Define the structure of the `BacktestResult` object (Boolean series? Trade entry/exit signals?).

---

## 4. Technical Constraints & Guiding Principles

* **Immutability:** The AST should be immutable once created.
* **Idempotency:** Evaluating the same expression on the same data set must *always* yield the same result.
* **Performance:** The Evaluator must be designed for `O(n)` complexity relative to the AST depth. Recursion depth limits must be defined to prevent stack overflow.
* **Floating Point Precision:** Specify how we handle floating point comparisons (e.g., use of epsilon `0.00001`).

---

## 5. Next Steps
Upon approval of these documents, we will move to **Phase 2: Core Implementation**, starting with the Lexer/Parser implementation in [Preferred Language, e.g., Python/Rust/C++].

**Action:** Acknowledge receipt and begin drafting the EBNF Grammar and Component Diagrams.