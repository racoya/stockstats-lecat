<p align="center">
  <h1 align="center">📈 LECAT</h1>
  <p align="center">
    <strong>Logical Expression Compiler for Algorithmic Trading</strong>
  </p>
  <p align="center">
    A DSL compiler that turns plain-English trading rules into executable strategies,<br>
    then evolves them using a genetic algorithm to find what actually works.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square" alt="Python 3.9+">
    <img src="https://img.shields.io/badge/tests-257%20passing-brightgreen?style=flat-square" alt="Tests">
    <img src="https://img.shields.io/badge/version-2.1.1-orange?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
    <img src="https://img.shields.io/github/actions/workflow/status/racoya/stockstats-lecat/build_release.yml?style=flat-square&label=release%20build" alt="Release Build">
  </p>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **DSL Compiler** | Write strategies like `RSI(14) > 70 AND PRICE > SMA(50)` — no code needed |
| ⏪ **Time-Travel** | Look back with `[n]` offsets: `EMA(10)[1] <= EMA(50)[1]` for crossover detection |
| 🧬 **Genetic Engine** | Automatically evolve profitable strategies via mutation, crossover, and tournament selection |
| 📊 **Web Dashboard** | Interactive Streamlit GUI with Plotly candlestick charts, metrics, and strategy presets |
| ⚡ **Parallel Evaluation** | Multi-core backtesting via ThreadPoolExecutor for 2–6x speedup |
| 📈 **8 Built-in Indicators** | SMA, EMA, RSI, ATR, MACD, Bollinger Bands, Stochastic Oscillator |
| 🔁 **Walk-Forward Validation** | Train/test split prevents overfitting; overfit ratio measures generalization |
| 💾 **SQLite Persistence** | Market data, custom indicators, and optimization history stored in a local database |
| 🛠️ **Indicator Manager** | Create, test, and save custom composite indicators directly from the dashboard UI |
| 🐍 **Python Plugin System** | Drop `.py` files into `lecat_plugins/` for complex math (log returns, custom vol, etc.) |
| 🖥️ **Desktop App** | Standalone Windows & macOS executable — no Python required for end users |

---

## 🚀 Quickstart

