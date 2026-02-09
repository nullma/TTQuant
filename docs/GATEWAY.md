# Gateway 模块文档

## 概述

Gateway（交易网关）是 TTQuant 系统的核心交易模块，负责：

1. **订单接收** - 从策略引擎接收订单（ZMQ PULL）
2. **风控检查** - 验证订单合规性（持仓限制、价格范围、频率限制）
3. **交易所路由** - 将订单提交到对应的交易所
4. **成交回报** - 广播交易结果（ZMQ PUB）
5. **持仓管理** - 实时跟踪持仓状态

## 架构设计

```
策略引擎 --[ZMQ PUSH]--> Gateway --[HTTP/WebSocket]--> 交易所
                            |
                            v
                      [ZMQ PUB] --> 策略引擎（成交回报）
```

### 核心组件

1. **OrderManager** - 订单管理器
   - 接收订单（ZMQ PULL）
   - 协调风控和交易所提交
   - 发布成交回报（ZMQ PUB）

2. **RiskManager** - 风控管理器
   - 订单年龄检查（防止过期订单）
   - 价格合理性检查
   - 持仓限制检查
   - 频率限制检查（全局 + 策略级别）

3. **ExchangeRouter** - 交易所路由器
   - 支持多交易所（当前：Binance）
   - 统一的订单提交接口
   - 自动降级到模拟模式

## 配置文件

### config/risk.toml

```toml
[position_limits]
BTCUSDT = 10
ETHUSDT = 100
BNBUSDT = 1000

[rate_limits]
max_orders_per_second = 100
max_orders_per_strategy_per_second = 10

[order_validation]
max_order_age_ms = 500
min_price = 0.01
max_price = 1000000.0
```

### 环境变量

```bash
# 交易所选择
EXCHANGE=binance

# ZeroMQ 端点
ZMQ_PULL_ENDPOINT=tcp://*:5556  # 接收订单
ZMQ_PUB_ENDPOINT=tcp://*:5557   # 发布成交

# Binance API（可选）
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true  # 使用测试网
```

## 运行模式

### 1. 模拟模式（默认）

不需要 API 密钥，自动模拟订单执行：

- 模拟滑点（0.01%）
- 模拟手续费（0.1%）
- 立即成交

```bash
# 不设置 API 密钥即为模拟模式
docker compose up gateway-binance
```

### 2. 测试网模式

使用 Binance 测试网：

```bash
export BINANCE_TESTNET=true
export BINANCE_API_KEY=your_testnet_key
export BINANCE_API_SECRET=your_testnet_secret

docker compose up gateway-binance
```

### 3. 生产模式

使用真实 Binance API：

```bash
export BINANCE_TESTNET=false
export BINANCE_API_KEY=your_real_key
export BINANCE_API_SECRET=your_real_secret

docker compose up gateway-binance
```

## 订单流程

### 1. 订单提交

策略引擎通过 ZMQ PUSH 发送订单：

```python
import zmq

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.connect("tcp://gateway-binance:5556")

order = {
    'order_id': 'ORDER_001',
    'strategy_id': 'my_strategy',
    'symbol': 'BTCUSDT',
    'price': 50000.0,
    'volume': 1,
    'side': 'BUY',
    'timestamp': int(time.time() * 1e9)
}

socket.send_json(order)
```

### 2. 风控检查

Gateway 自动执行以下检查：

- ✅ 订单年龄 < 500ms
- ✅ 价格在合理范围内
- ✅ 持仓不超过限制
- ✅ 频率不超过限制

### 3. 交易所提交

- 如果有 API 密钥：提交到真实交易所
- 如果没有 API 密钥：使用模拟模式
- 如果提交失败：降级到模拟模式

### 4. 成交回报

Gateway 通过 ZMQ PUB 广播成交结果：

```python
import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://gateway-binance:5557")
socket.setsockopt_string(zmq.SUBSCRIBE, "trade.")

while True:
    topic = socket.recv_string()
    data = socket.recv_string()
    trade = json.loads(data)

    if trade['status'] == 'FILLED':
        print(f"成交: {trade['filled_volume']} @ {trade['filled_price']}")
    else:
        print(f"拒绝: {trade['error_message']}")
```

## 错误处理

### 错误码

| 错误码 | 类型 | 说明 | 可重试 |
|--------|------|------|--------|
| 1001 | 风控拒绝 | 订单未通过风控检查 | ❌ |
| 2001 | 交易所错误 | 交易所提交失败 | ✅ |

### 可重试错误

以下错误会标记为可重试：

- 网络超时
- 连接错误
- 频率限制（429）

策略引擎可以根据 `is_retryable` 字段决定是否重试。

## 性能指标

### 延迟

- 风控检查: < 0.1ms
- 模拟模式: < 1ms
- 真实模式: 10-50ms（取决于网络）

### 吞吐量

- 最大订单频率: 100 orders/s（全局）
- 单策略频率: 10 orders/s

## 测试

### 单元测试

```bash
cd rust/gateway
cargo test
```

### 集成测试

```bash
# 启动服务
make up

# 运行网关测试
make test-gateway

# 查看日志
make logs-gateway
```

## 监控

### 日志

```bash
# 实时日志
make logs-gateway

# 查看最近 100 行
docker logs ttquant-gateway-binance --tail 100
```

### 关键日志

```
[Order #1] Received: BUY 1 BTCUSDT @ 50000.0 (strategy: my_strategy)
[Order #1] FILLED: 1 BTCUSDT @ 50005.0 (commission: $5.00)
```

## 故障排查

### 问题 1: 订单被拒绝

**症状**: 所有订单都被拒绝

**原因**: 风控配置过严

**解决**: 检查 `config/risk.toml`，调整限制

### 问题 2: 无法连接交易所

**症状**: 日志显示 "Connection timeout"

**原因**: 网络问题或 API 密钥错误

**解决**:
1. 检查网络连接
2. 验证 API 密钥
3. 使用模拟模式测试

### 问题 3: 频率限制

**症状**: 错误 "Rate limit exceeded"

**原因**: 订单提交过快

**解决**: 调整 `rate_limits` 配置

## 扩展

### 添加新交易所

1. 在 `src/exchange/` 创建新文件（如 `okx.rs`）
2. 实现 `Exchange` trait
3. 在 `ExchangeRouter::new()` 中注册

```rust
pub struct OkxExchange {
    // ...
}

impl Exchange for OkxExchange {
    fn name(&self) -> &str {
        "okx"
    }

    async fn submit_order(&self, order: &Order) -> Result<Trade> {
        // 实现 OKX API 调用
    }
}
```

## 安全建议

1. **API 密钥管理**
   - 使用环境变量，不要硬编码
   - 使用只读权限的 API 密钥（如果可能）
   - 定期轮换密钥

2. **风控配置**
   - 设置合理的持仓限制
   - 启用频率限制
   - 监控异常订单

3. **网络安全**
   - 使用 HTTPS
   - 验证 SSL 证书
   - 限制 IP 白名单（如果交易所支持）

## 下一步

- [ ] 实现数据库写入（订单和成交记录）
- [ ] 添加健康检查端点
- [ ] 实现 Prometheus 指标
- [ ] 支持更多交易所（OKX, Bybit）
- [ ] 实现订单撤销功能
- [ ] 添加订单状态查询

---

**文档版本**: v0.1.0
**最后更新**: 2026-02-10
