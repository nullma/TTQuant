#!/bin/bash
# TTQuant 策略引擎启动脚本

set -e

echo "=========================================="
echo "TTQuant Strategy Engine Deployment"
echo "=========================================="

# 检查配置文件
if [ ! -f "config/strategies.toml" ]; then
    echo "Error: config/strategies.toml not found"
    exit 1
fi

# 检查是否有启用的策略
enabled_count=$(grep "enabled = true" config/strategies.toml | wc -l)
if [ "$enabled_count" -eq 0 ]; then
    echo "Warning: No strategies are enabled in config/strategies.toml"
    echo "Please edit the file and set 'enabled = true' for at least one strategy"
    exit 1
fi

echo "Found $enabled_count enabled strategy(ies)"

# 选择交易所
echo ""
echo "Select exchange:"
echo "1) OKX (default)"
echo "2) Binance"
read -p "Enter choice [1-2]: " exchange_choice

case $exchange_choice in
    2)
        export STRATEGY_EXCHANGE=binance
        echo "Using Binance"
        ;;
    *)
        export STRATEGY_EXCHANGE=okx
        echo "Using OKX"
        ;;
esac

# 选择模式
echo ""
echo "Select trading mode:"
echo "1) Paper trading (模拟交易)"
echo "2) Live trading (实盘交易)"
read -p "Enter choice [1-2]: " mode_choice

case $mode_choice in
    2)
        echo "WARNING: Live trading mode selected!"
        read -p "Are you sure? This will use real money! (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "Aborted"
            exit 0
        fi
        ;;
    *)
        echo "Using paper trading mode"
        ;;
esac

# 构建并启动策略引擎
echo ""
echo "Building and starting strategy engine..."
cd docker
docker-compose build strategy-engine
docker-compose up -d strategy-engine

echo ""
echo "=========================================="
echo "Strategy Engine Started!"
echo "=========================================="
echo ""
echo "View logs:"
echo "  docker logs -f ttquant-strategy-engine"
echo ""
echo "Stop engine:"
echo "  docker-compose stop strategy-engine"
echo ""
echo "Monitor in Grafana:"
echo "  http://localhost:3000"
echo "=========================================="
