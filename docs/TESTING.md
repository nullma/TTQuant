# TTQuant 测试指南

## 🧪 测试清单

### ✅ 阶段 1: Docker 环境测试

#### 1.1 构建镜像

```bash
cd /c/Users/11915/Desktop/TTQuant
make build
```

**预期结果**:
- ✅ Rust 镜像构建成功
- ✅ Python 镜像构建成功
- ✅ 无编译错误

#### 1.2 启动服务

```bash
make up
```

**预期结果**:
```
Creating ttquant-timescaledb ... done
Creating ttquant-md-binance  ... done
Creating ttquant-test-client ... done
```

#### 1.3 检查服务状态

```bash
make ps
```

**预期结果**:
```
NAME                      STATUS
ttquant-timescaledb       Up (healthy)
ttquant-md-binance        Up
ttquant-test-client       Up
```

### ✅ 阶段 2: 行情模块测试

#### 2.1 查看行情日志

```bash
make logs-md
```

**预期输出**:
```
INFO Starting market data service: binance
INFO ZMQ endpoint: tcp://*:5555
INFO Starting Binance market data service
INFO Connected to Binance WebSocket
INFO Sent subscription message
```

#### 2.2 查看测试客户端

```bash
make logs-test
```

**预期输出**:
```
Connecting to tcp://md-binance:5555...
Listening for market data...
[    10] md.BTCUSDT.binance          | Rate: 5.2 msg/s
[    20] md.ETHUSDT.binance          | Rate: 6.1 msg/s
[    30] md.BTCUSDT.binance          | Rate: 5.8 msg/s
```

**性能指标**:
- ✅ 消息接收率 > 1 msg/s
- ✅ 无连接错误
- ✅ Topic 格式正确

#### 2.3 手动测试 ZeroMQ 连接

```bash
# 在宿主机测试
cd python
python test_market_data.py
```

**预期**: 能接收到行情数据

### ✅ 阶段 3: 数据库测试

#### 3.1 连接数据库

```bash
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading
```

#### 3.2 检查表结构

```sql
-- 列出所有表
\dt

-- 查看 market_data 表结构
\d market_data

-- 查看 hypertable 信息
SELECT * FROM timescaledb_information.hypertables;
```

**预期结果**:
- ✅ 7 个表已创建
- ✅ market_data 是 hypertable
- ✅ 索引已创建

#### 3.3 查询行情数据（TODO: 需要实现数据写入）

```sql
-- 查询最新行情
SELECT symbol, last_price, time
FROM market_data
ORDER BY time DESC
LIMIT 10;

-- 统计行情数量
SELECT symbol, COUNT(*) as count
FROM market_data
GROUP BY symbol;
```

**当前状态**: 数据库已就绪，但行情模块尚未实现数据写入

### ✅ 阶段 4: 性能测试

#### 4.1 测试行情吞吐量

```bash
# 运行 60 秒性能测试
docker compose -f docker/docker-compose.yml run --rm test-client \
  timeout 60 python test_market_data.py
```

**性能目标**:
- ✅ 平均吞吐量 > 10 msg/s
- ✅ 无消息丢失
- ✅ 延迟 < 100ms

#### 4.2 监控资源使用

```bash
docker stats ttquant-md-binance ttquant-test-client
```

**预期资源使用**:
- CPU: < 50%
- 内存: < 500MB
- 网络: 稳定

### ✅ 阶段 5: 容错测试

#### 5.1 测试自动重连

```bash
# 重启行情模块
docker compose -f docker/docker-compose.yml restart md-binance

# 观察日志
make logs-md
```

**预期**:
- ✅ 自动重连 WebSocket
- ✅ 3s 内恢复服务
- ✅ 测试客户端继续接收数据

#### 5.2 测试数据库故障恢复

```bash
# 重启数据库
docker compose -f docker/docker-compose.yml restart timescaledb

# 等待健康检查
sleep 15

# 检查服务状态
make ps
```

**预期**:
- ✅ 数据库自动恢复
- ✅ 行情模块继续运行

## 🐛 已知问题

### 1. 数据库写入未实现

**状态**: 🚧 待实现

**影响**: 行情数据不会持久化到数据库

**解决方案**: 需要在 market-data 模块中实现数据库写入逻辑

### 2. 健康检查端点未实现

**状态**: 🚧 待实现

**影响**: Docker healthcheck 会失败

**临时方案**: 注释掉 Dockerfile 中的 HEALTHCHECK

### 3. OKX 和 Tushare 未实现

**状态**: 🚧 待实现

**影响**: 只能接收 Binance 行情

## 📊 测试报告模板

```markdown
## TTQuant 测试报告

**测试日期**: 2026-02-10
**测试环境**: Docker on Windows/Linux/macOS
**测试人员**: [你的名字]

### 测试结果

| 测试项 | 状态 | 备注 |
|--------|------|------|
| Docker 构建 | ✅/❌ | |
| 服务启动 | ✅/❌ | |
| 行情接收 | ✅/❌ | 吞吐量: X msg/s |
| 数据库连接 | ✅/❌ | |
| 自动重连 | ✅/❌ | |
| 资源使用 | ✅/❌ | CPU: X%, MEM: XMB |

### 问题记录

1. [问题描述]
   - 复现步骤
   - 错误日志
   - 解决方案

### 性能数据

- 平均吞吐量: X msg/s
- P99 延迟: X ms
- 内存使用: X MB
- CPU 使用: X%

### 建议

1. [改进建议]
2. [优化方向]
```

## 🚀 下一步测试

1. **实现数据库写入** - 验证数据持久化
2. **压力测试** - 测试极限吞吐量
3. **长时间运行测试** - 24小时稳定性测试
4. **多市场测试** - 同时运行多个行情源

---

**测试完成后，请填写测试报告并提交 Issue！**
