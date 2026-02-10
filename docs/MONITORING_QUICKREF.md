# TTQuant 监控系统 - 快速参考卡

## 一键启动

```bash
# 启动监控系统
make monitoring-start

# 或
./scripts/monitoring.sh start
```

## 访问地址

| 服务 | URL | 凭证 |
|------|-----|------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| AlertManager | http://localhost:9093 | - |

## 指标端点

| 服务 | 端点 |
|------|------|
| Market Data | http://localhost:8080/metrics |
| Gateway | http://localhost:8081/metrics |
| Strategy Engine | http://localhost:8000/metrics |
| Node Exporter | http://localhost:9100/metrics |
| Postgres Exporter | http://localhost:9187/metrics |

## 常用命令

```bash
# 查看状态
make monitoring-status

# 查看日志
make monitoring-logs

# 重启服务
make monitoring-restart

# 验证配置
make monitoring-validate

# 运行测试
make monitoring-test

# 重新加载配置
make monitoring-reload

# 备份数据
make monitoring-backup
```

## 常用 PromQL 查询

```promql
# 行情延迟 P99
histogram_quantile(0.99, rate(market_data_latency_ms_bucket[5m]))

# 订单成功率
rate(orders_success_total[5m]) / rate(orders_total[5m])

# 策略 PnL
strategy_pnl_total

# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

## 告警级别

| 级别 | 响应时间 | 示例 |
|------|----------|------|
| Critical | 5 分钟内 | 服务宕机、严重亏损 |
| Warning | 1 小时内 | 高延迟、低胜率 |
| Info | 工作时间 | 一般性通知 |

## 故障排查

### Prometheus 无法抓取指标

```bash
# 检查网络
docker exec ttquant-prometheus ping md-binance

# 检查端口
docker exec ttquant-prometheus curl http://md-binance:8080/metrics

# 查看日志
docker logs ttquant-prometheus
```

### Grafana 无数据

```bash
# 测试 Prometheus 连接
curl http://localhost:9090/api/v1/query?query=up

# 检查数据源
# Grafana UI -> Configuration -> Data Sources
```

### 告警未触发

```bash
# 查看告警规则状态
curl http://localhost:9090/api/v1/rules

# 查看活跃告警
curl http://localhost:9090/api/v1/alerts
```

## 关键指标阈值

| 指标 | 正常值 | 警告值 | 严重值 |
|------|--------|--------|--------|
| 行情延迟 | < 50ms | > 1000ms | > 5000ms |
| 订单延迟 | < 100ms | > 500ms | > 2000ms |
| 订单成功率 | > 95% | < 90% | < 70% |
| CPU 使用率 | < 70% | > 80% | > 90% |
| 内存使用率 | < 75% | > 85% | > 95% |

## 文档位置

| 文档 | 路径 |
|------|------|
| 完整使用文档 | `docs/MONITORING.md` |
| 快速启动指南 | `monitoring/README.md` |
| 实现总结 | `docs/MONITORING_IMPLEMENTATION.md` |
| 完整报告 | `docs/MONITORING_REPORT.md` |

## 配置文件

| 配置 | 路径 |
|------|------|
| Prometheus | `monitoring/prometheus.yml` |
| 告警规则 | `monitoring/alerts.yml` |
| AlertManager | `monitoring/alertmanager.yml` |
| Dashboard | `monitoring/dashboards/ttquant.json` |

## 支持

- 📖 文档: `docs/MONITORING.md`
- 🚀 快速开始: `monitoring/README.md`
- 🔧 管理脚本: `scripts/monitoring.sh`
- ✅ 测试脚本: `scripts/test_monitoring.sh`
