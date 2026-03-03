# F. Operations Manual

**Parent Document:** [Overview](./00_Overview.md)

---

## 1. Getting Started

### 1.1 What is LECAT?

LECAT (**L**ogical **E**xpression **C**ompiler for **A**lgorithmic **T**rading) is a system that lets you write simple trading rules in plain English-like syntax, test them against market data, and automatically discover profitable strategies using a genetic algorithm.

**Example:** Instead of writing complex code, you write:
```
RSI(14) > 70 AND PRICE > SMA(50)
```
This means: *"Buy when RSI is above 70 AND the price is above the 50-period Simple Moving Average."*

### 1.2 System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.9+ | 3.12+ |
| RAM | 2 GB | 8 GB |
| CPU Cores | 1 | 4+ (for parallel optimization) |
| Disk | 50 MB | 200 MB (for logs and saved strategies) |
| OS | macOS, Linux, Windows | Any |

### 1.3 Installation (Step-by-Step)

**Step 1:** Clone the repository
```bash
git clone <repository-url>
cd stockstats-lecat
```

**Step 2:** Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows
```

**Step 3:** Install dependencies

*Option A — Using requirements.txt:*
```bash
pip install -r requirements.txt
```

*Option B — Using pip install (includes the `lecat` CLI command):*
```bash
pip install -e ".[all]"     # Install with all optional dependencies
# or
pip install -e ".[all,dev]" # Also include dev tools (pytest, black, isort)
```

*Option C — Using the Makefile:*
```bash
make install       # Same as pip install -r requirements.txt
make install-dev   # Same as pip install -e ".[all,dev]"
```

**Step 4:** Verify the installation
```bash
python3 -m unittest discover -s tests -v    # or: make test
```
You should see `Ran 235 tests ... OK`.

**Step 5:** Launch the dashboard
```bash
streamlit run lecat/dashboard/app.py    # or: make run
```
Open your browser to `http://localhost:8501`.

---

## 2. Using the Web Dashboard

The dashboard is the primary way to interact with LECAT. It has three tabs.

### 2.1 Getting Data Into the System

**Option A: Generate Random Data** (for testing/learning)
1. In the sidebar, select **"Generate Random"**
2. Choose the number of bars (1000 is a good start)
3. Set a random seed (42 is fine) for reproducible results

**Option B: Upload Your Own CSV**
1. In the sidebar, select **"Upload CSV"**
2. Click **"Browse files"** and select your CSV file
3. Your CSV must have these columns:

```csv
Date,Open,High,Low,Close,Volume
2024-01-01,100.00,110.00,90.00,105.00,1000
2024-01-02,105.00,115.00,95.00,110.00,1200
```

> **Flexible headers:** The system accepts many common column name formats:
> `open`, `Open`, `o` | `high`, `High`, `h` | `low`, `Low`, `l` | `close`, `Close`, `c`, `Adj Close` | `volume`, `Volume`, `vol`, `v`

