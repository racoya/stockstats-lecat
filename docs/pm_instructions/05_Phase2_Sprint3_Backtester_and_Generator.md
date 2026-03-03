
# Phase 2: Core Implementation — Sprint 3 (Backtester & Generator)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 2 — Implementation
**Goal:** Implement the `Backtester` (Time Loop) and `ExpressionGenerator` (Random Strategy Creator).

---

## 1. Objective
We need to scale the system from evaluating a *single moment* to evaluating an *entire history*, and then automatically generating strategies to test.

By the end of this sprint, we must be able to:
1.  **Generate:** Create a random, valid strategy string (e.g., `RSI(14) > 70 AND ...`).
2.  **Backtest:** Run that strategy across 10,000 bars of history efficiently.
3.  **Report:** Output a `BacktestResult` containing the signal array and basic stats.

---

## 2. Required File Structure
Add/Update the following files in `lecat/`:

```text
lecat/
├── ... (existing files)
├── generator.py       # Random expression generator
├── backtester.py      # Time-loop engine
├── stats.py           # Basic performance metrics
└── main.py            # CLI entry point to run a full cycle
tests/
├── test_generator.py
└── test_backtester.py

```

---

## 3. Implementation Tasks

### Task 1: The Generator (`generator.py`)

Implement the random strategy creator defined in `05_Integration_Strategy.md`.

* **Input:** `FunctionRegistry` (to know what functions are available).
* **Logic:**
* `generate_random_strategy(max_depth=3)`: Recursive builder.
* Randomly choose between: `BinaryOp` (`AND`/`OR`), `Comparison`, or `Terminal` (Function/Literal).
* **Smart Argument Generation:** Use the `arg_schema` from the registry to generate valid random numbers (e.g., `RSI` period between 2 and 50).
* **Context Shifting:** Randomly append `[n]` offsets to nodes (e.g., 10% chance).



### Task 2: The Backtester (`backtester.py`)

Implement the loop that applies the AST to the market data.

* **Class:** `Backtester`
* **Method:** `run(ast, context) -> BacktestResult`
* **Logic:**
1. Determine `warmup_period` (max lookback needed by the AST).
2. Iterate `bar_index` from `warmup_period` to `context.total_bars`.
3. Update `context.bar_index` (or create new lightweight context).
4. Call `evaluator.evaluate(ast, context)`.
5. Store result (True/False) in a numpy array or boolean list.


* **Optimization Hint:** If performance is slow, simple `dict` caching for indicator values at specific indices (`@lru_cache`) usually provides a 10x speedup.

### Task 3: Statistics & Reporting (`stats.py`)

Calculate basic metrics from the boolean signal array.

* `total_signals`: Count of `True`.
* `signal_density`: % of bars with a signal.
* *(Optional Phase 3)*: PnL calculation (simulate buying on True, selling on False). For now, just counting signals is sufficient to prove the engine works.

### Task 4: Main Entry Point (`main.py`)

Tie it all together.

1. Load dummy CSV data (or generate random OHLCV).
2. Init Registry & Evaluator.
3. **Loop 10 times:**
* Generate random strategy.
* Compile & Backtest.
* Print: "Strategy: [String] -> Signals: [Count] / [Time Taken]"



---

## 4. Acceptance Criteria (Test Cases)

**Case A: Generator Validity**

* Call `generate_random_strategy()` 100 times.
* **Check:** Every resulting string must successfully compile via `Parser` without syntax errors.

**Case B: Backtest Consistency**

* **Strategy:** `PRICE > 10`
* **Data:** `[11, 9, 12, 8, 15]`
* **Result:** `[True, False, True, False, True]`
* **Verify:** The Backtester output matches this array exactly.

**Case C: Performance Benchmark**

* Run a complex strategy (Depth 4) over 10,000 bars.
* **Target:** Should execute in under 1.0 seconds (Python) or 0.1s (Optimized).

---

**Action:** Generate the code for `generator.py`, `backtester.py`, `stats.py`, and `main.py`.