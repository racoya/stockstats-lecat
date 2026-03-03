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
from lecat.data_loader import load_from_csv, load_from_db, load_from_lists
from lecat.evaluator import Evaluator
from lecat.dynamic_registry import DynamicRegistry
from lecat.exporter import load_strategy, strategy_to_json_string
from lecat.fitness import FitnessResult, calculate_fitness
from lecat.indicators import register_extended_indicators
from lecat.lexer import Lexer
from lecat.main import generate_random_ohlcv
from lecat.optimizer import Optimizer
from lecat.parser import Parser
from lecat.registry import FunctionRegistry
from lecat.repository import Repository
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
# Design System — Custom CSS
# ------------------------------------------------------------------

# Color palette
CYAN = "#00d2ff"
CYAN_MUTED = "rgba(0, 210, 255, 0.08)"
GREEN = "#00ff88"
GREEN_MUTED = "rgba(0, 255, 136, 0.10)"
RED = "#ff6b6b"
RED_MUTED = "rgba(255, 107, 107, 0.10)"
GOLD = "#ffd700"
BG_PRIMARY = "#0e1117"
BG_CARD = "#131720"
BG_CARD_HOVER = "#181e2a"
BG_SIDEBAR = "#0d1117"
BORDER = "#1e2738"
BORDER_ACCENT = "#2a3650"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_DIM = "#484f58"

