Here is the consolidated instruction file.

---

### File: `06_CR001_Context_Shifting.md`

```markdown
# CR-001 — Change Request: Context Shifting & Lookback Implementation

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Status:** Approved
**Priority:** Critical

---

## 1. Overview
The current specification (v1.0) lacks a mechanism to evaluate expressions relative to a past point in time (e.g., "Was RSI > 70 *yesterday*?"). To support backtesting and complex signal logic, we are introducing **Context Shifting**.

**Core Concept:**
Instead of passing historical arrays to every function, we will allow the `Evaluator` to temporarily "shift" the `MarketContext.bar_index` to a past value. This allows us to reuse all existing logic without modification.

**Syntax:** `EXPRESSION[offset]`
* `RSI(14)[1]` → Value of RSI 1 bar ago.
* `(close > open)[1]` → Check if yesterday was a green candle.

---

## 2. Required Updates: `01_Grammar_Specification.md`

### 2.1 Update EBNF Grammar
Modify the `primary` rule to accept an optional offset, and define the `offset` syntax.

**Find:**
```ebnf
primary         = literal
                | function_call
                | identifier
                | "(" , expression , ")" ;

```

**Replace With:**

```ebnf
primary         = ( literal | function_call | identifier | "(" , expression , ")" ) , [ offset ] ;

offset          = "[" , int_literal , "]" ;

```

### 2.2 Update Operator Precedence Table

Add **Subscript/Offset** to the highest precedence level (binding tighter than function calls or unary operators).

| Precedence | Operator(s) | Associativity | Type |
| --- | --- | --- | --- |
| ... | ... | ... | ... |
| 7 (highest) | `[]` (offset) | Left | Postfix |

---

## 3. Required Updates: `02_System_Architecture.md`

### 3.1 Update AST Node Schemas

Add a new node type `OffsetNode` to handle the time-shift logic.

**Add to Section 4.1 (Node Type Enumeration):**
`OFFSET = "offset"`

**Add to Section 4.2 (Node Schemas):**

#### OffsetNode

Represents a time-shifted evaluation (e.g., `RSI(14)[1]`).

```json
{
  "type": "offset",
  "shift_amount": 1,
  "child": { "...child node..." }
}

```

### 3.2 Update Component Interface (Evaluator Logic)

Describe the logic for handling the `OffsetNode`.

**Add to Section 5.4 (Evaluator):**

> **Handling Offsets:**
> When visiting an `OffsetNode`, the Evaluator must:
> 1. Calculate `past_index = context.bar_index - node.shift_amount`.
> 2. If `past_index < 0`, return `FunctionResult.insufficient_data()`.
> 3. Create a **shallow copy** of the context: `temp_ctx = context.with_index(past_index)`.
> 4. Recursively call `evaluate(node.child, temp_ctx)`.
> 
> 

---

## 4. Required Updates: `03_Function_Registry_API.md`

### 4.1 Update `MarketContext` Class

Add the factory method to support efficient context cloning.

**Find:**

```python
@dataclass(frozen=True)
class MarketContext:
    # ... fields ...

```

**Add Method:**

```python
    def with_index(self, new_index: int) -> "MarketContext":
        """
        Return a lightweight copy of the context pointing to a different time.
        Does NOT copy the data arrays (references are preserved).
        
        Args:
            new_index: The target bar index (must be >= 0).
        """
        # Implementation note: In Python dataclasses, use replace()
        # return dataclasses.replace(self, bar_index=new_index)
        ...

```

### 4.2 Update Safety Rules

Add a rule explicitly forbidding "Future Lookup" (negative offsets).

**Add to Section 3.2 (Safety Features):**

* **No Future Peeking:** The `offset` syntax in the grammar uses positive integers (e.g., `[1]`). The parser must reject negative integers in the offset position (e.g., `[-1]`) to prevent looking ahead into the future.

---

## 5. Implementation Notes for Developer

* **Performance:** Since `MarketContext` holds references to large `numpy` arrays, ensure `with_index` is `O(1)` (reference copy only). Do not deep-copy the data arrays.
* **Caching:** The `Evaluator`'s cache key must now include the `bar_index`. `RSI(14)` at index 100 is different from `RSI(14)` at index 99.
* *Old Key:* `(function_name, args)`
* *New Key:* `(function_name, args, bar_index)`



---

**Action:** Please update the master documentation files to reflect these changes immediately.
