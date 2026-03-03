# LECAT: From Zero to Hero
## A Complete Theory Guide for Algorithmic Trading System Design

> **Purpose:** This document is a structured, self-contained learning resource covering every theoretical concept behind the LECAT (Logical Expression Compiler for Algorithmic Trading) system. It is designed to be used as a source for a training video and slide deck. Topics progress from foundational concepts to advanced engineering, and every concept is explicitly linked to the application feature where it is implemented. Suitable for viewers with an interest in finance and/or software development.

---

# MODULE 1: THE WORLD OF ALGORITHMIC TRADING

## 1.1 What Is Algorithmic Trading?

Algorithmic trading, also called **automated trading** or **quant trading**, is the practice of using computer programs to make financial trading decisions and execute orders. Instead of a human watching a screen and guessing when to buy or sell, a precisely defined **strategy** runs automatically 24/7.

**Why this matters:**
- Speed: algorithms execute in microseconds, faster than any human
- Consistency: algorithms follow rules without emotional bias (no panic selling, no greed-driven holding)
- Scale: a single algorithm can monitor hundreds of assets simultaneously

**The core idea:** Define a mathematical rule. If the rule is satisfied, buy. If another rule is satisfied, sell. Repeat forever.

---

## 1.2 OHLCV Data: The Language of Markets

Every bar (every unit of time — 1 minute, 1 hour, 1 day) in a financial market is described by exactly **5 values**, known as OHLCV:

| Field | Meaning | Example |
|-------|---------|---------|
| **O** — Open | Price at the start of the bar | $45,000 |
| **H** — High | The maximum price during the bar | $46,200 |
| **L** — Low | The minimum price during the bar | $44,800 |
| **C** — Close | Price at the end of the bar | $45,900 |
| **V** — Volume | Total amount traded during the bar | 12,400 BTC |

> **Key insight:** Most technical indicators are mathematical functions that transform this raw OHLCV stream into a single meaningful number per bar. The Close price is the most commonly used input.

---

## 1.3 What Is a Trading Strategy?

A trading strategy is a set of logical rules that answer two questions:
1. **When should I enter (buy)?** — The **entry condition**
2. **When should I exit (sell)?** — The **exit condition**

**Example in plain English:**
> "Buy when the market has been oversold for several days (RSI is very low) AND the price is below its recent average (below the Bollinger Band lower line)."

In LECAT's language:
```
RSI(14) < 30 AND PRICE < BB_LOWER(20, 2.0)
```

This single line becomes a fully executable, backtestable strategy.

---

# MODULE 2: TECHNICAL INDICATORS — THE BUILDING BLOCKS

## 2.1 The Philosophy of Technical Analysis

Technical analysis is the practice of forecasting future price movements based solely on **historical price and volume data**. The central assumption is:

> "All known information is already reflected in the price. Patterns in price history tend to repeat."

This is debated in academic finance (the *Efficient Market Hypothesis* argues against it), but it remains the foundation of the vast majority of retail and systematic trading tools.

---

## 2.2 Moving Averages

### Simple Moving Average (SMA)
The SMA is the arithmetic mean of the last N closing prices. It smooths out noise.

**Formula:**
```
SMA(n, t) = (Close[t] + Close[t-1] + ... + Close[t-n+1]) / n
```

**What it tells you:** SMA(20) shows where the "average" price has been over the last 20 days. If price is above SMA(200), the asset is in a long-term uptrend.

### Exponential Moving Average (EMA)
The EMA gives more weight to recent prices, so it reacts faster to new information than the SMA.

**Formula:**
```
Multiplier (k) = 2 / (n + 1)
EMA(t) = Close(t) * k + EMA(t-1) * (1 - k)
```

**Key insight:** The EMA "remembers" the entire history by compounding the previous EMA into the calculation, but recent bars have exponentially more influence.

### The Golden Cross & Death Cross
Two of the most famous candlestick patterns:
- **Golden Cross:** The 50-day SMA crosses above the 200-day SMA → **bullish signal**
- **Death Cross:** The 50-day SMA crosses below the 200-day SMA → **bearish signal**

In LECAT:
```
EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]
```
(The `[1]` looks one bar back to detect the exact moment of crossover.)

---

## 2.3 Relative Strength Index (RSI)

Developed by J. Welles Wilder in 1978, RSI measures the **speed and magnitude of recent price changes** to evaluate whether an asset is overbought or oversold.

**Formula:**
```
RS = Average Gain over N periods / Average Loss over N periods
RSI = 100 - (100 / (1 + RS))
```

**Interpretation:**
- RSI above **70** → Asset is **overbought** (may reverse down)
- RSI below **30** → Asset is **oversold** (may reverse up)
- RSI of 14 periods is the standard

**LECAT usage:**
```
RSI(14) < 30        # Oversold — potential buy signal
RSI(14) > 70        # Overbought — potential sell signal
```

---

## 2.4 Bollinger Bands

Developed by John Bollinger, Bollinger Bands add a statistical layer (standard deviation) around a moving average to create dynamic support/resistance levels.

**Three lines:**
```
Middle Band = SMA(n)
Upper Band  = SMA(n) + (k × Standard Deviation of Close over n periods)
Lower Band  = SMA(n) - (k × Standard Deviation of Close over n periods)
```

Standard parameters: n=20, k=2.0. This means approximately 95% of price action falls within the bands.

**What it tells you:**
- Price touching the **Upper Band** → Price is statistically "expensive" — potential reversal down
- Price touching the **Lower Band** → Price is statistically "cheap" — potential reversal up
- **Band squeeze** (bands narrowing) → Low volatility; a large move is coming

