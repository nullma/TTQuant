# TTQuant 数据持久化实现总结

## 实现概述

本次实现为 TTQuant 交易系统添加了完整的数据持久化功能，使用 TimescaleDB 作为时序数据库，实现了行情数据、订单、成交记录和持仓的自动存储。

## 修改的文件

### 1. Rust 核心模块

#### rust/common/src/lib.rs
- 导出 `database` 模块
- 导出 `Database` 和 `MarketDataBatchWriter` 类

#### rust/common/src/database.rs
- **已存在**，进行了优化：
  - 将 `MarketDataBatchWriter` 改为线程安全的 `Clone` 实现
  - 使用 `Arc<Mutex<>>` 包装内部状态
  - 支持多线程环境下的并发访问

#### rust/common/Cargo.toml
- 添加 `sqlx` 依赖（已在 workspace 中定义）

### 2. Market Data 模块

#### rust/market-data/src/binance.rs
**主要修改**：
- 添加数据库连接初始化逻辑
- 创建 `MarketDataBatchWriter` 实例
- 在 `handle_message` 中添加数据库写入逻辑
- 添加定时刷新机制（每秒检查一次）
- 在连接关闭时刷新剩余数据

**关键特性**：
- 批量写入：每 100 条或每 1 秒刷新
- 异步写入：不阻塞行情发布
- 错误处理：写入失败时记录警告但不影响行情流
- 优雅关闭：断开连接前刷新所有缓冲数据

### 3. Gateway 模块

#### rust/gateway/src/order_manager.rs
**主要修改**：
- 添加 `db: Option<Database>` 字段
- 添加 `with_database()` 方法用于设置数据库连接
- 在 `run()` 方法中添加订单写入逻辑
- 在 `run()` 方法中添加成交记录写入逻辑
- 在成交后写入持仓快照

**写入时机**：
- 订单接收时：立即写入 orders 表
- 成交完成时：写入 trades 表
- 持仓变化时：写入 positions 表

#### rust/gateway/src/risk.rs
**主要修改**：
- 添加 `get_position_details()` 方法
- 添加 `PositionDetails` 结构体
- 返回持仓数量和平均价格（平均价格待实现）

#### rust/gateway/src/main.rs
**主要修改**：
- 添加 `DB_URI` 环境变量读取
- 初始化数据库连接
- 使用 `with_database()` 方法配置 OrderManager
- 添加数据库连接失败的警告处理

### 4. 测试和文档

#### python/test_database.py
**新文件** - 数据库功能测试脚本

功能：
- 连接数据库验证
- 行情数据查询和统计
- 订单数据查询和统计
- 成交数据查询和统计
- 持仓数据查询
- 数据完整性检查
- 性能测试（查询速度、聚合查询）

#### python/test_integration.py
**新文件** - 集成测试脚本

功能：
- 自动启动服务
- 等待数据收集
- 验证数据写入
- 生成测试报告
- 可选的服务清理

#### docs/database_persistence.md
**新文件** - 完整的数据持久化文档

内容：
- 架构设计说明
- 数据库表结构详解
- 使用方法和配置
- 性能优化策略
- 查询示例
- 监控和维护指南
- 故障处理方案

#### docs/database_quickstart.md
**新文件** - 快速开始指南

内容：
- 分步骤的启动指南
- 验证方法
- 常用查询示例
- 故障排查
- 命令速查表

## 技术特点

### 1. 性能优化

**批量写入**：
- 行情数据使用批量写入，减少数据库连接开销
- 默认配置：每 100 条或每 1 秒刷新一次
- 可根据实际情况调整参数

**连接池**：
- 使用 sqlx 的连接池管理
- 最大连接数：10
- 最小连接数：2
- 连接超时：5 秒

**异步操作**：
- 所有数据库操作都是异步的
- 不阻塞主业务流程
- 使用 tokio 运行时

### 2. 可靠性保证

**错误处理**：
- 数据库连接失败时记录警告但不影响系统运行
- 写入失败时保留缓冲区数据，支持重试
- 优雅关闭时刷新所有缓冲数据

**数据完整性**：
- 使用事务保证批量写入的原子性
- 主键约束防止重复数据
- 外键关系保证数据一致性

**容错设计**：
- 数据库可选配置（未配置时系统仍可正常运行）
- 写入失败不影响行情发布和订单处理
- 自动重连机制（通过 sqlx 连接池）

