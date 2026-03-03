# F. Operations Manual

**Parent Document:** [Overview](./00_Overview.md)

---

## 1. Installation

### 1.1 Prerequisites

- **Python 3.10+** (standard library only for core engine)
- **Optional:** `streamlit`, `plotly`, `pandas` (for web dashboard)
- **Optional:** `matplotlib` (for static chart export)
- **Optional:** `numpy` (for optimized data loading)

### 1.2 Setup

```bash
# Clone the repository
git clone <repository-url>
cd stockstats-lecat

# Install dashboard dependencies (optional)
pip install streamlit plotly pandas matplotlib numpy
```

No build step is required. The core engine uses only Python standard library.

---

## 2. Command Line Interface (CLI)

### 2.1 Basic Usage — Strategy Generation & Backtest

```bash
# Generate and test 10 random strategies on 1000 bars
python3 -m lecat.main

# Customize parameters
python3 -m lecat.main --strategies 20 --bars 5000 --depth 3 --seed 42
```

### 2.2 Optimizer Mode

```bash
# Run genetic algorithm for 10 generations
python3 -m lecat.main --generations 10 --strategies 100 --bars 1000

# With parallel evaluation (4 CPU cores)
python3 -m lecat.main --generations 10 --strategies 100 --bars 1000 --cores 4
```

### 2.3 CLI Arguments

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--strategies` | `-n` | 10 | Number of strategies / population size |
| `--bars` | `-b` | 1000 | Number of price bars to generate |
| `--depth` | `-d` | 3 | Max expression tree depth |
| `--seed` | `-s` | None | Random seed for reproducibility |
| `--cores` | `-c` | 1 | CPU workers for parallel evaluation |
| `--generations` | `-g` | 0 | Optimizer generations (0 = simple backtest) |

---

## 3. Web Dashboard

### 3.1 Launching

```bash
streamlit run lecat/dashboard/app.py
```

The dashboard opens at `http://localhost:8501`.

### 3.2 Features

#### Strategy Lab (Tab 1)
1. **Upload Data** — Drag & drop a CSV file, or use the "Generate Random" option
2. **Enter Expression** — Type a LECAT strategy (e.g., `RSI(14) > 70 AND PRICE > SMA(50)`)
3. **Run Backtest** — Click to see metrics (Return, Sharpe, Win Rate) and interactive candlestick chart
4. **Quick Presets** — Use built-in strategy templates

#### Evolution Engine (Tab 2)
1. **Configure** — Set generations, population size, mutation rate, and train/test split
2. **Start Evolution** — Run the genetic optimizer with progress indicator
3. **Hall of Fame** — Browse the top strategies ranked by fitness
4. **Visualize** — Click any strategy to see its equity curve

#### Function Reference (Tab 3)
- Browse all available market data accessors and technical indicators
- View function signatures and argument schemas

### 3.3 CSV File Format

The data loader accepts standard OHLCV CSV files:

```csv
Date,Open,High,Low,Close,Volume
2024-01-01,100.00,110.00,90.00,105.00,1000
2024-01-02,105.00,115.00,95.00,110.00,1200
```

**Supported column aliases:** `open`/`o`, `high`/`h`, `low`/`l`, `close`/`c`/`adj close`, `volume`/`vol`/`v`

Missing values are automatically forward-filled.

---

## 4. Expression Language Reference

### 4.1 Syntax

```
expression := comparison ((AND | OR) comparison)*
comparison := primary (> | < | >= | <= | == | !=) primary
primary    := function_call | identifier | literal | (expression)[offset]
```

### 4.2 Market Data Accessors

| Function | Description |
|----------|-------------|
| `PRICE` / `close` | Current bar's close price |
| `OPEN` / `open` | Current bar's open price |
| `HIGH` / `high` | Current bar's high price |
| `LOW` / `low` | Current bar's low price |
| `VOLUME` / `volume` | Current bar's volume |

### 4.3 Technical Indicators

| Function | Args | Description |
|----------|------|-------------|
| `SMA(period)` | period: 1–500 | Simple Moving Average |
| `EMA(period)` | period: 1–500 | Exponential Moving Average |
| `RSI(period)` | period: 1–500 | Relative Strength Index (0–100) |
| `ATR(period)` | period: 1–500 | Average True Range |
| `MACD(fast, slow, signal)` | 2–100, 2–200, 2–50 | MACD Histogram |
| `BB_UPPER(period, std_dev)` | 2–500, 0.5–5.0 | Bollinger Band Upper |
| `BB_LOWER(period, std_dev)` | 2–500, 0.5–5.0 | Bollinger Band Lower |
| `STOCH(k_period, d_period)` | 1–500, 1–50 | Stochastic Oscillator %D |

### 4.4 Context Shifting (Lookback)

Append `[n]` to shift evaluation back by `n` bars:

```
RSI(14)[1] > 70    # RSI from 1 bar ago
(PRICE > SMA(50))[2]  # Was price above SMA 2 bars ago?
```

### 4.5 Example Strategies

```
RSI(14) > 70 AND PRICE > SMA(200)       # RSI overbought + uptrend
MACD(12, 26, 9) > 0 AND RSI(14) < 80    # MACD bullish + not overbought
PRICE > BB_UPPER(20, 2.0)               # Bollinger breakout
EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]  # EMA crossover
```

---

## 5. Running Tests

```bash
# Run all tests
python3 -m unittest discover -s tests -v

# Run specific test modules
python3 -m unittest tests.test_lexer -v
python3 -m unittest tests.test_indicators -v
```

Current test count: **220 tests** across 12 test files.

---

## 6. Project Structure

```
stockstats-lecat/
├── lecat/                 # Core engine
│   ├── lexer.py           # Tokenizer
│   ├── parser.py          # Recursive descent parser
│   ├── ast_nodes.py       # Immutable AST nodes
│   ├── evaluator.py       # Tree-walking evaluator
│   ├── context.py         # MarketContext (OHLCV data)
│   ├── registry.py        # Function plugin registry
│   ├── std_lib.py         # Built-in indicators
│   ├── indicators.py      # Extended indicators
│   ├── generator.py       # Random expression generator
│   ├── backtester.py      # Backtesting engine
│   ├── fitness.py         # Fitness scoring
│   ├── evolution.py       # Genetic operators
│   ├── optimizer.py       # GA loop
│   ├── parallel.py        # Multi-core evaluation
│   ├── data_loader.py     # CSV ingestion
│   ├── reporting.py       # Chart generation
│   ├── cache.py           # Indicator caching
│   ├── main.py            # CLI entry point
│   └── dashboard/
│       └── app.py         # Streamlit web dashboard
├── tests/                 # 220 unit tests
├── docs/                  # Documentation (SDD/SRS)
└── README.md
```

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: streamlit` | Run `pip install streamlit plotly pandas` |
| `ParserError: Chained comparison` | LECAT doesn't allow `A > B > C`; use `A > B AND B > C` |
| `InsufficientDataError` | Indicator needs more bars than available; increase data size |
| `NaN in data` | Check CSV for missing values; loader forward-fills automatically |
| Dashboard won't start | Ensure port 8501 is free; try `streamlit run lecat/dashboard/app.py --server.port 8502` |