st.markdown(f"""
<style>
    /* ── Import premium font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Global ── */
    .stApp {{
        background-color: {BG_PRIMARY};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {BG_SIDEBAR} 0%, #0a0e14 100%);
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .stMarkdown h2 {{
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}

    /* ── Header ── */
    .dashboard-header {{
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }}
    .dashboard-header h1 {{
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, {CYAN} 0%, #7b68ee 50%, {GREEN} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0;
    }}
    .dashboard-header .subtitle {{
        color: {TEXT_SECONDARY};
        font-size: 0.85rem;
        font-weight: 400;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 2px;
    }}

    /* ── Metric cards ── */
    .metric-card {{
        background: linear-gradient(135deg, {BG_CARD} 0%, #151b28 100%);
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 12px;
        text-align: center;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }}
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, {CYAN}, transparent);
        opacity: 0;
        transition: opacity 0.25s ease;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        border-color: {BORDER_ACCENT};
        box-shadow: 0 4px 20px rgba(0, 210, 255, 0.08);
    }}
    .metric-card:hover::before {{
        opacity: 1;
    }}
    .metric-value {{
        font-size: 1.6em;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: {CYAN};
        line-height: 1.2;
    }}
    .metric-value.positive {{ color: {GREEN}; }}
    .metric-value.negative {{ color: {RED}; }}
    .metric-label {{
        font-size: 0.7em;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 500;
        margin-bottom: 4px;
    }}

    /* ── Data overview cards ── */
    .data-stat {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }}
    .data-stat .stat-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.15em;
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}
    .data-stat .stat-label {{
        font-size: 0.7em;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 2px;
    }}

    /* ── Section headers ── */
    .section-header {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 1.2rem 0 0.6rem 0;
        padding-bottom: 8px;
        border-bottom: 1px solid {BORDER};
    }}
    .section-header .icon {{
        font-size: 1.3em;
    }}
    .section-header .title {{
        font-size: 1.1rem;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        letter-spacing: 0.3px;
    }}
    .section-header .badge {{
        font-size: 0.65rem;
        background: {CYAN_MUTED};
        color: {CYAN};
        padding: 2px 8px;
        border-radius: 20px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ── Preset pill buttons ── */
    .preset-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 8px 0;
    }}

    /* ── Function reference cards ── */
    .fn-card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85em;
        transition: border-color 0.2s ease;
    }}
    .fn-card:hover {{
        border-color: {BORDER_ACCENT};
    }}
    .fn-card .fn-name {{
        color: {CYAN};
        font-weight: 600;
    }}
    .fn-card .fn-args {{
        color: {TEXT_SECONDARY};
        font-weight: 400;
    }}
    .fn-card .fn-desc {{
        font-family: 'Inter', sans-serif;
        font-size: 0.85em;
        color: {TEXT_DIM};
        margin-top: 2px;
    }}

    /* ── Walk-forward result cards ── */
    .wf-card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }}
    .wf-card.good {{ border-left: 3px solid {GREEN}; }}
    .wf-card.warn {{ border-left: 3px solid {GOLD}; }}
    .wf-card.bad  {{ border-left: 3px solid {RED}; }}
    .wf-card .wf-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5em;
        font-weight: 700;
    }}
    .wf-card .wf-label {{
        font-size: 0.7em;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }}

    /* ── Streamlit overrides ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: {BG_CARD};
        border-radius: 8px;
        padding: 4px;
        border: 1px solid {BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 500;
        font-size: 0.85rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: {BG_PRIMARY} !important;
        border: 1px solid {BORDER_ACCENT};
    }}
    div[data-testid="stMetric"] {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 12px 16px;
    }}
    div[data-testid="stMetric"] label {{
        color: {TEXT_SECONDARY} !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.3rem !important;
    }}
    .stDataFrame {{
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}

    /* ── Quick action buttons ── */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }}
    .stDownloadButton > button {{
        background: linear-gradient(135deg, #1a3a4a 0%, #162d3e 100%);
        border: 1px solid {BORDER_ACCENT};
        border-radius: 8px;
        font-weight: 500;
    }}
    .stDownloadButton > button:hover {{
        border-color: {CYAN};
        box-shadow: 0 2px 12px rgba(0, 210, 255, 0.15);
    }}

    /* ── Dark mode for ALL inputs ── */
    /* Text inputs & text areas */
    .stTextArea textarea,
    .stTextInput input,
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {{
        background-color: {BG_CARD} !important;
        color: {TEXT_PRIMARY} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        caret-color: {CYAN} !important;
    }}
    .stTextArea textarea:focus,
    .stTextInput input:focus {{
        border-color: {BORDER_ACCENT} !important;
        box-shadow: 0 0 0 1px {BORDER_ACCENT} !important;
    }}

    /* Number inputs */
    div[data-testid="stNumberInput"] input {{
        background-color: {BG_CARD} !important;
        color: {TEXT_PRIMARY} !important;
        border: 1px solid {BORDER} !important;
    }}
    div[data-testid="stNumberInput"] button {{
        background-color: {BG_CARD} !important;
        color: {TEXT_SECONDARY} !important;
        border-color: {BORDER} !important;
    }}
    div[data-testid="stNumberInput"] button:hover {{
        background-color: {BG_CARD_HOVER} !important;
        color: {TEXT_PRIMARY} !important;
    }}

    /* Select boxes / dropdowns */
    div[data-baseweb="select"] > div {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    div[data-baseweb="popover"] > div {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER} !important;
    }}
    div[data-baseweb="menu"] {{
        background-color: {BG_CARD} !important;
    }}
    div[role="option"] {{
        background-color: {BG_CARD} !important;
        color: {TEXT_PRIMARY} !important;
    }}
    div[role="option"]:hover,
    div[role="option"][aria-selected="true"] {{
        background-color: {BG_CARD_HOVER} !important;
    }}

    /* File uploader */
    div[data-testid="stFileUploader"] section {{
        background-color: {BG_CARD} !important;
        border: 1px dashed {BORDER_ACCENT} !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stFileUploader"] section:hover {{
        border-color: {CYAN} !important;
    }}

    /* Expander */
    details[data-testid="stExpander"] {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
    }}
    details[data-testid="stExpander"] summary {{
        color: {TEXT_SECONDARY} !important;
    }}
    details[data-testid="stExpander"] summary:hover {{
        color: {TEXT_PRIMARY} !important;
    }}

    /* Radio buttons */
    div[data-testid="stRadio"] label span {{
        color: {TEXT_PRIMARY} !important;
    }}

    /* Sliders */
    div[data-testid="stSlider"] label {{
        color: {TEXT_SECONDARY} !important;
    }}

    /* Labels for all widgets */
    .stTextArea label,
    .stTextInput label,
    .stSelectbox label,
    .stMultiSelect label,
    .stSlider label,
    div[data-testid="stNumberInput"] label {{
        color: {TEXT_SECONDARY} !important;
    }}

    /* Info/success/error boxes */
    div[data-testid="stAlert"] {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER} !important;
        color: {TEXT_PRIMARY} !important;
    }}

    /* Sidebar inputs too */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {{
        background-color: #0a0e14 !important;
        color: {TEXT_PRIMARY} !important;
        border-color: {BORDER} !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button {{
        background-color: #0a0e14 !important;
        color: {TEXT_SECONDARY} !important;
        border-color: {BORDER} !important;
    }}

    /* Code blocks in Function Reference */
    .stCodeBlock, pre {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER} !important;
    }}

    /* ── Hide Streamlit branding ── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{
        background: {BG_PRIMARY};
        border-bottom: 1px solid {BORDER};
    }}

    /* ── Responsive tweaks ── */
    @media (max-width: 768px) {{
        .metric-card {{ padding: 10px 8px; }}
        .metric-value {{ font-size: 1.2em; }}
        .dashboard-header h1 {{ font-size: 1.4rem; }}
    }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Registry singleton
# ------------------------------------------------------------------

def get_repository() -> Repository:
    """Get the shared repository instance."""
    if "repository" not in st.session_state:
        st.session_state["repository"] = Repository()
    return st.session_state["repository"]


def get_registry() -> DynamicRegistry:
    """Create and cache the dynamic function registry."""
    if "registry" not in st.session_state:
        repo = get_repository()
        reg = DynamicRegistry(repo)
        register_std_lib(reg)
        register_extended_indicators(reg)
        reg.load_custom_indicators()
        st.session_state["registry"] = reg
    return st.session_state["registry"]


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
    st.sidebar.markdown("""
    <div style="text-align:center; padding: 8px 0 4px 0;">
        <span style="font-size: 1.6em;">📈</span><br>
        <span style="font-size: 1rem; font-weight: 700; letter-spacing: 1px;">LECAT</span><br>
        <span style="font-size: 0.65rem; color: #8b949e; letter-spacing: 2px; text-transform: uppercase;">Quantitative Dashboard</span>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Data source selection
    st.sidebar.markdown("##### 📊 Data Source")
    data_source = st.sidebar.radio(
        "Data Source",
        ["Upload CSV", "Database", "Generate Random"],
        index=2,
        label_visibility="collapsed",
    )

    ctx = None
    data_dict = None

    if data_source == "Upload CSV":
        uploaded = st.sidebar.file_uploader(
            "Upload OHLCV CSV",
            type=["csv"],
            help="Expected columns: Date, Open, High, Low, Close, Volume",
        )
        save_to_db = st.sidebar.checkbox("Save to database", value=True)
        if uploaded is not None:
            try:
                data_dict = load_csv_data(uploaded.getvalue(), uploaded.name)
                ctx = data_to_context(data_dict)
                st.sidebar.success(f"✅ {ctx.total_bars:,} bars — {data_dict['symbol']}")
                # Persist to DB
                if save_to_db:
                    _save_csv_to_db(data_dict)
            except Exception as e:
                st.sidebar.error(f"❌ {e}")
        else:
            st.sidebar.info("👆 Upload a CSV file to begin")

    elif data_source == "Database":
        repo = get_repository()
        symbols = repo.get_symbols()
        if symbols:
            selected_symbol = st.sidebar.selectbox("Select Asset", symbols)
            if selected_symbol:
                try:
                    ctx = load_from_db(selected_symbol)
                    st.sidebar.success(f"✅ {ctx.total_bars:,} bars — {selected_symbol}")
                except Exception as e:
                    st.sidebar.error(f"❌ {e}")
        else:
            st.sidebar.info("No assets yet. Upload a CSV first.")

    else:
        num_bars = st.sidebar.slider("Number of Bars", 100, 10000, 1000, step=100)
        seed = st.sidebar.number_input("Random Seed", value=42, step=1)
        ctx = generate_random_ohlcv(num_bars, seed=int(seed))

    st.sidebar.markdown("---")

    # Settings
    st.sidebar.markdown("##### ⚙️ Settings")
    initial_capital = st.sidebar.number_input(
        "Initial Capital ($)", value=10000, step=1000, min_value=100
    )

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<div style="text-align:center; font-size: 0.7rem; color: #484f58;">'
        'LECAT v2.0.0 · MIT License'
        '</div>',
        unsafe_allow_html=True,
    )

    return ctx, initial_capital


