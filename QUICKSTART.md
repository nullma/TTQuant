# 🚀 TTQuant 快速启动指南（本地 + Clash 代理）

## 📋 当前状态

✅ Docker 代理已配置：`198.18.0.1:7897`  
✅ Clash Verge 运行中：端口 7897, Allow LAN 已启用  
⚠️ 等待验证：交易所连接（可能需要切换节点）

---

## 🎯 立即执行（二选一）

### 选项 A：使用 OKX（推荐，对美国 IP 更友好）

```powershell
# 1. 查看 OKX 连接状态
docker logs ttquant-md-okx -f --tail 30

# 期待看到
# ✅ INFO WebSocket connected
# ✅ INFO Subscribed to BTC-USDT
# ✅ INFO Received tick data
```

**如果看到连接成功** → 系统正常，代理配置成功！🎉

**如果仍在重连** → 继续下面的步骤

---

### 选项 B：切换 Clash 节点后使用币安

#### 步骤 1: 切换节点

1. 打开 **Clash Verge**
2. 点击 **代理 (Proxies)** 选项卡
3. 选择节点（**重要**）：
   - ✅ 🇭🇰 Hong Kong (香港)
   - ✅ 🇸🇬 Singapore (新加坡)
   - ✅ 🇯🇵 Japan (日本)
   - ❌ 🇺🇸 **避免美国节点**（币安会封锁）

#### 步骤 2: 重启服务

```powershell
# 重启 Binance 服务
docker compose -f docker/docker-compose.prod.yml restart md-binance gateway-binance
```

#### 步骤 3: 查看日志

```powershell
# 实时查看 Binance 连接状态
docker logs ttquant-md-binance -f --tail 30

# 成功标志
# ✅ INFO WebSocket connected to wss://stream.binance.com:9443/ws
# ✅ INFO Subscribed to btcusdt@trade
```

---

## 🔍 诊断工具

### 快速测试 - 检查代理出口 IP

```powershell
# 在浏览器中访问（使用 Clash 系统代理）
https://ip-api.com/json

# 或在 PowerShell 中
Invoke-RestMethod -Uri "http://ip-api.com/json" -Proxy "http://127.0.0.1:7897"
```

**检查**：
- `country` 是否为 `United States` → **是** = 需要切换节点
- `country` 为香港/新加坡/日本 → **可以** = 可以访问币安

---

### 测试币安 API 可访问性

```powershell
# 通过代理测试
Invoke-WebRequest -Uri "https://api.binance.com/api/v3/ping" -Proxy "http://127.0.0.1:7897"
```

- **返回 200** → IP 可以访问币安 ✅
- **返回 403/451** → IP 被币安封锁（美国 IP）❌

---

### 测试 OKX API 可访问性

```powershell
# OKX 对美国 IP 限制更少
Invoke-WebRequest -Uri "https://www.okx.com/api/v5/public/time" -Proxy "http://127.0.0.1:7897"
```

---

## 📊 查看所有服务状态

```powershell
# 查看所有容器状态
docker compose -f docker/docker-compose.prod.yml ps

# 查看特定服务日志
docker logs ttquant-md-binance --tail 20    # Binance
docker logs ttquant-md-okx --tail 20        # OKX
docker logs ttquant-gateway-binance --tail 20
docker logs ttquant-gateway-okx --tail 20
```

---

## 🛠️ 常用管理命令

### 启动/停止服务

```powershell
# 启动所有服务
docker compose -f docker/docker-compose.prod.yml up -d

# 停止所有服务
docker compose -f docker/docker-compose.prod.yml down

# 重启特定服务
docker compose -f docker/docker-compose.prod.yml restart md-okx
```

### 查看监控

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)

---

## ❓ 常见问题

### Q: 服务一直重连，为什么？

**A**: 最可能的原因：

1. **Clash 使用美国节点** → 币安封锁
   - 解决方案：切换到香港/新加坡节点

2. **容器无法访问代理** → 网络配置问题
   - 测试：`docker exec ttquant-md-okx sh -c "env | grep PROXY"`
   - 应该看到：`HTTP_PROXY=http://198.18.0.1:7897`

3. **Clash 未允许 LAN 连接**
   - 解决方案：Clash → 设置 → Allow LAN ✅

---

### Q: Binance 不行，OKX 可以吗？

**A**: **可以！** OKX 对美国 IP 限制更少，即使 Clash 使用美国节点也可能正常工作。

**推荐**：优先使用 OKX，更稳定。

---

### Q: 如何切换到只用 OKX？

**A**: 编辑 `docker/docker-compose.prod.yml`，修改 `strategy-engine` 部分：

```yaml
strategy-engine:
  environment:
    # 只使用 OKX 数据源
    ZMQ_MD_ENDPOINTS: tcp://md-okx:5558
    ZMQ_TRADE_ENDPOINT: tcp://gateway-okx:5560
    ZMQ_ORDER_ENDPOINT: tcp://gateway-okx:5559
```

然后重启：
```powershell
docker compose -f docker/docker-compose.prod.yml restart strategy-engine
```

---

## 📚 详细文档

- **代理配置总结**: [`PROXY_SETUP_SUMMARY.md`](PROXY_SETUP_SUMMARY.md) ⭐
- **代理问题排查**: [`docs/PROXY_TROUBLESHOOTING.md`](docs/PROXY_TROUBLESHOOTING.md)
- **Clash 详细设置**: [`docs/CLASH_SETUP_GUIDE.md`](docs/CLASH_SETUP_GUIDE.md)
- **系统当前状态**: [`CURRENT_STATUS.md`](CURRENT_STATUS.md)
- **生产环境部署**: [`docs/PRODUCTION_DEPLOY.md`](docs/PRODUCTION_DEPLOY.md)

---

## 🎉 成功标志

当一切正常时，你会在日志中看到：

```
✅ INFO WebSocket connected to wss://...
✅ INFO Subscribed to BTC-USDT@ticker
✅ INFO Received tick: price=92341.50, volume=0.123
✅ INFO Published market data to ZMQ endpoint tcp://*:5558
```

访问 Grafana (http://localhost:3000)，你会看到实时行情数据！

---

**最后更新**: 2026-02-10 18:50  
**支持**: 如有问题，查看详细文档或调整配置  
**推荐**: 优先测试 OKX，更稳定可靠！
