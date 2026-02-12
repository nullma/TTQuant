@echo off
chcp 65001 >nul
cls
echo ==========================================
echo TTQuant 系统管理面板
echo ==========================================
echo.

:menu
echo 请选择操作：
echo.
echo 1. 查看实时行情数据
echo 2. 打开 Grafana 监控面板
echo 3. 查看系统运行状态
echo 4. 查看服务日志
echo 5. 退出
echo.

set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto view_data
if "%choice%"=="2" goto open_grafana
if "%choice%"=="3" goto check_status
if "%choice%"=="4" goto view_logs
if "%choice%"=="5" goto end

echo ❌ 无效选择
echo.
goto menu

:view_data
cls
echo ==========================================
echo 实时行情数据
echo ==========================================
echo.
echo 正在查询最新数据...
echo.

ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \"SELECT DISTINCT ON (exchange, symbol) exchange, symbol, last_price, volume, time as update_time FROM market_data ORDER BY exchange, symbol, time DESC;\""

echo.
echo 按任意键返回菜单...
pause >nul
cls
goto menu

:open_grafana
echo.
echo 正在打开 Grafana 监控面板...
start http://43.198.18.252:3000
echo.
echo ✅ 已在浏览器中打开
echo    用户名: admin
echo    密码: admin123
echo.
echo 按任意键返回菜单...
pause >nul
cls
goto menu

:check_status
cls
echo ==========================================
echo 系统运行状态
echo ==========================================
echo.

ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep ttquant"

echo.
echo 数据统计：
ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \"SELECT exchange, symbol, COUNT(*) as records FROM market_data GROUP BY exchange, symbol ORDER BY records DESC;\""

echo.
echo 按任意键返回菜单...
pause >nul
cls
goto menu

:view_logs
cls
echo ==========================================
echo 服务日志
echo ==========================================
echo.
echo 选择要查看的服务：
echo.
echo 1. OKX 行情服务
echo 2. Binance 行情服务
echo 3. 数据库
echo 4. 返回主菜单
echo.

set /p log_choice="请选择 (1-4): "

if "%log_choice%"=="1" (
    echo.
    echo 正在查看 OKX 行情服务日志 (按 Ctrl+C 退出)...
    echo.
    ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker logs ttquant-md-okx --tail 50"
) else if "%log_choice%"=="2" (
    echo.
    echo 正在查看 Binance 行情服务日志 (按 Ctrl+C 退出)...
    echo.
    ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker logs ttquant-md-binance --tail 50"
) else if "%log_choice%"=="3" (
    echo.
    echo 正在查看数据库日志 (按 Ctrl+C 退出)...
    echo.
    ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker logs ttquant-timescaledb --tail 50"
) else if "%log_choice%"=="4" (
    cls
    goto menu
)

echo.
echo 按任意键返回菜单...
pause >nul
cls
goto menu

:end
echo.
echo 再见！
timeout /t 2 >nul
exit

