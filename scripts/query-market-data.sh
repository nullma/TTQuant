#!/bin/bash
# 实时行情数据查询工具

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=========================================="
echo "TTQuant 实时行情数据查询"
echo "=========================================="
echo ""

# 1. 数据统计
echo "[1] 数据统计概览"
echo "----------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "
SELECT
    exchange,
    symbol,
    COUNT(*) as total_records,
    MIN(time) as first_record,
    MAX(time) as last_record,
    ROUND(AVG(last_price)::numeric, 2) as avg_price,
    ROUND(SUM(volume)::numeric, 4) as total_volume
FROM market_data
GROUP BY exchange, symbol
ORDER BY total_records DESC;
"
echo ""

# 2. 最新价格
echo "[2] 最新价格 (实时)"
echo "----------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "
SELECT DISTINCT ON (exchange, symbol)
    exchange,
    symbol,
    last_price,
    volume,
    time as update_time
FROM market_data
ORDER BY exchange, symbol, time DESC;
"
echo ""

# 3. 最近1分钟交易活跃度
echo "[3] 最近1分钟交易活跃度"
echo "----------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "
SELECT
    exchange,
    symbol,
    COUNT(*) as trades_count,
    ROUND(SUM(volume)::numeric, 4) as total_volume,
    ROUND(MIN(last_price)::numeric, 2) as low,
    ROUND(MAX(last_price)::numeric, 2) as high
FROM market_data
WHERE time > NOW() - INTERVAL '1 minute'
GROUP BY exchange, symbol
ORDER BY trades_count DESC;
"
echo ""

# 4. K线数据（最近10条）
echo "[4] K线数据 (最近10条)"
echo "----------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "
SELECT * FROM klines ORDER BY time DESC LIMIT 10;
" 2>/dev/null || echo "K线表为空或不存在"
echo ""

echo "=========================================="
echo "查询完成"
echo "=========================================="