**LECAT usage:**
```
PRICE < BB_LOWER(20, 2.0)       # Price at lower statistical extreme
PRICE > BB_UPPER(20, 2.0)       # Price at upper statistical extreme
```

---

## 2.5 MACD (Moving Average Convergence Divergence)

MACD is a momentum indicator that shows the **relationship between two EMAs**.

**Components:**
```
MACD Line    = EMA(12) - EMA(26)
Signal Line  = EMA(9) of the MACD Line
Histogram    = MACD Line - Signal Line
```

**LECAT returns the Histogram value.**

**Interpretation:**
- Histogram above **0** → Momentum is positive (bullish)
- Histogram below **0** → Momentum is negative (bearish)
- Histogram crossing from negative to positive → Strong buy signal

**LECAT usage:**
```
MACD(12, 26, 9) > 0             # Positive momentum
```

---

## 2.6 Average True Range (ATR)

ATR measures **volatility** — how much an asset moves on average per bar.

**True Range (TR) = max of:**
- High − Low
- |High − Previous Close|
- |Low − Previous Close|

```
ATR(n) = Moving average of TR over n periods
```

**Real-world use:** Professional traders use ATR to set stop-losses dynamically. Instead of a fixed "$100 stop," they use "2 × ATR below entry" so the stop adjusts to current market volatility.

---

## 2.7 Stochastic Oscillator (%K and %D)

The Stochastic Oscillator measures where the current closing price sits relative to the high-low range over a recent period.

**Formula:**
```
%K = ((Close - Lowest Low) / (Highest High - Lowest Low)) × 100
%D = 3-period SMA of %K
```

- Values range from 0–100
- Above 80 → Overbought
- Below 20 → Oversold

**LECAT returns %D (the smoothed signal line):**
```
STOCH(14, 3) < 20               # Oversold by stochastic measure
```

---

# MODULE 3: PROGRAMMING THE RULES — DOMAIN SPECIFIC LANGUAGES (DSLs)

## 3.1 What Is a DSL?

A **Domain Specific Language (DSL)** is a computer language tailored to express problems in a specific domain, rather than being a general-purpose programming language like Python or Java.

**Examples in the real world:**
- **SQL** — A DSL for querying relational databases
- **HTML** — A DSL for describing web page structure
- **Regular Expressions** — A DSL for pattern matching in text
- **Excel Formulas** — A DSL for financial calculations

**Why use a DSL for trading rules?**
- A non-programmer can read and write `RSI(14) > 70 AND PRICE > SMA(50)` ✅
- That same person cannot read Python source code ❌
- The DSL acts as a safe, validated interface between human thought and code execution

---

## 3.2 LECAT's DSL Design

LECAT's language is specifically designed to express **boolean trading conditions** — rules that evaluate to TRUE (buy/hold) or FALSE (do nothing/sell).

**The grammar in plain English:**
- You can combine conditions with `AND` and `OR`
- You can negate conditions with `NOT`
- You can compare indicators to numbers or other indicators with `>`, `<`, `>=`, `<=`, `==`, `!=`
- You can call indicator functions like `RSI(14)` or `MACD(12, 26, 9)`
- You can look back in time with `[n]` offsets
- You can write literal numbers like `70` or `0.5`

**Full precedence (lowest to highest):**
1. `OR` — evaluated last
2. `AND`
3. `NOT`
4. Comparisons (`>`, `<`, etc.)
5. Unary negation (`-`)
6. Function calls and literals
7. `[]` offset — evaluated first

**Key safety property:** LECAT expressions cannot execute arbitrary code, access the filesystem, make network calls, or do anything harmful. They are completely sandboxed within the compiler pipeline.

---

# MODULE 4: COMPILER THEORY — HOW LECAT WORKS INTERNALLY

## 4.1 What Is a Compiler?

A compiler is a program that reads source code written in one language and transforms it into another form that can be executed. The classic example is a C compiler that turns human-readable C code into machine-executable binary. LECAT implements a **subset of compiler theory** to turn trading rule strings into executable evaluation logic.

**LECAT's pipeline:**
```
"RSI(14) > 70"
       │
       ▼
  [1] LEXER          → Breaks text into tokens: [ID, LPAREN, INT, RPAREN, GT, INT]
       │
       ▼
  [2] PARSER         → Builds a tree structure (the AST)
       │
       ▼
  [3] AST            → An in-memory tree representing the expression
       │
       ▼
  [4] EVALUATOR      → Walks the tree, calls indicator functions, computes a boolean
       │
       ▼
  True / False       → Binary signal for each bar
```

---

## 4.2 Stage 1: The Lexer (Tokenizer)

The Lexer's job is to scan the raw input string character-by-character and group characters into meaningful units called **tokens**.

**Example:**
```
Input string: "RSI(14) > 70 AND PRICE"

Tokens produced:
  [IDENTIFIER "RSI"]
  [LPAREN "("]
  [INTEGER 14]
  [RPAREN ")"]
  [GT ">"]
  [INTEGER 70]
  [AND "AND"]
  [IDENTIFIER "PRICE"]
```

The Lexer discards whitespace and comments, then classifies each token with a **token type** and a **value**.

**Token types in LECAT:**
- `IDENTIFIER` — a name like `RSI`, `PRICE`, `SMA`, `AND`
- `INTEGER` / `FLOAT` — numbers like `14`, `2.0`
- `LPAREN` / `RPAREN` — brackets `(` and `)`
- `LBRACKET` / `RBRACKET` — square brackets `[` and `]`
- `GT / LT / GTE / LTE / EQ / NEQ` — comparison operators
- `AND / OR / NOT` — boolean operators
- `EOF` — signals the end of input

If the Lexer finds a character it doesn't recognize, it raises a `LexerError` immediately.

---

## 4.3 Stage 2: The Parser (Syntax Analysis)

