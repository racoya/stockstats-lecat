
# Phase 6: Data & Extensibility — Sprint 1 (Database & Dynamic Indicators)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 6 — Extensibility
**Goal:** Integrate SQLite to persist market data, manage custom indicators dynamically, and store optimization results.

---

## 1. Objective
1.  **Persistence:** Replace CSV uploads with a `lecat.db` SQLite database.
2.  **Dynamic Logic:** Implement a "Soft-Coding" engine where users can CRUD (Create, Read, Update, Delete) custom indicators via the GUI without touching code.
3.  **Documentation:** Update the `docs/` package to reflect the new database schema and operational workflows.

---

## 2. Database Schema Design
We will use `sqlite3` for simplicity and performance. Create `lecat/data/schema.sql`:

```sql
-- 1. Market Data (The Raw Material)
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1D',
    timestamp DATETIME NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    UNIQUE(symbol, timeframe, timestamp)
);

-- 2. Custom Indicators (The Logic)
-- Stores DSL formulas like "RSI(14) + RSI(21)"
CREATE TABLE indicators (
    name TEXT PRIMARY KEY,
    args JSON NOT NULL,        -- e.g. ["fast", "slow"]
    formula TEXT NOT NULL,     -- e.g. "SMA(fast) > SMA(slow)"
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Optimization Results (The Memory)
-- Stores the history of "Hall of Fame" strategies
CREATE TABLE strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expression TEXT NOT NULL,
    metrics JSON NOT NULL,     -- { "sharpe": 1.5, "return": 20.4 }
    dataset_symbol TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

```

---

## 3. Required File Structure

Add/Update the following:

```text
lecat/
├── repository.py          # New: SQLite CRUD wrapper
├── dynamic_registry.py    # New: Extends Registry to load from DB
├── data_loader.py         # Update: Add `load_from_db()`
├── dashboard/
│   ├── pages/
│   │   ├── 1_Lab.py
│   │   ├── 2_Evolution.py
│   │   └── 3_Indicator_Manager.py # New: CRUD Interface
│   └── app.py             # Update: Navigation setup
docs/
├── 07_Database_Schema.md  # New: Schema documentation
└── 06_Operations_Manual.md # Update: DB management instructions

```

---

## 4. Implementation Tasks

### Task 1: The Repository Layer (`repository.py`)

Centralize all SQL operations.

* **Class:** `Repository(db_path)`
* **Methods:**
* `save_market_data(df, symbol)`: Bulk insert Pandas DataFrame.
* `get_market_data(symbol)`: Return DataFrame.
* `save_indicator(name, args, formula, desc)`: Insert/Update `indicators` table.
* `delete_indicator(name)`: Remove from DB.
* `get_all_indicators()`: Return list of dicts.
* `save_result(result)`: Log a backtest result.



### Task 2: Dynamic Registry (`dynamic_registry.py`)

Bridge the Database to the Compiler.

* **Class:** `DynamicRegistry` (inherits `FunctionRegistry`).
* **Logic:**
* On `__init__`, call `repository.get_all_indicators()`.
* For each row, register a **Composite Handler**.
* **Composite Handler Logic:**
1. Accept arguments (e.g., `fast=10, slow=50`).
2. Load the formula string: `SMA(fast) > SMA(slow)`.
3. **Inject Values:** Replace `fast` with `10` and `slow` with `50` in the string (or AST).
4. Call `evaluator.evaluate(new_formula)`.


* *Safety:* Catch recursion errors (Circle references: A calls B, B calls A).



### Task 3: The Indicator Manager GUI (`3_Indicator_Manager.py`)

A new Streamlit page for the user.

* **Left Column (List):** Show all custom indicators. Click to edit.
* **Right Column (Editor):**
* **Name Input:** (e.g., `MY_MACD_CROSS`)
* **Arguments Input:** (e.g., `fast, slow`)
* **Formula Editor:** Text area with syntax highlighting if possible.
* **Test Area:** "Test on current data" button to verify the formula works before saving.
* **Save/Delete Buttons.**



### Task 4: Documentation Updates

* **`07_Database_Schema.md`:** Document the tables, relationships, and data types.
* **`06_Operations_Manual.md`:** Add a section on "Managing Custom Indicators" and "Backing up the Database."

---

## 5. Acceptance Criteria

**Case A: The "No-Code" Extension**

1. Open Dashboard > Indicator Manager.
2. Create `AVG_PRICE` with args `none` and formula `(high + low) / 2`.
3. Click Save.
4. Go to Lab. Type `close > AVG_PRICE()`.
5. **Check:** The backtest runs successfully using the new logic.

**Case B: Persistence**

1. Restart the Streamlit server (simulating a crash/restart).
2. **Check:** `AVG_PRICE` is still available in the Lab.

**Case C: Data Management**

1. Upload a CSV "BTC_USD".
2. **Check:** It saves to SQLite.
3. Reload the page. "BTC_USD" appears in the "Select Asset" dropdown (read from DB).

---

**Action:** Generate the code for `schema.sql`, `repository.py`, `dynamic_registry.py`, and the new Dashboard pages.