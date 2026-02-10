# TTQuant 数据持久化实现验证清单

## 代码修改验证

### ✓ Rust Common 模块
- [x] `rust/common/src/lib.rs` - 导出 database 模块
- [x] `rust/common/src/database.rs` - 优化为线程安全的实现
- [x] `rust/common/Cargo.toml` - 添加 sqlx 依赖

### ✓ Market Data 模块
- [x] `rust/market-data/src/binance.rs` - 集成数据库写入
  - [x] 数据库连接初始化
  - [x] 批量写入器创建
  - [x] 行情数据异步写入
  - [x] 定时刷新机制
  - [x] 优雅关闭处理

### ✓ Gateway 模块
- [x] `rust/gateway/src/order_manager.rs` - 集成数据库写入
  - [x] 添加数据库字段
  - [x] 订单写入逻辑
  - [x] 成交记录写入
  - [x] 持仓快照写入
- [x] `rust/gateway/src/risk.rs` - 添加持仓详情方法
- [x] `rust/gateway/src/main.rs` - 数据库连接初始化

### ✓ 测试脚本
- [x] `python/test_database.py` - 数据库功能测试
- [x] `python/test_integration.py` - 集成测试

### ✓ 文档
- [x] `docs/database_persistence.md` - 完整文档
- [x] `docs/database_quickstart.md` - 快速开始指南
- [x] `docs/database_implementation_summary.md` - 实现总结

## 功能验证清单

### 1. 数据库连接
```bash
# 启动 TimescaleDB
docker compose -f docker/docker-compose.yml up -d timescaledb

# 验证数据库运行
docker ps | grep timescaledb

# 连接数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "\dt"
```

预期结果：
- [ ] TimescaleDB 容器运行中
- [ ] 可以成功连接数据库
- [ ] 看到所有必需的表（market_data, orders, trades, positions 等）

### 2. Market Data 持久化
```bash
# 启动 Market Data 服务
docker compose -f docker/docker-compose.yml up -d md-binance

# 查看日志
docker compose -f docker/docker-compose.yml logs md-binance | grep -i database
```

预期结果：
- [ ] 日志显示 "Database connection established"
- [ ] 日志显示 "Connected to Binance WebSocket"
- [ ] 定期看到 "Flushed X market data records to database"

验证数据写入：
```sql
-- 连接数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading

-- 查询行情数据
SELECT COUNT(*) FROM market_data;
SELECT symbol, last_price, time FROM market_data ORDER BY time DESC LIMIT 5;
```

预期结果：
- [ ] 行情数据数量持续增长
- [ ] 最新数据时间在最近 1 分钟内

### 3. Gateway 持久化
```bash
# 启动 Gateway 服务
docker compose -f docker/docker-compose.yml up -d gateway-binance

# 查看日志
docker compose -f docker/docker-compose.yml logs gateway-binance | grep -i database
```

预期结果：
- [ ] 日志显示 "Database connection established"
- [ ] 日志显示 "Gateway ready, waiting for orders..."

### 4. 订单和成交记录
发送测试订单后验证：
```sql
-- 查询订单
SELECT * FROM orders ORDER BY time DESC LIMIT 5;

-- 查询成交
SELECT * FROM trades ORDER BY time DESC LIMIT 5;

-- 查询持仓
SELECT * FROM latest_positions;
```

预期结果：
- [ ] 订单记录正确写入
- [ ] 成交记录正确写入
- [ ] 持仓快照正确更新

### 5. 数据完整性
```sql
-- 检查订单和成交的关联
SELECT
    COUNT(DISTINCT o.order_id) as total_orders,
    COUNT(DISTINCT t.order_id) as orders_with_trades
FROM orders o
LEFT JOIN trades t ON o.order_id = t.order_id;

-- 检查孤立成交
SELECT COUNT(*) as orphan_trades
FROM trades t
LEFT JOIN orders o ON t.order_id = o.order_id
WHERE o.order_id IS NULL;
```

预期结果：
- [ ] 所有订单都有对应的成交记录
- [ ] 没有孤立的成交记录

### 6. 性能测试
```bash
cd python
python test_database.py
```

预期结果：
- [ ] 所有测试通过
- [ ] 查询响应时间 < 100ms
- [ ] 聚合查询响应时间 < 500ms

### 7. 集成测试
```bash
cd python
python test_integration.py
```

预期结果：
- [ ] 服务自动启动成功
- [ ] 数据收集正常
- [ ] 所有验证通过
- [ ] 生成完整的测试报告

