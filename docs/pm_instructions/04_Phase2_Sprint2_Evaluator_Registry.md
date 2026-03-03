
# Phase 2: Core Implementation — Sprint 2 (Evaluator & Registry)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 2 — Implementation
**Goal:** Implement the `Evaluator`, `FunctionRegistry`, and `MarketContext`.

---

## 1. Objective
We need to bridge the gap between the static AST (created in Sprint 1) and actual execution. By the end of this sprint, the system must be able to:
1.  Register a Python function (like `RSI` or `SMA`) into the system.
2.  Pass market data (`MarketContext`) to the Evaluator.
3.  Walk the AST, execute logic, and return a boolean array of signals.
4.  **Crucially:** Handle `OffsetNode` by cloning the context (Time Travel).

---

## 2. Required File Structure
Add/Update the following files in `lecat/`:

```text
lecat/
├── ... (existing files)
├── context.py         # MarketContext definition (Data Layer)
├── registry.py        # FunctionRegistry and decorators
├── evaluator.py       # The Tree Walker implementation
└── std_lib.py         # Basic built-in functions (SMA, RSI, etc.)
tests/
├── test_evaluator.py
└── test_registry.py

```

---

## 3. Implementation Tasks

### Task 1: The Data Layer (`context.py`)

Implement `MarketContext` as an immutable dataclass.

* **Fields:** `open`, `high`, `low`, `close`, `volume` (numpy arrays), `bar_index` (int).
* **Method:** `with_index(self, new_index: int) -> MarketContext`
* **Requirement:** This must be $O(1)$. Use `dataclasses.replace()` to create a shallow copy. Do **not** copy the numpy arrays.
* **Validation:** Raise `ValueError` if `new_index < 0` or `new_index > self.bar_index` (Future Peek protection).



### Task 2: The Registry (`registry.py`)

Implement the plugin system defined in `03_Function_Registry_API.md`.

* **Class:** `FunctionRegistry` with a dictionary of handlers.
* **Decorator:** `@register` to easily add functions.
* **Metadata:** Store `arg_schema` and `min_bars` logic for each function.

### Task 3: The Evaluator (`evaluator.py`)

Implement the `Evaluator` class that traverses the AST.

* **Method:** `visit_node(node, context)` (Recursive dispatcher).
* **Logic:**
* `BinaryOp` (`AND`/`OR`): Combine boolean results.
* `Comparison` (`>`, `<`): Compare float/int results.
* **OffsetNode (The Core Feature):**
1. Calculate `past_index = context.bar_index - node.shift`.
2. If `past_index < 0`, return `FunctionResult.insufficient_data()`.
3. Call `context.with_index(past_index)`.
4. Recurse.





### Task 4: Standard Library (`std_lib.py`)

Implement a few basic indicators to test the system.

* `PRICE()`: Returns `context.close[context.bar_index]`.
* `SMA(period)`: Calculates Simple Moving Average.
* *Optimization:* You don't need a full pandas implementation yet. A simple slice-and-average is fine for the prototype: `np.mean(context.close[idx-p+1 : idx+1])`.



---

## 4. Acceptance Criteria (Test Cases)

**Case A: Basic Execution**

* **Context:** `close = [10, 11, 12, 13, 14]`, `bar_index = 4` (Value is 14).
* **Expression:** `PRICE > 12`
* **Result:** `True` (since 14 > 12).

**Case B: Context Shifting (Time Travel)**

* **Context:** Same as above.
* **Expression:** `PRICE[1] > 12`
* **Logic:**
* `PRICE` at index 4 is 14.
* `PRICE[1]` shifts index to 3. `close[3]` is 13.
* 13 > 12 is `True`.


* **Result:** `True`.

**Case C: Deep Shift**

* **Expression:** `PRICE[2] == 12`
* **Logic:** Index 4 - 2 = 2. `close[2]` is 12.
* **Result:** `True`.

**Case D: Out of Bounds**

* **Expression:** `PRICE[10]`
* **Result:** `FunctionResult.insufficient_data()` (or `False` depending on error policy handling in `ComparisonNode`).

---

**Action:** Generate the Python code for `context.py`, `registry.py`, `evaluator.py`, and `std_lib.py`.
