# TTQuant 性能优化指南

## 当前性能指标

### 系统资源使用
- **OKX Market Data**:
  - CPU: ~0%
  - 内存: ~15 MB
  - 线程: 19
  - 文件描述符: 26

- **OKX Gateway**:
  - CPU: ~0%
  - 内存: ~15 MB
  - 线程: 21
  - 文件描述符: 36

### 数据吞吐量
- **行情数据**: ~4000-5000 条/小时/交易对
- **数据库写入**: 批量写入（100 条/批次，1 秒刷新）
- **ZMQ 延迟**: < 1ms

---

## 优化建议

### 1. 行情数据优化

#### 1.1 增加批量写入大小
**当前配置**：100 条/批次
**建议配置**：500-1000 条/批次

**修改位置**：`rust/market-data/src/okx.rs:24`
```rust
// 当前
Some(MarketDataBatchWriter::new(db, 100, 1))

// 优化后
Some(MarketDataBatchWriter::new(db, 500, 2))
```

**预期效果**：
- 减少数据库连接次数
- 降低 I/O 开销
- 提升 20-30% 写入性能

#### 1.2 使用连接池
**当前**：单个数据库连接
**建议**：使用 `sqlx::Pool` 连接池

**修改位置**：`rust/common/src/database.rs`
```rust
pub struct Database {
    pool: sqlx::PgPool,  // 改为连接池
}

impl Database {
    pub async fn new(uri: &str) -> Result<Self> {
        let pool = sqlx::postgres::PgPoolOptions::new()
            .max_connections(5)
            .connect(uri)
            .await?;
        Ok(Self { pool })
    }
}
```

**预期效果**：
- 支持并发写入
- 提升 50-100% 吞吐量

#### 1.3 异步批量写入
**当前**：同步批量写入
**建议**：使用 `tokio::spawn` 异步写入

**修改位置**：`rust/common/src/database.rs`
```rust
pub async fn flush(&self) -> Result<()> {
    let batch = self.buffer.lock().await.drain(..).collect::<Vec<_>>();
    if batch.is_empty() {
        return Ok(());
    }

    // 异步写入，不阻塞主线程
    let db = self.db.clone();
    tokio::spawn(async move {
        if let Err(e) = db.batch_insert(&batch).await {
            error!("Failed to batch insert: {}", e);
        }
    });

    Ok(())
}
```

**预期效果**：
- 不阻塞行情接收
- 降低延迟 50-80%

---

### 2. 订单处理优化

#### 2.1 订单缓存
**当前**：每次查询数据库
**建议**：使用 LRU 缓存

**实现**：
```rust
use lru::LruCache;

pub struct OrderManager {
    cache: Arc<Mutex<LruCache<String, Order>>>,
    // ...
}

impl OrderManager {
    pub async fn get_order(&self, order_id: &str) -> Result<Option<Order>> {
        // 先查缓存
        if let Some(order) = self.cache.lock().await.get(order_id) {
            return Ok(Some(order.clone()));
        }

        // 缓存未命中，查数据库
        if let Some(order) = self.db.get_order(order_id).await? {
            self.cache.lock().await.put(order_id.to_string(), order.clone());
            return Ok(Some(order));
        }

        Ok(None)
    }
}
```

**预期效果**：
- 减少数据库查询 80-90%
- 降低订单查询延迟 90%

#### 2.2 风控前置
**当前**：下单后风控检查
**建议**：下单前风控检查

**修改位置**：`rust/gateway/src/order_manager.rs`
```rust
pub async fn submit_order(&self, order: Order) -> Result<Trade> {
    // 1. 风控检查（前置）
    if !self.risk_manager.check_order(&order).await? {
        return Err(anyhow!("Order rejected by risk manager"));
    }

    // 2. 提交到交易所
    let trade = self.exchange.submit_order(&order).await?;

    // 3. 保存到数据库
    self.db.insert_trade(&trade).await?;

    Ok(trade)
}
```

**预期效果**：
- 快速拒绝无效订单
- 减少无效 API 调用
- 降低延迟 30-50%

---

### 3. 网络优化

#### 3.1 WebSocket 压缩
**当前**：无压缩
**建议**：启用 WebSocket 压缩