# ------------------------------------------------------------------
# Lab Mode
# ------------------------------------------------------------------

def render_lab_mode(ctx: MarketContext, initial_capital: float):
    """Render the Lab mode tab for manual strategy testing."""
    _section_header("🔬", "Strategy Lab", "Interactive")
    st.caption("Write a LECAT expression and click **Run Backtest** to see results.")

    # Presets as horizontal pills ABOVE the input
    st.markdown("**Quick Presets:**")
    presets = {
        "RSI Overbought": "RSI(14) > 70",
        "SMA Cross": "PRICE > SMA(50)",
        "Bollinger Band": "PRICE > BB_UPPER(20, 2.0)",
        "MACD Bull": "MACD(12, 26, 9) > 0",
        "EMA Crossover ↑": "EMA(10) > EMA(50) AND EMA(10)[1] <= EMA(50)[1]",
    }
    preset_cols = st.columns(len(presets))
    for col, (label, expr) in zip(preset_cols, presets.items()):
        with col:
            if st.button(label, key=f"preset_{label}", use_container_width=True):
                st.session_state["lab_expression"] = expr
                st.rerun()

    # Expression input + Run button
    col_input, col_run = st.columns([5, 1])
    with col_input:
        expression = st.text_area(
            "LECAT Expression",
            value=st.session_state.get("lab_expression", "RSI(14) > 70 AND PRICE > SMA(50)"),
            height=68,
            placeholder="e.g., RSI(14) > 70 AND PRICE > SMA(50)",
            label_visibility="collapsed",
        )
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        run_clicked = st.button("▶ Run Backtest", type="primary", use_container_width=True)

    # Strategy JSON upload (collapsed by default)
    with st.expander("📁 Import Strategy from JSON"):
        uploaded_json = st.file_uploader(
            "Upload Strategy JSON",
            type=["json"],
            help="Upload a previously saved strategy to auto-populate the expression",
            key="lab_json_upload",
            label_visibility="collapsed",
        )
        if uploaded_json is not None:
            try:
                import json
                strategy_data = json.loads(uploaded_json.getvalue())
                if "expression" in strategy_data:
                    st.session_state["lab_expression"] = strategy_data["expression"]
                    st.success(f"✅ Loaded: **{strategy_data.get('name', 'Unknown')}**")
                    st.rerun()
                else:
                    st.error("Invalid file: missing 'expression' field")
            except Exception as e:
                st.error(f"Failed to load: {e}")

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

        # Action row: Download
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
    """Render the metrics row with styled cards."""
    cols = st.columns(6)

    is_positive = fitness.total_return_pct >= 0
    ret_class = "positive" if is_positive else "negative"
    sharpe_class = "positive" if fitness.sharpe_ratio > 0 else "negative"

    metrics = [
        ("Total Return", f"{fitness.total_return_pct:+.2f}%", ret_class),
        ("Sharpe Ratio", f"{fitness.sharpe_ratio:.3f}", sharpe_class),
        ("Win Rate", f"{fitness.win_rate:.0%}", ""),
        ("Trades", f"{fitness.num_trades}", ""),
        ("Max Drawdown", f"{fitness.max_drawdown_pct:.1f}%", "negative" if fitness.max_drawdown_pct < -5 else ""),
        ("Fitness Score", f"{fitness.fitness_score:.4f}", "positive" if fitness.fitness_score > 0 else ""),
    ]

    for col, (label, value, css_class) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value {css_class}">{value}</div>
            </div>
            """, unsafe_allow_html=True)


def _render_candlestick_chart(result, ctx: MarketContext, expression: str, fitness: FitnessResult):
    """Render an interactive Plotly candlestick chart with signal overlays."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=[f"Price Chart — {expression}", "Volume", "Signal"],
        row_heights=[0.6, 0.2, 0.2],
    )

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
            increasing_line_color=CYAN,
            decreasing_line_color=RED,
        ),
        row=1, col=1,
    )

    # Buy signals
    buy_x = [i for i, s in enumerate(result.signals) if s]
    buy_y = [float(ctx.low[i]) * 0.998 for i in buy_x]
    fig.add_trace(
        go.Scatter(
            x=buy_x, y=buy_y,
            mode="markers",
            marker=dict(symbol="triangle-up", size=8, color=GREEN),
            name="Signal=True",
        ),
        row=1, col=1,
    )

    # Volume bars
    vol_colors = [CYAN if c > o else RED for c, o in zip(ctx.close, ctx.open)]
    fig.add_trace(
        go.Bar(x=x, y=list(ctx.volume), marker_color=vol_colors, name="Volume", opacity=0.4),
        row=2, col=1,
    )

    # Signal binary plot
    sig_colors = [GREEN if s else "#1a1a2e" for s in result.signals]
    fig.add_trace(
        go.Bar(x=x, y=[1 if s else 0 for s in result.signals],
               marker_color=sig_colors, name="Signal", opacity=0.7),
        row=3, col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        height=680,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11)),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=20, t=60, b=30),
        paper_bgcolor=BG_PRIMARY,
        plot_bgcolor=BG_PRIMARY,
        font=dict(family="Inter, sans-serif", size=11),
    )

    fig.update_xaxes(gridcolor=BORDER, zeroline=False)
    fig.update_yaxes(gridcolor=BORDER, zeroline=False)

    # Style subplot titles
    for annotation in fig.layout.annotations:
        annotation.font = dict(size=12, color=TEXT_SECONDARY)

    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------