> **Missing values** are automatically forward-filled (the previous bar's value is used).

### 2.2 Strategy Lab (Tab 1) — Testing Your Ideas

This is where you manually type a trading rule and see how it performs.

**Step 1: Write your strategy**

Type a LECAT expression in the text box. Here are some examples to try:

| Strategy | What It Does |
|----------|-------------|
| `RSI(14) > 70` | Signal when RSI indicates overbought |
| `PRICE > SMA(50)` | Signal when price is above 50-bar average |
| `MACD(12, 26, 9) > 0` | Signal when MACD histogram is positive |
| `PRICE > BB_UPPER(20, 2.0)` | Signal on Bollinger Band breakout |
| `EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]` | EMA crossover (current cross above) |
| `RSI(14) < 30 AND STOCH(14, 3) < 20` | Combined oversold condition |

Or use the **Quick Presets** buttons on the right side.

**Step 2: Click "Run Backtest"**

You'll see:
- **Metrics row** — Total Return, Sharpe Ratio, Win Rate, # Trades, Max Drawdown, Fitness Score
- **Interactive chart** — Candlestick with green triangle markers where your strategy signals True. Use your mouse to zoom, pan, and hover for exact values.
- **Download button** — Save your strategy as a JSON file for later use

**Step 3: Iterate**

Change the expression and click Run again. Compare metrics to find what works.

**Loading a saved strategy:**
1. Scroll below the presets to find **"📁 Upload Strategy JSON"**
2. Upload a previously downloaded `.json` file
3. The expression will auto-populate and you can run it immediately

### 2.3 Evolution Engine (Tab 2) — Automatic Strategy Discovery

This is where LECAT's genetic algorithm creates and evolves strategies automatically.

**Step 1: Configure the parameters**

| Parameter | What It Controls | Recommended Start |
|-----------|-----------------|-------------------|
| **Generations** | How many evolution cycles to run | 5–10 |
| **Population Size** | How many strategies per generation | 50–100 |
| **Mutation Rate** | Probability of random changes (0.0–1.0) | 0.2–0.4 |
| **Train/Test Split** | How much data to use for training vs validation | 0.7 (70% train) |

> **Train/Test Split explained:** If you have 1000 bars and set split to 0.7, the optimizer trains on the first 700 bars and validates the best strategy on the last 300 bars. This prevents overfitting — a strategy that only works on historical data it was trained on.

**Step 2: Click "🧬 Start Evolution"**

The optimizer will:
1. Generate random strategies
2. Test each one via backtesting
3. Keep the best performers (elitism)
4. Create new strategies by combining and mutating the best ones
5. Repeat for N generations

A progress indicator shows the current status.

**Step 3: Review the Hall of Fame**

After completion, you'll see:
- **Walk-forward metrics** — Train Sharpe, Test Sharpe, and Overfit Ratio
  - 🟢 Overfit Ratio > 0.7 = strategy generalizes well
  - 🔴 Overfit Ratio < 0.7 = may be overfit to training data
- **Leaderboard table** — Top strategies ranked by fitness
- **Visualization** — Select any strategy and click "Show Chart" to see it in action
- **Download** — Save the best strategy as JSON for deployment or sharing

### 2.4 Function Reference (Tab 3)

Lists all available functions with their argument types and default values.

### 2.5 Settings (Sidebar)

| Setting | Description | Default |
|---------|-------------|---------|
| Initial Capital | Starting capital for backtest calculations | $10,000 |

---

## 3. Command Line Interface (CLI)

For users who prefer the terminal or want to automate runs.

### 3.1 Simple Backtest Mode

Generate random strategies and test them:

```bash
# Default: 10 strategies, 1000 bars
python3 -m lecat.main

# Custom parameters
python3 -m lecat.main --strategies 20 --bars 5000 --depth 3 --seed 42
```

### 3.2 Optimizer Mode

Run the genetic algorithm from the command line:

```bash
# 10 generations, 100 strategies per generation
python3 -m lecat.main --generations 10 --strategies 100 --bars 1000

# With parallel processing (4 CPU cores)
python3 -m lecat.main --generations 10 --strategies 100 --bars 1000 --cores 4
```

### 3.3 CLI Argument Reference

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--strategies` | `-n` | 10 | Number of strategies / population size |
| `--bars` | `-b` | 1000 | Number of price bars to generate |
| `--depth` | `-d` | 3 | Max expression tree depth |
| `--seed` | `-s` | None | Random seed for reproducibility |
| `--cores` | `-c` | 1 | CPU workers for parallel evaluation |
| `--generations` | `-g` | 0 | Optimizer generations (0 = simple backtest) |

---

## 4. Writing Strategies (Expression Language)

### 4.1 Basic Structure

Every strategy is a boolean expression — it evaluates to `True` (signal) or `False` (no signal) at each bar.

```
<left side> <comparison operator> <right side>
```

Examples:
```
PRICE > 100         # Is price above 100?
RSI(14) > 70        # Is RSI above 70?
SMA(20) > SMA(50)   # Is short-term average above long-term?
```

### 4.2 Comparison Operators

| Operator | Meaning |
|----------|---------|
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |
| `==` | Equal (with epsilon tolerance) |
| `!=` | Not equal |

### 4.3 Combining Conditions

| Operator | Meaning | Example |
|----------|---------|---------|
| `AND` | Both must be true | `RSI(14) > 70 AND PRICE > SMA(50)` |
| `OR` | Either must be true | `RSI(14) > 80 OR MACD(12,26,9) > 0` |
| `NOT` | Negate condition | `NOT (RSI(14) > 70)` |

**Precedence:** `NOT` > `AND` > `OR`. Use parentheses to override:
```
(RSI(14) > 70 OR MACD(12,26,9) > 0) AND PRICE > SMA(200)
```

### 4.4 Market Data Accessors

Zero-argument functions that return current bar data:

| Function | Description | Also works as |
|----------|-------------|---------------|
| `PRICE` | Current close price | `close` |
| `OPEN` | Current open price | `open` |
| `HIGH` | Current high price | `high` |
| `LOW` | Current low price | `low` |
| `VOLUME` | Current volume | `volume` |

### 4.5 Technical Indicators

| Indicator | Arguments | Range | Description |
|-----------|-----------|-------|-------------|
| `SMA(period)` | period: 1–500 (default: 20) | Price level | Simple Moving Average |
| `EMA(period)` | period: 1–500 (default: 20) | Price level | Exponential Moving Average (reacts faster) |
| `RSI(period)` | period: 1–500 (default: 14) | 0–100 | Relative Strength Index (>70 overbought, <30 oversold) |
| `ATR(period)` | period: 1–500 (default: 14) | Always positive | Average True Range (volatility) |
| `MACD(fast, slow, signal)` | 2–100, 2–200, 2–50 (12,26,9) | Centered on 0 | MACD Histogram (>0 bullish, <0 bearish) |
| `BB_UPPER(period, std)` | 2–500, 0.5–5.0 (20, 2.0) | Price level | Bollinger Band Upper (breakout level) |
| `BB_LOWER(period, std)` | 2–500, 0.5–5.0 (20, 2.0) | Price level | Bollinger Band Lower (support level) |
| `STOCH(k, d)` | 1–500, 1–50 (14, 3) | 0–100 | Stochastic Oscillator (>80 overbought, <20 oversold) |

### 4.6 Context Shifting (Lookback)

Append `[n]` to any expression to look back `n` bars:

```
PRICE[1]                     # Yesterday's close price
RSI(14)[1]                   # RSI from 1 bar ago
(PRICE > SMA(50))[2]         # Was price above SMA 2 bars ago?
EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]  # Crossover detection
```

This is powerful for detecting **crossovers** (something changed from False → True).

### 4.7 Strategy Cookbook

Here are battle-tested strategy patterns:

**Trend Following:**
```
PRICE > SMA(200) AND RSI(14) > 50
```

**Mean Reversion:**
```
RSI(14) < 30 AND PRICE < BB_LOWER(20, 2.0)
```

**Momentum Crossover:**
```
EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]
```

**MACD + RSI Confirmation:**
```
MACD(12, 26, 9) > 0 AND RSI(14) > 50 AND RSI(14) < 80
```

**Volatility Breakout:**
```
PRICE > BB_UPPER(20, 2.0) AND VOLUME > 5000
```

**Combined Oversold Filter:**
```
RSI(14) < 30 AND STOCH(14, 3) < 20 AND MACD(12, 26, 9) > MACD(12, 26, 9)[1]
```

---

## 5. Strategy Persistence (Save & Load)

### 5.1 Saving from the Dashboard

After running a backtest in the Lab tab, click **"💾 Download Strategy (JSON)"**. The file contains:

```json
{
  "name": "RSI 14 > 70",
  "expression": "RSI(14) > 70",
  "metrics": {
    "sharpe": 0.5432,
    "return": 12.34,
    "win_rate": 0.6,
    "trades": 45,
    "max_drawdown": -8.5,
    "fitness": 0.3210
  },
  "timestamp": "2026-03-03T12:00:00+00:00",
  "engine_version": "2.0"
}
```

### 5.2 Loading into the Dashboard

1. Go to the **Strategy Lab** tab
2. Find the **"📁 Upload Strategy JSON"** uploader
3. Drop or browse for your `.json` file
4. The expression auto-populates — click **Run Backtest** to test

### 5.3 Programmatic Save/Load

```python
from lecat.exporter import save_strategy, load_strategy

