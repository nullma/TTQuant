# TTQuant 监控系统快速启动指南

## 一键启动

### 启动完整监控栈

```bash
# 进入 docker 目录
cd docker

# 启动所有监控服务
docker-compose up -d prometheus grafana alertmanager node-exporter postgres-exporter

# 查看服务状态
docker-compose ps
```

### 启动应用服务（带监控）

```bash
# 启动数据库
docker-compose up -d timescaledb

# 启动行情服务
docker-compose up -d md-binance

# 启动交易网关
docker-compose up -d gateway-binance

# 查看所有服务
docker-compose ps
```

## 访问地址

| 服务 | 地址 | 默认凭证 |
|------|------|----------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| AlertManager | http://localhost:9093 | - |
| Market Data Metrics | http://localhost:8080/metrics | - |
| Gateway Metrics | http://localhost:8081/metrics | - |

## 验证监控

### 1. 检查 Prometheus Targets

```bash
# 访问 Prometheus UI
open http://localhost:9090/targets

# 或使用 curl
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

所有 targets 应该显示为 "UP" 状态。

### 2. 查看 Grafana Dashboard

1. 访问 http://localhost:3000
2. 登录（admin/admin）
3. 导航到 Dashboards -> Browse
4. 打开 "TTQuant Trading System"

### 3. 测试指标采集

```bash
# 检查 Market Data 指标
curl http://localhost:8080/metrics | grep market_data

# 检查 Gateway 指标
curl http://localhost:8081/metrics | grep orders

# 检查系统指标
curl http://localhost:9100/metrics | grep node_cpu
```

## 常用命令

### 查看日志

```bash
# Prometheus 日志
docker logs -f ttquant-prometheus

# Grafana 日志
docker logs -f ttquant-grafana

# AlertManager 日志
docker logs -f ttquant-alertmanager
```

### 重启服务

```bash
# 重启 Prometheus（重新加载配置）
docker-compose restart prometheus

# 重启 Grafana
docker-compose restart grafana

# 重启所有监控服务
docker-compose restart prometheus grafana alertmanager
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## 配置文件位置

```
monitoring/
├── prometheus.yml          # Prometheus 配置
├── alerts.yml             # 告警规则
├── alertmanager.yml       # AlertManager 配置
├── grafana/
│   ├── datasources.yml    # Grafana 数据源
│   └── dashboards.yml     # Dashboard 配置
└── dashboards/
    └── ttquant.json       # 主 Dashboard
```

## 修改配置

### 修改 Prometheus 配置

1. 编辑 `monitoring/prometheus.yml`
2. 重新加载配置:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   # 或重启容器
   docker-compose restart prometheus
   ```

### 修改告警规则

1. 编辑 `monitoring/alerts.yml`
2. 重新加载配置:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

### 修改 AlertManager 配置

1. 编辑 `monitoring/alertmanager.yml`
2. 重新加载配置:
   ```bash
   curl -X POST http://localhost:9093/-/reload
   # 或重启容器
   docker-compose restart alertmanager
   ```

## Python 策略引擎集成

### 安装依赖

```bash
pip install prometheus-client
```

### 启动带监控的策略引擎

```bash
cd python/strategy
python engine_with_metrics.py
```

### 验证指标

```bash
# 查看策略指标
curl http://localhost:8000/metrics | grep strategy
```

## 故障排查

### Prometheus 无法抓取指标

```bash
# 检查网络连接
docker exec ttquant-prometheus ping md-binance

# 检查端口
docker exec ttquant-prometheus curl http://md-binance:8080/metrics

# 查看 Prometheus 日志
docker logs ttquant-prometheus | grep error
```

### Grafana 无数据

```bash
# 检查数据源
curl http://localhost:3000/api/datasources

# 测试 Prometheus 连接
curl http://localhost:9090/api/v1/query?query=up
```

### 告警未触发

```bash
# 查看告警规则状态
curl http://localhost:9090/api/v1/rules

# 查看活跃告警
curl http://localhost:9090/api/v1/alerts

# 查看 AlertManager 状态
curl http://localhost:9093/api/v2/status
```

## 下一步

1. 阅读完整文档: [docs/MONITORING.md](../docs/MONITORING.md)
2. 自定义 Dashboard: 在 Grafana UI 中创建新面板
3. 配置告警通知: 编辑 `monitoring/alertmanager.yml`
4. 添加自定义指标: 参考 `python/strategy/metrics.py`

## 支持

- 文档: [docs/MONITORING.md](../docs/MONITORING.md)
- Issues: https://github.com/ttquant/ttquant/issues
