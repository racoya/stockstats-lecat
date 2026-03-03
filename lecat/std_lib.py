"""Standard Library — Built-in indicator functions for LECAT.

Provides basic market data accessors and technical indicators registered
into a FunctionRegistry. All functions use pure Python (no numpy required).

See docs/03_Function_Registry_API.md §6 for the full built-in function catalog.
"""

from __future__ import annotations

from lecat.context import MarketContext
from lecat.registry import FunctionRegistry, FunctionResult


def register_std_lib(registry: FunctionRegistry) -> None:
    """Register all standard library functions into the given registry."""

    # ------------------------------------------------------------------
    # Market Data Accessors (zero-arg)
    # ------------------------------------------------------------------

    @registry.register(
        name="PRICE",
        description="Current bar's close price",
        arg_schema=[],
        min_bars_required=lambda _: 1,
    )
    def price_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.close[ctx.bar_index]))

    @registry.register(
        name="OPEN",
        description="Current bar's open price",
        arg_schema=[],
        min_bars_required=lambda _: 1,
    )
    def open_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.open[ctx.bar_index]))

    @registry.register(
        name="HIGH",
        description="Current bar's high price",
        arg_schema=[],
        min_bars_required=lambda _: 1,
    )
    def high_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.high[ctx.bar_index]))

    @registry.register(
        name="LOW",
        description="Current bar's low price",
        arg_schema=[],
        min_bars_required=lambda _: 1,
    )
    def low_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.low[ctx.bar_index]))

    @registry.register(
        name="VOLUME",
        description="Current bar's volume",
        arg_schema=[],
        min_bars_required=lambda _: 1,
    )
    def volume_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.volume[ctx.bar_index]))

    # ------------------------------------------------------------------
    # Also register lowercase aliases so identifiers like `close` work
    # ------------------------------------------------------------------

    @registry.register(name="close", description="Alias for close price")
    def close_alias(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.close[ctx.bar_index]))

    @registry.register(name="open", description="Alias for open price")
    def open_alias(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.open[ctx.bar_index]))

    @registry.register(name="high", description="Alias for high price")
    def high_alias(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.high[ctx.bar_index]))

    @registry.register(name="low", description="Alias for low price")
    def low_alias(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.low[ctx.bar_index]))

    @registry.register(name="volume", description="Alias for volume")
    def volume_alias(args: dict, ctx: MarketContext) -> FunctionResult:
        return FunctionResult.success(float(ctx.volume[ctx.bar_index]))

    # ------------------------------------------------------------------
    # Technical Indicators
    # ------------------------------------------------------------------

    @registry.register(
        name="SMA",
        description="Simple Moving Average",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 20, "min": 1, "max": 500}
        ],
        min_bars_required=lambda args: args.get("period", 20),
    )
    def sma_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        idx = ctx.bar_index

        if idx < period - 1:
            return FunctionResult.insufficient_data()

        window = ctx.close[idx - period + 1 : idx + 1]
        avg = sum(window) / period
        return FunctionResult.success(avg)

    @registry.register(
        name="EMA",
        description="Exponential Moving Average",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 20, "min": 1, "max": 500}
        ],
        min_bars_required=lambda args: args.get("period", 20),
    )
    def ema_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        idx = ctx.bar_index

        if idx < period - 1:
            return FunctionResult.insufficient_data()

        # Start with SMA of first `period` bars, then apply EMA formula
        multiplier = 2.0 / (period + 1)
        # Initial SMA
        ema = sum(ctx.close[:period]) / period
        # Apply EMA from period onwards up to bar_index
        for i in range(period, idx + 1):
            ema = (float(ctx.close[i]) - ema) * multiplier + ema
        return FunctionResult.success(ema)

    @registry.register(
        name="RSI",
        description="Relative Strength Index",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 14, "min": 1, "max": 500}
        ],
        min_bars_required=lambda args: args.get("period", 14) + 1,
    )
    def rsi_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        idx = ctx.bar_index

        if idx < period:
            return FunctionResult.insufficient_data()

        # Calculate price changes
        gains = 0.0
        losses = 0.0
        for i in range(idx - period + 1, idx + 1):
            change = float(ctx.close[i]) - float(ctx.close[i - 1])
            if change > 0:
                gains += change
            else:
                losses += abs(change)

        avg_gain = gains / period
        avg_loss = losses / period

        if avg_loss == 0:
            return FunctionResult.success(100.0)

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return FunctionResult.success(rsi)

    @registry.register(
        name="ATR",
        description="Average True Range",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 14, "min": 1, "max": 500}
        ],
        min_bars_required=lambda args: args.get("period", 14) + 1,
    )
    def atr_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        idx = ctx.bar_index

        if idx < period:
            return FunctionResult.insufficient_data()

        true_ranges = []
        for i in range(idx - period + 1, idx + 1):
            high = float(ctx.high[i])
            low = float(ctx.low[i])
            prev_close = float(ctx.close[i - 1])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        atr = sum(true_ranges) / period
        return FunctionResult.success(atr)