# Save
save_strategy(
    expression="RSI(14) > 70 AND PRICE > SMA(50)",
    metrics={"sharpe": 1.5, "return": 25.0},
    name="My Strategy v1",
    filepath="strategies/my_strategy.json"
)

# Load
data = load_strategy("strategies/my_strategy.json")
print(data["expression"])  # "RSI(14) > 70 AND PRICE > SMA(50)"
```

---

## 6. Configuration

### 6.1 config.yaml

The file `lecat/config.yaml` controls default system settings:

```yaml
initial_capital: 10000       # Starting capital for backtests
chart_theme: "plotly_dark"    # Dashboard chart theme
log_dir: "logs"               # Where log files are stored
strategies_dir: "strategies"  # Where strategies are saved

optimizer:                    # Default optimizer settings
  population_size: 100
  generations: 10
  mutation_rate: 0.3

dashboard:
  port: 8501
  theme: "dark"
```

Edit this file to change defaults. Requires PyYAML (`pip install pyyaml`).

### 6.2 Environment Variables

No environment variables are required. All configuration is via `config.yaml` or CLI flags.

---

## 7. Logging

### 7.1 Log Location

Logs are written to `logs/lecat.log` (auto-created).

### 7.2 Log Levels

- **Console:** Shows `INFO` and above
- **File:** Records `DEBUG` and above (much more detail)
- **Rotation:** 10 MB max file size, keeps 5 backups

### 7.3 Reading Logs

```bash
# View latest logs
tail -f logs/lecat.log

