# 🚀 OKX 快速启动脚本
# 优先使用 OKX，因为对美国 IP 限制更少

Write-Host "=== TTQuant OKX 模式启动 ===" -ForegroundColor Cyan

Write-Host "`n📋 检查代理连接..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://www.okx.com/api/v5/public/time" `
        -Proxy "http://127.0.0.1:7897" `
        -TimeoutSec 10 `
        -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ 代理正常，可以访问 OKX API" -ForegroundColor Green
    }
}
catch {
    Write-Host "❌ 无法通过代理访问 OKX" -ForegroundColor Red
    Write-Host "   请检查 Clash 是否运行在 7897 端口" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🔄 重启 OKX 服务..." -ForegroundColor Yellow
docker compose -f docker/docker-compose.prod.yml restart md-okx gateway-okx

Write-Host "`n⏳ 等待服务启动 (15秒)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`n📊 OKX 服务状态:" -ForegroundColor Yellow
docker ps --filter "name=okx" --format "{{.Names}}: {{.Status}}"

Write-Host "`n📝 最新日志 (OKX 行情):" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
docker logs ttquant-md-okx --tail 15
Write-Host "----------------------------------------" -ForegroundColor Gray

Write-Host "`n💡 查看实时日志:" -ForegroundColor Cyan
Write-Host "   docker logs ttquant-md-okx -f" -ForegroundColor White

Write-Host "`n✅ OKX 模式已激活" -ForegroundColor Green
