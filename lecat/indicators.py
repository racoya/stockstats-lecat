"""Extended Indicator Library — Advanced technical indicators for LECAT.

Adds MACD, Bollinger Bands, and Stochastic Oscillator to the registry.
These supplement the base indicators (SMA, EMA, RSI, ATR) in std_lib.py.

All functions use pure Python (no numpy required).
"""

from __future__ import annotations

from lecat.context import MarketContext
from lecat.registry import FunctionRegistry, FunctionResult


def register_extended_indicators(registry: FunctionRegistry) -> None:
    """Register extended technical indicators into the given registry."""

    # ------------------------------------------------------------------
    # MACD (Moving Average Convergence Divergence)
    # ------------------------------------------------------------------

    @registry.register(
        name="MACD",
        description="MACD Histogram (fast EMA - slow EMA - signal EMA)",
        arg_schema=[
            {"name": "fast", "type": "integer", "required": True, "default": 12, "min": 2, "max": 100},
            {"name": "slow", "type": "integer", "required": True, "default": 26, "min": 2, "max": 200},
            {"name": "signal", "type": "integer", "required": True, "default": 9, "min": 2, "max": 50},
        ],
        min_bars_required=lambda args: args.get("slow", 26) + args.get("signal", 9),
    )
    def macd_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        fast_period = int(args["fast"])
        slow_period = int(args["slow"])
        signal_period = int(args["signal"])
        idx = ctx.bar_index

        min_bars = slow_period + signal_period
        if idx < min_bars - 1:
            return FunctionResult.insufficient_data()

        # Calculate fast and slow EMAs up to current bar
        fast_ema = _calc_ema(ctx.close, fast_period, idx)
        slow_ema = _calc_ema(ctx.close, slow_period, idx)

        # MACD line
        macd_line = fast_ema - slow_ema

        # For signal line, we need MACD values over signal_period bars
        macd_values = []
        for i in range(idx - signal_period + 1, idx + 1):
            if i < slow_period - 1:
                macd_values.append(0.0)
            else:
                f = _calc_ema(ctx.close, fast_period, i)
                s = _calc_ema(ctx.close, slow_period, i)
                macd_values.append(f - s)

        # Signal line = EMA of MACD values
        signal_ema = _ema_of_values(macd_values, signal_period)

        # Histogram = MACD line - Signal line
        histogram = macd_line - signal_ema
        return FunctionResult.success(histogram)

    # ------------------------------------------------------------------
    # Bollinger Bands
    # ------------------------------------------------------------------

    @registry.register(
        name="BB_UPPER",
        description="Bollinger Band Upper (SMA + std_dev * σ)",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 20, "min": 2, "max": 500},
            {"name": "std_dev", "type": "float", "required": True, "default": 2.0, "min": 0.5, "max": 5.0},
        ],
        min_bars_required=lambda args: args.get("period", 20),
    )
    def bb_upper_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        std_dev = float(args["std_dev"])
        idx = ctx.bar_index

        if idx < period - 1:
            return FunctionResult.insufficient_data()

        window = [float(ctx.close[i]) for i in range(idx - period + 1, idx + 1)]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5

        return FunctionResult.success(mean + std_dev * std)

    @registry.register(
        name="BB_LOWER",
        description="Bollinger Band Lower (SMA - std_dev * σ)",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 20, "min": 2, "max": 500},
            {"name": "std_dev", "type": "float", "required": True, "default": 2.0, "min": 0.5, "max": 5.0},
        ],
        min_bars_required=lambda args: args.get("period", 20),
    )
    def bb_lower_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        std_dev = float(args["std_dev"])
        idx = ctx.bar_index

        if idx < period - 1:
            return FunctionResult.insufficient_data()

        window = [float(ctx.close[i]) for i in range(idx - period + 1, idx + 1)]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5

        return FunctionResult.success(mean - std_dev * std)

    # ------------------------------------------------------------------
    # Stochastic Oscillator
    # ------------------------------------------------------------------

    @registry.register(
        name="STOCH",
        description="Stochastic Oscillator %K",
        arg_schema=[
            {"name": "k_period", "type": "integer", "required": True, "default": 14, "min": 1, "max": 500},
            {"name": "d_period", "type": "integer", "required": True, "default": 3, "min": 1, "max": 50},
        ],
        min_bars_required=lambda args: args.get("k_period", 14) + args.get("d_period", 3),
    )
    def stoch_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        k_period = int(args["k_period"])
        d_period = int(args["d_period"])
        idx = ctx.bar_index

        if idx < k_period + d_period - 2:
            return FunctionResult.insufficient_data()

        # Calculate %K for d_period bars ending at idx
        k_values = []
        for i in range(idx - d_period + 1, idx + 1):
            if i < k_period - 1:
                k_values.append(50.0)
            else:
                highest = max(float(ctx.high[j]) for j in range(i - k_period + 1, i + 1))
                lowest = min(float(ctx.low[j]) for j in range(i - k_period + 1, i + 1))
                if highest == lowest:
                    k_values.append(50.0)
                else:
                    k_pct = ((float(ctx.close[i]) - lowest) / (highest - lowest)) * 100
                    k_values.append(k_pct)

        # %D = SMA of %K
        d_value = sum(k_values) / len(k_values)
        return FunctionResult.success(d_value)


# ------------------------------------------------------------------
# Internal calculation helpers
# ------------------------------------------------------------------


def _calc_ema(data, period: int, end_idx: int) -> float:
    """Calculate EMA ending at end_idx."""
    multiplier = 2.0 / (period + 1)
    # Start with SMA of first `period` bars
    ema = sum(float(data[i]) for i in range(period)) / period
    # Apply EMA formula
    for i in range(period, end_idx + 1):
        ema = (float(data[i]) - ema) * multiplier + ema
    return ema


def _ema_of_values(values: list[float], period: int) -> float:
    """Calculate EMA of a list of values."""
    if len(values) < period:
        return sum(values) / len(values) if values else 0.0

    multiplier = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for i in range(period, len(values)):
        ema = (values[i] - ema) * multiplier + ema
    return ema
