# TTQuant 数据持久化功能

## 概述

TTQuant 使用 TimescaleDB（基于 PostgreSQL 的时序数据库）来持久化交易系统的所有关键数据，包括：

- 行情数据（Market Data）
- 订单记录（Orders）
- 成交记录（Trades）
- 持仓快照（Positions）
- 账户余额（Account Balance）
- 性能指标（Metrics）

## 架构设计

### 1. 数据库模块 (rust/common/src/database.rs)

核心功能：
- **连接池管理**：使用 sqlx 的 PgPool，支持连接复用
- **批量写入**：MarketDataBatchWriter 实现行情数据的批量写入，减少数据库压力
- **异步操作**：所有数据库操作都是异步的，不阻塞主业务流程
- **错误处理**：失败时保留缓冲区数据，支持重试

关键类：
```rust
pub struct Database {
    pool: PgPool,
}

pub struct MarketDataBatchWriter {
    inner: Arc<Mutex<BatchWriterInner>>,
}
```

### 2. Market Data 集成

**文件**: `rust/market-data/src/binance.rs`

特性：
- 在发布行情到 ZMQ 的同时，异步写入数据库
- 使用批量写入器，每 100 条或每 1 秒刷新一次
- 不影响行情发布的实时性能
- 连接断开时自动刷新缓冲区

启动参数：
```bash
export DB_URI="postgresql://ttquant:changeme@localhost:5432/ttquant_trading"
cargo run --bin market-data
```

### 3. Gateway 集成

**文件**: `rust/gateway/src/order_manager.rs`, `rust/gateway/src/main.rs`

特性：
- 记录所有接收的订单
- 记录所有成交回报（包括成功和拒绝）
- 在成交后记录持仓快照
- 支持可选的数据库连接（未配置时仍可正常运行）

启动参数：
```bash
export DB_URI="postgresql://ttquant:changeme@localhost:5432/ttquant_trading"
cargo run --bin gateway
```

## 数据库表结构

### market_data - 行情数据表
```sql
CREATE TABLE market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    last_price DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    exchange_time TIMESTAMPTZ,
    local_time TIMESTAMPTZ,
    PRIMARY KEY (time, symbol, exchange)
);
```

特性：
- TimescaleDB hypertable，自动分区
- 7天后自动压缩
- 30天后自动删除
- 按 symbol 和 time 建立索引

### orders - 订单表
```sql
CREATE TABLE orders (
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
```

### trades - 成交表
```sql
CREATE TABLE trades (
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
```

### positions - 持仓快照表
```sql
CREATE TABLE positions (
    time TIMESTAMPTZ NOT NULL,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    position INTEGER,
    avg_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION,
    PRIMARY KEY (time, strategy_id, symbol)
);
```

## 使用方法

### 1. 启动 TimescaleDB

使用 Docker Compose：
```bash
cd /c/Users/11915/Desktop/TTQuant
docker-compose up -d timescaledb
```

### 2. 初始化数据库

```bash
docker exec -i ttquant-timescaledb psql -U ttquant -d ttquant_trading < sql/init.sql
```

### 3. 启动服务（带数据库持久化）

Market Data 服务：
```bash
export DB_URI="postgresql://ttquant:changeme@localhost:5432/ttquant_trading"
export MARKET="binance"
export ZMQ_PUB_ENDPOINT="tcp://*:5555"
cargo run --bin market-data
```

Gateway 服务：
```bash
export DB_URI="postgresql://ttquant:changeme@localhost:5432/ttquant_trading"
export EXCHANGE="binance"
export ZMQ_PULL_ENDPOINT="tcp://*:5556"
export ZMQ_PUB_ENDPOINT="tcp://*:5557"
cargo run --bin gateway
```

### 4. 测试数据持久化

运行测试脚本：
```bash
cd python
python test_database.py
```

测试内容：
- 查询行情数据
- 查询订单和成交记录
- 查询持仓快照
- 数据完整性检查
- 性能测试

## 性能优化

### 1. 批量写入
- 行情数据使用批量写入，减少数据库连接开销
- 默认配置：每 100 条或每 1 秒刷新一次

### 2. 连接池
- 最大连接数：10
- 最小连接数：2
- 连接超时：5 秒

### 3. 索引优化
- 按时间和品种建立复合索引
- 按策略 ID 建立索引，加速查询

### 4. 数据压缩
- 7天后自动压缩历史数据
- 压缩率可达 90%+

### 5. 数据保留策略
- 行情数据保留 30 天
- 性能指标保留 7 天
- 订单和成交数据永久保留

## 查询示例

### 查询最新行情
```sql
SELECT symbol, last_price, volume, time
FROM market_data
WHERE symbol = 'BTCUSDT'
ORDER BY time DESC
LIMIT 10;
```

### 查询策略成交统计
```sql
SELECT
    strategy_id,
    COUNT(*) as total_trades,
    SUM(CASE WHEN status = 'FILLED' THEN 1 ELSE 0 END) as filled_trades,
    AVG(CASE WHEN status = 'FILLED' THEN filled_price ELSE NULL END) as avg_fill_price
FROM trades
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY strategy_id;
```

### 查询当前持仓
```sql
SELECT * FROM latest_positions;
```

### 计算 K 线数据
```sql
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    first(last_price, time) AS open,
    max(last_price) AS high,
    min(last_price) AS low,
    last(last_price, time) AS close,
    sum(volume) AS volume
FROM market_data
WHERE symbol = 'BTCUSDT'
    AND time > NOW() - INTERVAL '1 hour'
GROUP BY bucket, symbol
ORDER BY bucket DESC;
```

## 监控和维护

### 查看数据库大小
```sql
SELECT
    hypertable_name,
    pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables;
```

### 查看压缩状态
```sql
SELECT
    hypertable_name,
    compression_status,
    uncompressed_heap_size,
    compressed_heap_size
FROM timescaledb_information.compression_settings;
```

### 手动压缩数据
```sql
SELECT compress_chunk(i)
FROM show_chunks('market_data', older_than => INTERVAL '7 days') i;
```

## 故障处理

### 数据库连接失败
- 检查 TimescaleDB 是否运行：`docker ps | grep timescaledb`
- 检查连接字符串是否正确
- 检查防火墙设置

### 写入性能下降
- 检查批量写入缓冲区大小
- 检查数据库连接池配置
- 考虑增加压缩策略的时间间隔

### 数据丢失
- 检查日志中的错误信息
- 批量写入器在失败时会保留数据并重试
- 考虑增加数据保留策略的时间

## 未来改进

1. **平均成本跟踪**：在 RiskManager 中跟踪持仓的平均成本
2. **实时盈亏计算**：结合最新行情计算未实现盈亏
3. **数据备份**：定期备份关键数据
4. **分布式部署**：支持多个数据库实例的负载均衡
5. **实时监控**：集成 Grafana 进行可视化监控

## 相关文件

- `rust/common/src/database.rs` - 数据库核心模块
- `rust/market-data/src/binance.rs` - 行情数据持久化
- `rust/gateway/src/order_manager.rs` - 订单和成交持久化
- `sql/init.sql` - 数据库初始化脚本
- `python/test_database.py` - 数据库测试脚本
