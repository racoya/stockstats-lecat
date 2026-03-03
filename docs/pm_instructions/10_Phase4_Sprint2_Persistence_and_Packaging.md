
# Phase 4: Interface & Deployment — Sprint 2 (Persistence & Packaging)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 4 — Interface & Deployment
**Goal:** Implement Strategy Persistence (Import/Export), Robust Logging, and finalize the Python environment setup.

---

## 1. Objective
1.  **Package:** Freeze all project dependencies into a `requirements.txt` file so the project is reproducible on any machine.
2.  **Persist:** Allow users to save their "winning" strategies from the Dashboard to a file (JSON) and load them back in.
3.  **Log:** Replace console prints with a professional logging system (`logging` module) to track optimization runs efficiently.

---

## 2. Required File Structure
Add/Update the following files:

```text
lecat/
├── ... (existing files)
├── exporter.py          # New: Logic to save/load strategies (JSON)
├── logger.py            # New: Centralized logging configuration
└── config.yaml          # New: Externalized settings (Capital, Theme, Paths)
root/
└── requirements.txt     # New: Complete dependency list

```

---

## 3. Implementation Tasks

### Task 1: Strategy Export & Import (`exporter.py`)

The user needs to save their best work.

* **Function:** `save_strategy(strategy_data: dict, filepath: str)`
* **Function:** `load_strategy(filepath: str) -> dict`
* **Format:** JSON.
* **Schema:**
```json
{
  "name": "Golden Cross V1",
  "expression": "SMA(50) > SMA(200)",
  "metrics": { "sharpe": 1.5, "return": 25.4 },
  "timestamp": "2026-03-03T12:00:00",
  "engine_version": "2.0"
}

```




* **Dashboard Integration:**
* Add a **"Download Strategy"** button in the "Hall of Fame" table.
* Add an **"Upload Strategy"** area in the "Lab" tab to load a JSON file and auto-populate the expression box.



### Task 2: Structured Logging (`logger.py`)

Debug prints are messy and disappear when the terminal closes.

* **Setup:** Configure Python's standard `logging` library.
* **Configuration:**
* Create a `logs/` directory if it doesn't exist.
* **Console Handler:** Level `INFO`, Format `[%(levelname)s] %(message)s`.
* **File Handler:** Level `DEBUG`, Rotating (10MB size, 5 backups), Format `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.


* **Action:** Refactor `optimizer.py`, `backtester.py`, and `evolution.py` to use `logger.info()` instead of `print()`.

### Task 3: Configuration (`config.yaml`)

Stop hardcoding paths and constants.

* **File:** `config.yaml`
* `initial_capital`: 10000
* `chart_theme`: "plotly_dark"
* `log_dir`: "logs"
* `strategies_dir`: "strategies"


* **Loader:** Update `lecat/__init__.py` to load this config into a global object on startup.

### Task 4: Dependency Freeze (`requirements.txt`)

Ensure the project environment is reproducible.

* **Command:** Scan imports or use `pip freeze`.
* **Required Packages:**
* `numpy` (Core math)
* `pandas` (Data handling)
* `scipy` (If used for advanced stats)
* `streamlit` (Dashboard)
* `plotly` (Charting)
* `pyyaml` (Config parsing)
* `pytest` (Testing)



---

## 4. Acceptance Criteria

**Case A: Reproducibility**

* **Action:** Create a fresh virtual environment (`python -m venv venv`), activate it, and run `pip install -r requirements.txt`.
* **Check:** `streamlit run lecat/dashboard/app.py` launches successfully without missing module errors.

**Case B: The "Save & Load" Loop**

* **Action:**
1. Evolve a strategy in the Dashboard.
2. Click "Download" (saves JSON).
3. Refresh the page.
4. Upload that JSON in the "Lab".


* **Check:** The expression text area is populated with the saved strategy, and the backtest runs automatically.

**Case C: Log Verification**

* **Action:** Run a short optimization (2 generations).
* **Check:** Check `logs/lecat.log`. It should contain timestamps and detailed progress info (e.g., "Evolution started", "Generation 1 best fitness: ...").

---

**Action:** Generate the code for `requirements.txt`, `exporter.py`, `logger.py`, and `config.yaml`.