**修改位置**：`rust/market-data/src/okx.rs`
```rust
use tokio_tungstenite::{connect_async_with_config, tungstenite::protocol::WebSocketConfig};

let config = WebSocketConfig {
    max_message_size: Some(64 << 20),  // 64 MB
    max_frame_size: Some(16 << 20),    // 16 MB
    accept_unmasked_frames: false,
    compression: Some(tungstenite::protocol::Compression::default()),  // 启用压缩
};

let (ws_stream, _) = connect_async_with_config(OKX_WS_URL, Some(config), false).await?;
```

**预期效果**：
- 减少网络带宽 30-50%
- 降低延迟 10-20%

#### 3.2 HTTP/2 连接复用
**当前**：HTTP/1.1
**建议**：使用 HTTP/2

**修改位置**：`rust/gateway/src/exchange/okx.rs`
```rust
use reqwest::Client;

let client = Client::builder()
    .http2_prior_knowledge()  // 强制使用 HTTP/2
    .pool_max_idle_per_host(10)
    .pool_idle_timeout(Duration::from_secs(90))
    .build()?;
```

**预期效果**：
- 减少连接建立开销
- 提升并发性能 50-100%

---

### 4. 内存优化

#### 4.1 使用 `Arc` 共享数据
**当前**：数据克隆
**建议**：使用 `Arc` 避免克隆

**示例**：
```rust
use std::sync::Arc;

pub struct MarketData {
    symbol: Arc<str>,  // 共享字符串
    exchange: Arc<str>,
    // ...
}
```

**预期效果**：
- 减少内存分配 50-70%
- 降低 GC 压力

#### 4.2 对象池
**当前**：频繁分配/释放
**建议**：使用对象池

**实现**：
```rust
use object_pool::Pool;

lazy_static! {
    static ref ORDER_POOL: Pool<Order> = Pool::new(100, || Order::default());
}

pub fn create_order() -> Order {
    ORDER_POOL.pull(|| Order::default())
}
```

**预期效果**：
- 减少内存分配 80-90%
- 提升性能 20-30%

---

### 5. 数据库优化

#### 5.1 分区表
**当前**：单表存储
**建议**：按时间分区

**SQL**：
```sql
-- 创建分区表
CREATE TABLE market_data_partitioned (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    last_price DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    exchange TEXT,
    exchange_time BIGINT,
    local_time BIGINT
) PARTITION BY RANGE (time);

-- 创建月度分区
CREATE TABLE market_data_2026_02 PARTITION OF market_data_partitioned
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE market_data_2026_03 PARTITION OF market_data_partitioned
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
```

**预期效果**：
- 查询性能提升 50-100%
- 支持自动归档旧数据

#### 5.2 索引优化
**当前**：单列索引
**建议**：复合索引

**SQL**：
```sql
-- 创建复合索引
CREATE INDEX idx_market_data_symbol_time ON market_data (symbol, time DESC);
CREATE INDEX idx_market_data_exchange_time ON market_data (exchange, time DESC);

-- 创建部分索引（仅索引最近数据）
CREATE INDEX idx_market_data_recent ON market_data (symbol, time DESC)
    WHERE time > NOW() - INTERVAL '7 days';
```

**预期效果**：
- 查询性能提升 100-200%
- 减少索引大小 50%

#### 5.3 数据压缩
**当前**：无压缩
**建议**：启用 TimescaleDB 压缩

**SQL**：
```sql
-- 启用压缩
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,exchange',
    timescaledb.compress_orderby = 'time DESC'
);

-- 自动压缩策略（7 天后压缩）
SELECT add_compression_policy('market_data', INTERVAL '7 days');
```

**预期效果**：
- 存储空间减少 80-90%
- 查询性能提升 20-30%

---

### 6. 监控优化

#### 6.1 自定义业务指标
**当前**：仅系统指标
**建议**：添加业务指标

**实现**：
```rust
use prometheus::{Counter, Histogram, register_counter, register_histogram};

lazy_static! {
    static ref MARKET_DATA_RECEIVED: Counter = register_counter!(
        "market_data_received_total",
        "Total number of market data messages received"
    ).unwrap();

    static ref ORDER_LATENCY: Histogram = register_histogram!(
        "order_submit_latency_seconds",
        "Order submission latency in seconds"
    ).unwrap();
}

// 使用
MARKET_DATA_RECEIVED.inc();
let timer = ORDER_LATENCY.start_timer();
// ... 下单逻辑
timer.observe_duration();
```

