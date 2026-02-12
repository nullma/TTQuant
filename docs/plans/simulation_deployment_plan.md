# 模拟环境部署实施计划

## 目标
部署完整系统到测试环境，进行纸面交易验证

## 任务分解

### Phase 1: Docker 环境准备 (30分钟)
- [ ] 创建 Docker Compose 配置
- [ ] 配置 TimescaleDB 容器
- [ ] 配置 Prometheus 容器
- [ ] 配置 Grafana 容器
- [ ] 配置应用容器（Python + Rust）
- [ ] 网络和卷配置

**容器清单**:
```yaml
services:
  - timescaledb: 时序数据库
  - prometheus: 监控指标收集
  - grafana: 可视化仪表板
  - market-data: 行情数据服务 (Rust)
  - strategy-engine: 策略引擎 (Python)
  - order-gateway: 订单网关 (Rust)
  - risk-monitor: 风险监控 (Python)
```

### Phase 2: 配置管理 (20分钟)
- [ ] 创建测试环境配置文件
- [ ] 配置交易所 API（测试网）
- [ ] 配置数据库连接
- [ ] 配置 ZMQ 通信端口
- [ ] 配置监控端口
- [ ] 环境变量管理

**配置文件**:
- `config/test.yaml`: 测试环境配置
- `config/exchanges/binance_testnet.yaml`: Binance 测试网
- `config/exchanges/okx_testnet.yaml`: OKX 测试网
- `.env.test`: 环境变量

### Phase 3: 服务部署 (40分钟)
- [ ] 构建 Docker 镜像
- [ ] 启动数据库服务
- [ ] 初始化数据库表结构
- [ ] 启动监控服务
- [ ] 启动行情数据服务
- [ ] 启动策略引擎
- [ ] 启动订单网关
- [ ] 启动风险监控

**部署顺序**:
1. TimescaleDB → 初始化表
2. Prometheus + Grafana → 导入仪表板
3. Market Data Service → 连接交易所
4. Strategy Engine → 加载策略
5. Order Gateway → 纸面交易模式
6. Risk Monitor → 启动监控

### Phase 4: 纸面交易测试 (30分钟)
- [ ] 连接交易所测试网
- [ ] 订阅实时行情
- [ ] 启动策略（小仓位）
- [ ] 验证信号生成
- [ ] 验证订单执行（模拟）
- [ ] 验证风险监控
- [ ] 验证数据持久化

**测试场景**:
1. 行情订阅和处理
2. 策略信号生成
3. 订单创建和执行（模拟）
4. 持仓管理
5. 风险限额检查
6. 异常情况处理

### Phase 5: 监控验证 (20分钟)
- [ ] 验证 Prometheus 指标采集
- [ ] 验证 Grafana 仪表板
- [ ] 验证日志输出
- [ ] 验证告警规则
- [ ] 性能指标检查

**监控指标**:
- 行情延迟 (< 100ms)
- 策略执行延迟 (< 50ms)
- 订单延迟 (< 200ms)
- CPU 使用率 (< 50%)
- 内存使用 (< 2GB)
- 网络流量

## 技术实现

### Docker Compose 配置
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_DB: ttquant_test
      POSTGRES_USER: ttquant
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards

  market-data:
    build:
      context: ./rust/market_data
    environment:
      RUST_LOG: info
      ZMQ_PUB_PORT: 5555
    ports:
      - "5555:5555"

  strategy-engine:
    build:
      context: ./python
    command: python strategy_engine.py --config config/test.yaml
    environment:
      PYTHONUNBUFFERED: 1
      DB_HOST: timescaledb
      ZMQ_SUB_PORT: 5555
    depends_on:
      - timescaledb
      - market-data

  order-gateway:
    build:
      context: ./rust/order_gateway
    environment:
      RUST_LOG: info
      PAPER_TRADING: "true"
    ports:
      - "5556:5556"

  risk-monitor:
    build:
      context: ./python
    command: python risk_monitor.py --port 8001
    environment:
      DB_HOST: timescaledb
    ports:
      - "8001:8001"
    depends_on:
      - timescaledb

volumes:
  timescale_data:
  prometheus_data:
  grafana_data:
```

### 测试环境配置
```yaml
# config/test.yaml
environment: test
paper_trading: true

database:
  host: timescaledb
  port: 5432
  database: ttquant_test
  user: ttquant
  password: ${DB_PASSWORD}

exchanges:
  binance:
    testnet: true
    api_key: ${BINANCE_TESTNET_KEY}
    api_secret: ${BINANCE_TESTNET_SECRET}

strategies:
  - id: ema_cross_test
    type: ema_cross
    symbol: BTCUSDT
    position_size: 0.01  # 小仓位测试
    enabled: true

risk_limits:
  max_position_size: 0.1
  max_daily_loss: 1000
  max_drawdown: 0.05

monitoring:
  prometheus_port: 8001
  log_level: info
```

### 部署脚本
```bash
#!/bin/bash
# scripts/deploy_test.sh

echo "🚀 部署测试环境..."

# 1. 检查环境变量
if [ ! -f .env.test ]; then
    echo "❌ .env.test 文件不存在"
    exit 1
fi

# 2. 构建镜像
echo "📦 构建 Docker 镜像..."
docker-compose -f docker-compose.test.yml build

# 3. 启动服务
echo "🔧 启动服务..."
docker-compose -f docker-compose.test.yml up -d

# 4. 等待数据库就绪
echo "⏳ 等待数据库启动..."
sleep 10

# 5. 初始化数据库
echo "💾 初始化数据库..."
docker-compose -f docker-compose.test.yml exec timescaledb \
    psql -U ttquant -d ttquant_test -f /docker-entrypoint-initdb.d/init.sql

# 6. 检查服务状态
echo "✅ 检查服务状态..."
docker-compose -f docker-compose.test.yml ps

echo "🎉 部署完成！"
echo "📊 Grafana: http://localhost:3000"
echo "📈 Prometheus: http://localhost:9090"
echo "🔍 风险监控: http://localhost:8001/metrics"
```

## 预期产出

1. **Docker 配置**:
   - `docker-compose.test.yml`
   - `Dockerfile` (Python, Rust)
   - `.dockerignore`

2. **配置文件**:
   - `config/test.yaml`
   - `config/exchanges/binance_testnet.yaml`
   - `.env.test`

3. **部署脚本**:
   - `scripts/deploy_test.sh`
   - `scripts/stop_test.sh`
   - `scripts/logs_test.sh`

4. **测试报告**:
   - `reports/simulation_test_report.md`
   - 包含所有服务的运行状态和性能指标

## 风险和注意事项

1. **测试网限制**: 测试网可能不稳定，需要处理连接中断
2. **资源消耗**: 多个容器需要足够的内存（建议 8GB+）
3. **端口冲突**: 确保端口未被占用
4. **数据同步**: 测试网数据可能与主网不同

## 成功标准

- ✅ 所有容器成功启动
- ✅ 数据库连接正常
- ✅ 行情数据实时接收
- ✅ 策略信号正常生成
- ✅ 订单模拟执行成功
- ✅ 监控指标正常采集
- ✅ Grafana 仪表板显示正常
- ✅ 系统稳定运行 > 1 小时

## 时间估算

总计: ~2.5 小时
- Phase 1: 30 分钟
- Phase 2: 20 分钟
- Phase 3: 40 分钟
- Phase 4: 30 分钟
- Phase 5: 20 分钟
- 调试和优化: 20 分钟

## 后续步骤

部署成功后：
1. 运行 24 小时稳定性测试
2. 收集性能数据和日志
3. 优化配置参数
4. 准备生产环境部署
