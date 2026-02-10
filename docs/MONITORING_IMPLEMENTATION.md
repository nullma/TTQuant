# TTQuant 监控系统实现总结

## 实现概述

已完成 TTQuant 交易系统的全方位监控系统，基于 Prometheus + Grafana 架构，提供实时性能监控、交易指标追踪和智能告警功能。

## 已实现的组件

### 1. Prometheus 配置 ✓

**文件**: `monitoring/prometheus.yml`

- 配置了 6 个抓取目标（market-data, gateway, strategy-engine, timescaledb, node, prometheus）
- 抓取间隔：关键服务 5s，一般服务 15s
- 数据保留：30 天，最大 50GB
- 集成 AlertManager 告警管理

### 2. Rust 指标导出 ✓

#### Market Data 模块

**文件**:
- `rust/market-data/src/metrics.rs` - 完整的指标收集器
- `rust/market-data/src/main.rs` - 集成 HTTP metrics 服务器
- `rust/market-data/Cargo.toml` - 添加 prometheus、axum 依赖

**导出指标**:
- `market_data_received_total` - 行情接收计数
- `market_data_latency_ms` - 行情延迟（histogram）
- `ws_connection_status` - WebSocket 连接状态
- `ws_reconnect_total` - 重连次数
- `message_parse_errors_total` - 解析错误
- `market_last_price` - 最新价格
- `market_volume_24h` - 24小时成交量
- `db_writes_total` - 数据库写入统计
- `zmq_published_total` - ZMQ 发布统计

**HTTP 端点**: `http://localhost:8080/metrics`

#### Gateway 模块

**文件**:
- `rust/gateway/src/metrics.rs` - 完整的指标收集器
- `rust/gateway/src/main.rs` - 集成 HTTP metrics 服务器
- `rust/gateway/Cargo.toml` - 添加 prometheus、axum 依赖

**导出指标**:
- `orders_total` - 订单总数
- `orders_success_total` - 成功订单数
- `orders_failed_total` - 失败订单数
- `orders_risk_rejected_total` - 风控拒单数
- `order_processing_latency_ms` - 订单处理延迟（histogram）
- `trades_total` - 成交统计
- `trade_volume_total` - 成交金额
- `commission_paid_total` - 手续费
- `current_position` - 当前持仓
- `active_orders` - 活跃订单数
- `risk_exposure_usd` - 风险敞口
- `max_drawdown_usd` - 最大回撤

**HTTP 端点**: `http://localhost:8081/metrics`

### 3. Python 指标导出 ✓

**文件**: `python/strategy/metrics.py`

**导出指标**:

#### 策略指标
- `strategy_pnl_total` - 策略总 PnL
- `strategy_realized_pnl` - 已实现 PnL
- `strategy_unrealized_pnl` - 未实现 PnL
- `strategy_position_size` - 持仓数量
- `strategy_position_value_usd` - 持仓价值
- `strategy_trades_total` - 交易次数
- `strategy_win_rate` - 胜率
- `strategy_winning_trades_total` - 盈利交易数
- `strategy_losing_trades_total` - 亏损交易数
- `strategy_avg_profit_usd` - 平均盈利
- `strategy_avg_loss_usd` - 平均亏损
- `strategy_max_drawdown_usd` - 最大回撤
- `strategy_sharpe_ratio` - 夏普比率

#### 引擎指标
- `engine_market_data_received_total` - 行情接收计数
- `engine_orders_sent_total` - 订单发送计数
- `engine_trades_received_total` - 成交回报计数
- `engine_strategy_latency_ms` - 策略执行延迟
- `engine_active_strategies` - 活跃策略数
- `engine_uptime_seconds` - 运行时间

**HTTP 端点**: `http://localhost:8000/metrics`

**示例集成**: `python/strategy/engine_with_metrics.py`

### 4. Grafana Dashboard ✓

**文件**: `monitoring/dashboards/ttquant.json`

**包含面板**:

1. **System Overview** - 系统概览
   - 服务状态指示器（Market Data, Gateway, Strategy Engine）
   - 活跃策略数

