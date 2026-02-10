# OKX 集成快速启动指南

## 🚀 快速启动

### 1. 启动 OKX 服务

```bash
cd /c/Users/11915/Desktop/TTQuant

# 启动 OKX Market Data 和 Gateway
docker compose -f docker/docker-compose.yml up -d md-okx gateway-okx

# 查看服务状态
docker compose -f docker/docker-compose.yml ps
```

### 2. 查看日志

```bash
# OKX Market Data 日志
docker compose -f docker/docker-compose.yml logs -f md-okx

# OKX Gateway 日志
docker compose -f docker/docker-compose.yml logs -f gateway-okx
```

### 3. 运行测试

```bash
cd python
python test_okx.py
```

---

## 📊 服务端口

| 服务 | ZMQ 端口 | Metrics 端口 | 用途 |
|------|----------|--------------|------|
| md-okx | 5558 | 8082 | OKX 行情数据 |
| gateway-okx | 5559 (Pull), 5560 (Pub) | 8083 | OKX 订单网关 |

---

## 🔑 环境变量配置

在 `.env` 文件中配置（可选，未配置时使用模拟模式）：

```bash
# OKX API 凭证
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
OKX_TESTNET=true
```

---

## 📝 Python 代码示例

### 接收 OKX 行情

```python
import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5558")
socket.setsockopt_string(zmq.SUBSCRIBE, "md.")

while True:
    topic = socket.recv_string()
    data = socket.recv_pyobj()
    print(f"{data.symbol}: {data.last_price}")
```

### 提交 OKX 订单

```python
from strategy.engine import OrderGateway, Order

gateway = OrderGateway(
    endpoint="tcp://localhost:5559",
    use_protobuf=True
)

order = Order(
    order_id="TEST_001",
    strategy_id="test",
    symbol="BTCUSDT",
    side="BUY",
    price=50000.0,
    volume=1,
)

gateway.submit_order(order)
```

### 运行策略

```python
from strategy.engine import StrategyEngine, OrderGateway
from strategy.strategies.ema_cross import EMACrossStrategy

# 创建引擎
engine = StrategyEngine(
    md_endpoints=["tcp://localhost:5558"],
    trade_endpoint="tcp://localhost:5560",
)

# 创建网关
gateway = OrderGateway(
    endpoint="tcp://localhost:5559",
    use_protobuf=True
)

# 创建策略
strategy = EMACrossStrategy(
    strategy_id="ema_cross_okx",
    config={
        "symbol": "BTCUSDT",
        "fast_period": 5,
        "slow_period": 20,
        "trade_volume": 1,
    }
)
strategy.set_order_gateway(gateway)

engine.add_strategy(strategy)
engine.run()
```

---

## 🔍 验证和监控

### 查看数据库数据

```bash
# OKX 行情数据
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
  "SELECT symbol, last_price, volume, exchange FROM market_data WHERE exchange='okx' ORDER BY time DESC LIMIT 10;"

# OKX 订单
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
  "SELECT order_id, symbol, side, price, volume, status FROM orders ORDER BY time DESC LIMIT 10;"
```

### 查看 Prometheus 指标

```bash
# OKX Market Data 指标
curl http://localhost:8082/metrics

# OKX Gateway 指标
curl http://localhost:8083/metrics
```

---

## 🛠️ 故障排除

### 服务无法启动

```bash
# 检查日志
docker compose -f docker/docker-compose.yml logs md-okx
docker compose -f docker/docker-compose.yml logs gateway-okx

# 重启服务
docker compose -f docker/docker-compose.yml restart md-okx gateway-okx
```

### 无法接收行情

1. 检查服务是否运行：`docker compose ps`
2. 检查端口是否开放：`netstat -an | grep 5558`
3. 查看日志：`docker compose logs -f md-okx`

### 订单提交失败

1. 检查 API 凭证是否正确
2. 查看 Gateway 日志：`docker compose logs -f gateway-okx`
3. 验证符号格式：BTCUSDT（内部格式）会自动转换为 BTC-USDT（OKX 格式）

---

## 📚 更多信息

- 详细实现说明：`IMPLEMENTATION_SUMMARY.md`
- 完整测试脚本：`python/test_okx.py`
- OKX API 文档：https://www.okx.com/docs-v5/en/

---

## ⚠️ 注意事项

1. **模拟模式**：未配置 API 凭证时，系统自动使用模拟模式
2. **符号格式**：内部统一使用 BTCUSDT 格式，会自动转换为 OKX 的 BTC-USDT 格式
3. **手续费**：模拟模式使用 0.1% 手续费
4. **滑点**：模拟模式使用 0.01% 滑点
5. **测试网**：默认使用测试网（OKX_TESTNET=true）

---

## 🎯 下一步

1. ✅ 启动服务
2. ✅ 运行测试
3. ✅ 验证数据
4. ⏭️ 配置真实 API（可选）
5. ⏭️ 部署到生产环境
