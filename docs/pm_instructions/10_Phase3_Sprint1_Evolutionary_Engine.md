
# Phase 3: Optimization & Evolution — Sprint 1 (The Genetic Engine)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 3 — Optimization
**Goal:** Implement the Genetic Algorithm (GA) loop to evolve strategies rather than just generating them randomly.

---

## 1. Objective
Transform the system from a "Random Strategy Generator" into an "Evolutionary Optimizer."
By the end of this sprint, the system should be able to:
1.  **Evaluate Fitness:** Calculate a real performance metric (e.g., Sharpe Ratio or Total Return), not just signal counts.
2.  **Select:** Pick the best performing strategies from a population.
3.  **Breed (Crossover):** Combine two strategies (e.g., take the `RSI` part of Parent A and the `MACD` part of Parent B).
4.  **Mutate:** Randomly tweak a strategy (e.g., change `RSI(14)` to `RSI(21)`).

---

## 2. Required File Structure
Add/Update the following files in `lecat/`:

```text
lecat/
├── ... (existing files)
├── fitness.py         # PnL and Sharpe Ratio calculations
├── evolution.py       # The Genetic Algorithm engine (Selection, Crossover, Mutation)
└── optimizer.py       # The main loop coordinating Generation -> Evaluation -> Evolution
tests/
├── test_fitness.py
└── test_evolution.py

```

---

## 3. Implementation Tasks

### Task 1: Fitness Calculator (`fitness.py`)

We need a way to score how "good" a strategy is.

* **Input:** `BacktestResult` (the boolean signal array) + `MarketContext` (price data).
* **Logic:**
* Simulate a trade: Buy on `True`, Sell on `False` (or exit after N bars).
* Calculate **Total Return** (%) and **Sharpe Ratio** (Risk-adjusted return).
* **Penalty:** Apply a fitness penalty for strategies with too few trades (< 5) to avoid overfitting small samples.



### Task 2: Genetic Operators (`evolution.py`)

Implement the biological operators for AST manipulation.

* **`mutate(ast_node) -> ast_node`**:
* Randomly change a parameter (e.g., `14` -> `15`).
* Randomly flip an operator (e.g., `>` -> `<`).
* Randomly replace a subtree with a new random branch.


* **`crossover(parent_a, parent_b) -> child`**:
* Swap subtrees between two parents. (e.g., Parent A is `(X AND Y)`, Parent B is `(Z OR W)`. Child becomes `(X AND W)`).


* **`tournament_selection(population, k=3)`**:
* Pick 3 random strategies, return the one with the highest fitness.



### Task 3: The Optimizer Loop (`optimizer.py`)

Tie it all together.

* **Algorithm:**
1. **Initialize:** Generate population of 100 random strategies.
2. **Evaluate:** Run backtest & fitness for all 100.
3. **Elitism:** Keep top 5 best performers unchanged.
4. **Breed:** Fill the rest of the next generation using Crossover & Mutation.
5. **Repeat:** Run for 10-50 generations.



---

## 4. Acceptance Criteria (Test Cases)

**Case A: Mutation Validity**

* **Input:** `RSI(14) > 50`
* **Action:** Call `mutate()` 100 times.
* **Check:** All 100 results must be valid, compilable ASTs. At least some must differ from the original.

**Case B: Crossover Validity**

* **Parent A:** `RSI(14) > 50`
* **Parent B:** `PRICE > SMA(200)`
* **Action:** Call `crossover(A, B)`.
* **Check:** Result is a valid AST combining parts of A and B (e.g., `RSI(14) > SMA(200)`).

**Case C: Improvement over Time**

* **Action:** Run the Optimizer on 1 year of data for 10 generations.
* **Check:** The "Best Fitness" of Generation 10 must be >= "Best Fitness" of Generation 0. (Evolution should effectively "climb the hill").

---

**Action:** Generate code for `fitness.py`, `evolution.py`, and `optimizer.py`.
