# Clash Verge 代理配置指南

## ⚠️ 当前问题

容器环境变量已正确配置代理，但无法连接到 `host.docker.internal:7890`。

```bash
# 测试结果
$ docker exec ttquant-md-binance printenv | findstr PROXY
HTTP_PROXY=http://host.docker.internal:7890  ✅ 配置正确
HTTPS_PROXY=http://host.docker.internal:7890 ✅ 配置正确

$ docker exec ttquant-md-binance curl -I http://host.docker.internal:7890
curl: (7) Failed to connect to host.docker.internal  ❌ 无法连接
```

---

## 🔧 解决方案步骤

### 步骤 1: 配置 Clash Verge 允许局域网连接

1. **打开 Clash Verge**
2. 进入 **设置 (Settings)** → **系统代理 (System Proxy)**
3. **启用以下选项**：
   ```
   ✅ 允许来自局域网的连接 (Allow connections from LAN)
   ✅ 系统代理 (System Proxy) - 可选
   ```

4. **检查监听地址**：
   - 应该显示为 `0.0.0.0:7890` 或 `127.0.0.1:7890`
   - 端口号默认为 `7890`

5. **重启 Clash Verge** 以确保配置生效

---

### 步骤 2: 验证 Clash 端口可访问

在 **PowerShell** 中测试：

```powershell
# 测试本地可访问
curl http://127.0.0.1:7890

# 预期输出：Clash 错误页面 (证明服务运行中)
# Bad Request / Invalid Request / 等
```

如果无法连接，检查：
- Clash Verge 是否正在运行
- 端口是否被防火墙阻止
- 端口号是否正确（可能不是 7890）

---

### 步骤 3: 修改 Docker Desktop 设置（关键）

#### 方法 A: Docker Desktop 全局代理设置（推荐）

1. **打开 Docker Desktop**
2. 进入 **Settings** → **Resources** → **Proxies**
3. **启用 Manual proxy configuration**
4. 填入：
   ```
   Web Server (HTTP): http://127.0.0.1:7890
   Secure Web Server (HTTPS): http://127.0.0.1:7890
   Bypass for these hosts: localhost,127.0.0.1
   ```
5. **点击 Apply & Restart**

#### 方法 B: 修改 docker-compose 使用宿主机 IP

如果方法 A 不生效，需要使用宿主机实际 IP：

**1. 获取本机 IP**：
```powershell
# 获取本机局域网 IP
ipconfig | findstr "IPv4"
# 例如: 192.168.1.100
```

**2. 修改 `docker-compose.prod.yml`**：
```yaml
# 将所有 host.docker.internal:7890 替换为实际 IP
HTTP_PROXY: http://192.168.1.100:7890
HTTPS_PROXY: http://192.168.1.100:7890
```

**3. 重启服务**：
```powershell
docker compose -f docker/docker-compose.prod.yml down
docker compose -f docker/docker-compose.prod.yml up -d
```

---

### 步骤 4: 测试代理连接

```powershell
# 测试容器能否访问代理
docker exec ttquant-md-binance sh -c "curl -x http://host.docker.internal:7890 -I https://api.binance.com/api/v3/ping"

# 或使用实际 IP
docker exec ttquant-md-binance sh -c "curl -x http://192.168.1.100:7890 -I https://api.binance.com/api/v3/ping"
```

预期输出：
```
HTTP/2 200
...
```

---

### 步骤 5: 检查服务日志

```powershell
# 查看 Binance 行情服务
docker logs ttquant-md-binance --tail 50

# 成功标志
✅ WebSocket connected to wss://stream.binance.com:9443/ws
✅ Subscribed to btcusdt@trade
✅ Published market data to ZMQ

# 失败标志
❌ Failed to connect: Connection refused
❌ WebSocket error: Timeout
```

---

## 🔍 常见问题排查

### 问题 1: `host.docker.internal` 无法解析

**症状**：
```
curl: (6) Could not resolve host: host.docker.internal
```

**解决方案**：
在 `docker-compose.prod.yml` 中添加 `extra_hosts`：