### 3. 可扩展性

**模块化设计**：
- 数据库模块独立于业务逻辑
- 易于添加新的数据表和写入逻辑
- 支持多种数据库后端（通过 sqlx）

**配置灵活**：
- 通过环境变量配置数据库连接
- 批量写入参数可调整
- 支持多个数据库实例

## 数据流程

### 行情数据流程
```
Binance WebSocket
    ↓
解析 JSON
    ↓
构建 MarketData
    ↓
发布到 ZMQ ────────────→ 策略接收
    ↓
添加到批量写入器
    ↓
(每100条或每1秒)
    ↓
批量写入数据库
    ↓
TimescaleDB (market_data 表)
```

### 订单和成交流程
```
策略发送订单
    ↓
Gateway 接收
    ↓
写入 orders 表 ←─────── 立即写入
    ↓
风控检查
    ↓
提交交易所
    ↓
生成成交记录
    ↓
写入 trades 表 ←─────── 立即写入
    ↓
更新持仓
    ↓
写入 positions 表 ←──── 立即写入
    ↓
发布到 ZMQ ────────────→ 策略接收
```

## 环境变量配置

### Market Data 服务
```bash
DB_URI=postgresql://ttquant:changeme@localhost:5432/ttquant_trading
MARKET=binance
ZMQ_PUB_ENDPOINT=tcp://*:5555
```

### Gateway 服务
```bash
DB_URI=postgresql://ttquant:changeme@localhost:5432/ttquant_trading
EXCHANGE=binance
ZMQ_PULL_ENDPOINT=tcp://*:5556
ZMQ_PUB_ENDPOINT=tcp://*:5557
```

## Docker Compose 集成

docker-compose.yml 已经配置好：
- TimescaleDB 服务（端口 5432）
- 自动执行 init.sql 初始化脚本
- Market Data 和 Gateway 服务已配置 DB_URI
- 健康检查确保数据库就绪后再启动服务

## 测试方法

### 1. 单元测试
```bash
cd rust
cargo test --workspace
```

### 2. 数据库功能测试
```bash
cd python
python test_database.py
```

### 3. 集成测试
```bash
cd python
python test_integration.py
```

### 4. 手动测试
```bash
# 启动服务
docker compose -f docker/docker-compose.yml up -d

# 查看日志
docker compose -f docker/docker-compose.yml logs -f

# 连接数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading

# 查询数据
SELECT COUNT(*) FROM market_data;
```

## 性能指标

### 预期性能
- 行情写入延迟：< 1 秒（批量写入）
- 订单写入延迟：< 10 毫秒（单条写入）
- 查询响应时间：< 100 毫秒（带索引）
- 数据库压缩率：> 90%（7天后）

### 资源占用
- 数据库内存：建议 2GB+
- 磁盘空间：约 1GB/天（未压缩）
- CPU：< 5%（正常负载）

## 已知限制和待改进

### 当前限制
1. 平均成本跟踪未实现（positions 表的 avg_price 为 0）
2. 未实现盈亏计算（unrealized_pnl 为 0）
3. 批量写入参数硬编码（需要配置文件支持）
4. 没有数据备份机制

### 改进计划
1. 在 RiskManager 中跟踪持仓平均成本
2. 结合最新行情计算实时盈亏
3. 添加配置文件支持批量写入参数
4. 实现定期数据备份
5. 添加数据归档功能
6. 支持多数据库实例的负载均衡

## 相关资源

### 文档
- `docs/database_persistence.md` - 完整文档
- `docs/database_quickstart.md` - 快速开始
- `sql/init.sql` - 数据库初始化脚本

### 代码
- `rust/common/src/database.rs` - 数据库核心模块
- `rust/market-data/src/binance.rs` - 行情数据持久化
- `rust/gateway/src/order_manager.rs` - 订单成交持久化

### 测试
- `python/test_database.py` - 功能测试
- `python/test_integration.py` - 集成测试

## 总结

本次实现为 TTQuant 添加了完整的数据持久化功能，具有以下特点：

✓ **高性能**：批量写入、连接池、异步操作
✓ **高可靠**：错误处理、事务保证、优雅关闭
✓ **易使用**：环境变量配置、Docker 集成、详细文档
✓ **可扩展**：模块化设计、灵活配置、易于维护

系统已经可以投入使用，建议先在测试环境验证后再部署到生产环境。