# Search for specific events
grep "Generation" logs/lecat.log
grep "Best Strategy" logs/lecat.log
```

Example log output:
```
2026-03-03 12:00:00 - lecat.optimizer - INFO - Evolution started — Population: 100, Generations: 10
2026-03-03 12:00:01 - lecat.optimizer - INFO - Gen   1 | best= 0.3210 avg= 0.0150 | ret=+12.3% trades=45       RSI(14) > 70 AND PRICE > SMA(50)
2026-03-03 12:00:05 - lecat.optimizer - INFO - Best Strategy: RSI(14) > 70 AND PRICE > SMA(50)
```

---

## 8. Running Tests

```bash
# Using Make (recommended)
make test                # Run all 235 tests with pytest
make test-fast           # Quick run without verbose output

# Using unittest directly
python3 -m unittest discover -s tests -v

# Using pytest directly
python3 -m pytest tests/ -v

# Run a specific test module
python3 -m unittest tests.test_lexer -v
python3 -m unittest tests.test_indicators -v
python3 -m unittest tests.test_persistence -v

# Run tests matching a pattern
python3 -m unittest tests.test_indicators.TestMACDIndicator -v
```

### 8.1 Test File Index

| File | Tests | Coverage |
|------|-------|----------|
| `test_lexer.py` | 31 | Tokenizer (numbers, strings, operators) |
| `test_parser.py` | 39 | Parser (AST construction, error handling, context shifting) |
| `test_registry.py` | 15 | Function registration and lookup |
| `test_evaluator.py` | 41 | AST evaluation, caching, boolean logic |
| `test_generator.py` | 10 | Random expression generation |
| `test_backtester.py` | 14 | Signal loop, trade execution |
| `test_fitness.py` | 10 | PnL, Sharpe, drawdown calculations |
| `test_evolution.py` | 18 | Mutation, crossover, selection |
| `test_data_loader.py` | 12 | CSV loading, column aliases, splitting |
| `test_reporting.py` | 8 | Chart generation, equity curves |
| `test_indicators.py` | 13 | MACD, Bollinger, Stochastic correctness |
| `test_parallel.py` | 9 | Parallel vs serial reproducibility |
| `test_persistence.py` | 15 | JSON export/import, logger, config |

---

## 9. Developer Shortcuts (Makefile)

The project includes a `Makefile` for common tasks:

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make install` | Install production dependencies |
| `make install-dev` | Install with dev tools (black, isort, pytest) |
| `make format` | Auto-format code with black + isort |
| `make lint` | Check formatting without modifying files |
| `make test` | Run all tests with pytest |
| `make test-fast` | Quick test run (no verbose) |
| `make run` | Launch the Streamlit dashboard |
| `make run-cli` | Run CLI with default settings |
| `make clean` | Remove caches, logs, and build artifacts |

