# ✅ OKX 模式 - 配置完成总结

## 🎯 当前状态

**选择**: 使用 OKX（对美国 IP 限制更少）  
**代理状态**: ✅ 可以访问 OKX API (HTTP 200)  
**服务状态**: ✅ md-okx 和 gateway-okx 已重启  

---

## ✅ 为什么选择 OKX？

1. **对美国 IP 更友好** - 即使 Clash 使用美国节点也可能正常工作
2. **API 稳定性好** - OKX 的 WebSocket 连接更稳定
3. **手续费合理** - 交易成本与币安类似
4. **支持合约** - 现货和合约都支持

---

## 📊 OKX 服务检查

### 查看服务状态
```powershell
# 查看容器是否运行
docker ps --filter "name=okx"

# 查看 OKX 行情服务日志
docker logs ttquant-md-okx -f --tail 30
```

**成功标志**：
```
✅ INFO Connected to OKX WebSocket
✅ INFO Subscribed to BTC-USDT
✅ INFO Received market data
✅ INFO Published to ZMQ
```

**如果还在重连**：
```
⚠️ WARN Reconnecting in 5s...
```
- 原因：代理配置可能还有问题
- 解决：继续下面的步骤

---

## 🔧 配置策略引擎使用 OKX

如果 OKX 连接成功，需要更新策略引擎使用 OKX 数据源：

### 方法 1: 手动编辑配置文件

编辑 `docker/docker-compose.prod.yml`，找到 `strategy-engine` 部分：

```yaml
strategy-engine:
  environment:
    # 修改为使用 OKX
    ZMQ_MD_ENDPOINTS: tcp://md-okx:5558
    ZMQ_TRADE_ENDPOINT: tcp://gateway-okx:5560
    ZMQ_ORDER_ENDPOINT: tcp://gateway-okx:5559
```

### 方法 2: 使用 SED 自动替换（Linux/Mac）

```bash
sed -i 's/md-binance:5555/md-okx:5558/g' docker/docker-compose.prod.yml
sed -i 's/gateway-binance:5557/gateway-okx:5560/g' docker/docker-compose.prod.yml
sed -i 's/gateway-binance:5556/gateway-okx:5559/g' docker/docker-compose.prod.yml
```

### 重启策略引擎

```powershell
docker compose -f docker/docker-compose.prod.yml restart strategy-engine
```

---

## 🧪 测试 OKX 连接

### 测试 1: API 可访问性
```powershell
Invoke-WebRequest -Uri "https://www.okx.com/api/v5/public/time" `
                  -Proxy "http://127.0.0.1:7897" `
                  -UseBasicParsing
```
预期：返回 200 ✅

### 测试 2: 容器代理配置
```powershell
docker exec ttquant-md-okx printenv | findstr PROXY
```
预期：
```
HTTP_PROXY=http://198.18.0.1:7897
HTTPS_PROXY=http://198.18.0.1:7897
```

### 测试 3: 查看实时日志
```powershell
docker logs ttquant-md-okx -f
```

按 `Ctrl+C` 停止查看。

---

## 📈 监控 OKX 数据

### Prometheus 指标

访问：http://localhost:8082/metrics（OKX 行情服务）

关键指标：
- `websocket_connected` = 1 → 已连接
- `websocket_messages_received_total` > 0 → 正在接收数据
- `market_data_tick_count` > 0 → 行情数据正常

### Grafana 面板

1. 访问：http://localhost:3000
2. 登录：admin / admin123
3. 查看行情数据仪表板

---

## ❓ 故障排查

### 问题 1: OKX 一直重连

**可能原因**：
1. 代理配置不对（端口不是 7897）
2. Clash 没有运行
3. 容器无法访问 `198.18.0.1:7897`

**解决方案**：
```powershell
# 1. 检查代理是否可访问
curl http://127.0.0.1:7897

# 2. 检查容器代理配置
docker exec ttquant-md-okx printenv | findstr PROXY

# 3. 重新运行配置脚本
.\update-proxy-ip.ps1
docker compose -f docker/docker-compose.prod.yml restart md-okx
```

### 问题 2: 代理端口不是 7897

**解决方案**：
1. 打开 Clash Verge 查看实际端口
2. 编辑 `update-proxy-port.ps1` 修改端口号
3. 重新运行脚本

### 问题 3: 想同时使用币安和 OKX

**解决方案**：

策略引擎可以同时订阅两个数据源：

```yaml
strategy-engine:
  environment:
    # 同时使用币安和 OKX
    ZMQ_MD_ENDPOINTS: tcp://md-binance:5555,tcp://md-okx:5558
```

---

## 🚀 下一步

### 选项 A: 本地测试成功

如果 OKX 连接成功，你可以：

1. **开发策略** - 在 `python/strategy/` 编写交易策略
2. **回测** - 使用历史数据测试策略
3. **监控** - 通过 Grafana 观察实时数据

### 选项 B: 部署到香港 VPS

本地测试通过后，强烈建议部署到海外 VPS：

1. **无需代理** - 直接连接交易所
2. **更稳定** - 7x24 不间断运行
3. **延迟更低** - 更适合高频策略

参考：[`docs/VPS_DEPLOYMENT_HK.md`](docs/VPS_DEPLOYMENT_HK.md)

---

## 📚 相关文档

- **快速启动**: [`QUICKSTART.md`](../QUICKSTART.md)
- **OKX 快速开始**: [`QUICKSTART_OKX.md`](../QUICKSTART_OKX.md)  
- **系统状态**: [`CURRENT_STATUS.md`](../CURRENT_STATUS.md)
- **VPS 部署**: [`docs/VPS_DEPLOYMENT_HK.md`](docs/VPS_DEPLOYMENT_HK.md)

---

## 🎉 成功标志

当一切正常时：

```bash
$ docker logs ttquant-md-okx --tail 10

✅ INFO WebSocket connected to wss://ws.okx.com:8443/ws/v5/public
✅ INFO Subscribed to BTC-USDT ticker
✅ INFO Received tick: price=92341.50
✅ INFO Published market data to ZMQ
```

访问 Grafana (http://localhost:3000)，你会看到 OKX 的实时行情！

---

**最后更新**: 2026-02-10 19:12  
**模式**: OKX 优先  
**状态**: 配置完成，等待验证连接  
**推荐**: 查看实时日志确认连接状态
