
# Phase 3: Optimization — Sprint 2 (Data & Validation)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 3 — Optimization
**Goal:** Connect the system to real market data and implement "Walk-Forward Validation" to prevent overfitting.

---

## 1. Objective
Currently, the system optimizes on whatever data is fed to it. If we feed it the entire history, it will "memorize" the chart (Overfitting).
We need to:
1.  **Ingest Real Data:** Load standard CSV/Pandas OHLCV data (e.g., from Yahoo Finance or broker exports).
2.  **Split Data:** Implement **In-Sample (Training)** vs **Out-of-Sample (Testing)** splitting.
3.  **Visualize:** Generate an Equity Curve chart to see *how* the strategy performed, not just the final number.

---

## 2. Required File Structure
Add/Update the following files in `lecat/`:

```text
lecat/
├── ... (existing files)
├── data_loader.py     # New: Handles CSV/DataFrame loading and cleaning
├── reporting.py       # New: Generates charts (Matplotlib/Plotly)
└── optimizer.py       # Update: Add Train/Test split logic
tests/
├── test_data_loader.py
└── test_reporting.py

```

---

## 3. Implementation Tasks

### Task 1: Data Ingestion (`data_loader.py`)

Create a robust loader for financial time series.

* **Function:** `load_from_csv(filepath: str) -> MarketContext`
* **Requirements:**
* Expect columns: `Date`, `Open`, `High`, `Low`, `Close`, `Volume`.
* Handle missing values (forward fill).
* Convert columns to efficient numpy arrays (float32 to save memory).
* **Validation:** Ensure data is sorted by date.



### Task 2: Walk-Forward Logic (`optimizer.py`)

Update the `Optimizer` class to handle data splitting.

* **Update `run()` method:** Accept a `split_ratio` (default 0.7).
* **Logic:**
1. Slice `MarketContext` into `train_ctx` (first 70%) and `test_ctx` (last 30%).
2. **Train:** Run the Genetic Algorithm (Selection/Crossover/Mutation) **ONLY** on `train_ctx`.
3. **Validate:** Take the best strategy from the final generation and run it once on `test_ctx`.
4. **Report:** specific metrics for *both* periods. (e.g., "Train Sharpe: 2.5 | Test Sharpe: 0.8").


* *Note:* A huge drop from Train to Test indicates overfitting.



### Task 3: Visual Reporting (`reporting.py`)

We need to see the growth of the account.

* **Function:** `plot_equity_curve(result: BacktestResult, title: str)`
* **Tool:** Use `matplotlib` or `plotly` (simple static image is fine for now).
* **Output:** A line chart showing Cumulative Return over time.
* Overlay the "Buy & Hold" benchmark for comparison.
* Mark "Buy" and "Sell" points on a sub-chart if possible.



---

## 4. Acceptance Criteria (Test Cases)

**Case A: Real Data Loading**

* **Input:** A sample `AAPL.csv` (provided or mocked in tests).
* **Check:** `MarketContext` is created correctly. `close_prices` is a numpy array. Accessing index `-1` returns the last price.

**Case B: Split Enforcement**

* **Action:** Run Optimizer with `split_ratio=0.5`.
* **Check:**
* The "Best Strategy" must be selected based on fitness calculated from the *first half* of data.
* The "Test Result" must be calculated using that strategy on the *second half*.
* Ensure no data leakage (Training fitness should not change if Test data changes).



**Case C: Visualization**

* **Action:** Run a backtest and call `plot_equity_curve`.
* **Check:** An image file (e.g., `backtest_chart.png`) is generated. The curve starts at 0% (or Initial Capital).

---

**Action:** Generate the code for `data_loader.py` and `reporting.py`, and update `optimizer.py`.
