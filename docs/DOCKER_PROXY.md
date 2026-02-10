# Docker 代理配置说明

## 已完成配置 ✅

系统已配置为使用 **Clash Verge** 代理访问交易所。

### 配置详情

已为以下服务添加代理环境变量：
- `md-binance` (Binance 行情服务)
- `md-okx` (OKX 行情服务)
- `gateway-binance` (Binance 交易网关)
- `gateway-okx` (OKX 交易网关)

### 代理配置参数

```yaml
HTTP_PROXY: http://host.docker.internal:7890
HTTPS_PROXY: http://host.docker.internal:7890
NO_PROXY: localhost,127.0.0.1,timescaledb
```

**说明**：
- `host.docker.internal` 会自动解析为宿主机 IP
- `7890` 是 Clash 默认监听端口
- `NO_PROXY` 排除内部服务，避免不必要的代理

---

## 使用前检查清单

### 1. 确认 Clash Verge 配置

打开 **Clash Verge** → **设置** → **系统代理**，确认：

```
✅ 允许来自局域网的连接（Allow LAN）
✅ HTTP 端口: 7890
✅ SOCKS 端口: 7891（可选）
```

### 2. 验证代理端口

在 PowerShell 中运行：

```powershell
# 测试代理是否可访问
curl http://127.0.0.1:7890
```

如果返回类似 `Bad Request` 或 Clash 错误信息，说明代理**正常运行**。

### 3. 启动服务

```powershell
# 重启容器以应用代理配置
make prod-down
make prod-up

# 查看日志，确认是否连接成功
make prod-logs
```

---

## 常见问题排查

### ❌ 问题 1: 容器仍然无法连接

**可能原因**：Clash 端口不是 7890

**解决方案**：
1. 打开 Clash Verge，查看实际端口
2. 修改 `docker-compose.prod.yml` 中的端口号
3. 重启容器

---

### ❌ 问题 2: `host.docker.internal` 解析失败

**可能原因**：旧版 Docker Desktop

**解决方案**：
在 `docker-compose.prod.yml` 中添加 `extra_hosts`:

```yaml
md-binance:
  # ... 其他配置
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

---

### ❌ 问题 3: WebSocket 连接断开

**可能原因**：代理不支持 WebSocket

**解决方案**：
在 Clash Verge 中启用 **TUN 模式**（设置 → TUN 模式）

---

## 验证连接成功

### 查看行情服务日志

```powershell
# Binance
docker logs ttquant-md-binance --tail 50

# OKX
docker logs ttquant-md-okx --tail 50
```

**成功标志**：
```
✅ WebSocket connected to wss://stream.binance.com:9443/ws
✅ Received market data for BTCUSDT
✅ Published tick to ZMQ
```

### 检查 Prometheus 指标

访问：http://localhost:8080/metrics（Binance）

查找：
```
# 成功接收数据
websocket_messages_received_total > 0
market_data_tick_count > 0
```

---

## 生产环境部署注意

⚠️ **VPS 上无需配置代理**

海外 VPS 可直接访问交易所，部署时需要：

1. 删除或注释掉 `HTTP_PROXY` 相关环境变量
2. 或者使用独立的 `docker-compose.prod.vps.yml`

示例：
```yaml
# VPS 配置（无需代理）
environment:
  MARKET: binance
  ZMQ_PUB_ENDPOINT: tcp://*:5555
  # HTTP_PROXY: http://host.docker.internal:7890  # 注释掉
```

---

## Rust 代码中的代理支持

如果需要在 Rust 代码中手动设置代理（目前由环境变量自动处理）：

```rust
// reqwest 自动读取 HTTP_PROXY 环境变量
let client = reqwest::Client::builder()
    .build()?;

// 或手动指定
use reqwest::Proxy;
let client = reqwest::Client::builder()
    .proxy(Proxy::all("http://127.0.0.1:7890")?)
    .build()?;
```

---

## 总结

✅ **当前本地测试：使用 Clash 代理**
- 已配置 `HTTP_PROXY` 环境变量
- 容器通过 `host.docker.internal:7890` 访问

✅ **VPS 生产部署：无需代理**
- 注释掉代理配置
- 或使用独立配置文件

---

**最后更新**: 2026-02-10
**配置版本**: v1.0