---

## 10. Python Packaging

LECAT is packaged with `pyproject.toml` and can be installed as a Python package:

```bash
# Install in development mode
pip install -e .

# Install with optional dependency groups
pip install -e ".[dashboard]"   # streamlit + plotly + pandas
pip install -e ".[data]"        # numpy + matplotlib
pip install -e ".[all]"         # Everything
pip install -e ".[all,dev]"     # Everything + pytest, black, isort
```

After installation, `import lecat` works from anywhere, and the `lecat` CLI command is available:

```bash
lecat --help
lecat --generations 10 --strategies 100 --cores 4
```

---

## 11. Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| `ModuleNotFoundError: streamlit` | Dependencies not installed | Run `pip install -r requirements.txt` or `make install` |
| `ModuleNotFoundError: plotly` | Missing visualization lib | Run `pip install plotly` |
| `TypeError: unsupported operand \| ` | Python 3.9 without future imports | Ensure all `.py` files have `from __future__ import annotations` |
| Dashboard blank after upload | CSV format issue | Check column names match §2.1; ensure no empty rows |
| `ParserError: Chained comparison` | `A > B > C` is not allowed | Rewrite as `A > B AND B > C` |
| `InsufficientData` | Indicator needs more bars | Increase data size or reduce indicator period |
| `EvaluationError: Unknown identifier` | Typo in function name | Check spelling; use Function Reference tab |
| Strategy returns are NaN | No trades triggered | Try a less restrictive condition |
| Dashboard won't launch | Port in use | `streamlit run lecat/dashboard/app.py --server.port 8502` |
| Optimizer takes too long | Large population/generations | Reduce pop size, use `--cores 4` for parallel |
| Log file not created | Permission issue | Check `logs/` directory is writable |
| `pip install .` fails | Missing setuptools | Run `pip install setuptools wheel` first |
| Custom indicator error | Invalid formula | Test formula in Lab first; must be a valid boolean LECAT expression |
| Database not found | DB not initialized | The `lecat.db` file is auto-created on first use |

### Getting Help

1. Check the **Function Reference** tab in the dashboard for correct syntax
2. Start with **Quick Presets** and modify from there
3. Review `logs/lecat.log` for detailed error messages
4. Run tests to verify installation: `make test` or `python3 -m unittest discover -s tests`
5. Check the [README](../README.md) for architecture overview and quickstart

---

## 8. Database Management

LECAT uses a SQLite database (`lecat.db`) to persist market data, custom indicators, and optimization history.

### 8.1 Data Sources

The dashboard sidebar offers three data sources:

| Source | Description |
|--------|-------------|
| **Upload CSV** | Upload OHLCV files; optionally save to database |
| **Database** | Load previously saved datasets from SQLite |
| **Generate Random** | Synthetic data for testing |

When uploading a CSV with **"Save to database"** checked, the data is persisted and available under "Database" on subsequent visits.

### 8.2 Managing Custom Indicators

Open the **🛠️ Indicator Manager** tab to create, edit, and delete custom indicators:

1. Click **➕ New Indicator** (or select an existing one from the left panel)
2. Fill in the fields:
   - **Name:** Uppercase identifier (e.g., `MY_CROSS`)
   - **Arguments:** Comma-separated parameter names (leave blank for none)
   - **Formula:** Valid LECAT boolean expression (e.g., `SMA(fast) > SMA(slow)`)
   - **Description:** Optional human-readable description
3. Click **🧪 Test** to verify the formula compiles and runs
4. Click **💾 Save** to persist to the database

Custom indicators are immediately available in the Strategy Lab and persist across restarts.

### 8.3 Backing Up the Database

```bash
# Create a timestamped backup
cp lecat.db lecat_backup_$(date +%Y%m%d).db

# Restore from backup
cp lecat_backup_20260303.db lecat.db
```

### 8.4 Schema Reference

See [07_Database_Schema.md](./07_Database_Schema.md) for full table definitions.