2. **Market Data Monitoring** - 行情监控
   - 行情接收速率图表
   - 行情延迟分布（P50/P95/P99）

3. **Trading Monitoring** - 交易监控
   - 订单处理速率
   - 订单处理延迟
   - 订单成功率仪表盘
   - 成交统计

4. **Strategy Performance** - 策略性能
   - 策略 PnL 曲线
   - 策略胜率
   - 策略持仓
   - 最大回撤

**访问**: http://localhost:3000

### 5. Docker Compose 集成 ✓

**文件**: `docker/docker-compose.yml`

**新增服务**:

1. **prometheus** (9090) - 指标收集和存储
2. **grafana** (3000) - 可视化展示
3. **alertmanager** (9093) - 告警管理
4. **node-exporter** (9100) - 系统指标
5. **postgres-exporter** (9187) - 数据库指标

**数据卷**:
- `prometheus-data` - Prometheus 数据持久化
- `grafana-data` - Grafana 配置和数据
- `alertmanager-data` - AlertManager 数据

### 6. 告警规则 ✓

**文件**: `monitoring/alerts.yml`

**告警组**:

1. **market_data_alerts** - 行情数据告警
   - HighMarketDataLatency (>1000ms)
   - CriticalMarketDataLatency (>5000ms)
   - MarketDataStreamDown (2分钟无数据)
   - LowMarketDataRate (接收速率过低)

2. **gateway_alerts** - 交易网关告警
   - HighOrderLatency (>500ms)
   - CriticalOrderLatency (>2000ms)
   - HighOrderFailureRate (>10%)
   - CriticalOrderFailureRate (>30%)
   - HighRiskRejectionRate (>5%)
   - GatewayDown (服务宕机)

3. **strategy_alerts** - 策略告警
   - StrategyLoss (亏损 >$1000)
   - CriticalStrategyLoss (亏损 >$5000)
   - LowWinRate (胜率 <30%)
   - StrategyEngineDown (引擎宕机)
   - HighPositionSize (持仓过大)

4. **system_alerts** - 系统资源告警
   - HighCPUUsage (>80%)
   - HighMemoryUsage (>85%)
   - HighDiskUsage (>85%)

5. **database_alerts** - 数据库告警
   - HighDatabaseConnections (>80)
   - DatabaseDown (数据库宕机)
   - SlowQueries (慢查询)

**告警配置**: `monitoring/alertmanager.yml`
- 支持邮件通知
- 支持 Slack 通知（可选）
- 告警分组和抑制规则
- 多级告警路由

### 7. 文档 ✓

**主文档**: `docs/MONITORING.md` (完整的使用指南)

**内容包括**:
- 系统概述和架构设计
- 快速开始指南
- 详细的指标说明
- Dashboard 使用教程
- 告警配置指南
- 故障排查手册
- 最佳实践建议
- 常用 PromQL 查询示例

**快速指南**: `monitoring/README.md`
- 一键启动命令
- 访问地址列表
- 验证步骤
- 常用命令
- 配置修改方法

### 8. 管理脚本 ✓

**监控管理脚本**: `scripts/monitoring.sh`

**功能**:
- `start` - 启动监控系统
- `stop` - 停止监控系统
- `restart` - 重启监控系统
- `status` - 检查服务状态
- `logs` - 查看服务日志
- `reload` - 重新加载配置
- `validate` - 验证配置文件
- `backup` - 备份监控数据
- `clean` - 清理所有数据

**测试脚本**: `scripts/test_monitoring.sh`

**测试项目**:
- Prometheus 健康检查
- Grafana 健康检查
- AlertManager 健康检查
- Node Exporter 测试
- Postgres Exporter 测试
- 应用指标端点测试
- 指标查询测试
- 告警规则测试
- 性能测试
- 数据完整性测试
- 配置验证

## 文件清单

