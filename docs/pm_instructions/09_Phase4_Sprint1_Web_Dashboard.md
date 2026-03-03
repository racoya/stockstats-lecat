
# Phase 4: Interface — Sprint 1 (The Quantitative Dashboard)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 4 — Interface & Deployment
**Goal:** Build an interactive Web GUI (Streamlit) to control the optimizer, visualize charts, and manually test strategies.

---

## 1. Objective
Replace the static command-line interface with a modern web dashboard.
By the end of this sprint, the user should be able to:
1.  **Upload Data:** Drag & drop a CSV file (e.g., `BTC_USD.csv`).
2.  **The "Lab" Mode:** Type a strategy manually (e.g., `RSI(14) < 30`) and instantly see the Buy/Sell signals on an interactive candlestick chart.
3.  **The "Evolution" Mode:** Click "Start Optimization", watch a progress bar, and see a live-updating "Hall of Fame" table of the best strategies.

---

## 2. Required File Structure
Add the following folder and file:

```text
lecat/
├── ... (existing engine files)
└── dashboard/
    └── app.py         # The Streamlit Application entry point

```

---

## 3. Implementation Tasks

### Task 1: The Setup (`app.py`)

Initialize a Streamlit app with a sidebar for configuration.

* **Sidebar:**
* **File Uploader:** Accept `.csv` files.
* **Settings:** Date Range slider, Initial Capital input.


* **Backend Connection:**
* Use `lecat.data_loader` to parse the uploaded file.
* Cache the data loading using `@st.cache_data` to prevent reloading on every click.



### Task 2: "Lab" Mode (Manual Testing)

Create a tab for testing specific ideas.

* **Input:** Text area for DSL Expression.
* **Action:** "Run Backtest" button.
* **Output:**
* **Metrics:** Simple metrics row (Total Return, Win Rate, Trades).
* **Chart:** Use `plotly.graph_objects` (Candlestick) to plot the price.
* **Overlay:** Add markers (Triangles) where the signal is `True`.



### Task 3: "Evolution" Mode (The Optimizer)

Create a tab for running the Genetic Algorithm.

* **Inputs:** Number of Generations, Population Size, Mutation Rate.
* **Process:**
* When "Evolve" is clicked, run the `Optimizer` (reusing your parallel engine).
* **Challenge:** Streamlit refreshes on interaction. You might need a "Callback" mechanism to update a progress bar or text area during the evolution loop.


* **Output:**
* **Leaderboard:** A `st.dataframe` showing the top 10 strategies sorted by Fitness.
* **Selection:** Clicking a row in the dataframe should visualize that strategy's equity curve.



---

## 4. Technical Constraints

* **Framework:** Use `streamlit` (it is the standard for Python data apps and requires minimal frontend code).
* **Charting:** Use `plotly` for interactivity (Zoom/Pan), not `matplotlib`.
* **State Management:** Use `st.session_state` to store the "Best Strategies" so they don't disappear when you interact with other widgets.

---

## 5. Acceptance Criteria

**Case A: The "Sanity Check"**

* **Action:** Upload data, type `PRICE > SMA(50)` in the Lab, click Run.
* **Check:** An interactive chart appears. You can zoom in and see exactly where the price crossed the SMA.

**Case B: The Optimization Loop**

* **Action:** Go to Evolution tab, set Gen=3, Pop=20, click "Start".
* **Check:** The app does not freeze completely (or displays a spinner). After completion, a table of results appears.

**Case C: Error Handling**

* **Action:** Type `INVALID_SYNTAX(123)` in the Lab.
* **Check:** The app displays a friendly error message (e.g., "Syntax Error: ...") instead of crashing with a Python traceback.

---

**Action:** Generate the code for `lecat/dashboard/app.py`.