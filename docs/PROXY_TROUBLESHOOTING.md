## 🔧 Docker 代理连接问题总结

### ✅ 已完成的配置

1. **Clash Verge 设置正确**
   - Allow LAN: ✅ 启用
   - Port: 7897 ✅
   - 本机可访问: ✅ `curl http://127.0.0.1:7897` 返回 400 (正常)

2. **Docker Compose 配置正确**
   - 环境变量: `HTTP_PROXY=http://host.docker.internal:7897` ✅
   - 容器内变量验证通过: ✅

### ❌ 当前问题

**容器无法连接 `host.docker.internal:7897`**

测试结果：
```bash
$ docker exec ttquant-md-binance curl -I http://host.docker.internal:7897
# 超时或连接被拒绝
```

---

## 🎯 解决方案

### 方案 1: 使用本机实际 IP（推荐）

#### 步骤 1: 获取本机 IP

```powershell
# 在 PowerShell 执行
ipconfig | Select-String "IPv4" | Select-Object -First 1

# 示例输出
#    IPv4 地址 . . . . . . . . . . . . : 192.168.1.100
```

#### 步骤 2: 更新配置文件

将 `docker-compose.prod.yml` 和 `docker-compose.yml` 中的代理地址改为实际 IP：

```yaml
# 将所有出现的
HTTP_PROXY: http://host.docker.internal:7897

# 修改为（使用你的实际 IP）
HTTP_PROXY: http://192.168.1.100:7897
```

手动编辑或运行脚本：

```powershell
# 创建更新脚本 update-proxy-ip.ps1
$MY_IP = "192.168.1.100"  # 替换为你的实际 IP

$files = @("docker\docker-compose.prod.yml", "docker\docker-compose.yml")
foreach ($file in $files) {
    $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
    $updated = $content -replace 'host\.docker\.internal:7897', "$MY_IP:7897"
    [System.IO.File]::WriteAllText($file, $updated, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "✅ Updated $file"
}
```

#### 步骤 3: 重启服务

```powershell
docker compose -f docker/docker-compose.prod.yml restart md-binance md-okx gateway-binance gateway-okx
```

#### 步骤 4: 验证连接

```powershell
# 等待 10 秒后检查
Start-Sleep -Seconds 10
docker logs ttquant-md-binance --tail 20

# 期待看到
# ✅ WebSocket connected to wss://stream.binance.com:9443/ws
# ✅ Subscribed to btcusdt@trade
```

---

### 方案 2: 配置 Docker Desktop全局代理（备选）

1. 打开 **Docker Desktop**
2. **Settings** → **Resources** → **Proxies**
3. 启用 **Manual proxy configuration**
4. 填入：
   - Web Server (HTTP): `http://127.0.0.1:7897`
   - Secure Web Server (HTTPS): `http://127.0.0.1:7897`
5. **Apply & Restart**

这种方式会让 Docker 引擎自动处理代理，不需要在 compose 文件中配置。

---

### 方案 3: 添加 extra_hosts（兜底方案）

如果 `host.docker.internal` 无法解析，在 compose 文件中添加：

```yaml
md-binance:
  # ... 其他配置
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

---

## 🧪 快速测试脚本

创建 `test-docker-proxy.ps1`：

```powershell
Write-Host "=== Docker 代理连接测试 ===" -ForegroundColor Cyan

Write-Host "`n1️⃣  本机 IP 地址:" -ForegroundColor Yellow
ipconfig | Select-String "IPv4" | Select-Object -First 1

Write-Host "`n2️⃣  Clash 代理可访问性:" -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:7897" -Method GET -ErrorAction SilentlyContinue >$null 2>&1
    Write-Host "✅ Clash 运行在 7897 端口" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "✅ Clash 运行正常 (400 错误是正常的)" -ForegroundColor Green
    } else {
        Write-Host "❌ Clash 无法访问" -ForegroundColor Red
    }
}

Write-Host "`n3️⃣  容器内代理配置:" -ForegroundColor Yellow
docker exec ttquant-md-binance printenv | Select-String "PROXY"

Write-Host "`n4️⃣  容器访问本机 7897 测试:" -ForegroundColor Yellow
$result = docker exec ttquant-md-binance sh -c "curl -s -I -m 3 http://host.docker.internal:7897 2>&1 | head -1"
if ($result -like "*HTTP*" -or $result -like "*400*") {
    Write-Host "✅ 容器能访问代理" -ForegroundColor Green
} else {
    Write-Host "❌ 容器无法访问代理" -ForegroundColor Red
    Write-Host "   错误: $result" -ForegroundColor Gray
}

Write-Host "`n5️⃣  使用代理访问 Binance API:" -ForegroundColor Yellow
$apiResult = docker exec ttquant-md-binance sh -c "curl -s -I -m 5 https://api.binance.com/api/v3/ping 2>&1 | head -1"
if ($apiResult -like "*200*") {
    Write-Host "✅ 通过代理成功访问 Binance" -ForegroundColor Green
} else {
    Write-Host "⚠️  无法访问 Binance (可能需要配置 IP 地址)" -ForegroundColor Yellow
    Write-Host "   结果: $apiResult" -ForegroundColor Gray
}

Write-Host "`n6️⃣  行情服务状态 (最后10行日志):" -ForegroundColor Yellow
docker logs ttquant-md-binance --tail 10

Write-Host "`n=== 测试完成 ===" -ForegroundColor Cyan
```

运行：
```powershell
powershell -ExecutionPolicy Bypass -File test-docker-proxy.ps1
```

---

## 📝 总结

**推荐使用方案 1（实际 IP）**，因为：
1. 最可靠，不依赖 Docker 特殊配置
2. 配置简单明确
3. 适用于所有 Windows/macOS 环境

**下一步操作**：
1. 获取本机 IP: `ipconfig`
2. 将配置文件中的 `host.docker.internal:7897` 替换为 `<你的IP>:7897`
3. 重启服务
4. 验证日志

---

**更新时间**: 2026-02-10 18:46
**状态**: 等待用户获取本机 IP 并更新配置
