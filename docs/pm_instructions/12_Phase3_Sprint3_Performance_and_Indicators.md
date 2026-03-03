
# Phase 3: Optimization — Sprint 3 (Performance & Extended Library)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 3 — Optimization
**Goal:** Implement Parallel Processing to speed up the Genetic Loop and expand the Indicator Library to enable real-world strategies.

---

## 1. Objective
1.  **Parallelize:** Use `multiprocessing` to run the `Backtester` on multiple CPU cores. The Genetic Algorithm (Evaluation step) is "embarrassingly parallel."
2.  **Expand Vocabulary:** Add standard technical indicators (MACD, Bollinger Bands, ATR, Stochastic) to the `FunctionRegistry`.
3.  **Optimize Caching:** Ensure indicators like `RSI(14)` are not re-calculated 100 times if 100 different strategies use them.

---

## 2. Required File Structure
Add/Update the following files in `lecat/`:

```text
lecat/
├── ... (existing files)
├── parallel.py        # New: ProcessPoolExecutor wrapper for batch evaluation
├── indicators.py      # Update: Add MACD, BBANDS, ATR, STOCH
├── cache.py           # New: Shared Memoization logic (optional, or stick to LRU)
└── optimizer.py       # Update: Use parallel.py for population evaluation
tests/
├── test_indicators.py # Test values against known formulas (or pandas-ta)
└── test_parallel.py   # Ensure results match serial execution

```

---

## 3. Implementation Tasks

### Task 1: The Parallel Evaluator (`parallel.py`)

Processing 1000 items in a loop is slow. We need to map this to CPU cores.

* **Class:** `BatchEvaluator`
* **Method:** `evaluate_population(population, context, max_workers=None)`
* **Logic:**
* Use `concurrent.futures.ProcessPoolExecutor`.
* **Challenge:** `MarketContext` might be large. If we pickle it for every process, overhead kills the speedup.
* **Solution:** Use Python's `multiprocessing.shared_memory` OR rely on Linux `fork()` copy-on-write behavior (easiest for Phase 3).
* Return a list of `FunctionResult` or `BacktestResult` objects in the same order as the input.



### Task 2: Extended Indicator Library (`indicators.py`)

Implement the standard trading suite. You may use `numpy` vectorization for speed.

* **MACD(fast, slow, signal):** Returns the Histogram value. (Requires recursive EMA calculation).
* **ATR(period):** Average True Range (Volatility).
* **BBANDS(period, std_dev):** Returns `%B` (Percentage Bandwidth) or just the logic for `Upper` and `Lower`.
* *Suggestion:* Implement `BB_UPPER(period, std)` and `BB_LOWER(period, std)` as separate functions for the DSL.


* **STOCH(k, d):** Stochastic Oscillator.

### Task 3: Global Indicator Cache (Optimization)

In a population of 1000 strategies, `RSI(14)` might appear 500 times.

* **Mechanism:** Since `MarketContext` is immutable for a given generation, we can cache indicator arrays.
* **Implementation:** Decorate the indicator handlers with a custom `@context_cache` that uses `(function_name, args_tuple, context_id)` as the key.
* *Note:* This works best within a single process. For multiprocessing, simple `@lru_cache` inside the worker process is sufficient because the OS handles the rest.



### Task 4: CLI Update (`main.py`)

Update the command line interface to accept:

* `--cores N`: Number of CPU workers (default: count - 1).
* `--generations N`: Number of evolution cycles.

---

## 4. Acceptance Criteria (Test Cases)

**Case A: Parallel Speedup**

* **Action:** Run a benchmark with Population=500, Generations=5.
* **Check:**
* `serial` execution time: T1.
* `parallel` (4 cores) execution time: T2.
* Target: T2 should be significantly < T1 (ideally ~3x faster).



**Case B: Indicator Correctness**

* **Action:** Calculate `MACD(12, 26, 9)` manually on a small array.
* **Check:** The `lecat` implementation matches the manual calculation within `1e-5` tolerance.

**Case C: Reproducibility**

* **Action:** Run the optimizer in Parallel mode with `seed=42`.
* **Check:** The final "Best Strategy" must be identical to running it in Serial mode with `seed=42`.

---

**Action:** Generate the code for `parallel.py`, update `indicators.py`, and refactor `optimizer.py`.
