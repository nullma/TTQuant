# Docker 使用 Clash 代理配置指南

## 问题

Docker 容器无法通过 Clash Verge TUN 模式访问被墙的网站（如 Binance）。

## 原因

1. Clash TUN 模式只代理宿主机流量
2. Docker 容器使用独立的网络栈
3. 需要配置 Docker 使用 Clash 的 HTTP 代理

## 解决步骤

### 1. 配置 Clash Verge

**开启允许局域网连接**:

1. 打开 Clash Verge
2. 点击 "设置" → "系统设置"
3. 找到 "允许局域网连接" (Allow LAN)
4. **开启此选项** ✅
5. 记下代理端口（通常是 7890）

### 2. 查看 Clash 监听地址

在 Clash Verge 中查看：
- HTTP 代理: `127.0.0.1:7890` 或 `0.0.0.0:7890`
- SOCKS5 代理: `127.0.0.1:7891` 或 `0.0.0.0:7891`

### 3. 测试宿主机代理

```bash
# 测试 HTTP 代理
curl -x http://127.0.0.1:7890 https://www.google.com

# 测试访问 Binance
curl -x http://127.0.0.1:7890 https://api.binance.com/api/v3/ping
```

如果返回正常，说明代理工作正常。

### 4. Docker Compose 配置

已在 `docker-compose.yml` 中添加代理配置：

```yaml
md-binance:
  environment:
    HTTP_PROXY: http://host.docker.internal:7890
    HTTPS_PROXY: http://host.docker.internal:7890
    http_proxy: http://host.docker.internal:7890
    https_proxy: http://host.docker.internal:7890
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

### 5. 重启服务

```bash
cd docker
docker compose restart md-binance
docker compose logs -f md-binance
```

### 6. 验证连接

查看日志，应该看到：
```
[INFO] Starting Binance market data service
[INFO] Connected to Binance WebSocket
[INFO] Subscribed to BTCUSDT@trade
```

## 替代方案

### 方案 A: 使用 Clash 混合模式

如果 TUN 模式不工作，切换到混合模式：

1. Clash Verge → 模式 → 选择 "规则" 或 "全局"
2. 确保 "允许局域网连接" 开启
3. 重启 Docker 服务

### 方案 B: 配置 Docker Desktop 代理

1. 打开 Docker Desktop
2. Settings → Resources → Proxies
3. 启用 "Manual proxy configuration"
4. 设置:
   - Web Server (HTTP): `http://127.0.0.1:7890`
   - Secure Web Server (HTTPS): `http://127.0.0.1:7890`
5. Apply & Restart

### 方案 C: 使用 VPN 或 VPS

如果以上方案都不行：
- 使用全局 VPN（如 WireGuard）
- 或在海外 VPS 上部署

## 测试命令

```bash
# 1. 测试宿主机代理
curl -x http://127.0.0.1:7890 https://api.binance.com/api/v3/ping

# 2. 测试 Docker 容器代理
docker run --rm \
  -e HTTP_PROXY=http://host.docker.internal:7890 \
  -e HTTPS_PROXY=http://host.docker.internal:7890 \
  --add-host host.docker.internal:host-gateway \
  curlimages/curl:latest \
  curl https://api.binance.com/api/v3/ping

# 3. 重启并查看日志
cd docker
docker compose restart md-binance
docker compose logs -f md-binance
```

## 预期结果

成功后应该看到：
```
[INFO] Starting Binance market data service
[INFO] Connected to wss://stream.binance.com:9443/ws/btcusdt@trade
[INFO] Market data: BTCUSDT @ $50123.45
```

## 故障排查

### 问题 1: 仍然 451 错误

**检查**:
- Clash 是否开启"允许局域网连接"
- 代理端口是否正确（7890）
- 防火墙是否阻止

**解决**:
```bash
# 检查 Clash 监听端口
netstat -ano | findstr 7890

# 测试代理
curl -v -x http://127.0.0.1:7890 https://www.google.com
```

### 问题 2: host.docker.internal 无法解析

**解决**:
```yaml
extra_hosts:
  - "host.docker.internal:192.168.1.100"  # 替换为你的实际 IP
```

查看本机 IP:
```bash
ipconfig | findstr IPv4
```

### 问题 3: 代理连接超时

**检查**:
- Clash 是否正在运行
- 代理规则是否正确
- 尝试切换到全局模式

## 当前状态

✅ Docker Compose 已配置代理
⚠️ 需要在 Clash 中开启"允许局域网连接"
🔄 重启服务后验证

---

**下一步**: 开启 Clash 允许局域网连接，然后运行测试命令验证
