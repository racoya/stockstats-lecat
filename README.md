# LECAT — Logical Expression Compiler for Algorithmic Trading

A high-performance **Domain-Specific Language (DSL) compiler** for evaluating boolean logical expressions in financial markets. LECAT parses text-based trading strategies, resolves dynamic indicator functions from an expandable plugin registry, and executes logic against historical OHLCV data.

**Primary Use Case:** Serve as the fitness function for Genetic Programming / Neural Network optimization loops.

```
RSI(14) > 80 AND PRICE > SMA(50)
NOT (VOLUME < SMA_VOL(20)) OR MACD(12, 26, 9) > 0
RSI(14)[1] > 70 AND (close > open)[1]
```

---

## Project Status

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

---

## Quick Start

**Requirements:** Python 3.10+, standard library only (no external dependencies).

```python
from lecat.lexer import Lexer
from lecat.parser import Parser
from lecat.evaluator import Evaluator
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib
from lecat.context import MarketContext

# 1. Set up the registry with built-in indicators
registry = FunctionRegistry()
register_std_lib(registry)

# 2. Parse a trading strategy expression
source = "PRICE > SMA(3) AND PRICE[1] <= SMA(3)[1]"
tokens = Lexer(source).tokenize()
ast = Parser(tokens).parse()

# 3. Evaluate against market data
context = MarketContext(
    open=[9.0, 10.0, 11.0, 12.0, 13.0],
    high=[11.0, 12.0, 13.0, 14.0, 15.0],
    low=[8.0, 9.0, 10.0, 11.0, 12.0],
    close=[10.0, 11.0, 12.0, 13.0, 14.0],
    volume=[100.0] * 5,
    bar_index=4,
)

evaluator = Evaluator(registry)
result = evaluator.evaluate(ast, context)
print(f"Signal: {result.value}")  # 1.0 (True) or 0.0 (False)
```

### Running Tests

```bash
python3 -m unittest discover -s tests -v
```

### CLI — Generate & Backtest

```bash
python3 -m lecat.main --strategies 10 --bars 5000 --depth 3 --seed 42
```

---

## Project Structure

```
stockstats-lecat/
├── lecat/                    # Core compiler package
│   ├── __init__.py
│   ├── errors.py             # LexerError, ParserError exception hierarchy
│   ├── tokens.py             # TokenType enum, Token dataclass
│   ├── ast_nodes.py          # AST nodes + ast_to_string() serializer
│   ├── lexer.py              # Tokenizer — string → token stream
│   ├── parser.py             # Recursive descent parser — tokens → AST
│   ├── context.py            # MarketContext (OHLCV data + split())
│   ├── registry.py           # FunctionRegistry with @register decorator
│   ├── evaluator.py          # Tree-walking AST evaluator
│   ├── std_lib.py            # Built-in indicators (PRICE, SMA, EMA, RSI, ATR)
│   ├── indicators.py         # Extended indicators (MACD, BB_UPPER, BB_LOWER, STOCH)
│   ├── cache.py              # Cross-bar indicator memoization
│   ├── generator.py          # Random expression generator
│   ├── backtester.py         # Time-loop backtesting engine
│   ├── stats.py              # Signal statistics and metrics
│   ├── main.py               # CLI entry point (--cores, --generations)
│   ├── fitness.py            # PnL, Sharpe Ratio, fitness scoring
│   ├── evolution.py          # Genetic operators (mutation, crossover, selection)
│   ├── optimizer.py          # GA loop with walk-forward + parallel eval
│   ├── parallel.py           # Multi-core batch evaluation (ThreadPoolExecutor)
│   ├── data_loader.py        # CSV/DataFrame ingestion into MarketContext
│   ├── reporting.py          # Equity curve charts and text reports
│   └── dashboard/
│       └── app.py            # Streamlit web dashboard
├── tests/                    # Unit tests (220 tests)
│   ├── test_lexer.py         # Lexer tests (31 tests)
│   ├── test_parser.py        # Parser tests (39 tests)
│   ├── test_registry.py      # Registry tests (15 tests)
│   ├── test_evaluator.py     # Evaluator tests (41 tests)
│   ├── test_generator.py     # Generator tests (10 tests)
│   ├── test_backtester.py    # Backtester tests (14 tests)
│   ├── test_fitness.py       # Fitness tests (10 tests)
│   ├── test_evolution.py     # Evolution tests (18 tests)
│   ├── test_data_loader.py   # Data loader tests (12 tests)
│   ├── test_reporting.py     # Reporting tests (8 tests)
│   ├── test_indicators.py    # Extended indicator tests (13 tests)
│   └── test_parallel.py      # Parallel evaluator tests (9 tests)
├── docs/                     # System design documentation (SDD/SRS)
│   ├── 00_Overview.md
│   ├── 01_Grammar_Specification.md
│   ├── 02_System_Architecture.md
│   ├── 03_Function_Registry_API.md
│   ├── 04_Error_Handling.md
│   ├── 05_Integration_Strategy.md
│   └── 06_Operations_Manual.md
├── README.md
└── LICENSE
```

---

## Documentation

All system design documents are located in the [`docs/`](./docs/) directory:

| Document | Description |
|----------|-------------|
| [00 — Overview](./docs/00_Overview.md) | Executive summary, technical constraints, glossary |
| [01 — Grammar Specification](./docs/01_Grammar_Specification.md) | EBNF grammar, operator precedence, token spec |
| [02 — System Architecture](./docs/02_System_Architecture.md) | Component & sequence diagrams, AST node schemas |
| [03 — Function Registry API](./docs/03_Function_Registry_API.md) | Plugin registration, MarketContext, FunctionResult |
| [04 — Error Handling](./docs/04_Error_Handling.md) | Error taxonomy, edge cases, safety guarantees |
| [05 — Integration Strategy](./docs/05_Integration_Strategy.md) | Optimizer hook, BacktestResult, batch evaluation |

### Standards

- **IEEE 830** — Software Requirements Specification
- **EBNF (ISO 14977)** — Grammar definition
- **C4 Model** — Architecture diagrams (rendered via Mermaid)

---

## Architecture Overview

```
Source String → Lexer → Parser → AST (immutable) → Evaluator → bool[] signals
                                                        ↕
                                                   Function Registry
                                                   (plugin system)
```

### Key Design Principles

- **Immutability** — AST is frozen after construction
- **Idempotency** — Same expression + same data = same result, always
- **Performance** — O(n) evaluation relative to AST depth; 256-node recursion limit
- **Safety** — No look-ahead bias; floating-point epsilon comparisons; graceful error propagation
- **Extensibility** — Decorator-based function registration; zero core changes to add indicators

---

## License

See [LICENSE](./LICENSE) for details.