The Parser reads the token stream produced by the Lexer and builds an **Abstract Syntax Tree (AST)** — a hierarchical tree structure that encodes the meaning of the expression.

LECAT uses a technique called **Recursive Descent Parsing**, which is one of the most intuitive parsing algorithms. Each grammar rule (e.g., "an or_expression is made of one or more and_expressions joined by OR") directly corresponds to a function in the parser.

**Example:** How `RSI(14) > 70 AND PRICE > SMA(50)` becomes a tree:

```
        AND
       /   \
      >     >
     / \   / \
  RSI  70 PRICE SMA
  |              |
  14             50
```

The root node is `AND`. Its two children are the two comparison operations. Each comparison has its own left and right children.

**Operator Precedence is encoded by the grammar itself.** Because `AND` is at a higher level in the grammar than comparisons, comparisons are always evaluated before `AND`. This is how `1 + 2 * 3 = 7` (not 9) works in math — the grammar enforces that multiplication has higher precedence than addition.

---

## 4.4 Stage 3: The AST (Abstract Syntax Tree)

The AST is the output of the parser — a tree of **node objects**, each representing a piece of the expression. It is called "abstract" because it drops insignificant details like parentheses and whitespace from the source, keeping only the semantic structure.

**AST Node Types in LECAT:**

| Node | Fields | Represents |
|------|--------|----------|
| `BooleanOp` | `op` (AND/OR), `left`, `right` | `A AND B` |
| `NotOp` | `operand` | `NOT A` |
| `ComparisonOp` | `op` (>, <, etc.), `left`, `right` | `RSI(14) > 70` |
| `FunctionCall` | `name`, `args[]`, `offset` | `RSI(14)` or `RSI(14)[1]` |
| `Identifier` | `name`, `offset` | `PRICE` or `PRICE[2]` |
| `Literal` | `value` | `70`, `2.0`, `TRUE` |

**Key design principles:**
- **Immutability:** Once built, AST nodes cannot be changed. This prevents bugs where shared nodes are accidentally mutated.
- **Separation of concerns:** The Parser only builds the tree. The Evaluator only walks it. They don't know about each other's internals.

---

## 4.5 Stage 4: The Evaluator (Tree Walker)

The Evaluator performs a **recursive depth-first walk** of the AST, computing a result for each node bottom-up.

**How it works:**
1. Start at the root node
2. Recursively evaluate all child nodes first (depth-first)
3. Compute the current node's result using the children's results

**Evaluation of `RSI(14) > 70 AND PRICE > SMA(50)` at bar #100:**

```
evaluate(AND)
  → evaluate(ComparisonOp ">")
      → evaluate(FunctionCall "RSI", args=[14])
          → calls RSI handler → reads Close prices → returns 65.3
      → evaluate(Literal 70)
          → returns 70.0
      → 65.3 > 70.0 = FALSE
  → evaluate(ComparisonOp ">")
      ... (similar)
  → FALSE AND ... = FALSE   ← AND short-circuits!
```

**Short-circuit evaluation:** Like most languages, LECAT's `AND` stops as soon as the LEFT side is `FALSE`, because the whole expression must be `FALSE` regardless of the right side. This saves compute time.

**Error propagation:** If an indicator returns `InsufficientData` (e.g., asking for `SMA(200)` when only 50 bars exist), the evaluator propagates this as a `NaN`-like sentinel value and the bar is skipped rather than causing a crash.

---

## 4.6 Stage 5: The Function Registry (Plugin Architecture)

The Evaluator doesn't hardcode any indicator logic. Instead, it looks up function names at runtime in the **Function Registry** — a dictionary that maps indicator names to handler functions.

**The Registry Pattern** is a classic software design pattern:
- A central map: `"RSI"` → `rsi_handler_function`
- Anyone can register new entries at startup
- The Evaluator only needs to know the name→handler contract

**LECAT's three-tier Registry:**
1. **Built-in Standard Library:** SMA, EMA, RSI, ATR — registered at startup from `std_lib.py`
2. **Extended Indicators:** MACD, Bollinger Bands, Stochastic — registered from `indicators.py`
3. **Python Plugins:** Any `.py` file in `lecat_plugins/` is auto-discovered and its indicators are registered via `plugin_loader.py`
4. **Database Indicators:** Custom composite indicators stored in SQLite are loaded by `dynamic_registry.py` and compiled/evaluated on the fly using the same pipeline

**The `FunctionResult` contract:**
Every registered handler must return a `FunctionResult` with one of three states:
- `success(value: float)` — Indicator computed successfully
- `insufficient_data()` — Not enough historical bars yet
- `from_error(message: str)` — Something went wrong

---

# MODULE 5: BACKTESTING — MEASURING STRATEGIES AGAINST HISTORY

## 5.1 What Is Backtesting?

Backtesting is the process of testing a trading strategy on **historical market data** to see how it would have performed. The core assumption is: "If it worked in the past, it has some evidence of edge in the future."

**The backtesting loop:**
```
For each bar from start to end:
  1. Evaluate the strategy expression → True or False
  2. If True AND not in position → ENTER (buy at next open)
  3. If False AND in position → EXIT (sell at next open)
  4. Record the trade and its profit/loss
```

**Important caveat — Look-Ahead Bias:** When backtesting, you must never use future data to make a decision about the past. Using tomorrow's Close to decide whether to buy today is cheating — the market hasn't closed tomorrow yet. LECAT's `MarketContext` enforces this by only exposing data up to the current bar index.

---

## 5.2 Key Performance Metrics

After backtesting a strategy, several statistics are computed:

### Total Return
```
Return = (Final Portfolio Value / Initial Portfolio Value - 1) × 100%
```
The simplest metric — but dangerous alone. A 1000% return that came from one lucky trade or required 90% drawdown is not a good strategy.

