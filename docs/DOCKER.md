# Docker 部署和测试指南

## 🐳 前置要求

- Docker 20.10+
- Docker Compose 2.0+

检查安装：
```bash
docker --version
docker compose version
```

## 🚀 快速启动

### 方法 1: 使用 Makefile（推荐）

```bash
# 查看所有命令
make help

# 构建镜像
make build

# 启动服务
make up

# 查看日志
make logs

# 查看行情日志
make logs-md

# 查看测试客户端
make logs-test

# 停止服务
make down
```

### 方法 2: 使用部署脚本

```bash
chmod +x deploy.sh
./deploy.sh
```

### 方法 3: 手动 Docker Compose

```bash
# 构建
docker compose -f docker/docker-compose.yml build

# 启动
docker compose -f docker/docker-compose.yml up -d

# 查看状态
docker compose -f docker/docker-compose.yml ps

# 查看日志
docker compose -f docker/docker-compose.yml logs -f
```

## 📊 验证部署

### 1. 检查服务状态

```bash
docker compose -f docker/docker-compose.yml ps
```

应该看到：
```
NAME                      STATUS
ttquant-timescaledb       Up (healthy)
ttquant-md-binance        Up
ttquant-test-client       Up
```

### 2. 查看行情数据

```bash
# 查看 Binance 行情日志
docker compose -f docker/docker-compose.yml logs -f md-binance
```

应该看到：
```
INFO Starting market data service: binance
INFO Connected to Binance WebSocket
INFO Sent subscription message
```

### 3. 查看测试客户端

```bash
docker compose -f docker/docker-compose.yml logs -f test-client
```

应该看到实时行情：
```
Connecting to tcp://md-binance:5555...
Listening for market data...
[    10] md.BTCUSDT.binance          | Rate: 5.2 msg/s
[    20] md.ETHUSDT.binance          | Rate: 6.1 msg/s
```

### 4. 连接数据库

```bash
# 进入数据库容器
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading

# 查询行情数据
SELECT symbol, last_price, time
FROM market_data
ORDER BY time DESC
LIMIT 10;

# 退出
\q
```

## 🔧 开发模式

### 实时查看日志

```bash
# 所有服务
make logs

# 只看行情模块
make logs-md

# 只看测试客户端
make logs-test
```

### 重启服务

```bash
# 重启所有服务
make restart

# 重启单个服务
docker compose -f docker/docker-compose.yml restart md-binance
```

### 进入容器调试

```bash
# 进入行情模块容器
docker exec -it ttquant-md-binance /bin/bash

# 进入测试客户端容器
docker exec -it ttquant-test-client /bin/bash
```

### 查看资源使用

```bash
docker stats
```

## 🐛 故障排查

### 问题 1: 容器无法启动

```bash
# 查看详细日志
docker compose -f docker/docker-compose.yml logs md-binance

# 检查容器状态
docker compose -f docker/docker-compose.yml ps
```

### 问题 2: 数据库连接失败

```bash
# 检查数据库是否健康
docker compose -f docker/docker-compose.yml ps timescaledb

# 查看数据库日志
docker compose -f docker/docker-compose.yml logs timescaledb

# 手动测试连接
docker exec -it ttquant-timescaledb pg_isready -U ttquant
```

### 问题 3: 行情数据收不到

```bash
# 检查网络连接
docker network inspect ttquant-network

# 检查端口映射
docker port ttquant-md-binance

# 测试 ZeroMQ 连接
docker run --rm --network ttquant-network python:3.11-slim \
  bash -c "pip install pyzmq && python -c 'import zmq; c=zmq.Context(); s=c.socket(zmq.SUB); s.connect(\"tcp://md-binance:5555\"); s.subscribe(b\"\"); print(s.recv_multipart())'"
```

### 问题 4: 构建失败

```bash
# 清理缓存重新构建
docker compose -f docker/docker-compose.yml build --no-cache

# 查看构建日志
docker compose -f docker/docker-compose.yml build --progress=plain
```

## 🧹 清理

### 停止服务（保留数据）

```bash
make down
# 或
docker compose -f docker/docker-compose.yml down
```

### 完全清理（删除所有数据）

```bash
make clean
# 或
docker compose -f docker/docker-compose.yml down -v
```

### 清理未使用的镜像

```bash
docker system prune -a
```

## 📈 性能测试

### 测试行情吞吐量

```bash
# 运行测试客户端 60 秒
docker compose -f docker/docker-compose.yml run --rm test-client timeout 60 python test_market_data.py
```

### 监控资源使用

```bash
# 实时监控
docker stats ttquant-md-binance ttquant-test-client

# 查看容器资源限制
docker inspect ttquant-md-binance | grep -A 10 "Memory"
```

## 🔐 生产环境配置

### 1. 创建 .env 文件

```bash
cp .env.example .env
# 编辑 .env 填入真实配置
```

### 2. 配置资源限制

在 docker-compose.yml 中添加：
```yaml
services:
  md-binance:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '1'
          memory: 512M
```

### 3. 启用持久化日志

```bash
# 配置日志驱动
# 已在 docker-compose.yml 中配置
```

## 📚 下一步

1. **添加更多市场** - 实现 OKX、Tushare 模块
2. **实现 Gateway** - 交易柜台模块
3. **实现策略引擎** - Python 策略开发
4. **添加监控** - Prometheus + Grafana

---

**遇到问题？** 查看 [QUICKSTART.md](QUICKSTART.md) 或提交 Issue
