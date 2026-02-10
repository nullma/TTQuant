# TTQuant Docker 代理配置完成总结

## ✅ 已完成的配置

### 1. Clash Verge 代理设置
- **端口**: 7897 ✅
- **Allow LAN**: 已启用 ✅
- **本机可访问**: `curl http://127.0.0.1:7897` 返回 400（正常）✅

### 2. Docker Compose 配置
- **代理地址**: `198.18.0.1:7897`（本机实际 IP）✅
- **已更新文件**:
  - `docker/docker-compose.prod.yml` ✅
  - `docker/docker-compose.yml` ✅
- **配置的服务**:
  - `md-binance` (Binance 行情)
  - `md-okx` (OKX 行情)
  - `gateway-binance` (Binance 交易)
  - `gateway-okx` (OKX 交易)

### 3. 环境变量验证
```bash
$ docker exec ttquant-md-binance printenv | grep PROXY
HTTP_PROXY=http://198.18.0.1:7897  ✅
HTTPS_PROXY=http://198.18.0.1:7897 ✅
NO_PROXY=localhost,127.0.0.1,timescaledb ✅
```

---

## ⚠️ 重要发现：币安封锁美国 IP

### 问题
**币安 (Binance) 会封锁美国 IP 地址的连接请求。**

如果你的 Clash 代理使用美国节点，会导致：
- WebSocket 连接被拒绝（403/451 错误）
- REST API 请求失败
- 持续重连循环

### 解决方案

#### 方案 1: 切换 Clash 节点为允许的地区

在 **Clash Verge** 中选择以下地区节点：

| 地区 | 状态 | 推荐度 |
|------|------|--------|
| 🇭🇰 Hong Kong (香港) | ✅ 允许 | ⭐⭐⭐⭐⭐ |
| 🇸🇬 Singapore (新加坡) | ✅ 允许 | ⭐⭐⭐⭐⭐ |
| 🇯🇵 Japan (日本) | ✅ 允许 | ⭐⭐⭐⭐ |
| 🇰🇷 South Korea (韩国) | ✅ 允许 | ⭐⭐⭐⭐ |
| 🇹🇼 Taiwan (台湾) | ✅ 允许 | ⭐⭐⭐⭐ |
| 🇺🇸 United States (美国) | ❌ **封锁** | ❌ |

**操作步骤**:
1. 打开 **Clash Verge**
2. 点击 **代理 (Proxies)** 选项卡
3. 选择一个 **香港** 或 **新加坡** 节点
4. 重启 Docker 服务：
   ```bash
   docker compose -f docker/docker-compose.prod.yml restart md-binance
   ```

---

#### 方案 2: 使用 OKX 代替币安（推荐）

**OKX 对美国 IP 限制更宽松**，即使使用美国节点也可能正常工作。

系统已经内置 OKX 支持，只需：

1. **查看 OKX 日志**：
   ```powershell
   docker logs ttquant-md-okx --tail 30 -f
   ```

2. **如果 OKX 连接成功**，你会看到：
   ```
   ✅ WebSocket connected to wss://ws.okx.com:8443/ws/v5/public
   ✅ Subscribed to BTC-USDT
   ✅ Received tick data
   ```

3. **切换策略引擎使用 OKX**：
   
   编辑 `docker/docker-compose.prod.yml` 中的 `strategy-engine` 服务：
   ```yaml
   strategy-engine:
     environment:
       # 改为使用 OKX 数据源
       ZMQ_MD_ENDPOINTS: tcp://md-okx:5558
       ZMQ_TRADE_ENDPOINT: tcp://gateway-okx:5560
       ZMQ_ORDER_ENDPOINT: tcp://gateway-okx:5559
   ```

---

## 🧪 验证步骤

### 1. 检查当前 Clash 出口 IP

在浏览器中通过代理访问：
```
https://ip-api.com/json
```

或在 PowerShell 中：
```powershell
Invoke-RestMethod -Uri "http://ip-api.com/json" -Proxy "http://127.0.0.1:7897"
```

确认 `country` 字段**不是** `United States`。

---

### 2. 测试币安 API 访问

```powershell
# 使用代理访问币安 API
Invoke-WebRequest -Uri "https://api.binance.com/api/v3/ping" -Proxy "http://127.0.0.1:7897"
```

- **成功** (200): IP 允许访问币安 ✅
- **失败** (403/451): IP 被币安封锁 ❌

---

### 3. 测试 OKX API 访问

```powershell
# OKX 通常更宽松
Invoke-WebRequest -Uri "https://www.okx.com/api/v5/public/time" -Proxy "http://127.0.0.1:7897"
```

---

### 4. 查看服务日志

```powershell
# Binance 行情服务
docker logs ttquant-md-binance --tail 20 -f

# OKX 行情服务
docker logs ttquant-md-okx --tail 20 -f
```

**成功连接标志**：
```
✅ INFO Connected to WebSocket
✅ INFO Subscribed to btcusdt@trade
✅ INFO Received market data
✅ INFO Published tick to ZMQ
```

**失败标志**：
```
❌ ERROR WebSocket close code: 1006
❌ ERROR Connection refused
❌ WARN Reconnecting in 5s
```

---

## 📝 快速命令

### 重启特定服务
```powershell
# 只重启 OKX 服务
docker compose -f docker/docker-compose.prod.yml restart md-okx gateway-okx

# 只重启 Binance 服务
docker compose -f docker/docker-compose.prod.yml restart md-binance gateway-binance

# 重启所有交易服务
docker compose -f docker/docker-compose.prod.yml restart md-binance md-okx gateway-binance gateway-okx
```

### 查看实时日志
```powershell
# OKX 行情实时日志
docker logs ttquant-md-okx -f --tail 50

# Binance 行情实时日志
docker logs ttquant-md-binance -f --tail 50
```

### 检查服务状态
```powershell
docker compose -f docker/docker-compose.prod.yml ps
```

---

## 🎯 推荐下一步

1. **先测试 OKX**：
   ```powershell
   docker logs ttquant-md-okx --tail 30 -f
   ```
   
   如果 OKX 能正常连接，说明代理配置正确，只是币安被封了。

2. **如果 OKX 正常**：
   - 继续使用 OKX（推荐）
   - 或切换 Clash 节点为香港/新加坡后使用币安

3. **如果 OKX 也失败**：
   - 检查 Clash 是否真的在监听 `198.18.0.1:7897`
   - 可能需要配置 Clash 监听 `0.0.0.0:7897`（允许所有 IP 访问）

---

## 📚 相关文档

- **代理配置指南**: [`docs/DOCKER_PROXY.md`](DOCKER_PROXY.md)
- **代理问题排查**: [`docs/PROXY_TROUBLESHOOTING.md`](PROXY_TROUBLESHOOTING.md)
- **Clash 设置指南**: [`docs/CLASH_SETUP_GUIDE.md`](CLASH_SETUP_GUIDE.md)
- **生产环境部署**: [`docs/PRODUCTION_DEPLOY.md`](PRODUCTION_DEPLOY.md)

---

**最后更新**: 2026-02-10 18:48
**状态**: 配置完成，等待验证 OKX 连接
**建议**: 优先测试 OKX，如失败则调整 Clash 节点
