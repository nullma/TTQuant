#!/bin/bash
# 一键启动模拟交易

echo "=========================================="
echo "TTQuant 模拟交易启动向导"
echo "=========================================="
echo ""

echo "当前系统状态："
echo "----------------------------------------"
echo "✅ 数据采集: OKX 行情正在实时采集"
echo "✅ 数据库: 已有 23万+ 条行情数据"
echo "✅ 监控: Grafana 运行中"
echo ""

echo "可用策略："
echo "----------------------------------------"
echo "1. 网格交易 (BTCUSDT) - 适合震荡行情"
echo "2. 均线交叉 (ETHUSDT) - 适合趋势行情"
echo "3. 动量突破 (SOLUSDT) - 适合突破行情"
echo ""

read -p "请选择要启动的策略 (1/2/3): " choice

case $choice in
    1)
        STRATEGY="grid_trading_btc"
        SYMBOL="BTCUSDT"
        TYPE="网格交易"
        ;;
    2)
        STRATEGY="ma_cross_eth"
        SYMBOL="ETHUSDT"
        TYPE="均线交叉"
        ;;
    3)
        STRATEGY="momentum_sol"
        SYMBOL="SOLUSDT"
        TYPE="动量突破"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "启动策略: $TYPE ($SYMBOL)"
echo "=========================================="
echo ""

# 修改配置文件，启用选中的策略
echo "📝 正在配置策略..."
sed -i "/name = \"$STRATEGY\"/,/enabled = false/ s/enabled = false/enabled = true/" config/strategies.toml

echo "✅ 策略已启用"
echo ""

# 显示策略配置
echo "策略配置："
echo "----------------------------------------"
grep -A 15 "name = \"$STRATEGY\"" config/strategies.toml | head -16
echo ""

# 重启策略引擎
echo "🔄 重启策略引擎..."
docker restart ttquant-strategy-engine

echo ""
echo "=========================================="
echo "✅ 启动完成！"
echo "=========================================="
echo ""
echo "📊 查看实时状态："
echo "  docker logs ttquant-strategy-engine -f"
echo ""
echo "🌐 查看监控面板："
echo "  http://43.198.18.252:3000"
echo ""
echo "⚠️  注意: 当前为模拟交易模式，不会使用真实资金"
echo ""