# Evolution Mode
# ------------------------------------------------------------------

def render_evolution_mode(ctx: MarketContext, initial_capital: float):
    """Render the Evolution mode tab for genetic optimization."""
    _section_header("🧬", "Evolution Engine", "Genetic Algorithm")
    st.caption("Configure and run the genetic algorithm to discover optimal strategies.")

    # Config — two rows for visual balance
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        generations = st.number_input("Generations", value=5, min_value=1, max_value=100, step=1)
    with col2:
        pop_size = st.number_input("Population", value=50, min_value=10, max_value=1000, step=10)
    with col3:
        mutation_rate = st.slider("Mutation Rate", 0.0, 1.0, 0.3, 0.05)
    with col4:
        split_ratio = st.slider("Train / Test", 0.5, 0.9, 0.7, 0.05)

    # Action row
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        evolve_clicked = st.button("🧬 Start Evolution", type="primary", use_container_width=True)
    with col_info:
        train_bars = int(ctx.total_bars * split_ratio)
        test_bars = ctx.total_bars - train_bars
        st.info(f"Train: **{train_bars:,} bars** ({split_ratio:.0%}) · "
                f"Test: **{test_bars:,} bars** ({1-split_ratio:.0%})")

    if evolve_clicked:
        _run_evolution(ctx, generations, pop_size, mutation_rate, split_ratio, initial_capital)

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

    start = time.perf_counter()
    try:
        result = optimizer.run(generations=generations, split_ratio=split_ratio)
        elapsed = time.perf_counter() - start

        progress_bar.progress(1.0, text="✅ Evolution complete!")

        hall_of_fame = []
        registry = get_registry()
        evaluator = Evaluator(registry)
        backtester = Backtester(evaluator, registry)

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

        status_text.success(f"✅ Completed {generations} generations in **{elapsed:.1f}s**")

    except Exception as e:
        progress_bar.empty()
        st.error(f"Evolution failed: {e}")


