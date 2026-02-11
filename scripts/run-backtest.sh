#!/bin/bash
# TTQuant 回测运行脚本

set -e

echo "=========================================="
echo "TTQuant Backtest Runner"
echo "=========================================="

# 检查数据库是否运行
if ! docker ps | grep -q ttquant-timescaledb; then
    echo "Error: TimescaleDB is not running"
    echo "Please start the database first:"
    echo "  cd docker && docker-compose up -d timescaledb"
    exit 1
fi

# 检查是否有历史数据
echo "Checking for historical data..."
data_count=$(docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -t -c "SELECT COUNT(*) FROM market_data;" 2>/dev/null || echo "0")
data_count=$(echo $data_count | tr -d ' ')

if [ "$data_count" -lt 1000 ]; then
    echo "Warning: Only $data_count market data records found"
    echo "You may need more data for meaningful backtest results"
    read -p "Continue anyway? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        exit 0
    fi
fi

echo "Found $data_count market data records"

# 运行回测
echo ""
echo "Starting backtest..."
cd docker
docker-compose --profile backtest up backtest

echo ""
echo "=========================================="
echo "Backtest Complete!"
echo "=========================================="
echo ""
echo "Results saved to: backtest_results/"
echo ""
echo "View results in Grafana:"
echo "  http://localhost:3000/d/backtest"
echo "=========================================="
