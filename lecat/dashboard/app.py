"""LECAT Quantitative Dashboard — Streamlit Web Application.

Interactive web GUI for the LECAT strategy compiler and optimizer.
Two operating modes:
  - Lab Mode:       Test individual strategies with interactive candlestick charts
  - Evolution Mode: Run the genetic optimizer and browse the Hall of Fame

Usage:
    streamlit run lecat/dashboard/app.py
    # or
    python -m streamlit run lecat/dashboard/app.py
"""

from __future__ import annotations

import io
import sys
import os
import time
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lecat.backtester import Backtester
from lecat.context import MarketContext
from lecat.data_loader import load_from_csv, load_from_lists
from lecat.evaluator import Evaluator
from lecat.exporter import load_strategy, strategy_to_json_string
from lecat.fitness import FitnessResult, calculate_fitness
from lecat.indicators import register_extended_indicators
from lecat.lexer import Lexer
from lecat.main import generate_random_ohlcv
from lecat.optimizer import Optimizer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.std_lib import register_std_lib


# ------------------------------------------------------------------
# Page Config
# ------------------------------------------------------------------

st.set_page_config(
    page_title="LECAT — Quantitative Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------
# Custom CSS
# ------------------------------------------------------------------

st.markdown("""
<style>
    /* Dark theme enhancements */
    .stApp {
        background-color: #0e1117;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-value {
        font-size: 2em;
        font-weight: 700;
        color: #00d2ff;
    }
    .metric-label {
        font-size: 0.85em;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .hall-of-fame {
        border: 1px solid #2d3748;
        border-radius: 8px;
        overflow: hidden;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    }
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Registry singleton
# ------------------------------------------------------------------

@st.cache_resource
def get_registry() -> FunctionRegistry:
    """Create and cache the function registry."""
    reg = FunctionRegistry()
    register_std_lib(reg)
    register_extended_indicators(reg)
    return reg


# ------------------------------------------------------------------
# Data Loading
# ------------------------------------------------------------------

@st.cache_data
def load_csv_data(file_bytes: bytes, filename: str) -> dict:
    """Parse uploaded CSV file into MarketContext-compatible data."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(file_bytes)
        temp_path = f.name

    try:
        ctx = load_from_csv(temp_path, symbol=filename.replace(".csv", ""))
        return {
            "open": list(ctx.open),
            "high": list(ctx.high),
            "low": list(ctx.low),
            "close": list(ctx.close),
            "volume": list(ctx.volume),
            "symbol": ctx.symbol,
            "total_bars": ctx.total_bars,
        }
    finally:
        os.unlink(temp_path)


def data_to_context(data: dict) -> MarketContext:
    """Convert cached data dict back to MarketContext."""
    return MarketContext(
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        volume=data["volume"],
        bar_index=data["total_bars"] - 1,
        symbol=data.get("symbol", ""),
    )


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------

def render_sidebar():
    """Render the sidebar with data upload and settings."""
    st.sidebar.markdown("## 📈 LECAT Dashboard")
    st.sidebar.markdown("---")

    # Data source selection
    data_source = st.sidebar.radio(
        "Data Source",
        ["Upload CSV", "Generate Random"],
        index=1,
    )

    ctx = None
    data_dict = None

    if data_source == "Upload CSV":
        uploaded = st.sidebar.file_uploader(
            "Upload OHLCV CSV",
            type=["csv"],
            help="Expected columns: Date, Open, High, Low, Close, Volume",
        )
        if uploaded is not None:
            try:
                data_dict = load_csv_data(uploaded.getvalue(), uploaded.name)
                ctx = data_to_context(data_dict)
                st.sidebar.success(f"✅ Loaded {ctx.total_bars:,} bars — {data_dict['symbol']}")
            except Exception as e:
                st.sidebar.error(f"❌ Error: {e}")
        else:
            st.sidebar.info("👆 Upload a CSV file to begin")

    else:
        num_bars = st.sidebar.slider("Number of Bars", 100, 10000, 1000, step=100)
        seed = st.sidebar.number_input("Random Seed", value=42, step=1)
        ctx = generate_random_ohlcv(num_bars, seed=int(seed))

    st.sidebar.markdown("---")

    # Settings
    st.sidebar.markdown("### ⚙️ Settings")
    initial_capital = st.sidebar.number_input(
        "Initial Capital ($)", value=10000, step=1000, min_value=100
    )

    return ctx, initial_capital


# ------------------------------------------------------------------
# Lab Mode
# ------------------------------------------------------------------

def render_lab_mode(ctx: MarketContext, initial_capital: float):
    """Render the Lab mode tab for manual strategy testing."""
    st.markdown("### 🔬 Strategy Lab")
    st.markdown("Type a LECAT expression below and click **Run Backtest** to see results.")

    col1, col2 = st.columns([3, 1])

    with col1:
        expression = st.text_area(
            "LECAT Expression",
            value=st.session_state.get("lab_expression", "RSI(14) > 70 AND PRICE > SMA(50)"),
            height=80,
            placeholder="e.g., RSI(14) > 70 AND PRICE > SMA(50)",
            key="lab_input",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_clicked = st.button("▶ Run Backtest", type="primary", use_container_width=True)

        # Quick presets
        st.markdown("**Quick Presets:**")
        presets = {
            "RSI Overbought": "RSI(14) > 70",
            "SMA Cross": "PRICE > SMA(50)",
            "Bollinger": "PRICE > BB_UPPER(20, 2.0)",
            "MACD Bull": "MACD(12, 26, 9) > 0",
        }
        for label, expr in presets.items():
            if st.button(label, key=f"preset_{label}", use_container_width=True):
                st.session_state["lab_expression"] = expr
                st.session_state["lab_input"] = expr
                st.rerun()

    # Strategy JSON upload
    st.markdown("---")
    uploaded_json = st.file_uploader(
        "📁 Upload Strategy JSON",
        type=["json"],
        help="Upload a previously saved strategy to auto-populate the expression",
        key="lab_json_upload",
    )
    if uploaded_json is not None:
        try:
            import json
            strategy_data = json.loads(uploaded_json.getvalue())
            if "expression" in strategy_data:
                st.session_state["lab_expression"] = strategy_data["expression"]
                st.success(f"✅ Loaded strategy: **{strategy_data.get('name', 'Unknown')}**")
                st.rerun()
            else:
                st.error("Invalid strategy file: missing 'expression' field")
        except Exception as e:
            st.error(f"Failed to load strategy: {e}")

    if run_clicked:
        st.session_state["lab_expression"] = expression
        _run_lab_backtest(expression, ctx, initial_capital)


def _run_lab_backtest(expression: str, ctx: MarketContext, initial_capital: float):
    """Run a single strategy backtest and display results."""
    try:
        # Compile
        tokens = Lexer(expression).tokenize()
        ast = Parser(tokens).parse()

        # Run backtest
        registry = get_registry()
        evaluator = Evaluator(registry)
        backtester = Backtester(evaluator, registry)
        result = backtester.run(ast, ctx, expression=expression)
        fitness = calculate_fitness(result, ctx)

        # Store in session
        st.session_state["lab_result"] = result
        st.session_state["lab_fitness"] = fitness
        st.session_state["lab_ctx"] = ctx

        # Display metrics
        _render_metrics(fitness, initial_capital)

        # Download strategy button
        json_str = strategy_to_json_string(expression, fitness)
        st.download_button(
            label="💾 Download Strategy (JSON)",
            data=json_str,
            file_name=f"strategy_{expression[:20].replace(' ', '_')}.json",
            mime="application/json",
        )

        # Display chart
        _render_candlestick_chart(result, ctx, expression, fitness)

    except Exception as e:
        error_type = type(e).__name__
        st.error(f"**{error_type}:** {e}")
        st.info("💡 Check your expression syntax. Example: `RSI(14) > 70 AND PRICE > SMA(50)`")


def _render_metrics(fitness: FitnessResult, initial_capital: float):
    """Render the metrics row."""
    cols = st.columns(6)

    metrics = [
        ("Total Return", f"{fitness.total_return_pct:+.2f}%", "📊"),
        ("Sharpe Ratio", f"{fitness.sharpe_ratio:.3f}", "📐"),
        ("Win Rate", f"{fitness.win_rate:.0%}", "🎯"),
        ("Trades", f"{fitness.num_trades}", "🔄"),
        ("Max Drawdown", f"{fitness.max_drawdown_pct:.1f}%", "📉"),
        ("Fitness", f"{fitness.fitness_score:.4f}", "⭐"),
    ]

    for col, (label, value, icon) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{icon} {label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)


def _render_candlestick_chart(result, ctx: MarketContext, expression: str, fitness: FitnessResult):
    """Render an interactive Plotly candlestick chart with signal overlays."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=[f"Price Chart — {expression}", "Volume", "Signal"],
        row_heights=[0.6, 0.2, 0.2],
    )

    # Bar indices
    x = list(range(ctx.total_bars))

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=x,
            open=list(ctx.open),
            high=list(ctx.high),
            low=list(ctx.low),
            close=list(ctx.close),
            name="Price",
            increasing_line_color="#00d2ff",
            decreasing_line_color="#ff6b6b",
        ),
        row=1, col=1,
    )

    # Buy signals (True → green triangles)
    buy_x = [i for i, s in enumerate(result.signals) if s]
    buy_y = [float(ctx.low[i]) * 0.998 for i in buy_x]
    fig.add_trace(
        go.Scatter(
            x=buy_x, y=buy_y,
            mode="markers",
            marker=dict(symbol="triangle-up", size=8, color="#00ff88"),
            name="Signal=True",
        ),
        row=1, col=1,
    )

    # Volume bars
    vol_colors = ["#00d2ff" if c > o else "#ff6b6b"
                  for c, o in zip(ctx.close, ctx.open)]
    fig.add_trace(
        go.Bar(x=x, y=list(ctx.volume), marker_color=vol_colors, name="Volume", opacity=0.5),
        row=2, col=1,
    )

    # Signal binary plot
    sig_colors = ["#00ff88" if s else "#333" for s in result.signals]
    fig.add_trace(
        go.Bar(x=x, y=[1 if s else 0 for s in result.signals],
               marker_color=sig_colors, name="Signal", opacity=0.7),
        row=3, col=1,
    )

    # Layout
    fig.update_layout(
        template="plotly_dark",
        height=700,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=80, b=50),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
    )

    fig.update_xaxes(gridcolor="#1a1a2e")
    fig.update_yaxes(gridcolor="#1a1a2e")

    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------
# Evolution Mode
# ------------------------------------------------------------------

def render_evolution_mode(ctx: MarketContext, initial_capital: float):
    """Render the Evolution mode tab for genetic optimization."""
    st.markdown("### 🧬 Evolution Engine")
    st.markdown("Configure and run the genetic algorithm to discover optimal strategies.")

    # Config columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        generations = st.number_input("Generations", value=5, min_value=1, max_value=100, step=1)
    with col2:
        pop_size = st.number_input("Population Size", value=50, min_value=10, max_value=1000, step=10)
    with col3:
        mutation_rate = st.slider("Mutation Rate", 0.0, 1.0, 0.3, 0.05)
    with col4:
        split_ratio = st.slider("Train/Test Split", 0.5, 0.9, 0.7, 0.05)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        evolve_clicked = st.button("🧬 Start Evolution", type="primary", use_container_width=True)
    with col_info:
        st.info(f"Will train on first {split_ratio:.0%} of data ({int(ctx.total_bars * split_ratio):,} bars), "
                f"test on remaining {1-split_ratio:.0%} ({ctx.total_bars - int(ctx.total_bars * split_ratio):,} bars)")

    if evolve_clicked:
        _run_evolution(ctx, generations, pop_size, mutation_rate, split_ratio, initial_capital)

    # Display stored results
    if "evolution_results" in st.session_state:
        _render_hall_of_fame(ctx, initial_capital)


def _run_evolution(ctx, generations, pop_size, mutation_rate, split_ratio, initial_capital):
    """Run the optimizer with progress display."""
    progress_bar = st.progress(0.0, text="Initializing population...")
    status_text = st.empty()

    optimizer = Optimizer(
        ctx,
        population_size=pop_size,
        mutation_rate=mutation_rate,
        seed=42,
        verbose=False,
    )

    # Run with progress simulation
    start = time.perf_counter()
    try:
        result = optimizer.run(generations=generations, split_ratio=split_ratio)
        elapsed = time.perf_counter() - start

        progress_bar.progress(1.0, text="✅ Evolution complete!")

        # Store top strategies in session state
        hall_of_fame = []
        registry = get_registry()
        evaluator = Evaluator(registry)
        backtester = Backtester(evaluator, registry)

        # Get top individuals from the final population
        final_gen = result.generations[-1] if result.generations else None

        # Collect unique strategies from the optimizer result
        seen = set()
        best_ind = result.best_individual
        if best_ind.expression not in seen:
            seen.add(best_ind.expression)
            try:
                bt = backtester.run(best_ind.ast, ctx, expression=best_ind.expression)
                fit = calculate_fitness(bt, ctx)
                hall_of_fame.append({
                    "rank": 1,
                    "expression": best_ind.expression,
                    "fitness": fit.fitness_score,
                    "return_pct": fit.total_return_pct,
                    "sharpe": fit.sharpe_ratio,
                    "win_rate": fit.win_rate,
                    "trades": fit.num_trades,
                    "drawdown": fit.max_drawdown_pct,
                })
            except Exception:
                pass

        st.session_state["evolution_results"] = hall_of_fame
        st.session_state["evolution_result"] = result
        st.session_state["evolution_elapsed"] = elapsed

        status_text.success(f"Completed {generations} generations in {elapsed:.1f}s")

    except Exception as e:
        progress_bar.empty()
        st.error(f"Evolution failed: {e}")


def _render_hall_of_fame(ctx: MarketContext, initial_capital: float):
    """Render the Hall of Fame leaderboard."""
    st.markdown("---")
    st.markdown("### 🏆 Hall of Fame")

    hall = st.session_state.get("evolution_results", [])
    result = st.session_state.get("evolution_result")

    if not hall:
        st.info("No strategies found. Try running evolution with more generations.")
        return

    # Walk-forward results
    if result and result.walk_forward:
        wf = result.walk_forward
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Train Sharpe", f"{wf.train_fitness.sharpe_ratio:.3f}")
        with col2:
            st.metric("Test Sharpe", f"{wf.test_fitness.sharpe_ratio:.3f}")
        with col3:
            overfit_color = "🟢" if wf.overfit_ratio > 0.7 else "🔴"
            st.metric("Overfit Ratio", f"{overfit_color} {wf.overfit_ratio:.2f}")

    # Leaderboard table
    import pandas as pd
    df = pd.DataFrame(hall)
    df.columns = ["Rank", "Strategy", "Fitness", "Return %", "Sharpe", "Win Rate", "Trades", "Max DD %"]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fitness": st.column_config.NumberColumn(format="%.4f"),
            "Return %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Sharpe": st.column_config.NumberColumn(format="%.3f"),
            "Win Rate": st.column_config.NumberColumn(format="%.1%%"),
            "Max DD %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    # Visualize selected strategy
    if hall:
        st.markdown("### 📊 Strategy Visualization")
        selected = st.selectbox(
            "Select strategy to visualize",
            [h["expression"] for h in hall],
        )

        col_viz, col_dl = st.columns([1, 1])
        with col_viz:
            if selected and st.button("📈 Show Chart", use_container_width=True):
                _run_lab_backtest(selected, ctx, initial_capital)
        with col_dl:
            if selected:
                sel_data = next((h for h in hall if h["expression"] == selected), None)
                if sel_data:
                    json_str = strategy_to_json_string(
                        selected,
                        sel_data,
                        name=f"Evolved Strategy #{sel_data.get('rank', 1)}"
                    )
                    st.download_button(
                        "💾 Download Strategy",
                        data=json_str,
                        file_name="evolved_strategy.json",
                        mime="application/json",
                        use_container_width=True,
                    )


# ------------------------------------------------------------------
# Data Overview
# ------------------------------------------------------------------

def render_data_overview(ctx: MarketContext):
    """Render a data overview section."""
    st.markdown("### 📋 Data Overview")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Bars", f"{ctx.total_bars:,}")
    with col2:
        st.metric("Price Range", f"${min(ctx.close):,.2f} — ${max(ctx.close):,.2f}")
    with col3:
        first = float(ctx.close[0])
        last = float(ctx.close[-1])
        change = ((last - first) / first) * 100 if first > 0 else 0
        st.metric("Period Return", f"{change:+.1f}%")
    with col4:
        st.metric("Symbol", ctx.symbol or "Generated")

    # Mini price chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=list(ctx.close),
        mode="lines",
        line=dict(color="#00d2ff", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0, 210, 255, 0.05)",
        name="Close",
    ))
    fig.update_layout(
        template="plotly_dark",
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#1a1a2e", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------
# Available Functions Reference
# ------------------------------------------------------------------

def render_function_reference():
    """Render the available functions reference."""
    st.markdown("### 📚 Available Functions")

    registry = get_registry()
    functions = registry.get_available_functions()

    # Group into categories
    accessors = [f for f in functions if not f.arg_schema]
    indicators = [f for f in functions if f.arg_schema]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Market Data Accessors**")
        for fn in accessors:
            st.code(fn.name, language=None)

    with col2:
        st.markdown("**Technical Indicators**")
        for fn in indicators:
            args_str = ", ".join(
                f"{a['name']}: {a.get('type', 'float')} = {a.get('default', '?')}"
                for a in fn.arg_schema
            )
            st.code(f"{fn.name}({args_str})", language=None)


# ------------------------------------------------------------------
# Main App
# ------------------------------------------------------------------

def main():
    """Main application entry point."""
    # Sidebar
    ctx, initial_capital = render_sidebar()

    # Header
    st.markdown("""
    # 📈 LECAT — Quantitative Dashboard
    *Logical Expression Compiler for Algorithmic Trading*
    """)

    if ctx is None:
        st.warning("⬅️ Please upload data or generate random data from the sidebar to begin.")
        return

    # Data overview
    render_data_overview(ctx)

    st.markdown("---")

    # Mode tabs
    tab_lab, tab_evolution, tab_reference = st.tabs([
        "🔬 Strategy Lab",
        "🧬 Evolution Engine",
        "📚 Function Reference",
    ])

    with tab_lab:
        render_lab_mode(ctx, initial_capital)

    with tab_evolution:
        render_evolution_mode(ctx, initial_capital)

    with tab_reference:
        render_function_reference()


if __name__ == "__main__":
    main()