```yaml
md-binance:
  # ... 其他配置
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

---

### 问题 2: 防火墙阻止连接

**症状**：
```
curl: (7) Failed to connect to host.docker.internal port 7890: Connection refused
```

**解决方案**：
在 Windows 防火墙中允许 Clash Verge：

1. 打开 **Windows Defender 防火墙**
2. **允许应用通过防火墙**
3. 找到 **Clash Verge** 并勾选 **专用** 和 **公用**

---

### 问题 3: Clash 未监听 0.0.0.0

**症状**：
本机 `curl 127.0.0.1:7890` 可以，但容器无法连接

**解决方案**：

编辑 Clash 配置文件（通常在 `%HOMEPATH%/.config/clash-verge/config.yaml`）：

```yaml
mixed-port: 7890
allow-lan: true
bind-address: "0.0.0.0"  # 允许外部连接
```

保存后重启 Clash Verge。

---

### 问题 4: WebSocket 不支持代理

**症状**：
HTTP API 可以访问，但 WebSocket 连接失败

**解决方案**：

#### 方案 A: 启用 Clash TUN 模式

1. **Clash Verge** → **设置** → **TUN 模式**
2. **启用 TUN Mode**
3. 重启 Clash Verge

#### 方案 B: 使用 Socks5 代理

修改代理配置为 Socks5：

```yaml
# docker-compose.prod.yml
HTTP_PROXY: socks5://host.docker.internal:7891
HTTPS_PROXY: socks5://host.docker.internal:7891
```

注意：Socks5 端口通常是 `7891`

---

## ✅ 验证成功

当所有配置正确后，你应该看到：

### 1. Clash Verge 日志

```
[INFO] New connection from 172.17.0.x:xxxxx
[INFO] stream.binance.com:9443 -> Direct
```

### 2. Docker 日志

```bash
$ docker logs ttquant-md-binance --tail 20

2026-02-10T10:35:12Z INFO Connected to Binance WebSocket
2026-02-10T10:35:12Z INFO Subscribed to BTCUSDT@trade
2026-02-10T10:35:13Z INFO Received tick: price=92341.50
```

### 3. Prometheus 指标

访问 http://localhost:8080/metrics

```
websocket_connected 1
websocket_messages_received_total 1234
market_data_tick_count{symbol="BTCUSDT"} 567
```

---

## 🚀 快速测试脚本

保存为 `test-proxy.ps1`：

```powershell
# 测试 Clash 代理配置

Write-Host "=== 1. 测试 Clash 运行状态 ===" -ForegroundColor Cyan
curl -s http://127.0.0.1:7890 | Out-Null
if ($?) {
    Write-Host "✅ Clash 代理运行正常" -ForegroundColor Green
} else {
    Write-Host "❌ Clash 代理无法访问" -ForegroundColor Red
    Exit 1
}

Write-Host "`n=== 2. 检查容器代理配置 ===" -ForegroundColor Cyan
docker exec ttquant-md-binance printenv | findstr PROXY

Write-Host "`n=== 3. 测试容器访问代理 ===" -ForegroundColor Cyan
docker exec ttquant-md-binance sh -c "curl -s -I http://host.docker.internal:7890 2>&1 | head -1"

Write-Host "`n=== 4. 测试访问 Binance API ===" -ForegroundColor Cyan
docker exec ttquant-md-binance sh -c "curl -s -I https://api.binance.com/api/v3/ping 2>&1 | head -1"

Write-Host "`n=== 5. 查看行情服务日志 ===" -ForegroundColor Cyan
docker logs ttquant-md-binance --tail 10

Write-Host "`n测试完成！" -ForegroundColor Green
```

运行：
```powershell
powershell -ExecutionPolicy Bypass -File test-proxy.ps1
```

---

## 📝 配置检查清单

在启动服务前，确认以下项目：

- [ ] Clash Verge 正在运行
- [ ] **允许来自局域网的连接** 已启用
- [ ] HTTP 端口为 `7890`（或记下实际端口）
- [ ] Windows 防火墙允许 Clash Verge
- [ ] Docker Desktop 代理设置已配置（可选）
- [ ] `docker-compose.prod.yml` 中代理配置正确
- [ ] 容器可以 ping 通 `host.docker.internal`

---

## 🔄 完整重启流程

```powershell
# 1. 停止所有容器
docker compose -f docker/docker-compose.prod.yml down

# 2. 重启 Clash Verge
# 手动重启 Clash Verge 应用

# 3. 验证 Clash 可访问
curl http://127.0.0.1:7890

# 4. 重启 Docker Desktop（如果修改了代理设置）
# 右键 Docker Desktop 托盘图标 -> Restart

# 5. 启动服务
docker compose -f docker/docker-compose.prod.yml up -d

# 6. 查看日志
docker logs ttquant-md-binance -f
```

---

**最后更新**: 2026-02-10 18:35
**状态**: 配置中，需要用户完成 Clash 设置
