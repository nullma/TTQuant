# 更新 Clash 代理端口 (7890 -> 7897)
# 使用 UTF-8 编码避免文件损坏

$files = @(
    "docker\docker-compose.prod.yml",
    "docker\docker-compose.yml"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "Updating $file..." -ForegroundColor Cyan
        
        # 使用 UTF-8 BOM 编码读取和写入
        $content = Get-Content $file -Raw -Encoding UTF8
        $updated = $content -replace 'host\.docker\.internal:7890', 'host.docker.internal:7897'
        
        # 保存时使用 UTF-8 无 BOM
        [System.IO.File]::WriteAllText((Resolve-Path $file).Path, $updated, (New-Object System.Text.UTF8Encoding $false))
        
        Write-Host "✅ Updated $file" -ForegroundColor Green
    } else {
        Write-Host "❌ File not found: $file" -ForegroundColor Red
    }
}

Write-Host "`n🎉 All files updated! Port changed from 7890 -> 7897" -ForegroundColor Green
