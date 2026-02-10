# TTQuant 监控系统使用指南

## 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [快速开始](#快速开始)
4. [指标说明](#指标说明)
5. [Dashboard 使用](#dashboard-使用)
6. [告警配置](#告警配置)
7. [故障排查](#故障排查)
8. [最佳实践](#最佳实践)

---

## 系统概述

TTQuant 监控系统基于 Prometheus + Grafana 构建，提供全方位的系统性能和交易指标监控。

### 核心功能

- **实时监控**: 5秒级别的指标采集和展示
- **多维度指标**: 覆盖行情、交易、策略、系统资源等
- **智能告警**: 基于规则的自动告警和通知
- **可视化分析**: 丰富的 Dashboard 和图表
- **历史数据**: 30天数据保留，支持趋势分析

### 监控组件

| 组件 | 端口 | 说明 |
|------|------|------|
| Prometheus | 9090 | 指标收集和存储 |
| Grafana | 3000 | 可视化展示 |
| AlertManager | 9093 | 告警管理 |
| Node Exporter | 9100 | 系统指标导出 |
| Postgres Exporter | 9187 | 数据库指标导出 |

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Grafana (3000)                         │
│                    可视化 Dashboard                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Prometheus (9090)                         │
│              指标收集、存储、告警规则评估                      │
└─────┬──────────┬──────────┬──────────┬──────────┬──────────┘
      │          │          │          │          │
      ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Market   │ │ Gateway  │ │ Strategy │ │   Node   │ │ Postgres │
│   Data   │ │          │ │  Engine  │ │ Exporter │ │ Exporter │
│  :8080   │ │  :8080   │ │  :8000   │ │  :9100   │ │  :9187   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 数据流

1. **指标导出**: 各服务通过 HTTP `/metrics` 端点导出 Prometheus 格式指标
2. **指标采集**: Prometheus 定期抓取各服务的指标
3. **规则评估**: Prometheus 评估告警规则，触发告警
4. **告警通知**: AlertManager 接收告警并发送通知
5. **可视化**: Grafana 查询 Prometheus 数据并展示

---

## 快速开始

### 1. 启动监控系统

```bash
cd docker
docker-compose up -d prometheus grafana alertmanager node-exporter postgres-exporter
```

### 2. 访问 Grafana

1. 打开浏览器访问: http://localhost:3000
2. 默认登录凭证:
   - 用户名: `admin`
   - 密码: `admin` (首次登录后会要求修改)

### 3. 查看 Dashboard

导入预配置的 Dashboard:
- 主 Dashboard: "TTQuant Trading System"
- 自动加载位置: `monitoring/dashboards/ttquant.json`

### 4. 访问 Prometheus

- Web UI: http://localhost:9090
- 查看指标: http://localhost:9090/graph
- 查看告警: http://localhost:9090/alerts

### 5. 访问 AlertManager

- Web UI: http://localhost:9093
- 查看活跃告警和静默规则

---

## 指标说明

### Market Data 指标

#### 行情接收指标

```promql
# 行情接收速率 (msg/s)
rate(market_data_received_total[1m])

# 行情延迟 (ms)
histogram_quantile(0.99, rate(market_data_latency_ms_bucket[5m]))

# WebSocket 连接状态 (1=连接, 0=断开)
ws_connection_status
```

#### 关键指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `market_data_received_total` | Counter | 接收的行情消息总数 |
| `market_data_latency_ms` | Histogram | 行情延迟（交易所时间到本地时间） |
| `ws_connection_status` | Gauge | WebSocket 连接状态 |
| `ws_reconnect_total` | Counter | WebSocket 重连次数 |
| `message_parse_errors_total` | Counter | 消息解析错误数 |
| `market_last_price` | Gauge | 最新价格 |
| `market_volume_24h` | Gauge | 24小时成交量 |

### Gateway 指标

#### 订单处理指标

```promql
# 订单处理速率 (orders/s)
rate(orders_total[1m])

# 订单成功率
rate(orders_success_total[5m]) / rate(orders_total[5m])

# 订单延迟 (ms)
histogram_quantile(0.99, rate(order_processing_latency_ms_bucket[5m]))
```

#### 关键指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `orders_total` | Counter | 订单总数 |
| `orders_success_total` | Counter | 成功订单数 |
| `orders_failed_total` | Counter | 失败订单数 |
| `orders_risk_rejected_total` | Counter | 风控拒单数 |
| `order_processing_latency_ms` | Histogram | 订单处理延迟 |
| `trades_total` | Counter | 成交总数 |
| `trade_volume_total` | Counter | 成交金额 |
| `commission_paid_total` | Counter | 手续费总额 |
| `current_position` | Gauge | 当前持仓 |
| `active_orders` | Gauge | 活跃订单数 |

### Strategy Engine 指标

#### 策略性能指标

```promql
# 策略 PnL
strategy_pnl_total

# 策略胜率
strategy_win_rate

# 策略持仓
strategy_position_size

# 策略最大回撤
strategy_max_drawdown_usd
```

#### 关键指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `strategy_pnl_total` | Gauge | 策略总 PnL（已实现+未实现） |
| `strategy_realized_pnl` | Gauge | 已实现 PnL |
| `strategy_unrealized_pnl` | Gauge | 未实现 PnL |
| `strategy_position_size` | Gauge | 持仓数量 |
| `strategy_position_value_usd` | Gauge | 持仓价值 |
| `strategy_trades_total` | Counter | 交易次数 |
| `strategy_win_rate` | Gauge | 胜率 |
| `strategy_max_drawdown_usd` | Gauge | 最大回撤 |
| `strategy_sharpe_ratio` | Gauge | 夏普比率 |

### 系统资源指标

```promql
# CPU 使用率
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 磁盘使用率
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100
```

---

## Dashboard 使用

### 主 Dashboard 面板

#### 1. System Overview（系统概览）

- **服务状态**: 显示各服务的运行状态（绿色=正常，红色=异常）
- **活跃策略数**: 当前运行的策略数量
- **关键指标**: 快速查看系统健康状况

#### 2. Market Data Monitoring（行情监控）

- **行情接收速率**: 每秒接收的行情消息数
- **行情延迟**: P50/P95/P99 延迟分布
- **连接状态**: WebSocket 连接健康状况

**使用建议**:
- 正常情况下，行情接收速率应该稳定
- P99 延迟应该 < 100ms
- 如果延迟突然增加，检查网络和交易所状态

#### 3. Trading Monitoring（交易监控）

- **订单处理速率**: 每秒处理的订单数
- **订单延迟**: 订单从接收到执行的延迟
- **订单成功率**: 成功订单占比（应该 > 95%）
- **成交统计**: 成交次数和金额

**使用建议**:
- 订单成功率低于 90% 需要立即检查
- P99 延迟应该 < 500ms
- 关注失败订单的错误类型

#### 4. Strategy Performance（策略性能）

- **策略 PnL**: 实时盈亏曲线
- **胜率**: 盈利交易占比
- **持仓**: 当前持仓情况
- **最大回撤**: 风险指标

**使用建议**:
- 每日检查策略 PnL 曲线
- 胜率低于 30% 需要优化策略
- 最大回撤超过阈值应该停止策略

### 自定义查询

在 Grafana 中可以使用 PromQL 进行自定义查询:

```promql
# 查询特定交易对的行情延迟
market_data_latency_ms{symbol="BTCUSDT"}

# 查询特定策略的 PnL
strategy_pnl_total{strategy_id="ema_cross_1"}

# 计算订单失败率
rate(orders_failed_total[5m]) / rate(orders_total[5m])
```

---

## 告警配置

### 告警规则

告警规则定义在 `monitoring/alerts.yml` 中，包括:

#### 1. 行情数据告警

- **HighMarketDataLatency**: 行情延迟 > 1000ms 持续 1 分钟
- **CriticalMarketDataLatency**: 行情延迟 > 5000ms 持续 30 秒
- **MarketDataStreamDown**: 2 分钟内无行情数据
- **LowMarketDataRate**: 行情接收速率异常低

#### 2. 交易网关告警

- **HighOrderLatency**: 订单延迟 > 500ms 持续 1 分钟
- **CriticalOrderLatency**: 订单延迟 > 2000ms 持续 30 秒
- **HighOrderFailureRate**: 订单失败率 > 10% 持续 2 分钟
- **CriticalOrderFailureRate**: 订单失败率 > 30% 持续 1 分钟
- **GatewayDown**: Gateway 服务宕机

#### 3. 策略告警

- **StrategyLoss**: 策略亏损 > $1000 持续 5 分钟
- **CriticalStrategyLoss**: 策略亏损 > $5000 持续 2 分钟
- **LowWinRate**: 胜率 < 30% 持续 10 分钟
- **StrategyEngineDown**: 策略引擎宕机

#### 4. 系统资源告警

- **HighCPUUsage**: CPU 使用率 > 80% 持续 5 分钟
- **HighMemoryUsage**: 内存使用率 > 85% 持续 5 分钟
- **HighDiskUsage**: 磁盘使用率 > 85% 持续 5 分钟

### 告警通知配置

编辑 `monitoring/alertmanager.yml` 配置告警接收者:

#### 邮件通知

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'ttquant-alerts@example.com'
  smtp_auth_username: 'your-email@example.com'
  smtp_auth_password: 'your-app-password'
```

#### Slack 通知（可选）

```yaml
receivers:
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#critical-alerts'
        api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'
```

### 告警静默

在 AlertManager UI (http://localhost:9093) 中可以临时静默告警:

1. 点击 "Silences"
2. 点击 "New Silence"
3. 填写匹配条件和持续时间
4. 添加注释说明原因

---

## 故障排查

### 问题 1: 无法访问 Grafana

**症状**: 浏览器无法打开 http://localhost:3000

**排查步骤**:
```bash
# 检查容器状态
docker ps | grep grafana

# 查看日志
docker logs ttquant-grafana

# 重启容器
docker-compose restart grafana
```

### 问题 2: Dashboard 无数据

**症状**: Grafana Dashboard 显示 "No data"

**排查步骤**:
```bash
# 1. 检查 Prometheus 是否正常
curl http://localhost:9090/-/healthy

# 2. 检查数据源配置
# 在 Grafana UI: Configuration -> Data Sources -> Prometheus

# 3. 检查服务是否导出指标
curl http://localhost:8080/metrics  # Market Data
curl http://localhost:8081/metrics  # Gateway

# 4. 在 Prometheus UI 查询指标
# 访问 http://localhost:9090/graph
# 输入查询: up{job="market-data"}
```

### 问题 3: 告警未触发

**症状**: 满足告警条件但未收到通知

**排查步骤**:
```bash
# 1. 检查 Prometheus 告警规则
# 访问 http://localhost:9090/alerts

# 2. 检查 AlertManager 状态
curl http://localhost:9093/-/healthy

# 3. 查看 AlertManager 日志
docker logs ttquant-alertmanager

# 4. 测试邮件配置
# 在 AlertManager UI 手动触发测试告警
```

### 问题 4: 指标采集失败

**症状**: Prometheus targets 显示 "DOWN"

**排查步骤**:
```bash
# 1. 检查目标服务是否运行
docker ps | grep market-data

# 2. 检查网络连接
docker exec ttquant-prometheus ping md-binance

# 3. 检查端口是否开放
docker exec ttquant-prometheus curl http://md-binance:8080/metrics

# 4. 检查 Prometheus 配置
docker exec ttquant-prometheus cat /etc/prometheus/prometheus.yml
```

---

## 最佳实践

### 1. 监控策略

- **分层监控**: 系统层 -> 服务层 -> 业务层
- **关键指标**: 重点关注延迟、成功率、PnL
- **趋势分析**: 定期查看历史数据，发现潜在问题
- **告警优化**: 避免告警疲劳，调整阈值和持续时间

### 2. Dashboard 使用

- **日常检查**: 每天查看主 Dashboard，确认系统健康
- **问题定位**: 使用时间范围选择器缩小问题时间段
- **对比分析**: 使用多个时间序列对比不同交易对或策略
- **导出数据**: 使用 "Inspect" 功能导出原始数据

### 3. 告警管理

- **分级响应**:
  - Critical: 立即处理（5分钟内）
  - Warning: 1小时内处理
  - Info: 工作时间处理
- **告警文档**: 为每个告警编写处理手册
- **定期回顾**: 每周回顾告警历史，优化规则
- **静默管理**: 维护计划时使用静默，避免误报

### 4. 性能优化

- **查询优化**: 使用合适的时间范围和聚合函数
- **数据保留**: 根据需求调整保留时间（默认 30 天）
- **采集频率**: 关键服务 5s，一般服务 15s
- **资源监控**: 定期检查 Prometheus 和 Grafana 资源使用

### 5. 安全建议

- **修改默认密码**: 首次登录后立即修改 Grafana 密码
- **访问控制**: 使用防火墙限制监控端口访问
- **HTTPS**: 生产环境使用 HTTPS 访问 Grafana
- **备份**: 定期备份 Grafana Dashboard 和 Prometheus 数据

### 6. 扩展建议

- **长期存储**: 配置 Prometheus remote write 到 Thanos 或 VictoriaMetrics
- **多集群**: 使用 Prometheus Federation 聚合多个集群数据
- **自定义指标**: 根据业务需求添加自定义指标
- **集成**: 与 PagerDuty、OpsGenie 等工具集成

---

## 附录

### A. 常用 PromQL 查询

```promql
# 行情延迟 P99
histogram_quantile(0.99, rate(market_data_latency_ms_bucket[5m]))

# 订单成功率
rate(orders_success_total[5m]) / rate(orders_total[5m])

# 策略日收益
increase(strategy_pnl_total[1d])

# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 活跃订单数
sum(active_orders) by (exchange)

# 成交金额（1小时）
increase(trade_volume_total[1h])
```

### B. 指标端点

| 服务 | 端点 | 说明 |
|------|------|------|
| Market Data | http://localhost:8080/metrics | 行情服务指标 |
| Gateway | http://localhost:8081/metrics | 交易网关指标 |
| Strategy Engine | http://localhost:8000/metrics | 策略引擎指标 |
| Prometheus | http://localhost:9090/metrics | Prometheus 自身指标 |
| Node Exporter | http://localhost:9100/metrics | 系统指标 |
| Postgres Exporter | http://localhost:9187/metrics | 数据库指标 |

### C. 相关文档

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [AlertManager 配置](https://prometheus.io/docs/alerting/latest/configuration/)

---

## 支持

如有问题或建议，请联系:
- 技术支持: support@ttquant.com
- 文档反馈: docs@ttquant.com
- GitHub Issues: https://github.com/ttquant/ttquant/issues
