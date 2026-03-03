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
| **Phase 2** — Core Implementation | Sprint 2 — Evaluator & Registry | 🔲 Not started |

---

## Quick Start

**Requirements:** Python 3.10+, standard library only (no external dependencies).

```python
from lecat.lexer import Lexer
from lecat.parser import Parser

# Parse a trading strategy expression
source = "RSI(14) > 80 AND PRICE > SMA(50)"
tokens = Lexer(source).tokenize()
ast = Parser(tokens).parse()

print(ast)
# BinaryOpNode(operator='AND',
#   left=ComparisonNode(operator='>',
#     left=FunctionCallNode(name='RSI', arguments=(LiteralNode(value=14, ...),)),
#     right=LiteralNode(value=80, ...)),
#   right=ComparisonNode(operator='>',
#     left=IdentifierNode(name='PRICE'),
#     right=FunctionCallNode(name='SMA', arguments=(LiteralNode(value=50, ...),))))
```

### Running Tests

```bash
python3 -m unittest discover -s tests -v
```

---

## Project Structure

```
stockstats-lecat/
├── lecat/                    # Core compiler package
│   ├── __init__.py
│   ├── errors.py             # LexerError, ParserError exception hierarchy
│   ├── tokens.py             # TokenType enum, Token dataclass
│   ├── ast_nodes.py          # Immutable AST node dataclasses (frozen=True)
│   ├── lexer.py              # Tokenizer — string → token stream
│   └── parser.py             # Recursive descent parser — tokens → AST
├── tests/                    # Unit tests (70 tests)
│   ├── test_lexer.py         # Lexer tests (31 tests)
│   └── test_parser.py        # Parser tests (39 tests)
├── docs/                     # System design documentation (SDD/SRS)
│   ├── 00_Overview.md
│   ├── 01_Grammar_Specification.md
│   ├── 02_System_Architecture.md
│   ├── 03_Function_Registry_API.md
│   ├── 04_Error_Handling.md
│   └── 05_Integration_Strategy.md
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