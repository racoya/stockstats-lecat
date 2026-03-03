"""Seed the LECAT database with sample BTC-USD data and example custom indicators."""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lecat.repository import Repository


def seed_btc_data(repo: Repository, days: int = 365) -> int:
    """Generate realistic BTC-USD daily data (Jan 2024 – Dec 2024).

    Uses geometric Brownian motion with mean-reverting volatility
    to produce realistic-looking price action.
    """
    random.seed(42)
    price = 42_000.0  # BTC starting price Jan 2024
    rows = []

    for d in range(days):
        month = (d // 30) + 1
        day = (d % 30) + 1
        if month > 12:
            month = 12
            day = min(day, 28)
        timestamp = f"2024-{month:02d}-{day:02d}"

        # Daily return with slight upward drift + volatility clustering
        drift = 0.0003
        vol = 0.025 * (1 + 0.5 * math.sin(d / 30))
        ret = drift + vol * random.gauss(0, 1)
        price *= (1 + ret)

        # Intraday range
        daily_vol = abs(ret) + 0.01
        high = price * (1 + daily_vol * random.uniform(0.3, 1.0))
        low = price * (1 - daily_vol * random.uniform(0.3, 1.0))
        opn = low + (high - low) * random.uniform(0.2, 0.8)
        volume = random.uniform(15_000, 60_000) * (1 + abs(ret) * 20)

        rows.append({
            "timestamp": timestamp,
            "open": round(opn, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(price, 2),
            "volume": round(volume, 2),
        })

    return repo.save_market_data(rows, "BTC_USD")


def seed_indicators(repo: Repository) -> int:
    """Add example custom indicators to the database."""

    examples = [
        {
            "name": "RSI_OVERSOLD_BOUNCE",
            "args": ["period", "threshold"],
            "formula": "RSI(period) > threshold AND RSI(period)[1] <= threshold",
            "description": "Detects RSI crossing back above a threshold (oversold bounce). Uses context shifting [1] to find the exact crossover bar.",
        },
        {
            "name": "MACD_BULL_CROSS",
            "args": ["fast", "slow", "signal"],
            "formula": "MACD(fast, slow, signal) > 0 AND MACD(fast, slow, signal)[1] <= 0",
            "description": "MACD histogram crossing from negative to positive (bullish crossover). Context shift [1] compares current vs previous bar.",
        },
        {
            "name": "TREND_BREAKOUT",
            "args": ["short_ma", "long_ma"],
            "formula": "EMA(short_ma) > SMA(long_ma) AND EMA(short_ma)[1] <= SMA(long_ma)[1]",
            "description": "EMA/SMA golden cross: short EMA crossing above long SMA. Classic trend-following entry with context shifting.",
        },
        {
            "name": "MOMENTUM_SURGE",
            "args": [],
            "formula": "RSI(14) > 60 AND PRICE > EMA(20) AND MACD(12, 26, 9) > 0",
            "description": "Multi-indicator momentum confirmation: RSI bullish + price above EMA + MACD positive. No context shifting (snapshot condition).",
        },
        {
            "name": "REVERSAL_SIGNAL",
            "args": ["rsi_period"],
            "formula": "RSI(rsi_period) < 30 AND RSI(rsi_period)[1] >= 30 AND PRICE > SMA(50)",
            "description": "Mean reversion: RSI drops below 30 (context shift detects the cross) while price remains above the 50-SMA support.",
        },
    ]

    count = 0
    for ind in examples:
        repo.save_indicator(
            name=ind["name"],
            args=ind["args"],
            formula=ind["formula"],
            description=ind["description"],
        )
        count += 1

    return count


def main():
    repo = Repository()
    print("Seeding BTC-USD data...")
    bars = seed_btc_data(repo)
    print(f"  ✅ Inserted {bars:,} bars of BTC_USD data")

    print("Seeding example indicators...")
    count = seed_indicators(repo)
    print(f"  ✅ Created {count} custom indicators")

    # Verify
    symbols = repo.get_symbols()
    indicators = repo.get_all_indicators()
    print(f"\nDatabase summary:")
    print(f"  Symbols: {symbols}")
    print(f"  Custom indicators: {[i['name'] for i in indicators]}")


if __name__ == "__main__":
    main()
