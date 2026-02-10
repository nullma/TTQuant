# 简单的代理配置更新脚本

$IP = "198.18.0.1"
$PORT = "7897"
$TARGET = "${IP}:${PORT}"

Write-Host "更新代理配置为: $TARGET`n" -ForegroundColor Cyan

# 更新生产环境配置
$file1 = "docker\docker-compose.prod.yml"
$content1 = Get-Content $file1 -Raw -Encoding UTF8
$content1 = $content1 -replace 'host\.docker\.internal:7897', $TARGET
$Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllText("$PWD\$file1", $content1, $Utf8NoBomEncoding)
Write-Host "✅ 已更新: $file1" -ForegroundColor Green

# 更新开发环境配置
$file2 = "docker\docker-compose.yml"
$content2 = Get-Content $file2 -Raw -Encoding UTF8
$content2 = $content2 -replace 'host\.docker\.internal:7897', $TARGET
[System.IO.File]::WriteAllText("$PWD\$file2", $content2, $Utf8NoBomEncoding)
Write-Host "✅ 已更新: $file2" -ForegroundColor Green

Write-Host "`n下一步运行:" -ForegroundColor Yellow
Write-Host "docker compose -f docker/docker-compose.prod.yml restart md-binance md-okx" -ForegroundColor White
