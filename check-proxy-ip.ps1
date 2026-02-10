# 检测 Clash 代理出口 IP 和地区

Write-Host "=== Clash 代理出口检测 ===" -ForegroundColor Cyan

Write-Host "`n1️⃣  检测代理出口 IP 和地区..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://ip-api.com/json" -Proxy "http://127.0.0.1:7897" -ProxyUseDefaultCredentials
    
    Write-Host "`n当前代理出口信息:" -ForegroundColor White
    Write-Host "  IP 地址: $($response.query)" -ForegroundColor Cyan
    Write-Host "  国家: $($response.country)" -ForegroundColor Cyan
    Write-Host "  城市: $($response.city)" -ForegroundColor Cyan
    Write-Host "  ISP: $($response.isp)" -ForegroundColor Cyan
    
    if ($response.country -eq "United States") {
        Write-Host "`n⚠️  警告: 当前使用美国 IP！" -ForegroundColor Red
        Write-Host "   币安会封锁美国 IP，连接将失败" -ForegroundColor Red
        Write-Host "`n建议: 在 Clash 中切换到以下地区节点:" -ForegroundColor Yellow
        Write-Host "   ✅ 香港 (Hong Kong)" -ForegroundColor Green
        Write-Host "   ✅ 新加坡 (Singapore)" -ForegroundColor Green
        Write-Host "   ✅ 日本 (Japan)" -ForegroundColor Green
    }
    else {
        Write-Host "`n✅ 当前 IP 地区正常，可以访问币安" -ForegroundColor Green
    }
}
catch {
    Write-Host "`n❌ 无法检测代理出口 IP" -ForegroundColor Red
    Write-Host "   请确保 Clash 正在运行" -ForegroundColor Yellow
}

Write-Host "`n2️⃣  测试访问币安 API..." -ForegroundColor Yellow
try {
    $headers = @{
        "User-Agent" = "Mozilla/5.0"
    }
    $binanceTest = Invoke-WebRequest -Uri "https://api.binance.com/api/v3/ping" -Proxy "http://127.0.0.1:7897" -Headers $headers -TimeoutSec 10
    
    if ($binanceTest.StatusCode -eq 200) {
        Write-Host "✅ 成功访问币安 API！" -ForegroundColor Green
    }
}
catch {
    Write-Host "❌ 无法访问币安 API" -ForegroundColor Red
    
    if ($_.Exception.Message -like "*451*") {
        Write-Host "   错误 451: IP 被币安封锁（美国 IP）" -ForegroundColor Red
        Write-Host "   解决方案: 切换 Clash 节点为香港/新加坡" -ForegroundColor Yellow
    }
    elseif ($_.Exception.Message -like "*403*") {
        Write-Host "   错误 403: 访问被拒绝" -ForegroundColor Red
        Write-Host "   可能原因: 美国 IP 被封锁" -ForegroundColor Yellow
    }
    else {
        Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Gray
    }
}

Write-Host "`n3️⃣  测试访问 OKX API (备选交易所)..." -ForegroundColor Yellow
try {
    $okxTest = Invoke-WebRequest -Uri "https://www.okx.com/api/v5/public/time" -Proxy "http://127.0.0.1:7897" -TimeoutSec 10
    
    if ($okxTest.StatusCode -eq 200) {
        Write-Host "✅ 成功访问 OKX API！（OKX 对地区限制较少）" -ForegroundColor Green
    }
}
catch {
    Write-Host "⚠️  无法访问 OKX API: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n=== 检测完成 ===" -ForegroundColor Cyan
Write-Host "`n💡 提示: 如果币安被封锁，建议:" -ForegroundColor Yellow
Write-Host "   1. 切换 Clash 节点为香港/新加坡/日本" -ForegroundColor White
Write-Host "   2. 或者使用 OKX 交易所（对美国 IP 限制更少）" -ForegroundColor White