### Sharpe Ratio
The Sharpe Ratio measures **risk-adjusted return** — how much return are you getting per unit of risk?

```
Sharpe Ratio = (Mean Daily Return - Risk Free Rate) / Standard Deviation of Daily Returns × √252
```

(252 = approximate number of trading days per year)

**Interpretation:**
- Sharpe < 0 → Strategy loses money on average
- Sharpe 0–1 → Mediocre
- Sharpe 1–2 → Good
- Sharpe > 2 → Excellent (rare in live trading)

### Maximum Drawdown
```
Drawdown = (Peak Portfolio Value - Trough Portfolio Value) / Peak Portfolio Value × 100%
```

This is the largest peak-to-trough decline in portfolio value. A strategy with 50% max drawdown means at some point in history your portfolio lost half its value before recovering. This is a key risk metric — many traders focus on minimizing drawdown as much as maximizing return.

### Win Rate
```
Win Rate = (Number of Profitable Trades / Total Trades) × 100%
```

**Important:** A high win rate alone doesn't mean a good strategy. You could win 90% of trades but lose so much on the 10% of losing trades that you're unprofitable overall. Win rate must be considered with the **Profit Factor** (average win / average loss).

---

## 5.3 Walk-Forward Validation (Preventing Overfitting)

**Overfitting** is the number one enemy of backtested strategies. A strategy can be tuned to produce incredible returns on historical data by memorizing the specific sequence of past events — but then fails completely on new data because it has no predictive power.

**The solution:** Walk-Forward Validation (a.k.a. out-of-sample testing)

```
Total Dataset: [=============================]
                  ↑                     ↑
              Training Set          Test Set
           (In-sample)          (Out-of-sample)
           [=================][================]
```

**The process:**
1. Split data into a **Training Set** (e.g., 70%) and a **Test Set** (e.g., 30%)
2. Evolve/optimize the strategy using ONLY the Training Set
3. Forward-test the best strategy on the Test Set (data it has never seen)
4. Compare the two results

**The Overfit Ratio:**
```
Overfit Ratio = Test Sharpe / Train Sharpe
```
- Ratio near 1.0 → Strategy generalizes well (not overfit)
- Ratio near 0.0 → Strategy memorized training data (overfit)

---

# MODULE 6: GENETIC ALGORITHMS — EVOLVING BETTER STRATEGIES

## 6.1 The Problem: Infinite Search Space

How do you find the optimal trading strategy when the number of possible strategy expressions is effectively infinite? You can't try every combination — there are too many.

**Enter Metaheuristics:** A class of optimization algorithms that don't guarantee the perfect solution, but find very good solutions in reasonable time by intelligently exploring the search space.

---

## 6.2 What Is a Genetic Algorithm?

Genetic Algorithms (GAs) are a family of optimization algorithms **inspired by biological evolution**. The key insight from Darwin: in a competitive environment, fit individuals survive and reproduce, passing on their traits; unfit individuals die. Over generations, the population evolves toward better fitness.

**Mapping to trading:**
| Biology | LECAT |
|---------|-------|
| Individual | A single trading strategy (expression string) |
| Population | A collection of N strategies |
| Fitness | The Sharpe Ratio of the backtested strategy |
| Genes | The AST nodes and indicator parameters |
| Selection | Pick the fittest strategies to reproduce |
| Crossover | Combine two strategies to make new ones |
| Mutation | Randomly modify parts of a strategy |
| Generation | One round of selection + reproduction |

---

## 6.3 The Genetic Algorithm Loop in Detail

```
1. INITIALIZE: Generate a random population of N strategy expressions
        │
        ▼
2. EVALUATE: Backtest every strategy, compute fitness (Sharpe Ratio)
        │
        ▼
3. SELECT: Tournament selection — pick pairs of random strategies,
           the fitter one wins and advances to reproduce
        │
        ▼
4. CROSSOVER: Randomly swap subtrees between two parent ASTs
              to create two child ASTs (recombination)
        │
        ▼
5. MUTATE: With some probability P, randomly modify part of the
           child AST (change a parameter, swap an operator, etc.)
        │
        ▼
6. REPLACE: Form the new population from the children
            (keeping the top few parents unchanged — "elitism")
        │
        ▼
7. REPEAT: Go to step 2. Stop after N generations or when
           the fitness plateau.
        │
        ▼
RESULT: The Hall of Fame — the all-time best strategies found
```

---

## 6.4 Tournament Selection

Instead of selecting the single best individual (which would converge too fast and get stuck in local optima), LECAT uses **Tournament Selection**:

1. Randomly pick `k` individuals from the population (tournament size)
2. The individual with the highest fitness wins
3. Repeat to select the breeding pool

**Why tournaments?** They provide selection pressure (better individuals win more often) while maintaining diversity (even mediocre individuals occasionally win).

---

## 6.5 Crossover (Recombination)

Crossover mixes the genetic material of two parents to create offspring. LECAT implements **subtree crossover** at the AST level:

1. Pick two parent expressions (ASTs)
2. Randomly select a subtree from Parent 1
3. Randomly select a compatible subtree from Parent 2
4. Swap them

**Example:**
```
Parent 1: RSI(14) > 70  AND  PRICE > SMA(50)
Parent 2: EMA(10) > EMA(50)  AND  MACD(12,26,9) > 0

                    ↓ swap right subtrees ↓

Child 1:  RSI(14) > 70  AND  MACD(12,26,9) > 0    ← new combination!
Child 2:  EMA(10) > EMA(50)  AND  PRICE > SMA(50)  ← new combination!
```

---

## 6.6 Mutation

