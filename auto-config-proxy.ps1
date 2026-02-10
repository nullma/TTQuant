# 自动更新 Docker 代理配置为本机 IP
Write-Host "=== 自动配置 Docker 代理 ===" -ForegroundColor Cyan

# 自动检测本机 IP
$ipLine = ipconfig | Select-String "IPv4" | Select-Object -First 1
$ip = ($ipLine -split ":")[1].Trim()

Write-Host "`n检测到本机 IP: $ip" -ForegroundColor Yellow

# 更新配置文件
$files = @(
    "docker\docker-compose.prod.yml",
    "docker\docker-compose.yml"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "`n正在更新 $file..." -ForegroundColor Cyan
        
        # 使用 UTF-8 无 BOM 编码
        $content = [System.IO.File]::ReadAllText((Resolve-Path $file).Path, [System.Text.Encoding]::UTF8)
        
        # 替换 host.docker.internal 为实际 IP
        $updated = $content -replace 'host\.docker\.internal:7897', "${ip}:7897"
        
        # 保存
        [System.IO.File]::WriteAllText((Resolve-Path $file).Path, $updated, (New-Object System.Text.UTF8Encoding $false))
        
        Write-Host "✅ 已更新为: ${ip}:7897" -ForegroundColor Green
    }
    else {
        Write-Host "❌ 文件不存在: $file" -ForegroundColor Red
    }
}

Write-Host "`n🎉 配置更新完成！" -ForegroundColor Green
Write-Host "下一步: 运行以下命令重启服务" -ForegroundColor Yellow
Write-Host "docker compose -f docker/docker-compose.prod.yml restart md-binance md-okx gateway-binance gateway-okx" -ForegroundColor White