## 性能指标验证

### 写入性能
```sql
-- 查看每分钟写入量
SELECT
    time_bucket('1 minute', time) AS bucket,
    COUNT(*) as records_per_minute
FROM market_data
WHERE time > NOW() - INTERVAL '10 minutes'
GROUP BY bucket
ORDER BY bucket DESC;
```

预期结果：
- [ ] 每分钟写入量稳定
- [ ] 没有明显的写入延迟

### 查询性能
```sql
-- 测试查询速度
EXPLAIN ANALYZE
SELECT * FROM market_data
WHERE symbol = 'BTCUSDT'
    AND time > NOW() - INTERVAL '1 hour'
ORDER BY time DESC;
```

预期结果：
- [ ] 使用索引扫描
- [ ] 执行时间 < 100ms

### 数据库大小
```sql
SELECT
    hypertable_name,
    pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables;
```

预期结果：
- [ ] 数据库大小合理
- [ ] 压缩策略正常工作

## 错误处理验证

### 1. 数据库连接失败
```bash
# 停止数据库
docker compose -f docker/docker-compose.yml stop timescaledb

# 启动服务（应该继续运行）
docker compose -f docker/docker-compose.yml restart md-binance

# 查看日志
docker compose -f docker/docker-compose.yml logs md-binance | tail -20
```

预期结果：
- [ ] 日志显示数据库连接失败警告
- [ ] 服务继续运行
- [ ] 行情仍然发布到 ZMQ

### 2. 数据库恢复
```bash
# 重启数据库
docker compose -f docker/docker-compose.yml start timescaledb

# 等待几秒后检查
docker compose -f docker/docker-compose.yml logs md-binance | tail -20
```

预期结果：
- [ ] 服务自动重连数据库
- [ ] 数据写入恢复正常

## 文档验证

### 文档完整性
- [ ] `docs/database_persistence.md` 内容完整
- [ ] `docs/database_quickstart.md` 步骤清晰
- [ ] `docs/database_implementation_summary.md` 总结准确

### 文档准确性
- [ ] 所有命令可以正常执行
- [ ] 所有 SQL 查询正确
- [ ] 配置示例有效

## 代码质量验证

### Rust 代码
```bash
# 编译检查
cd rust
cargo check --workspace

# 运行测试
cargo test --workspace

# 代码格式
cargo fmt --check

# Clippy 检查
cargo clippy --workspace
```

预期结果：
- [ ] 编译无错误
- [ ] 所有测试通过
- [ ] 代码格式正确
- [ ] 无 Clippy 警告

### Python 代码
```bash
# 运行测试脚本
cd python
python test_database.py
python test_integration.py
```

预期结果：
- [ ] 脚本运行无错误
- [ ] 所有测试通过

## 部署验证

### Docker 部署
```bash
# 构建镜像
docker compose -f docker/docker-compose.yml build

# 启动所有服务
docker compose -f docker/docker-compose.yml up -d

# 检查服务状态
docker compose -f docker/docker-compose.yml ps
```

预期结果：
- [ ] 所有镜像构建成功
- [ ] 所有服务运行正常
- [ ] 健康检查通过

### 环境变量
验证以下环境变量正确配置：
- [ ] `DB_URI` - 数据库连接字符串
- [ ] `MARKET` - 市场类型
- [ ] `EXCHANGE` - 交易所类型
- [ ] `ZMQ_*_ENDPOINT` - ZMQ 端点

## 最终检查

### 系统整体验证
1. [ ] 所有服务正常启动
2. [ ] 行情数据持续写入数据库
3. [ ] 订单和成交记录正确保存
4. [ ] 持仓快照实时更新
5. [ ] 查询性能满足要求
6. [ ] 错误处理正常工作
7. [ ] 文档完整准确
8. [ ] 测试全部通过

### 生产就绪检查
- [ ] 数据备份策略已制定
- [ ] 监控告警已配置
- [ ] 性能基准已建立
- [ ] 故障恢复流程已测试
- [ ] 运维文档已准备

## 验证签名

验证人：__________________

验证日期：__________________

验证结果：
- [ ] 通过 - 可以部署到生产环境
- [ ] 部分通过 - 需要修复以下问题：
  - ___________________________________
  - ___________________________________
- [ ] 未通过 - 需要重新实现

备注：
_______________________________________________
_______________________________________________
_______________________________________________
