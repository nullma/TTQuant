@echo off
echo ============================================
echo TTQuant OKX 连接状态诊断
echo ============================================
echo.

echo [1/5] 容器运行状态
echo ----------------------------------------
docker ps --filter "name=ttquant-md-okx" --format "名称: {{.Names}}" 
docker ps --filter "name=ttquant-md-okx" --format "状态: {{.Status}}" 
docker ps --filter "name=ttquant-md-okx" --format "端口: {{.Ports}}"
echo.

echo [2/5] 资源使用情况
echo ----------------------------------------
docker stats ttquant-md-okx --no-stream --format "CPU: {{.CPUPerc}}  内存: {{.MemUsage}}"
echo.

echo [3/5] 环境变量检查
echo ----------------------------------------
docker exec ttquant-md-okx sh -c "printenv | grep -E '(MARKET|PROXY)' | sort"
echo.

echo [4/5] 网络连通性测试
echo ----------------------------------------
echo 测试代理访问 OKX API...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'https://www.okx.com/api/v5/public/time' -Proxy 'http://127.0.0.1:7897' -TimeoutSec 5 -UseBasicParsing; Write-Host '✓ OKX API 可访问 (HTTP' $r.StatusCode')' -ForegroundColor Green } catch { Write-Host '✗ 无法访问 OKX API' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Gray }"
echo.

echo [5/5] 最新日志 (最后 20 行)
echo ----------------------------------------
docker logs ttquant-md-okx --tail 20 2>&1
echo ----------------------------------------
echo.

echo ============================================
echo 诊断完成
echo ============================================
echo.
echo 💡 查看实时日志: docker logs ttquant-md-okx -f
echo 💡 重启服务: docker compose -f docker/docker-compose.prod.yml restart md-okx
echo 💡 访问监控: http://localhost:8082/metrics
echo.
pause