def _render_hall_of_fame(ctx: MarketContext, initial_capital: float):
    """Render the Hall of Fame leaderboard."""
    st.markdown("---")
    _section_header("🏆", "Hall of Fame", "Best Strategies")

    hall = st.session_state.get("evolution_results", [])
    result = st.session_state.get("evolution_result")

    if not hall:
        st.info("No strategies found. Try running evolution with more generations.")
        return

    # Walk-forward results as styled cards
    if result and result.walk_forward:
        wf = result.walk_forward
        ratio = wf.overfit_ratio
        ratio_grade = "good" if ratio > 0.7 else ("warn" if ratio > 0.4 else "bad")
        ratio_color = GREEN if ratio > 0.7 else (GOLD if ratio > 0.4 else RED)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="wf-card good">
                <div class="wf-label">Train Sharpe</div>
                <div class="wf-value" style="color: {CYAN};">{wf.train_fitness.sharpe_ratio:.3f}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            test_color = GREEN if wf.test_fitness.sharpe_ratio > 0 else RED
            st.markdown(f"""
            <div class="wf-card {'good' if wf.test_fitness.sharpe_ratio > 0 else 'bad'}">
                <div class="wf-label">Test Sharpe</div>
                <div class="wf-value" style="color: {test_color};">{wf.test_fitness.sharpe_ratio:.3f}</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="wf-card {ratio_grade}">
                <div class="wf-label">Overfit Ratio</div>
                <div class="wf-value" style="color: {ratio_color};">{ratio:.2f}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

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

    # Strategy actions
    if hall:
        selected = st.selectbox(
            "Select strategy",
            [h["expression"] for h in hall],
            label_visibility="collapsed",
        )

        col_viz, col_dl, col_spacer = st.columns([1, 1, 3])
        with col_viz:
            if selected and st.button("📈 Show Chart", use_container_width=True):
                _run_lab_backtest(selected, ctx, initial_capital)
        with col_dl:
            if selected:
                sel_data = next((h for h in hall if h["expression"] == selected), None)
                if sel_data:
                    json_str = strategy_to_json_string(
                        selected, sel_data,
                        name=f"Evolved Strategy #{sel_data.get('rank', 1)}"
                    )
                    st.download_button(
                        "💾 Download",
                        data=json_str,
                        file_name="evolved_strategy.json",
                        mime="application/json",
                        use_container_width=True,
                    )


# ------------------------------------------------------------------
# Data Overview
# ------------------------------------------------------------------

def render_data_overview(ctx: MarketContext):
    """Render a compact data overview section."""

    # Stats row with styled cards
    price_min = min(ctx.close)
    price_max = max(ctx.close)
    first = float(ctx.close[0])
    last = float(ctx.close[-1])
    change = ((last - first) / first) * 100 if first > 0 else 0
    change_color = GREEN if change >= 0 else RED

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""<div class="data-stat">
            <div class="stat-label">Total Bars</div>
            <div class="stat-value">{ctx.total_bars:,}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="data-stat">
            <div class="stat-label">Price Low</div>
            <div class="stat-value">${price_min:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="data-stat">
            <div class="stat-label">Price High</div>
            <div class="stat-value">${price_max:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="data-stat">
            <div class="stat-label">Period Return</div>
            <div class="stat-value" style="color: {change_color};">{change:+.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class="data-stat">
            <div class="stat-label">Symbol</div>
            <div class="stat-value">{ctx.symbol or 'Generated'}</div>
        </div>""", unsafe_allow_html=True)

    # Mini sparkline chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=list(ctx.close),
        mode="lines",
        line=dict(color=CYAN, width=1.5),
        fill="tozeroy",
        fillcolor=CYAN_MUTED,
        name="Close",
        hovertemplate="Bar %{x}<br>Close: $%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        height=160,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, showticklabels=False),
        font=dict(family="Inter, sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------
# Available Functions Reference
# ------------------------------------------------------------------

INDICATOR_DESCRIPTIONS = {
    "PRICE": "Current close price",
    "OPEN": "Current bar open price",
    "HIGH": "Current bar high price",
    "LOW": "Current bar low price",
    "VOLUME": "Current bar volume",
    "close": "Alias for PRICE",
    "open": "Alias for OPEN",
    "high": "Alias for HIGH",
    "low": "Alias for LOW",
    "volume": "Alias for VOLUME",
    "SMA": "Simple Moving Average",
    "EMA": "Exponential Moving Average",
    "RSI": "Relative Strength Index (0–100)",
    "ATR": "Average True Range (volatility)",
    "MACD": "MACD Histogram (>0 bullish)",
    "BB_UPPER": "Bollinger Band Upper",
    "BB_LOWER": "Bollinger Band Lower",
    "STOCH": "Stochastic Oscillator %D (0–100)",
}


def render_function_reference():
    """Render the available functions reference as compact cards."""
    _section_header("📚", "Function Reference", f"{len(INDICATOR_DESCRIPTIONS)} Functions")

    registry = get_registry()
    functions = registry.get_available_functions()

    accessors = [f for f in functions if not f.arg_schema]
    indicators = [f for f in functions if f.arg_schema]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Market Data Accessors")
        for fn in accessors:
            desc = INDICATOR_DESCRIPTIONS.get(fn.name, "")
            st.markdown(f"""<div class="fn-card">
                <span class="fn-name">{fn.name}</span>
                <div class="fn-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("##### Technical Indicators")
        for fn in indicators:
            args_str = ", ".join(
                f"{a['name']}={a.get('default', '?')}"
                for a in fn.arg_schema
            )
            desc = INDICATOR_DESCRIPTIONS.get(fn.name, "")
            st.markdown(f"""<div class="fn-card">
                <span class="fn-name">{fn.name}</span><span class="fn-args">({args_str})</span>
                <div class="fn-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # Cheat sheet
    st.markdown("---")
    st.markdown("##### ⚡ Quick Syntax Reference")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**Operators**")
        st.code("AND  OR  NOT\n>  <  >=  <=  ==  !=", language=None)
    with col_b:
        st.markdown("**Context Shifting**")
        st.code("PRICE[1]     # 1 bar ago\nRSI(14)[3]   # 3 bars ago", language=None)
    with col_c:
        st.markdown("**Example Strategy**")
        st.code("EMA(10) > EMA(50)\n  AND EMA(10)[1] <= EMA(50)[1]", language=None)


# ------------------------------------------------------------------
# Indicator Manager
# ------------------------------------------------------------------

def render_indicator_manager(ctx: MarketContext):
    """Render the Indicator Manager tab for CRUD on custom indicators."""
    _section_header("🛠️", "Indicator Manager", "Custom")
    st.caption("Create, edit, and test custom indicators stored in the database.")

    repo = get_repository()
    indicators = repo.get_all_indicators()

    col_list, col_editor = st.columns([1, 2])

    # ---------- Left Column: Indicator List ----------
    with col_list:
        st.markdown("##### 📂 Saved Indicators")
        if not indicators:
            st.info("No custom indicators yet.")
        for ind in indicators:
            label = f"**{ind['name']}**"
            if ind['args']:
                label += f" ({', '.join(ind['args'])})"
            if st.button(label, key=f"sel_{ind['name']}", use_container_width=True):
                st.session_state["mgr_name"] = ind["name"]
                st.session_state["mgr_args"] = ", ".join(ind["args"])
                st.session_state["mgr_formula"] = ind["formula"]
                st.session_state["mgr_desc"] = ind.get("description", "")
                st.rerun()

        st.markdown("---")
        if st.button("➕ New Indicator", use_container_width=True):
            st.session_state["mgr_name"] = ""
            st.session_state["mgr_args"] = ""
            st.session_state["mgr_formula"] = ""
            st.session_state["mgr_desc"] = ""
            st.rerun()

    # ---------- Right Column: Editor ----------
    with col_editor:
        st.markdown("##### ✏️ Indicator Editor")

        name = st.text_input(
            "Name (e.g. AVG_PRICE)",
            value=st.session_state.get("mgr_name", ""),
            placeholder="MY_INDICATOR",
        ).strip().upper()

        args_str = st.text_input(
            "Arguments (comma-separated, leave empty for none)",
            value=st.session_state.get("mgr_args", ""),
            placeholder="fast, slow",
        ).strip()

        formula = st.text_area(
            "Formula (LECAT expression)",
            value=st.session_state.get("mgr_formula", ""),
            height=80,
            placeholder="e.g., (HIGH + LOW) / 2",
        ).strip()

        description = st.text_input(
            "Description (optional)",
            value=st.session_state.get("mgr_desc", ""),
            placeholder="Average of high and low prices",
        ).strip()

        # Parse args
        args_list = [a.strip() for a in args_str.split(",") if a.strip()] if args_str else []

        # Action buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            save_clicked = st.button("💾 Save", type="primary", use_container_width=True,
                                     disabled=not name or not formula)
        with btn_col2:
            test_clicked = st.button("🧪 Test", use_container_width=True,
                                     disabled=not formula)
        with btn_col3:
            delete_clicked = st.button("🗑️ Delete", use_container_width=True,
                                       disabled=not name)

        if save_clicked and name and formula:
            repo.save_indicator(name, args_list, formula, description)
            # Reload registry to pick up the new indicator
            registry = get_registry()
            registry.reload_custom_indicators()
            st.success(f"✅ Saved indicator **{name}**")
            st.session_state["mgr_name"] = name
            st.session_state["mgr_args"] = args_str
            st.session_state["mgr_formula"] = formula
            st.session_state["mgr_desc"] = description

        if test_clicked and formula:
            _test_indicator(name or "TEST", args_list, formula, ctx)

        if delete_clicked and name:
            if repo.delete_indicator(name):
                registry = get_registry()
                registry.reload_custom_indicators()
                st.success(f"🗑️ Deleted **{name}**")
                st.session_state["mgr_name"] = ""
                st.session_state["mgr_formula"] = ""
                st.session_state["mgr_args"] = ""
                st.session_state["mgr_desc"] = ""
            else:
                st.warning(f"Indicator '{name}' not found.")


def _test_indicator(name: str, args_list: list, formula: str, ctx: MarketContext):
    """Test a custom indicator formula against the current data."""
    try:
        from lecat.dynamic_registry import _substitute_args, _evaluate_composite

        # Build test args with default values (use 14 instead of 0 to avoid ZeroDivisionError in MA/RSI etc)
        test_args = {a: 14 for a in args_list}
        resolved = _substitute_args(formula, args_list, test_args)

        # Try to compile
        tokens = Lexer(resolved).tokenize()
        ast = Parser(tokens).parse()

        # Evaluate at the last bar
        registry = get_registry()
        evaluator = Evaluator(registry)
        result = evaluator.evaluate(ast, ctx)

        st.success(f"✅ Formula compiles OK. Result at last bar: **{result}**")

    except Exception as e:
        st.error(f"❌ **{type(e).__name__}:** {e}")
        st.info("💡 Check your formula syntax. Variables like `fast` will be replaced with argument values.")


def _save_csv_to_db(data_dict: dict) -> None:
    """Save uploaded CSV data to the SQLite database."""
    repo = get_repository()
    symbol = data_dict.get("symbol", "UNKNOWN")
    n = data_dict["total_bars"]
    rows = []
    for i in range(n):
        rows.append({
            "timestamp": f"2020-01-01T{i:06d}",  # Synthetic timestamps
            "open": data_dict["open"][i],
            "high": data_dict["high"][i],
            "low": data_dict["low"][i],
            "close": data_dict["close"][i],
            "volume": data_dict["volume"][i],
        })
    inserted = repo.save_market_data(rows, symbol)
    if inserted > 0:
        st.sidebar.caption(f"💾 Saved {inserted:,} bars to database")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _section_header(icon: str, title: str, badge: str = ""):
    """Render a styled section header."""
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="section-header">
        <span class="icon">{icon}</span>
        <span class="title">{title}</span>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Main App
# ------------------------------------------------------------------

def main():
    """Main application entry point."""
    ctx, initial_capital = render_sidebar()

    # Header
    st.markdown("""
    <div class="dashboard-header">
        <h1>📈 LECAT</h1>
        <div class="subtitle">Logical Expression Compiler for Algorithmic Trading</div>
    </div>
    """, unsafe_allow_html=True)

    if ctx is None:
        st.warning("⬅️ Please upload data or generate random data from the sidebar to begin.")
        return

    # Data overview
    render_data_overview(ctx)

    # Mode tabs
    tab_lab, tab_evolution, tab_indicators, tab_reference = st.tabs([
        "🔬 Strategy Lab",
        "🧬 Evolution Engine",
        "🛠️ Indicator Manager",
        "📚 Function Reference",
    ])

    with tab_lab:
        render_lab_mode(ctx, initial_capital)

    with tab_evolution:
        render_evolution_mode(ctx, initial_capital)

    with tab_indicators:
        render_indicator_manager(ctx)

    with tab_reference:
        render_function_reference()


if __name__ == "__main__":
    main()
