#!/bin/bash
# OKX 连接验证脚本
# 用途：验证 OKX WebSocket 连接和数据接收

set -e

echo "=========================================="
echo "OKX 连接验证"
echo "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "docker/docker-compose.yml" ]; then
    echo "❌ 错误：请在 TTQuant 项目根目录下运行此脚本"
    exit 1
fi

cd docker

# 1. 检查服务状态
echo "📊 [1/5] 检查服务状态..."
if ! docker compose ps | grep -q "md-okx.*running"; then
    echo "❌ OKX Market Data 服务未运行"
    echo "   启动服务: docker compose up -d md-okx"
    exit 1
fi
echo "✅ OKX Market Data 服务正在运行"
echo ""

# 2. 检查 WebSocket 连接
echo "🔌 [2/5] 检查 WebSocket 连接..."
if docker compose logs md-okx | grep -q "Connected to OKX WebSocket"; then
    echo "✅ WebSocket 连接成功"
    LAST_CONNECT=$(docker compose logs md-okx | grep "Connected to OKX WebSocket" | tail -1)
    echo "   最后连接: $LAST_CONNECT"
else
    echo "❌ 未找到 WebSocket 连接成功日志"
    echo ""
    echo "最近的错误日志："
    docker compose logs md-okx | grep -i "error\|tls\|failed" | tail -5
    echo ""
    echo "查看完整日志: docker compose logs md-okx"
    exit 1
fi
echo ""

# 3. 检查数据接收
echo "📈 [3/5] 检查数据接收..."
DATA_COUNT=$(docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -t -c \
    "SELECT COUNT(*) FROM market_data WHERE exchange='okx' AND time > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')

if [ -z "$DATA_COUNT" ] || [ "$DATA_COUNT" -eq 0 ]; then
    echo "⚠️  最近 5 分钟没有接收到新数据"
    echo "   这可能是正常的（如果刚启动）"
    echo "   等待 1 分钟后再次检查..."
    sleep 60
    DATA_COUNT=$(docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -t -c \
        "SELECT COUNT(*) FROM market_data WHERE exchange='okx' AND time > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
fi

if [ "$DATA_COUNT" -gt 0 ]; then
    echo "✅ 正在接收数据（最近 5 分钟: $DATA_COUNT 条）"
else
    echo "❌ 未接收到数据"
    exit 1
fi
echo ""

# 4. 检查数据详情
echo "📋 [4/5] 数据详情..."
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
    "SELECT
        exchange,
        symbol,
        COUNT(*) as count,
        MAX(time) as last_update,
        ROUND(AVG(last_price)::numeric, 2) as avg_price
     FROM market_data
     WHERE exchange='okx' AND time > NOW() - INTERVAL '5 minutes'
     GROUP BY exchange, symbol
     ORDER BY last_update DESC;" 2>/dev/null
echo ""

# 5. 检查服务健康指标
echo "💊 [5/5] 服务健康指标..."
METRICS=$(curl -s http://localhost:8082/metrics 2>/dev/null || echo "")

if [ -n "$METRICS" ]; then
    echo "✅ 指标端点可访问"

    # 提取关键指标
    MSG_COUNT=$(echo "$METRICS" | grep "^market_data_messages_total" | awk '{print $2}')
    ERROR_COUNT=$(echo "$METRICS" | grep "^market_data_errors_total" | awk '{print $2}')

    if [ -n "$MSG_COUNT" ]; then
        echo "   总消息数: $MSG_COUNT"
    fi
    if [ -n "$ERROR_COUNT" ]; then
        echo "   错误数: $ERROR_COUNT"
    fi
else
    echo "⚠️  无法访问指标端点"
fi

cd ..

echo ""
echo "=========================================="
echo "✅ 验证完成！OKX 连接正常"
echo "=========================================="
echo ""
echo "实时监控："
echo "  查看日志: cd docker && docker compose logs -f md-okx"
echo "  查看指标: curl http://localhost:8082/metrics"
echo "  Grafana:  http://$(curl -s ifconfig.me):3000"
echo ""
