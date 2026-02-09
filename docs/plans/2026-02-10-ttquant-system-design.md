# TTQuant 量化交易系统设计文档

**项目名称**: TTQuant (TurboTrade Quantitative Trading System)
**设计日期**: 2026-02-10
**架构**: Python + Rust 混合架构
**目标**: 多市场量化交易系统，支持 A股、加密货币、期货等

---

## 目录

1. [系统概述](#1-系统概述)
2. [通信架构](#2-通信架构)
3. [模块设计](#3-模块设计)
4. [数据存储与回测](#4-数据存储与回测)
5. [系统集成与部署](#5-系统集成与部署)
6. [项目结构](#6-项目结构)

---

## 1. 系统概述

### 1.1 项目目标

构建一个**多市场量化交易系统**，支持 A股、加密货币、期货等多个市场，采用 **Python + Rust 混合架构**，兼顾开发效率和执行性能。

### 1.2 非功能性约束（Constraints）

- **穿透延迟**：信号触发到订单发出的本地穿透延迟控制在 **< 1ms**
- **容错能力**：行情模块崩溃后，Docker Compose 应在 **3s 内完成自愈**（restart policy）
- **回测对齐**：实盘与回测必须共用一套 `BaseStrategy` 代码，实现"回测即实盘"（统一接口抽象）

### 1.3 核心架构

采用**事件驱动 + 微服务架构**，通过 ZeroMQ 实现模块间解耦通信：

```
┌─────────────┐ PUB/SUB ┌──────────────┐ PUSH/PULL ┌─────────────┐
│ 行情模块(MD) │────────>│ 策略引擎(Py)  │─────────>│ 交易柜台(GW) │
│   (Rust)    │         │  (Python)    │          │   (Rust)    │
└──────┬──────┘         └──────┬───────┘          └──────┬──────┘
       │                       │                         │
       │                       │<──── PUB/SUB ───────────┘
       │                       │    (成交回报)
       │                       │
       └───────────────────────┴─────────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │  TimescaleDB    │
                        │  - tick 数据     │
                        │  - K线数据       │
                        │  - 订单记录      │
                        │  - 持仓快照      │
                        └─────────────────┘
```

**模块说明**：

- **行情模块（Rust）**：多进程架构，每个市场独立进程（md-binance、md-okx、md-tushare），通过 WebSocket 接收实时行情，ZeroMQ PUB/SUB 模式广播给策略引擎
- **策略引擎（Python）**：订阅行情数据，计算量化因子，生成交易信号，通过 ZeroMQ PUSH/PULL 模式发送订单到交易柜台
- **交易柜台（Rust）**：接收订单请求，执行交易，风控检查，通过 ZeroMQ PUB/SUB 模式广播成交回报
- **数据存储（TimescaleDB）**：存储历史行情、订单记录、持仓快照，支持回测和分析

### 1.4 技术栈

- **Rust**：行情采集、交易执行（高性能、内存安全）
- **Python**：策略开发、因子计算（生态丰富、快速迭代）
- **ZeroMQ**：进程间通信（低延迟、灵活）
- **Docker Compose**：服务编排和部署
- **TimescaleDB**：时序数据存储
- **Prometheus + Grafana**：监控和可视化
- **Loki + Promtail**：日志聚合

---

## 2. 通信架构

### 2.1 ZeroMQ 通信拓扑

系统采用三种 ZeroMQ 模式，针对不同场景优化：

#### 2.1.1 行情分发（MD → Strategy）：PUB/SUB

- **端口**：`tcp://localhost:5555`（Binance）、`tcp://localhost:5556`（OKX）、`tcp://localhost:5557`（Tushare）
- **Topic 规范**：`md.{symbol}.{exchange}`（例如 `md.BTCUSDT.Binance`）
- **消息格式**：`[Topic][Protobuf Data]`，ZeroMQ 在内核态过滤 Topic
- **Python 优化**：使用 `memoryview` + `ParseFromString` 避免拷贝，配合 `zmq.POLL` 非阻塞接收

#### 2.1.2 订单下单（Strategy → Gateway）：PUSH/PULL

- **端口**：`tcp://localhost:5558`（Gateway **bind**，Strategy **connect**）
- **消息格式**：Protocol Buffers 序列化的 `Order` 结构（**必须包含 timestamp**）
- **Gateway 自锁机制**：收到订单后立即校验 `if (now - order.timestamp) > 500ms { reject(order); }`，防止过期订单成交
- **断线处理**：连接断开超过 5s 未重连，策略自动进入"休眠/风控"模式

#### 2.1.3 成交回报（Gateway → Strategy）：PUB/SUB

- **端口**：`tcp://localhost:5559`
- **Topic 规范**：`rt.{strategy_id}`（例如 `rt.EMA_Cross_01`）

#### 2.1.4 监控通道（inproc）：PUB/SUB

- **端口**：`inproc://metrics`（进程内通信，零开销）
- **监控指标**：Tick 进入到订单发出的 P99 延迟，每秒上报一次

### 2.2 延迟优化措施（满足 < 1ms 约束）

- **ZeroMQ 配置**：
  - `TCP_NODELAY = 1`（禁用 Nagle 算法）
  - `SNDHWM / RCVHWM = 1000`（合理缓冲区）
- **Rust 零拷贝**：`zmq::Message::from(data)` 直接发送
- **Python 零拷贝**：`memoryview` + `ParseFromString`
- **非阻塞模式**：`zmq.NOBLOCK` + `zmq.POLL`

### 2.3 Protocol Buffers 定义

```protobuf
syntax = "proto3";
package ttquant;

message MarketData {
  string symbol = 1;
  double last_price = 2;
  double volume = 3;
  int64 exchange_time = 4;  // 交易所时间戳
  int64 local_time = 5;     // 本地接收时间戳
}

message Order {
  string order_id = 1;
  string strategy_id = 2;
  string symbol = 3;
  double price = 4;
  int32 volume = 5;
  string side = 6;  // BUY/SELL
  int64 timestamp = 7;  // 订单生成时间戳（必须）
}

message Trade {
  string trade_id = 1;
  string order_id = 2;
  string strategy_id = 3;
  string symbol = 4;
  string side = 5;
  double filled_price = 6;
  int32 filled_volume = 7;
  int64 trade_time = 8;
  string status = 9;  // FILLED / REJECTED
  int32 error_code = 10;  // 错误码（仅 REJECTED 时有效）
  string error_message = 11;
  bool is_retryable = 12;  // 是否可重试
  double commission = 13;  // 手续费
}

message Metrics {
  string component = 1;  // md-binance / gateway / strategy
  int64 p99_latency_ns = 2;
  int64 msg_count = 3;
  int64 timestamp = 4;
}
```

### 2.4 Python 策略引擎接收示例

```python
def on_market_data(self):
    while True:
        try:
            msg = self.sub_socket.recv_multipart(flags=zmq.NOBLOCK)
            topic = msg[0]
            data_view = memoryview(msg[1])  # 零拷贝
            self.md_proto.ParseFromString(data_view)
            # 进入策略逻辑
        except zmq.Again:
            break
```

---

## 3. 模块设计

### 3.1 行情模块（Rust - market-data）

#### 3.1.1 职责

- 连接多个交易所 WebSocket，接收实时行情（Tick、K线、深度）
- 标准化不同交易所的数据格式（零拷贝优化）
- 通过 ZeroMQ PUB 广播行情数据
- 记录本地接收时间戳，用于延迟监控

#### 3.1.2 多进程架构

- 每个市场独立进程：`md-binance`、`md-okx`、`md-tushare`
- 共享 `rust/common` 库（ZMQ 封装、Protobuf 定义、配置解析）
- Docker Compose 配置 `restart: always`，3s 内自愈

#### 3.1.3 性能优化措施

1. **零拷贝解析**：使用 `serde_json` 的 Borrowing 特性，直接从 WebSocket 缓冲区切片提取字段
2. **内存预分配**：使用 `bumpalo` 内存池或对象池，通过 `clear()` 复用 Protobuf 对象
3. **非侵入式监控**：使用 `crossbeam-channel` SPSC 队列，将延迟数据发送到专门的监控线程

#### 3.1.4 WebSocket 重连机制

- **指数退避**：连接失败时采用 Exponential Backoff（初始 100ms，最大 30s）
- **心跳维护**：使用 `tokio::select!` 同时处理"接收行情"和"定时发送 Pong"
- **序列号校验**：深度数据必须校验 Update ID，不连续则触发全量快照重拉

#### 3.1.5 配置文件（config/markets.toml）

```toml
[binance]
ws_url = "wss://stream.binance.com:9443/ws"
symbols = ["BTCUSDT", "ETHUSDT"]
heartbeat_interval_secs = 20
reconnect_backoff_ms = [100, 500, 2000, 10000, 30000]

[okx]
ws_url = "wss://ws.okx.com:8443/ws/v5/public"
symbols = ["BTC-USDT", "ETH-USDT"]
heartbeat_interval_secs = 15
```

### 3.2 策略引擎（Python - strategy）

#### 3.2.1 职责

- 订阅行情数据（ZMQ SUB，Topic 过滤）
- 计算量化因子（技术指标、基本面、情绪等）
- 执行策略逻辑，生成交易信号
- 发送订单到交易柜台（ZMQ PUSH）
- 监听成交回报，更新持仓状态

#### 3.2.2 核心设计原则：回测即实盘

- 所有策略继承统一的 `BaseStrategy` 抽象类
- 回测和实盘共用同一套策略代码
- 通过依赖注入切换数据源（历史数据 vs 实时行情）

#### 3.2.3 目录结构

```
python/strategy/
├── engine.py           # 策略引擎核心
├── base_strategy.py    # BaseStrategy 抽象类
├── factors/            # 因子库
│   ├── momentum.py
│   ├── volatility.py
│   └── volume.py
├── strategies/         # 具体策略实现
│   ├── ema_cross.py
│   └── mean_reversion.py
└── portfolio.py        # 持仓管理
```

#### 3.2.4 BaseStrategy 抽象类

```python
from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseStrategy(ABC):
    """策略基类：回测和实盘共用"""

    def __init__(self, strategy_id: str, config: Dict):
        self.strategy_id = strategy_id
        self.config = config
        self.portfolio = Portfolio()

    @abstractmethod
    def on_market_data(self, md: MarketData) -> Optional[Signal]:
        """行情回调：子类必须实现"""
        pass

    @abstractmethod
    def on_trade(self, trade: Trade):
        """成交回报回调：更新持仓"""
        pass

    def send_order(self, symbol: str, side: str, price: float, volume: int):
        """下单接口：回测和实盘通过依赖注入切换实现"""
        order = Order(
            order_id=generate_order_id(),
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=side,
            price=price,
            volume=volume,
            timestamp=time.time_ns()
        )
        self._order_gateway.send(order)
```

### 3.3 交易柜台（Rust - gateway）

#### 3.3.1 职责

- 接收策略引擎的订单请求（ZMQ PULL）
- 订单有效性校验（时间戳、价格、数量）
- 风控检查（持仓限制、资金检查、频率限制）
- 路由订单到对应交易所 API
- 接收交易所成交回报，广播给策略（ZMQ PUB）
- **异步批量写入** TimescaleDB（非阻塞）

#### 3.3.2 关键优化

1. **数据库非阻塞化**：独立任务 + mpsc 通道批量写入
2. **风控快照恢复**：启动时从 TimescaleDB 加载持仓
3. **错误码精细化**：使用枚举错误码，便于策略重试

#### 3.3.3 错误码定义

```rust
#[derive(Debug, Clone)]
enum RejectReason {
    OrderExpired = 1001,
    PositionLimitExceeded = 2001,
    InsufficientFunds = 2002,
    FrequencyLimitExceeded = 2003,
    InvalidPrice = 3001,
    InvalidVolume = 3002,
    ExchangeError = 4001,
    UnknownSymbol = 4002,
}
```

#### 3.3.4 风控配置（config/risk.toml）

```toml
[position_limits]
BTCUSDT = 10
ETHUSDT = 100

[rate_limits]
max_orders_per_second = 100
max_orders_per_strategy_per_second = 10

[order_validation]
max_order_age_ms = 500
min_price = 0.01
max_price = 1000000.0
```

---

## 4. 数据存储与回测

### 4.1 TimescaleDB Schema

```sql
-- 启用 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Tick 数据表
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

SELECT create_hypertable('market_data', 'time');
CREATE INDEX idx_market_data_symbol ON market_data (symbol, time DESC);

-- 设置压缩策略（7天后压缩）
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,exchange'
);
SELECT add_compression_policy('market_data', INTERVAL '7 days');

-- 2. K线数据表
CREATE TABLE klines (
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

SELECT create_hypertable('klines', 'time');

-- 3. 订单表
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

SELECT create_hypertable('orders', 'time');

-- 4. 成交表
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

SELECT create_hypertable('trades', 'time');

-- 5. 持仓快照表（支持 UPSERT）
CREATE TABLE positions (
    time TIMESTAMPTZ NOT NULL,
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    position INTEGER,
    avg_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION,
    PRIMARY KEY (time, strategy_id, symbol)
);

SELECT create_hypertable('positions', 'time');

-- 数据保留策略
SELECT add_retention_policy('market_data', INTERVAL '30 days');
```

### 4.2 回测框架

#### 4.2.1 回测配置

```python
@dataclass
class BacktestConfig:
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003  # 0.03% 手续费
    slippage_bps: float = 5.0  # 5个基点滑点
```

#### 4.2.2 数据源抽象

```python
class DataSource(ABC):
    @abstractmethod
    def get_market_data(self, symbol: str, start: int, end: int) -> pl.DataFrame:
        pass

class BacktestDataSource(DataSource):
    def get_market_data(self, symbol: str, start: int, end: int) -> pl.DataFrame:
        # 使用 ConnectorX + Polars 加速读取
        query = f"""
            SELECT * FROM market_data
            WHERE symbol = '{symbol}'
                AND time >= to_timestamp({start} / 1e9)
                AND time <= to_timestamp({end} / 1e9)
            ORDER BY time
        """
        return pl.read_database_uri(query, self.db_uri)
```

#### 4.2.3 订单网关抽象

```python
class BacktestOrderGateway(OrderGateway):
    def send(self, order: Order) -> Optional[Trade]:
        # 模拟滑点
        slippage_factor = self.config.slippage_bps / 10000.0
        if order.side == "BUY":
            filled_price = market_price * (1 + slippage_factor)
        else:
            filled_price = market_price * (1 - slippage_factor)

        # 计算手续费
        commission = filled_price * order.volume * self.config.commission_rate

        return Trade(...)
```

---

## 5. 系统集成与部署

### 5.1 Docker Compose 编排

完整配置见 `docker/docker-compose.yml`，关键特性：

- **网络优化**：核心服务使用 `network_mode: "host"` 降低延迟
- **日志管理**：统一配置日志旋转（max-size: 100m, max-file: 3）
- **健康检查**：所有服务配置 healthcheck
- **依赖管理**：使用 `depends_on` + `condition: service_healthy`

### 5.2 监控系统

#### 5.2.1 Prometheus 指标

- `p99_latency_ns`：P99 延迟（纳秒）
- `orders_total`：订单总数
- `orders_rejected_total`：拒绝订单数
- `trades_filled_total`：成交总数
- `market_data_messages_total`：行情消息数
- `db_pool_connections_active`：数据库连接池使用率

#### 5.2.2 告警规则

- 延迟超过 1ms
- 行情模块宕机
- 交易柜台宕机
- 订单拒绝率 > 10%
- 数据库连接池耗尽
- 持仓接近限制

### 5.3 秘密管理

使用 `.env` 文件管理敏感信息：

```bash
DB_PASSWORD=your_password
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
OKX_API_KEY=your_key
OKX_SECRET_KEY=your_secret
GRAFANA_PASSWORD=your_password
```

**重要**：`.env` 文件必须添加到 `.gitignore`

### 5.4 部署脚本

```bash
#!/bin/bash
# 检查环境变量
source .env

# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 检查健康状态
docker-compose ps
```

---

## 6. 项目结构

```
TTQuant/
├── rust/                    # Rust 工作空间
│   ├── Cargo.toml          # 工作空间配置
│   ├── market-data/        # 行情模块
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── binance.rs
│   │   │   ├── okx.rs
│   │   │   └── tushare.rs
│   │   └── Cargo.toml
│   ├── gateway/            # 交易柜台
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── order_receiver.rs
│   │   │   ├── risk_manager.rs
│   │   │   ├── exchange_router.rs
│   │   │   ├── trade_publisher.rs
│   │   │   └── db_writer.rs
│   │   └── Cargo.toml
│   └── common/             # 共享库
│       ├── src/
│       │   ├── lib.rs
│       │   ├── zmq_wrapper.rs
│       │   └── proto.rs
│       └── Cargo.toml
│
├── python/                 # Python 策略引擎
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── base_strategy.py
│   │   ├── factors/
│   │   │   ├── momentum.py
│   │   │   ├── volatility.py
│   │   │   └── volume.py
│   │   └── strategies/
│   │       ├── ema_cross.py
│   │       └── mean_reversion.py
│   ├── backtest/
│   │   ├── engine.py
│   │   ├── data_source.py
│   │   └── order_gateway.py
│   ├── requirements.txt
│   └── Dockerfile.strategy
│
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.rust
│   └── Dockerfile.python
│
├── config/
│   ├── markets.toml
│   ├── strategies.yaml
│   ├── risk.toml
│   └── database.toml
│
├── monitoring/
│   ├── prometheus.yml
│   ├── alerts.yml
│   ├── alertmanager.yml
│   ├── loki-config.yaml
│   ├── promtail-config.yaml
│   └── grafana/
│       ├── dashboards/
│       └── datasources/
│
├── sql/
│   └── init.sql
│
├── docs/
│   ├── plans/
│   │   └── 2026-02-10-ttquant-system-design.md
│   └── api/
│
├── .env.example
├── .gitignore
├── deploy.sh
└── README.md
```

---

## 附录

### A. 关键性能指标

- **延迟目标**：< 1ms（信号到订单）
- **吞吐量**：> 10,000 msg/s（行情处理）
- **可用性**：99.9%（年停机时间 < 8.76 小时）
- **恢复时间**：< 3s（服务自愈）

### B. 技术债务与未来优化

1. **FPGA 加速**：对于超高频场景，考虑 FPGA 硬件加速
2. **内核旁路**：使用 DPDK 或 io_uring 进一步降低延迟
3. **机器学习因子**：集成 PyTorch/TensorFlow 进行因子挖掘
4. **多策略组合优化**：实现策略权重动态调整

### C. 参考资料

- [WorldQuant 101 Alphas](https://docs.dolphindb.com/en/Tutorials/wq101alpha.html)
- [ZeroMQ Guide](https://zguide.zeromq.org/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Rust Async Book](https://rust-lang.github.io/async-book/)

---

**文档版本**: v1.0
**最后更新**: 2026-02-10
**作者**: Claude Opus 4.6 + User
**状态**: 设计完成，待实施