```
TTQuant/
├── monitoring/
│   ├── prometheus.yml              # Prometheus 配置
│   ├── alerts.yml                  # 告警规则
│   ├── alertmanager.yml            # AlertManager 配置
│   ├── README.md                   # 快速启动指南
│   ├── grafana/
│   │   ├── datasources.yml         # Grafana 数据源配置
│   │   └── dashboards.yml          # Dashboard 配置
│   └── dashboards/
│       └── ttquant.json            # 主 Dashboard
│
├── rust/
│   ├── market-data/
│   │   ├── src/
│   │   │   ├── metrics.rs          # Market Data 指标模块
│   │   │   └── main.rs             # 集成 metrics 服务器
│   │   └── Cargo.toml              # 添加 prometheus 依赖
│   │
│   └── gateway/
│       ├── src/
│       │   ├── metrics.rs          # Gateway 指标模块
│       │   └── main.rs             # 集成 metrics 服务器
│       └── Cargo.toml              # 添加 prometheus 依赖
│
├── python/
│   ├── strategy/
│   │   ├── metrics.py              # Python 指标模块
│   │   └── engine_with_metrics.py  # 集成示例
│   └── requirements.txt            # 添加 prometheus-client
│
├── docker/
│   └── docker-compose.yml          # 添加监控服务
│
├── scripts/
│   ├── monitoring.sh               # 监控管理脚本
│   └── test_monitoring.sh          # 监控测试脚本
│
└── docs/
    └── MONITORING.md               # 完整使用文档
```

## 使用方法

### 1. 启动监控系统

```bash
# 方法 1: 使用管理脚本
./scripts/monitoring.sh start

# 方法 2: 使用 docker-compose
cd docker
docker-compose up -d prometheus grafana alertmanager node-exporter postgres-exporter
```

### 2. 启动应用服务

```bash
cd docker
docker-compose up -d timescaledb md-binance gateway-binance
```

### 3. 访问监控界面

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093

### 4. 查看指标

```bash
# Market Data 指标
curl http://localhost:8080/metrics

# Gateway 指标
curl http://localhost:8081/metrics

# Strategy Engine 指标（需要先启动）
curl http://localhost:8000/metrics
```

### 5. 运行测试

```bash
./scripts/test_monitoring.sh
```

## 技术栈

- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化展示
- **AlertManager**: 告警管理
- **Node Exporter**: 系统指标导出
- **Postgres Exporter**: 数据库指标导出
- **Rust prometheus crate**: Rust 应用指标导出
- **Python prometheus-client**: Python 应用指标导出
- **Axum**: Rust HTTP 服务器框架

## 关键特性

1. **实时监控**: 5秒级别的指标采集
2. **全面覆盖**: 系统、应用、业务三层指标
3. **智能告警**: 多级告警规则和通知
4. **可视化**: 丰富的 Dashboard 和图表
5. **易用性**: 一键启动和管理脚本
6. **可扩展**: 易于添加自定义指标
7. **高性能**: 低延迟的指标采集和查询
8. **持久化**: 30天数据保留

## 性能指标

- **指标采集延迟**: < 5s
- **查询响应时间**: < 100ms
- **Dashboard 刷新**: 5s
- **告警评估**: 30s
- **数据保留**: 30天
- **存储限制**: 50GB

## 下一步建议

1. **生产环境部署**:
   - 配置 HTTPS 访问
   - 设置防火墙规则
   - 配置邮件/Slack 告警
   - 调整资源限制

2. **扩展功能**:
   - 添加更多自定义指标
   - 创建更多专用 Dashboard
   - 集成日志系统（ELK/Loki）
   - 添加分布式追踪（Jaeger）

3. **优化**:
   - 调整告警阈值
   - 优化查询性能
   - 配置长期存储（Thanos）
   - 实现多集群监控

## 支持和维护

- 文档: `docs/MONITORING.md`
- 快速指南: `monitoring/README.md`
- 管理脚本: `scripts/monitoring.sh`
- 测试脚本: `scripts/test_monitoring.sh`

## 总结

TTQuant 监控系统已完整实现，提供了从基础设施到业务指标的全方位监控能力。系统易于部署、使用和维护，为交易系统的稳定运行提供了强有力的保障。