### Option 1: Standalone Desktop App (Easiest)
Download the standalone executable (no Python required) for Windows or macOS from the [Releases page](https://github.com/racoya/stockstats-lecat/releases). Extract the `.zip` file and double-click `LECAT_Trader`.

> **Data persistence:** All uploaded data, custom indicators, and logs are saved to `~/.lecat/` so your work is never lost between sessions.

### Option 2: Run from Source (For Developers)

```bash
# 1. Clone & install
git clone https://github.com/racoya/stockstats-lecat.git && cd stockstats-lecat
pip install -r requirements.txt

# 2. Launch the dashboard
streamlit run lecat/dashboard/app.py

# 3. Or run from the command line
python -m lecat.main --generations 10 --strategies 100 --cores 4
```

---

## 🖥️ Dashboard

The interactive web dashboard provides five tabs:

| Tab | Description |
|-----|-------------|
| **🔬 Strategy Lab** | Type any expression, click Run, see candlestick chart with buy/sell markers and metrics |
| **🧬 Evolution Engine** | Run the genetic optimizer and watch the Hall of Fame populate in real time |
| **🛠️ Indicator Manager** | Create, test, and save custom composite indicators backed by the database |
| **📚 Function Reference** | Browse all available built-in and plugin indicators with syntax and examples |
| **📊 Results** | View and compare historical backtest results |

---

## 📝 The Language

LECAT uses a simple, expressive DSL for writing trading strategies:

```
RSI(14) > 70 AND PRICE > SMA(50)
```

### Operators
```
AND  OR  NOT                    # Boolean logic
>  <  >=  <=  ==  !=            # Comparisons
```

### Market Data
```
PRICE  OPEN  HIGH  LOW  VOLUME  # Current bar values
```

### Built-in Indicators
```
SMA(20)                         # Simple Moving Average
EMA(20)                         # Exponential Moving Average
RSI(14)                         # Relative Strength Index (0–100)
ATR(14)                         # Average True Range
MACD(12, 26, 9)                 # MACD Histogram
BB_UPPER(20, 2.0)               # Bollinger Band Upper
BB_LOWER(20, 2.0)               # Bollinger Band Lower
STOCH(14, 3)                    # Stochastic Oscillator %D (0–100)
```

### Time Travel (Context Shifting)
```
PRICE[1]                        # Yesterday's close
RSI(14)[3]                      # RSI from 3 bars ago
(EMA(10) > EMA(50))[1]          # Was fast EMA above slow EMA yesterday?
```

### Example Strategies
```
RSI(14) < 30 AND PRICE < BB_LOWER(20, 2.0)          # Mean reversion
EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]      # Golden crossover
MACD(12, 26, 9) > 0 AND RSI(14) > 50 AND RSI(14) < 80  # Momentum filter
```

---

## 🐍 Python Plugins (Complex Math)

For indicators that need full mathematical power (logarithms, volatility, custom models), drop a `.py` file into the `lecat_plugins/` folder:

```python
# lecat_plugins/my_math.py
from lecat.registry import FunctionRegistry, FunctionResult
from lecat.context import MarketContext
import math

def register_plugin(registry: FunctionRegistry) -> None:
    @registry.register(
        name="LOG_RETURN",
        description="Logarithmic return over N periods (%).",
        arg_schema=[{"name": "period", "type": "integer", "default": 1}],
        min_bars_required=lambda args: args.get("period", 1) + 1,
    )
    def handler(args: dict, ctx: MarketContext) -> FunctionResult:
        p = int(args["period"])
        return FunctionResult.success(
            math.log(ctx.close[ctx.bar_index] / ctx.close[ctx.bar_index - p]) * 100
        )
```

Plugins are auto-discovered at startup and immediately available in all dashboard tabs. Two example plugins are included: `HALF_SMA` and `LOG_RETURN`.

---

## 🏗️ Architecture

```mermaid
graph LR
    A["📝 Strategy<br/><i>RSI(14) > 70</i>"] --> B["🔤 Lexer"]
    B --> C["🌳 Parser"]
    C --> D["⚡ Evaluator"]
    D --> E["📊 Backtester"]
    E --> F["📈 Fitness"]

    G["📚 Registry<br/><i>Built-ins + Plugins + DB</i>"] --> D
    H["📉 Market Data<br/><i>OHLCV Bars</i>"] --> D

    F --> I["🧬 Optimizer<br/><i>Genetic Algorithm</i>"]
    I -->|"mutate &<br/>crossover"| A

    style A fill:#1a1a2e,stroke:#00d2ff,color:#fff
    style I fill:#1a1a2e,stroke:#00ff88,color:#fff
```

The compiler pipeline: **String → Tokens → AST → Evaluator → Signals → Fitness**. The genetic optimizer closes the loop by evolving new strategy strings from the fittest individuals.

---

## 📁 Project Structure

```
stockstats-lecat/
├── lecat/                        # Core engine
│   ├── lexer.py                  # Tokenizer
│   ├── parser.py                 # Recursive descent parser
│   ├── ast_nodes.py              # Immutable AST nodes
│   ├── evaluator.py              # Tree-walking evaluator
│   ├── context.py                # MarketContext (OHLCV + split)
│   ├── registry.py               # Function plugin registry
│   ├── std_lib.py                # Built-in indicators
│   ├── indicators.py             # Extended indicators (MACD, BB, STOCH)
│   ├── dynamic_registry.py       # DB-backed + plugin indicator loader
│   ├── plugin_loader.py          # Auto-discovers lecat_plugins/ at startup
│   ├── repository.py             # SQLite CRUD (market data, indicators, results)
│   ├── cache.py                  # Cross-bar indicator memoization
│   ├── generator.py              # Random expression generator
│   ├── backtester.py             # Time-loop backtesting engine
│   ├── fitness.py                # PnL, Sharpe, fitness scoring
│   ├── evolution.py              # Genetic operators
│   ├── optimizer.py              # GA loop + walk-forward
│   ├── parallel.py               # Multi-core batch evaluator
│   ├── data_loader.py            # CSV / DB ingestion
│   ├── reporting.py              # Equity curve charts
│   ├── exporter.py               # Strategy JSON save/load
│   ├── logger.py                 # Structured logging
│   ├── main.py                   # CLI entry point
│   └── dashboard/
│       └── app.py                # Streamlit web dashboard (5 tabs)
├── lecat_plugins/                # Drop-in Python math plugins
│   └── math_utils.py             # Example: HALF_SMA, LOG_RETURN
├── tests/                        # 257 unit tests
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_registry.py
│   ├── test_evaluator.py
│   ├── test_generator.py
│   ├── test_backtester.py
│   ├── test_fitness.py
│   ├── test_evolution.py
│   ├── test_data_loader.py
│   ├── test_reporting.py
│   ├── test_indicators.py
│   ├── test_parallel.py
│   ├── test_persistence.py
│   ├── test_database.py          # 19 DB integration tests
│   └── test_plugin_loader.py     # Plugin system tests
├── docs/                         # Full documentation package
│   ├── 00_Overview.md
│   ├── 01_Grammar_Specification.md
│   ├── 02_System_Architecture.md
│   ├── 03_Function_Registry_API.md
│   ├── 04_Error_Handling.md
│   ├── 05_Integration_Strategy.md
│   └── 06_Operations_Manual.md
├── .github/workflows/
│   └── build_release.yml         # Auto-builds Windows & macOS on tag push
├── run_desktop.py                # Desktop app bootstrapper
├── lecat.spec                    # PyInstaller build specification
├── pyproject.toml                # Python packaging
├── requirements.txt              # Dependencies
├── Makefile                      # Developer shortcuts
├── LICENSE                       # MIT License
└── .gitignore
```

---

## 🛠️ Development

```bash
# Install with dev tools
pip install -e ".[all,dev]"

# Run tests
make test

# Format code
make format

# Launch dashboard
make run

# Build standalone desktop executable (requires PyInstaller)
make build-desktop

# Clean build artifacts
make clean
```

See the full [Operations Manual](docs/06_Operations_Manual.md) for detailed usage, expression language reference, troubleshooting, and more.

---

## 📊 Project Status

| Phase | Sprint | Status |
|-------|--------|--------|
| **Phase 1** — Requirements & Specification | — | ✅ Complete |
| **Phase 2** — Core Implementation | Sprint 1 — Compiler Frontend | ✅ Complete |
| **Phase 2** — Core Implementation | Sprint 2 — Evaluator & Registry | ✅ Complete |
| **Phase 2** — Core Implementation | Sprint 3 — Backtester & Generator | ✅ Complete |
| **Phase 3** — Optimization & Evolution | Sprint 1 — Genetic Engine | ✅ Complete |
| **Phase 3** — Optimization & Evolution | Sprint 2 — Data & Validation | ✅ Complete |
| **Phase 3** — Optimization & Evolution | Sprint 3 — Performance & Indicators | ✅ Complete |
| **Phase 4** — Interface & Deployment | Sprint 1 — Web Dashboard | ✅ Complete |
| **Phase 4** — Interface & Deployment | Sprint 2 — Persistence & Packaging | ✅ Complete |
| **Phase 5** — Release Engineering | Final Polish & Handoff | ✅ Complete |
| **Phase 6** — Database & Extensibility | Sprint 1 — SQLite + Indicator Manager | ✅ Complete |
| **Phase 6** — Database & Extensibility | Sprint 2 — Python Plugin System | ✅ Complete |
| **Phase 7** — Deployment | Sprint 1 — Desktop Packaging (Win/Mac) | ✅ Complete |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.