Mutation introduces random variation into the offspring, preventing premature convergence where the population becomes too similar ("genetic drift").

**Types of mutations in LECAT:**
- **Parameter mutation:** Change a number (e.g., `RSI(14)` → `RSI(21)`)
- **Operator mutation:** Swap a comparison (e.g., `>` → `>=`)
- **Subtree replacement:** Replace an entire subtree with a randomly generated one
- **Boolean operator mutation:** Swap `AND` ↔ `OR`

Mutation probability is a hyperparameter — typically 5–20%. Too low: the population converges. Too high: the algorithm degenerates into random search.

---

## 6.7 Elitism

A small number of the best individuals from each generation are **copied unchanged** into the next generation. This guarantees that the all-time best solution found is never lost due to random mutation.

---

# MODULE 7: DATA ENGINEERING & PERSISTENCE

## 7.1 Data Loading and Normalization

LECAT ingests financial data from CSV files conforming to a standard OHLCV schema:
```
date,open,high,low,close,volume
2024-01-01,44000,46000,43500,45500,12400
2024-01-02,45500,46800,45000,46200,9800
...
```

The data loader validates columns, handles missing values, and converts types. The data is then stored in a `MarketContext` object which wraps the raw arrays and exposes a controlled interface to the evaluator.

---

## 7.2 SQLite — The Right Database for a Desktop App

LECAT uses **SQLite** for persistence. SQLite is a **serverless, embedded, file-based relational database**. Unlike PostgreSQL or MySQL, there is no server to install — the entire database is a single `.db` file.

