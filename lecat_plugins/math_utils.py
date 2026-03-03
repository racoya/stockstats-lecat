"""Example Python Math Plugin.

Demonstrates how to write pure Python functions and register them natively 
into the LECAT engine for highly performant, custom mathematical indicators.
"""

from lecat.context import MarketContext
from lecat.registry import FunctionRegistry, FunctionResult

import math

def register_plugin(registry: FunctionRegistry) -> None:
    """Entry point called by the plugin loader."""

    @registry.register(
        name="HALF_SMA",
        description="Returns exactly half of the Simple Moving Average.",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 20, "min": 2, "max": 500}
        ],
        min_bars_required=lambda args: args.get("period", 20),
    )
    def half_sma_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        idx = ctx.bar_index

        if idx < period - 1:
            return FunctionResult.insufficient_data()

        # Complex math in native Python
        window = [float(ctx.close[i]) for i in range(idx - period + 1, idx + 1)]
        sma = sum(window) / period
        half_sma = sma / 2.0

        return FunctionResult.success(half_sma)


    @registry.register(
        name="LOG_RETURN",
        description="Calculates the logarithmic return over N periods.",
        arg_schema=[
            {"name": "period", "type": "integer", "required": True, "default": 1, "min": 1, "max": 100}
        ],
        min_bars_required=lambda args: args.get("period", 1) + 1,
    )
    def log_return_handler(args: dict, ctx: MarketContext) -> FunctionResult:
        period = int(args["period"])
        idx = ctx.bar_index

        if idx < period:
            return FunctionResult.insufficient_data()

        current_price = float(ctx.close[idx])
        past_price = float(ctx.close[idx - period])

        if past_price <= 0:
            return FunctionResult.success(0.0) # Avoid domain error for log(0)

        # Log return = ln(current / past)
        # Multiplying by 100 to make it a percentage for easier thresholding
        log_ret = math.log(current_price / past_price) * 100

        return FunctionResult.success(log_ret)
