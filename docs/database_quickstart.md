# TTQuant 数据持久化 - 快速开始指南

## 前置条件

- Docker 和 Docker Compose 已安装
- Python 3.8+ (用于测试脚本)
- psycopg2 Python 包

## 步骤 1: 安装 Python 依赖

```bash
cd /c/Users/11915/Desktop/TTQuant/python
pip install psycopg2-binary
```

## 步骤 2: 启动 TimescaleDB

```bash
cd /c/Users/11915/Desktop/TTQuant
docker compose -f docker/docker-compose.yml up -d timescaledb
```

等待数据库启动（约 10-15 秒），然后检查状态：

```bash
docker compose -f docker/docker-compose.yml ps timescaledb
```

## 步骤 3: 验证数据库初始化

数据库会自动执行 `sql/init.sql` 脚本。验证表是否创建成功：

```bash
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "\dt"
```

应该看到以下表：
- market_data
- orders
- trades
- positions
- account_balance
- metrics
- klines

## 步骤 4: 启动 Market Data 服务（带数据库持久化）

```bash
cd /c/Users/11915/Desktop/TTQuant
docker compose -f docker/docker-compose.yml up -d md-binance
```

查看日志，确认数据库连接成功：

```bash
docker compose -f docker/docker-compose.yml logs -f md-binance
```

应该看到类似的日志：
```
INFO  Starting Binance market data service
INFO  Database connection established
INFO  Connected to Binance WebSocket
```

## 步骤 5: 启动 Gateway 服务（带数据库持久化）

```bash
docker compose -f docker/docker-compose.yml up -d gateway-binance
```

查看日志：

```bash
docker compose -f docker/docker-compose.yml logs -f gateway-binance
```

应该看到：
```
INFO  Starting Gateway service
INFO  Database connection established
INFO  Gateway ready, waiting for orders...
```

## 步骤 6: 运行数据库测试

等待几分钟让系统收集一些数据，然后运行测试脚本：

```bash
cd /c/Users/11915/Desktop/TTQuant/python
python test_database.py
```

测试脚本会：
1. 连接数据库
2. 查询行情数据
3. 查询订单和成交记录
4. 查询持仓快照
5. 执行性能测试
6. 检查数据完整性

## 步骤 7: 手动查询数据

### 连接数据库

```bash
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading
```

### 查询最新行情

```sql
SELECT symbol, last_price, volume, exchange, time
FROM market_data
ORDER BY time DESC
LIMIT 10;
```

### 查询行情统计

```sql
SELECT
    symbol,
    COUNT(*) as tick_count,
    MIN(time) as first_time,
    MAX(time) as last_time
FROM market_data
GROUP BY symbol;
```

### 查询订单

```sql
SELECT order_id, strategy_id, symbol, side, price, volume, time
FROM orders
ORDER BY time DESC
LIMIT 10;
```

### 查询成交

```sql
SELECT trade_id, order_id, symbol, side, filled_price, filled_volume, status, time
FROM trades
ORDER BY time DESC
LIMIT 10;
```

### 查询当前持仓

```sql
SELECT * FROM latest_positions;
```

### 计算 1 分钟 K 线

```sql
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    first(last_price, time) AS open,
    max(last_price) AS high,
    min(last_price) AS low,
    last(last_price, time) AS close,
    sum(volume) AS volume
FROM market_data
WHERE symbol = 'BTCUSDT'
    AND time > NOW() - INTERVAL '1 hour'
GROUP BY bucket, symbol
ORDER BY bucket DESC;
```

## 故障排查

### 问题 1: 数据库连接失败

**症状**: 日志显示 "Failed to connect to database"

**解决方案**:
1. 检查 TimescaleDB 是否运行：
   ```bash
   docker ps | grep timescaledb
   ```

2. 检查数据库健康状态：
   ```bash
   docker compose -f docker/docker-compose.yml ps timescaledb
   ```

3. 查看数据库日志：
   ```bash
   docker compose -f docker/docker-compose.yml logs timescaledb
   ```

### 问题 2: 没有数据写入

**症状**: 查询返回空结果

**解决方案**:
1. 检查 Market Data 服务是否正常运行
2. 查看日志中是否有 "Flushed X market data records" 的消息
3. 检查 WebSocket 连接是否成功

### 问题 3: 测试脚本连接失败

**症状**: `psycopg2.OperationalError: could not connect to server`

**解决方案**:
1. 确保 TimescaleDB 端口已映射：
   ```bash
   docker port ttquant-timescaledb
   ```
   应该显示 `5432/tcp -> 0.0.0.0:5432`

2. 检查防火墙设置

3. 尝试使用 Docker 内部网络：
   ```bash
   docker run --rm --network ttquant-network postgres:16 \
     psql -h timescaledb -U ttquant -d ttquant_trading -c "SELECT 1"
   ```

## 性能监控

### 查看数据库大小

```sql
SELECT
    hypertable_name,
    pg_size_pretty(hypertable_size(format('%I.%I', hypertable_schema, hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables;
```

### 查看写入速率

```sql
SELECT
    time_bucket('1 minute', time) AS bucket,
    COUNT(*) as records_per_minute
FROM market_data
WHERE time > NOW() - INTERVAL '10 minutes'
GROUP BY bucket
ORDER BY bucket DESC;
```

### 查看压缩状态

```sql
SELECT
    chunk_name,
    compression_status,
    before_compression_total_bytes,
    after_compression_total_bytes,
    pg_size_pretty(before_compression_total_bytes) as before_size,
    pg_size_pretty(after_compression_total_bytes) as after_size
FROM timescaledb_information.compressed_chunk_stats
ORDER BY before_compression_total_bytes DESC
LIMIT 10;
```

## 停止服务

停止所有服务：

```bash
cd /c/Users/11915/Desktop/TTQuant
docker compose -f docker/docker-compose.yml down
```

停止但保留数据：

```bash
docker compose -f docker/docker-compose.yml stop
```

## 清理数据

**警告**: 这将删除所有数据！

```bash
docker compose -f docker/docker-compose.yml down -v
```

## 下一步

1. 查看完整文档：`docs/database_persistence.md`
2. 运行策略测试并观察订单和成交记录
3. 配置 Grafana 仪表板进行可视化监控
4. 设置数据备份策略

## 相关命令速查

```bash
# 启动数据库
docker compose -f docker/docker-compose.yml up -d timescaledb

# 启动所有服务
docker compose -f docker/docker-compose.yml up -d

# 查看服务状态
docker compose -f docker/docker-compose.yml ps

# 查看日志
docker compose -f docker/docker-compose.yml logs -f

# 连接数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading

# 运行测试
cd python && python test_database.py

# 停止服务
docker compose -f docker/docker-compose.yml down
```