**Why SQLite is perfect for LECAT:**
1. Zero configuration — just a file path
2. Full SQL support — complex queries, transactions, indexes
3. ACID compliant — data is never corrupted by crashes or power loss
4. Cross-platform — the same `.db` file works on Windows, Mac, and Linux
5. Performant for single-user desktop apps (LECAT's use case)

**LECAT's database schema (3 tables):**

```sql
market_data      → Stores OHLCV bars per symbol and timeframe
indicators       → Stores custom composite indicator definitions
strategy_results → Stores the backtest results of evolved strategies
```

**The Repository Pattern:** LECAT wraps all SQLite operations in a `Repository` class. The rest of the application never writes SQL directly — it calls clean Python methods like `repo.save_market_data(rows, symbol)` or `repo.get_all_indicators()`. This keeps the database logic in one place and makes it easy to swap the database engine in the future.

---

## 7.3 The Dynamic Registry: DB-Backed Indicators

Custom indicators created through the UI are stored in the `indicators` table as:
- A name (`MY_CROSS`)
- A list of argument names (`["fast", "slow"]`)
- A formula (`SMA(fast) > SMA(slow)`)

When the application starts, the `DynamicRegistry` loads these records from SQLite and registers live handler functions that:
1. Accept the user's argument values at evaluation time
2. Substitute them into the formula string (e.g., `SMA(10) > SMA(50)`)
3. Run the full Lexer → Parser → Evaluator pipeline on the substituted formula
4. Return the result

This is a form of **meta-evaluation** — the interpreter interpreting itself — and enables a fully dynamic, no-code indicator definition experience.

---

# MODULE 8: PYTHON PLUGIN SYSTEM

## 8.1 When the DSL Isn't Enough

For truly complex math — logarithmic returns, N-period rolling standard deviation, volatility surface calculations — a text-based DSL grammar would become impossibly complex to maintain. Instead, LECAT provides a **Python Plugin System** that bridges the gap between user-defined native Python math and the DSL evaluation engine.

## 8.2 How It Works

1. Create a `.py` file in the `lecat_plugins/` folder
2. Define a `register_plugin(registry)` function in it
3. Use `@registry.register(name=..., ...)` to register handlers
4. At app startup, `plugin_loader.py` scans the folder using Python's `importlib` and executes each file

The plugin handler has the same interface as built-in indicators (`args` + `ctx`), so the evaluator doesn't know or care whether it's calling a built-in or a plugin.

**Security model:** Plugins are Python files written by developers and committed to the project. They are NOT user input from the UI — they are not stored in the database and not accepted from untrusted sources. This is the key distinction that makes this approach safe.

---

# MODULE 9: DESKTOP DEPLOYMENT — PACKAGING FOR END USERS

## 9.1 The Challenge: Distributing Python Applications

Python is an interpreted language — you need the Python runtime, the correct version, and all the installed packages to run a Python program. This is fine for developers but terrible for end users.

**Solution: PyInstaller.** PyInstaller freezes a Python application and all its dependencies into a single standalone folder. The user doesn't need Python installed.

## 9.2 How PyInstaller Works (Conceptually)

1. **Dependency analysis:** Starting from the entry point (`run_desktop.py`), PyInstaller traces all `import` statements to find every module the application uses
2. **Collection:** All Python source files, extension modules (`.so`/`.dll`), and data files are gathered
3. **Packaging:** Everything is zipped into a bundle with a custom Python interpreter included
4. **Bootstrap:** A native launcher stub (`LECAT_Trader.exe`) extracts the bundle to a temp folder and starts the embedded Python interpreter

## 9.3 The Desktop App Architecture

```
User double-clicks LECAT_Trader
        │
        ▼
run_desktop.py starts
        │
        ▼
subprocess.Popen launches Streamlit server on port 8501
        │
        ▼
webbrowser.open("http://localhost:8501") opens the UI
        │
        ▼
User interacts with the browser-based dashboard
        │
        ▼
User closes the terminal window
        │
        ▼
process.terminate() gracefully kills the Streamlit server
```

## 9.4 Data Persistence in Packaged Apps

A critical engineering challenge: PyInstaller extracts the bundle to a temporary folder (`_MEIxxxxxx`) that is **deleted on exit**. Any data written there is permanently lost.

**Fix:** Detect when running in a packaged context (`sys.frozen == True`) and redirect all writes to the user's permanent home directory:
```python
if getattr(sys, "frozen", False):
    DEFAULT_DB_PATH = Path.home() / ".lecat" / "lecat.db"
else:
    DEFAULT_DB_PATH = Path(__file__).parent.parent / "lecat.db"
```

## 9.5 CI/CD with GitHub Actions

**Continuous Integration / Continuous Delivery (CI/CD)** automates the build and release process. LECAT uses GitHub Actions — a cloud-based automation platform built directly into GitHub — to:

1. Detect when a new version tag is pushed (`v2.1.0`, `v2.1.1`, etc.)
2. Spin up both a Windows and a macOS virtual machine
3. Install Python and all dependencies on each
4. Run PyInstaller to build the executable
5. Zip the output folder
6. Attach both `.zip` files to a new GitHub Release automatically

This means releasing a new version of LECAT for both Windows and Mac requires exactly **one command** from the developer:
```bash
git tag v2.2.0 && git push origin v2.2.0
```

---

# MODULE 10: PUTTING IT ALL TOGETHER — THE LECAT JOURNEY

## End-to-End Walkthrough

Let's follow one user session to tie all modules together:

### Step 1: Data Ingestion
The user uploads a CSV file of Bitcoin daily OHLCV data. The data loader validates and normalizes it. The user clicks "Save to Database." The Repository writes 1,825 rows to the `market_data` SQLite table.

### Step 2: Strategy Testing
The user types `RSI(14) < 30 AND PRICE < BB_LOWER(20, 2.0)` in the Strategy Lab. They click Run.
- The **Lexer** tokenizes the string
- The **Parser** builds an AST with an `AND` node at the root
- The **Evaluator** walks the AST bar-by-bar for all 1,825 days, calling the RSI and BB_LOWER handlers, which read from the `MarketContext`
- The **Backtester** detects buy signals (TRUE), enters positions, detects exits, and calculates P&L
- Metrics are computed: Return=47%, Sharpe=1.8, Drawdown=12%, Win Rate=58%

### Step 3: Genetic Optimization
The user opens the Evolution Engine tab and runs 20 generations with 100 strategies. The GA:
1. Generates 100 random strategy expressions
2. Backtests all 100 (using multi-core parallel evaluation)
3. Runs tournament selection
4. Performs subtree crossover and parameter mutation
5. Repeats for 20 generations
6. The best 10 strategies are saved to the Hall of Fame (SQLite `strategy_results` table)

### Step 4: Custom Plugin
The user writes a `LOG_RETURN` indicator as a Python plugin in `lecat_plugins/`. On the next app restart, it is auto-discovered and available. They test `LOG_RETURN(5) > 2.0` in the Strategy Lab.

### Step 5: Distribution
The team decides to release. They commit the code, push a `v2.1.1` tag. GitHub Actions:
1. Builds `LECAT_Trader.exe` on a Windows virtual machine
2. Builds `LECAT_Trader` (macOS app) on a Mac virtual machine
3. Publishes both as downloadable files on the GitHub Releases page
4. Team members across the world download and run the app with a double-click — no Python, no terminal, no configuration.

---

# KEY CONCEPTS GLOSSARY

| Term | Definition |
|------|------------|
| **OHLCV** | Open, High, Low, Close, Volume — the five data points describing each market bar |
| **DSL** | Domain Specific Language — a specialized programming language for a narrow problem domain |
| **Token** | A single meaningful unit produced by the Lexer (e.g., a number, a keyword, an operator) |
| **AST** | Abstract Syntax Tree — a tree structure encoding the meaning of an expression |
| **Recursive Descent** | A parsing technique where each grammar rule maps to a recursive function |
| **Evaluator** | The component that walks an AST and computes its result for a given market bar |
| **Function Registry** | A name→handler dictionary enabling plugin-style indicator extension |
| **Backtesting** | Testing a strategy on historical data to estimate performance |
| **Overfitting** | When a strategy is tuned to past data and fails on new data |
| **Walk-Forward** | Train on one period, test on another — the gold standard for validation |
| **Sharpe Ratio** | Return divided by volatility — measures risk-adjusted performance |
| **Max Drawdown** | Largest peak-to-trough decline — measures downside risk |
| **Genetic Algorithm** | Evolutionary optimization inspired by natural selection |
| **Crossover** | Combining parts of two parent expressions to form a child |
| **Mutation** | Randomly modifying part of an expression to introduce diversity |
| **Elitism** | Preserving the best individuals unchanged across generations |
| **SQLite** | A serverless, embedded, file-based SQL database |
| **Repository Pattern** | Centralizing all data access logic in a single class |
| **PyInstaller** | A tool that packages Python apps into standalone executables |
| **CI/CD** | Continuous Integration / Delivery — automating build, test, and release |
| **Look-Ahead Bias** | The error of using future data to make past decisions in a backtest |
| **Python Plugin** | A `.py` file auto-loaded at startup to register new indicators |

---

# MODULE 11: THEORY IN PRACTICE — WHERE EVERY CONCEPT LIVES IN LECAT

This module is a cross-reference guide that connects every theoretical concept directly to the application feature where it is implemented, the file it lives in, and the dashboard tab where users interact with it.

---

## 11.1 Data Layer — Where Markets Meet the App

| Theory Concept | LECAT Feature | Files Involved | Dashboard Interaction |
|---|---|---|---|
| OHLCV bars | Market data ingestion | `lecat/data_loader.py` | Sidebar → Upload CSV or select from Database |
| Data normalization | Type checking, missing-value handling | `lecat/data_loader.py` | Upload feedback message shown in sidebar |
| SQLite persistence | Save/load datasets across sessions | `lecat/repository.py`, `lecat/data/schema.sql` | "Save to database" checkbox on CSV upload |
| `MarketContext` (look-ahead prevention) | Exposes only past data to the evaluator | `lecat/context.py` | Invisible to the user — enforced automatically |

---

## 11.2 The Compiler Pipeline — Turning Words Into Logic

| Theory Concept | LECAT Feature | Files Involved | Dashboard Interaction |
|---|---|---|---|
| DSL grammar design | The LECAT expression language | `docs/01_Grammar_Specification.md` | Strategy text box in Strategy Lab |
| Lexer (tokenizer) | Breaks typed text into tokens | `lecat/lexer.py` | Behind "▶ Run Strategy" button |
| Recursive descent parser | Builds the syntax tree | `lecat/parser.py` | Behind "▶ Run Strategy" button |
| AST nodes | In-memory strategy representation | `lecat/ast_nodes.py` | Invisible — used by evaluator |
| Evaluator (tree walker) | Computes TRUE/FALSE per bar | `lecat/evaluator.py` | Generates buy/sell signals on chart |
| Short-circuit evaluation | `AND`/`OR` skip unnecessary branches | `lecat/evaluator.py` | Performance — keeps backtests fast |
| Error propagation / InsufficientData | Skips bars where indicators can't compute | `lecat/evaluator.py`, `lecat/registry.py` | "⚠️ Insufficient data" warning on chart |
| Operator precedence | `AND` before `OR`, comparisons first | `lecat/parser.py` | Enforced silently — no parentheses needed for simple rules |

---

## 11.3 Indicators — Built-in, DB, and Plugin

| Theory Concept | LECAT Feature | Files / Location | Dashboard Interaction |
|---|---|---|---|
| Function Registry pattern | Name→handler lookup map | `lecat/registry.py` | All indicator calls in any expression |
| Built-in indicators (SMA, EMA, RSI, ATR) | Standard library handlers | `lecat/std_lib.py` | Available in all expression boxes |
| Extended indicators (MACD, BB, STOCH) | Plugin-style registration | `lecat/indicators.py` | Available in all expression boxes |
| DSL composite indicators (DB-backed) | User-defined via Indicator Manager | `lecat/dynamic_registry.py`, `lecat/repository.py` | **🛠️ Indicator Manager** tab |
| Python plugin indicators (complex math) | Auto-discovered from `lecat_plugins/` | `lecat/plugin_loader.py`, `lecat_plugins/math_utils.py` | Appear automatically in **📚 Function Reference** tab |
| `FunctionResult` contract | Standardized success/error return | `lecat/registry.py` | Error messages shown in Strategy Lab on failure |
| Circular reference detection | Guards composite indicators calling each other | `lecat/dynamic_registry.py` | "Circular reference detected" error message |

---

## 11.4 Backtesting — Measuring History

| Theory Concept | LECAT Feature | Files Involved | Dashboard Interaction |
|---|---|---|---|
| Time-loop backtesting | Bar-by-bar signal evaluation | `lecat/backtester.py` | Triggered by "▶ Run Strategy" |
| Entry/exit logic | Buy on TRUE, sell on FALSE | `lecat/backtester.py` | Green ▲ / Red ▼ markers on candlestick chart |
| Total Return | Portfolio % change over period | `lecat/fitness.py` | **Return** metric card in Strategy Lab |
| Sharpe Ratio | Risk-adjusted return score | `lecat/fitness.py` | **Sharpe** metric card in Strategy Lab |
| Maximum Drawdown | Largest peak-to-trough loss | `lecat/fitness.py` | **Drawdown** metric card in Strategy Lab |
| Win Rate | % of profitable trades | `lecat/fitness.py` | **Win Rate** metric card in Strategy Lab |
| Walk-Forward Validation | Train on 70%, test on 30% | `lecat/optimizer.py`, `lecat/context.py` | Train/Test Split slider in Evolution Engine |
| Overfit Ratio | Test Sharpe ÷ Train Sharpe | `lecat/fitness.py` | **Overfit** metric on Hall of Fame rows |
| Look-Ahead Bias prevention | `bar_index` boundary enforcement | `lecat/context.py` | Not visible — enforced by design |
| Strategy JSON export | Save a strategy and its metrics to disk | `lecat/exporter.py` | **⬇ Download JSON** button in Strategy Lab |

---

## 11.5 Genetic Algorithm — Evolving Strategies

| Theory Concept | LECAT Feature | Files Involved | Dashboard Interaction |
|---|---|---|---|
| Population initialization | Random valid expression generation | `lecat/generator.py` | "Population Size" slider in Evolution Engine |
| Fitness evaluation | Sharpe Ratio per strategy | `lecat/fitness.py` | Runs automatically each generation |
| Tournament selection | Picks parents for reproduction | `lecat/evolution.py` | "Tournament Size" parameter |
| Subtree crossover | Swaps AST sub-branches between parents | `lecat/evolution.py` | Happens automatically during optimization |
| Mutation | Random changes to parameters, operators, subtrees | `lecat/evolution.py` | "Mutation Rate" slider in Evolution Engine |
| Elitism | Top N individuals kept unchanged | `lecat/optimizer.py` | Implicit — best strategies always preserved |
| Hall of Fame | All-time best strategies across all generations | `lecat/optimizer.py` | **Hall of Fame** table in Evolution Engine tab |
| Parallel backtesting | Multi-core evaluation of population | `lecat/parallel.py` | "Cores" setting — speeds up each generation |
| Walk-forward in optimization | GA only sees training data | `lecat/optimizer.py` | Train/Test Split applied before GA starts |
| Strategy persistence | Save Hall of Fame results to DB | `lecat/repository.py` | Automatically saved; viewable in Results tab |

---

## 11.6 Data Persistence — SQLite in Action

| Theory Concept | LECAT Feature | Files Involved | Dashboard Interaction |
|---|---|---|---|
| SQLite embedded database | Single `.lecat/lecat.db` file per user | `lecat/repository.py`, `lecat/data/schema.sql` | Invisible — auto-created on first run |
| `market_data` table | Stores uploaded OHLCV datasets | `lecat/repository.py` | Sidebar → "Database" data source |
| `indicators` table | Stores custom indicator definitions | `lecat/repository.py` | **🛠️ Indicator Manager** tab |
| `strategy_results` table | Stores backtest results | `lecat/repository.py` | **📊 Results** tab |
| Repository pattern | Single class owns all DB calls | `lecat/repository.py` | Invisible abstraction |
| WAL journal mode | Prevents DB corruption on crash | `lecat/repository.py` | `PRAGMA journal_mode=WAL` set at connect time |
| Dynamic Indicator loading | DB indicators registered as live handlers | `lecat/dynamic_registry.py` | Custom indicators available in expression box |

---

## 11.7 Python Plugin System — Extending LECAT

| Theory Concept | LECAT Feature | Files Involved | Dashboard Interaction |
|---|---|---|---|
| `importlib` dynamic module loading | Auto-discovers `.py` files from a folder | `lecat/plugin_loader.py` | Happens at app startup |
| `register_plugin(registry)` contract | Entry point every plugin must implement | `lecat_plugins/math_utils.py` | Developer API — not a UI feature |
| HALF_SMA plugin | SMA divided by 2 (native Python) | `lecat_plugins/math_utils.py` | Visible in **📚 Function Reference** tab |
| LOG_RETURN plugin | Logarithmic return % over N periods | `lecat_plugins/math_utils.py` | Visible in **📚 Function Reference** tab |
| Security model | Plugins are source-controlled, not from DB | `lecat/plugin_loader.py` | Trusted developer code only |

---

## 11.8 Desktop Packaging & Release Engineering

| Theory Concept | LECAT Feature | Files Involved | User Impact |
|---|---|---|---|
| PyInstaller frozen bundle | Embeds Python + all deps into one folder | `lecat.spec` | Creates the downloadable `.zip` |
| `sys.frozen` detection | Routes data to `~/.lecat/` when packaged | `lecat/repository.py`, `lecat/logger.py` | Users don't lose data on app close |
| Bootstrapper script | Starts Streamlit & opens browser automatically | `run_desktop.py` | One double-click to launch |
| GitHub Actions CI/CD | Automatic Windows + macOS build on tag push | `.github/workflows/build_release.yml` | Developer releases in seconds |
| GitHub Releases | Downloadable `.zip` files per OS | GitHub platform | End users find and download the app |

---

## 11.9 Dashboard Tabs — Where It All Comes Together

| Dashboard Tab | Core Theory Concepts Demonstrated |
|---|---|
| **🔬 Strategy Lab** | DSL grammar, full compiler pipeline (Lexer→Parser→AST→Evaluator), backtesting, all performance metrics, equity curve charting |
| **🧬 Evolution Engine** | Genetic algorithm (population, selection, crossover, mutation, elitism), walk-forward validation, parallel evaluation, Hall of Fame |
| **🛠️ Indicator Manager** | DSL composite indicators, dynamic registry, SQLite persistence, meta-evaluation (interpreter within interpreter) |
| **📚 Function Reference** | Function Registry pattern, all built-in indicators, Python plugin indicators, indicator argument schemas |
| **📊 Results** | Strategy persistence, historical backtest comparison, SQLite queries |

---

# KEY CONCEPTS GLOSSARY

| Term | Definition |
|------|------------|
| **OHLCV** | Open, High, Low, Close, Volume — the five data points describing each market bar |
| **DSL** | Domain Specific Language — a specialized programming language for a narrow problem domain |
| **Token** | A single meaningful unit produced by the Lexer (e.g., a number, a keyword, an operator) |
| **AST** | Abstract Syntax Tree — a tree structure encoding the meaning of an expression |
| **Recursive Descent** | A parsing technique where each grammar rule maps to a recursive function |
| **Evaluator** | The component that walks an AST and computes its result for a given market bar |
| **Function Registry** | A name→handler dictionary enabling plugin-style indicator extension |
| **Backtesting** | Testing a strategy on historical data to estimate performance |
| **Overfitting** | When a strategy is tuned to past data and fails on new data |
| **Walk-Forward** | Train on one period, test on another — the gold standard for validation |
| **Sharpe Ratio** | Return divided by volatility — measures risk-adjusted performance |
| **Max Drawdown** | Largest peak-to-trough decline — measures downside risk |
| **Genetic Algorithm** | Evolutionary optimization inspired by natural selection |
| **Crossover** | Combining parts of two parent expressions to form a child |
| **Mutation** | Randomly modifying part of an expression to introduce diversity |
| **Elitism** | Preserving the best individuals unchanged across generations |
| **SQLite** | A serverless, embedded, file-based SQL database |
| **Repository Pattern** | Centralizing all data access logic in a single class |
| **PyInstaller** | A tool that packages Python apps into standalone executables |
| **CI/CD** | Continuous Integration / Delivery — automating build, test, and release |
| **Look-Ahead Bias** | The error of using future data to make past decisions in a backtest |
| **Python Plugin** | A `.py` file auto-loaded at startup to register new indicators |

---

*Document version: aligned with LECAT v2.1.1 — March 2026*
*This document is structured for zero-to-hero progression: from finance basics through compiler theory, machine learning, data engineering, and deployment automation. Every concept is bridged to its concrete LECAT feature in Module 11.*
