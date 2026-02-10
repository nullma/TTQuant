# OKX 连接状态诊断脚本

Write-Host "`n=== OKX 服务状态诊断 ===" -ForegroundColor Cyan

Write-Host "`n1️⃣  容器运行状态:" -ForegroundColor Yellow
docker ps --filter "name=ttquant-md-okx" --format "  状态: {{.Status}}`n  端口: {{.Ports}}"

Write-Host "`n2️⃣  环境变量配置:" -ForegroundColor Yellow
docker exec ttquant-md-okx sh -c "printenv | grep -E '(PROXY|MARKET)' | sort"

Write-Host "`n3️⃣  最近 20 条日志:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
docker logs ttquant-md-okx --tail 20 --timestamps
Write-Host "----------------------------------------" -ForegroundColor Gray

Write-Host "`n4️⃣  连接状态分析:" -ForegroundColor Yellow
$logs = docker logs ttquant-md-okx --tail 50 2>&1 | Out-String

if ($logs -match "WebSocket connected" -or $logs -match "Connected to") {
    Write-Host "  ✅ WebSocket 已连接" -ForegroundColor Green
}
elseif ($logs -match "reconnecting" -or $logs -match "Reconnecting") {
    Write-Host "  ⚠️  正在重连中..." -ForegroundColor Yellow
    Write-Host "  原因: 可能是代理配置或网络问题" -ForegroundColor Gray
}
elseif ($logs -match "Connection refused" -or $logs -match "Timeout") {
    Write-Host "  ❌ 连接被拒绝/超时" -ForegroundColor Red
    Write-Host "  建议: 检查代理配置和网络连接" -ForegroundColor Gray
}
else {
    Write-Host "  ⚙️  状态未知，查看上方日志" -ForegroundColor Yellow
}

Write-Host "`n5️⃣  测试代理访问 OKX API:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://www.okx.com/api/v5/public/time" `
        -Proxy "http://127.0.0.1:7897" `
        -TimeoutSec 10 `
        -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✅ 通过代理可以访问 OKX API" -ForegroundColor Green
        Write-Host "  代理配置正常！" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ❌ 无法通过代理访问 OKX API" -ForegroundColor Red
    if ($_.Exception.Message -like "*超时*" -or $_.Exception.Message -like "*timeout*") {
        Write-Host "  原因: 代理超时" -ForegroundColor Gray
    }
    elseif ($_.Exception.Message -like "*Connection refused*") {
        Write-Host "  原因: 代理拒绝连接" -ForegroundColor Gray
    }
    else {
        Write-Host "  错误: $($_.Exception.Message)" -ForegroundColor Gray
    }
}

Write-Host "`n=== 诊断完成 ===" -ForegroundColor Cyan

Write-Host "`n💡 下一步操作建议:" -ForegroundColor Yellow
Write-Host "  - 如果看到 '正在重连': 等待或检查 Clash 代理节点" -ForegroundColor White
Write-Host "  - 如果看到 '连接被拒绝': 运行 .\update-proxy-ip.ps1 重新配置" -ForegroundColor White
Write-Host "  - 查看实时日志: docker logs ttquant-md-okx -f" -ForegroundColor White