**指标列表**：
- `market_data_received_total` - 接收的行情数量
- `market_data_latency_seconds` - 行情延迟
- `order_submit_total` - 提交的订单数量
- `order_submit_latency_seconds` - 订单延迟
- `order_reject_total` - 拒绝的订单数量
- `database_write_total` - 数据库写入次数
- `database_write_latency_seconds` - 数据库写入延迟

#### 6.2 告警规则
**文件**：`monitoring/alerts.yml`

```yaml
groups:
  - name: okx_alerts
    interval: 30s
    rules:
      # 行情延迟告警
      - alert: HighMarketDataLatency
        expr: market_data_latency_seconds{exchange="okx"} > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "OKX market data latency is high"
          description: "Latency: {{ $value }}s"

      # 订单失败率告警
      - alert: HighOrderRejectRate
        expr: rate(order_reject_total{exchange="okx"}[5m]) / rate(order_submit_total{exchange="okx"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "OKX order reject rate is high"
          description: "Reject rate: {{ $value | humanizePercentage }}"

      # 数据库写入失败告警
      - alert: DatabaseWriteFailure
        expr: rate(database_write_errors_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database write failures detected"
```

---

### 7. 压力测试

#### 7.1 行情数据压力测试
**工具**：`wrk` 或 `hey`

```bash
# 模拟 1000 个并发连接
hey -n 100000 -c 1000 http://localhost:8082/metrics
```

#### 7.2 订单压力测试
**脚本**：`python/stress_test.py`

```python
import asyncio
from strategy.engine import OrderGateway

async def stress_test():
    gateway = OrderGateway("tcp://localhost:5559", use_protobuf=True)

    tasks = []
    for i in range(1000):
        order = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 50000 + i,
            "quantity": 0.001,
        }
        tasks.append(gateway.submit_order(order))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success = sum(1 for r in results if not isinstance(r, Exception))
    print(f"Success: {success}/1000")

asyncio.run(stress_test())
```

#### 7.3 数据库压力测试
**工具**：`pgbench`

```bash
docker exec ttquant-timescaledb pgbench -U ttquant -d ttquant_trading -c 10 -j 2 -t 1000
```

---

### 8. 性能监控

#### 8.1 实时性能监控
**Grafana 面板**：
- CPU 使用率
- 内存使用率
- 网络吞吐量
- 行情延迟
- 订单延迟
- 数据库 QPS

#### 8.2 性能分析工具
**Rust Profiling**：
```bash
# 安装 flamegraph
cargo install flamegraph

# 生成火焰图
cargo flamegraph --bin market-data
```

**数据库分析**：
```sql
-- 慢查询分析
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 表大小分析
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 优化优先级

### 高优先级（立即实施）
1. ✅ 增加批量写入大小（简单，效果明显）
2. ✅ 添加订单缓存（简单，效果明显）
3. ✅ 风控前置（简单，降低延迟）
4. ✅ 数据库索引优化（简单，效果明显）

### 中优先级（1-2 周内）
1. ⏳ 使用连接池（中等复杂度）
2. ⏳ 异步批量写入（中等复杂度）
3. ⏳ 添加业务指标（中等复杂度）
4. ⏳ 数据库分区表（中等复杂度）

### 低优先级（长期优化）
1. ⏸️ WebSocket 压缩（复杂，收益有限）
2. ⏸️ HTTP/2 连接复用（复杂，收益有限）
3. ⏸️ 对象池（复杂，收益有限）
4. ⏸️ 数据压缩（复杂，需要测试）

---

## 预期性能提升

### 优化前
- 行情延迟：10-50ms
- 订单延迟：50-200ms
- 数据库 QPS：100-200
- 内存使用：15-20 MB/服务

### 优化后
- 行情延迟：5-20ms（提升 50%）
- 订单延迟：20-100ms（提升 50%）
- 数据库 QPS：500-1000（提升 400%）
- 内存使用：10-15 MB/服务（降低 25%）

---

## 参考资料

- [Rust Performance Book](https://nnethercote.github.io/perf-book/)
- [TimescaleDB Best Practices](https://docs.timescale.com/timescaledb/latest/how-to-guides/hypertables/best-practices/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [ZeroMQ Performance](https://zeromq.org/socket-api/)
