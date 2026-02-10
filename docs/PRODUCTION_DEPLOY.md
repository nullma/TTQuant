# TTQuant 生产环境部署指南（搬瓦工 VPS）

## 前置要求

| 项目 | 要求 |
|------|------|
| VPS | 搬瓦工（或其他海外 VPS），≥ 2 核 CPU，≥ 4GB 内存 |
| 系统 | Ubuntu 20.04+ / Debian 11+ / CentOS 8+ |
| 网络 | 可直连 Binance/OKX（海外节点即可） |

---

## 部署步骤

### 1. SSH 连接到 VPS

```bash
ssh root@<VPS-IP>
```

### 2. 安装 Docker

```bash
# 一键安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动并设置开机自启
systemctl enable --now docker

# 验证
docker --version
docker compose version
```

### 3. 上传项目到 VPS

在 **本地电脑** 执行：

```bash
# 方法 1：scp 上传（推荐）
cd C:\Users\11915\Desktop
scp -r TTQuant root@<VPS-IP>:/root/

# 方法 2：使用 Git
# 先推送到 GitHub，然后在 VPS 上 clone
# ssh root@<VPS-IP>
# git clone https://github.com/你的用户名/TTQuant.git
```

### 4. 配置环境变量

```bash
cd /root/TTQuant

# 从模板创建 .env
cp .env.production .env

# 编辑 .env，替换所有 CHANGE_ME 值
nano .env
```

**必须配置的值：**

```bash
DB_PASSWORD=<你的强密码>        # 数据库密码
GRAFANA_PASSWORD=<你的密码>     # Grafana 面板密码

# 以下根据你要使用的交易所填写：
BINANCE_API_KEY=<你的 API Key>
BINANCE_API_SECRET=<你的 Secret>

OKX_API_KEY=<你的 API Key>
OKX_SECRET_KEY=<你的 Secret Key>
OKX_PASSPHRASE=<你的 Passphrase>
```

> [!CAUTION]
> 如果暂时不想连接真实交易所，可以把 API 密钥留空（系统会自动进入模拟模式）。

### 5. 一键部署

```bash
chmod +x deploy-vps.sh
bash deploy-vps.sh
```

脚本会自动完成：构建镜像 → 启动数据库 → 等待就绪 → 启动所有服务 → 健康检查。

### 6. 验证部署

```bash
# 查看服务状态
docker compose -f docker/docker-compose.prod.yml ps

# 查看行情日志
docker compose -f docker/docker-compose.prod.yml logs -f md-binance

# 查看网关日志
docker compose -f docker/docker-compose.prod.yml logs -f gateway-binance

# 测试健康检查
curl http://127.0.0.1:8080/health   # Binance 行情
curl http://127.0.0.1:8081/health   # Binance 网关
```

---

## 访问面板

| 服务 | URL |
|------|-----|
| Grafana 监控面板 | `http://<VPS-IP>:3000` |
| Prometheus 指标 | `http://127.0.0.1:9090` （仅本机） |

Grafana 默认账号：`admin` / `<你设置的 GRAFANA_PASSWORD>`

---

## 日常运维

### 查看日志

```bash
# 所有服务
docker compose -f docker/docker-compose.prod.yml logs -f

# 指定服务
docker compose -f docker/docker-compose.prod.yml logs -f md-binance
docker compose -f docker/docker-compose.prod.yml logs -f gateway-binance
docker compose -f docker/docker-compose.prod.yml logs -f strategy-engine
```

### 重启服务

```bash
# 重启所有
docker compose -f docker/docker-compose.prod.yml restart

# 重启单个
docker compose -f docker/docker-compose.prod.yml restart md-binance
```

### 停止/启动

```bash
# 停止（保留数据）
docker compose -f docker/docker-compose.prod.yml down

# 启动
docker compose -f docker/docker-compose.prod.yml up -d
```

### 数据库备份

```bash
# 手动备份
bash scripts/backup.sh

# 设置自动备份（每天凌晨 3 点）
(crontab -l 2>/dev/null; echo "0 3 * * * cd /root/TTQuant && bash scripts/backup.sh >> /var/log/ttquant-backup.log 2>&1") | crontab -
```

### 数据库查询

```bash
# 查看行情数据
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading \
  -c "SELECT symbol, last_price, exchange, time FROM market_data ORDER BY time DESC LIMIT 10;"

# 查看订单
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading \
  -c "SELECT * FROM orders ORDER BY time DESC LIMIT 10;"

# 查看策略统计
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading \
  -c "SELECT * FROM strategy_stats;"
```

### 更新部署

```bash
cd /root/TTQuant

# 拉取最新代码（如果用 Git）
git pull

# 重新构建并启动
docker compose -f docker/docker-compose.prod.yml build
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker compose -f docker/docker-compose.prod.yml logs --tail=50 <服务名>

# 查看容器退出原因
docker inspect ttquant-<服务名> --format='{{.State.ExitCode}}: {{.State.Error}}'
```

### 行情无法连接

```bash
# 测试到 Binance 的连接
curl -I https://api.binance.com/api/v3/ping

# 测试到 OKX 的连接
curl -I https://www.okx.com/api/v5/public/time

# 查看 DNS 解析
nslookup stream.binance.com
```

### 数据库连接失败

```bash
# 检查数据库容器
docker exec ttquant-timescaledb pg_isready -U ttquant

# 查看数据库日志
docker compose -f docker/docker-compose.prod.yml logs timescaledb
```

### 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 查看 Docker 占用
docker system df

# 清理无用镜像（注意！不要在有运行服务时执行 prune -a）
docker image prune
docker volume prune
```

---

## 端口一览

| 端口 | 服务 | 协议 | 说明 |
|------|------|------|------|
| 3000 | Grafana | HTTP | 监控面板（外网可访问） |
| 5555 | md-binance | ZMQ PUB | Binance 行情广播 |
| 5556 | gateway-binance | ZMQ PULL | Binance 订单接收 |
| 5557 | gateway-binance | ZMQ PUB | Binance 成交回报 |
| 5558 | md-okx | ZMQ PUB | OKX 行情广播 |
| 5559 | gateway-okx | ZMQ PULL | OKX 订单接收 |
| 5560 | gateway-okx | ZMQ PUB | OKX 成交回报 |
| 5432 | TimescaleDB | TCP | 数据库（仅本机） |
| 8080-8083 | Metrics | HTTP | Prometheus 指标（仅本机） |
| 9090 | Prometheus | HTTP | 指标采集（仅本机） |
| 9093 | AlertManager | HTTP | 告警管理（仅本机） |

---

## 安全建议

1. **防火墙**: 只开放 3000（Grafana）和 5555-5560（ZMQ）端口
2. **SSH Key**: 禁用密码登录，只用 SSH Key
3. **API 权限**: Binance/OKX API 密钥只授予交易权限，禁止提现
4. **IP 白名单**: 在交易所后台设置 API 访问 IP 白名单为 VPS IP
5. **定期备份**: 设置 crontab 每日自动备份数据库

```bash
# 防火墙配置（搬瓦工通常使用 ufw）
sudo ufw allow 22      # SSH
sudo ufw allow 3000    # Grafana
sudo ufw allow 5555:5560/tcp  # ZMQ
sudo ufw enable
```
