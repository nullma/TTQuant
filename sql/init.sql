-- TTQuant 数据库初始化脚本

-- 启用 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Tick 数据表（高频数据）
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    last_price DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    exchange_time TIMESTAMPTZ,
    local_time TIMESTAMPTZ,
    PRIMARY KEY (time, symbol, exchange)
);

-- 转换为 hypertable（自动分区）
SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data (symbol, time DESC);

-- 设置压缩策略（7天后压缩）
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,exchange'
);

SELECT add_compression_policy('market_data', INTERVAL '7 days', if_not_exists => TRUE);

-- 2. K线数据表
CREATE TABLE IF NOT EXISTS klines (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    interval TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    PRIMARY KEY (time, symbol, exchange, interval)
);

SELECT create_hypertable('klines', 'time', if_not_exists => TRUE);

-- 3. 订单表
CREATE TABLE IF NOT EXISTS orders (
    time TIMESTAMPTZ NOT NULL,
    order_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price DOUBLE PRECISION,
    volume INTEGER,
    timestamp BIGINT,
    PRIMARY KEY (time, order_id)
);

SELECT create_hypertable('orders', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_orders_strategy ON orders (strategy_id, time DESC);

-- 4. 成交表
CREATE TABLE IF NOT EXISTS trades (
    time TIMESTAMPTZ NOT NULL,
    trade_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    filled_price DOUBLE PRECISION,
    filled_volume INTEGER,
    trade_time BIGINT,
    status TEXT,
    error_code INTEGER,
    error_message TEXT,
    PRIMARY KEY (time, trade_id)
);

SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades (strategy_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_order ON trades (order_id);

-- 5. 持仓快照表
CREATE TABLE IF NOT EXISTS positions (
    time TIMESTAMPTZ NOT NULL,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    position INTEGER,
    avg_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION,
    PRIMARY KEY (time, strategy_id, symbol)
);

SELECT create_hypertable('positions', 'time', if_not_exists => TRUE);

-- 6. 资金变化表
CREATE TABLE IF NOT EXISTS account_balance (
    time TIMESTAMPTZ NOT NULL,
    strategy_id TEXT NOT NULL,
    balance DOUBLE PRECISION,
    frozen DOUBLE PRECISION,
    available DOUBLE PRECISION,
    PRIMARY KEY (time, strategy_id)
);

SELECT create_hypertable('account_balance', 'time', if_not_exists => TRUE);

-- 7. 性能指标表
CREATE TABLE IF NOT EXISTS metrics (
    time TIMESTAMPTZ NOT NULL,
    component TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION,
    PRIMARY KEY (time, component, metric_name)
);

SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);

-- 数据保留策略（自动删除旧数据）
SELECT add_retention_policy('market_data', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics', INTERVAL '7 days', if_not_exists => TRUE);

-- 创建视图：最新持仓
CREATE OR REPLACE VIEW latest_positions AS
SELECT DISTINCT ON (strategy_id, symbol)
    strategy_id,
    symbol,
    position,
    avg_price,
    unrealized_pnl,
    time
FROM positions
ORDER BY strategy_id, symbol, time DESC;

-- 创建视图：策略统计
CREATE OR REPLACE VIEW strategy_stats AS
SELECT
    strategy_id,
    COUNT(*) as total_trades,
    SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_trades,
    SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected_trades,
    AVG(CASE WHEN status = 'FILLED' THEN filled_price ELSE NULL END) as avg_fill_price
FROM trades
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY strategy_id;

-- 完成
\echo 'TTQuant database initialized successfully!'
