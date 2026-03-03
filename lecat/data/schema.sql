-- LECAT Database Schema
-- SQLite3 database for market data, custom indicators, and optimization results.

-- 1. Market Data (The Raw Material)
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1D',
    timestamp DATETIME NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol
    ON market_data(symbol, timeframe);

-- 2. Custom Indicators (The Logic)
-- Stores DSL formulas like "RSI(14) + RSI(21)"
CREATE TABLE IF NOT EXISTS indicators (
    name TEXT PRIMARY KEY,
    args TEXT NOT NULL DEFAULT '[]',       -- JSON array: ["fast", "slow"]
    formula TEXT NOT NULL,                 -- DSL expression: "SMA(fast) > SMA(slow)"
    description TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Optimization Results (The Memory)
-- Stores the history of "Hall of Fame" strategies
CREATE TABLE IF NOT EXISTS strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expression TEXT NOT NULL,
    metrics TEXT NOT NULL,                 -- JSON: {"sharpe": 1.5, "return": 20.4}
    dataset_symbol TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_strategy_results_timestamp
    ON strategy_results(timestamp DESC);
