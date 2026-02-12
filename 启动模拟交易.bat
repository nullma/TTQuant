@echo off
chcp 65001 >nul
echo ==========================================
echo TTQuant 模拟交易启动向导
echo ==========================================
echo.

echo 当前系统状态：
echo ----------------------------------------
echo ✅ 数据采集: OKX 行情正在实时采集
echo ✅ 数据库: 已有 23万+ 条行情数据
echo ✅ 监控: Grafana 运行中
echo.

echo 可用策略：
echo ----------------------------------------
echo 1. 网格交易 (BTCUSDT) - 适合震荡行情
echo 2. 均线交叉 (ETHUSDT) - 适合趋势行情
echo 3. 动量突破 (SOLUSDT) - 适合突破行情
echo.

set /p choice="请选择要启动的策略 (1/2/3): "

if "%choice%"=="1" (
    set STRATEGY=grid_trading_btc
    set SYMBOL=BTCUSDT
    set TYPE=网格交易
) else if "%choice%"=="2" (
    set STRATEGY=ma_cross_eth
    set SYMBOL=ETHUSDT
    set TYPE=均线交叉
) else if "%choice%"=="3" (
    set STRATEGY=momentum_sol
    set SYMBOL=SOLUSDT
    set TYPE=动量突破
) else (
    echo ❌ 无效选择
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 启动策略: %TYPE% (%SYMBOL%)
echo ==========================================
echo.

echo 📝 正在上传配置到服务器...
scp -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" scripts\start-trading.sh ubuntu@43.198.18.252:~/TTQuant/scripts/

echo.
echo 🚀 正在启动策略...
ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "cd TTQuant && bash scripts/start-trading.sh" < nul

echo.
echo ==========================================
echo ✅ 启动完成！
echo ==========================================
echo.
echo 📊 查看实时日志，请运行:
echo    ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252 "docker logs ttquant-strategy-engine -f"
echo.
echo 🌐 查看监控面板:
echo    http://43.198.18.252:3000
echo.
echo ⚠️  注意: 当前为模拟交易模式，不会使用真实资金
echo.

pause
