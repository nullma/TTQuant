#!/bin/bash
# TTQuant 部署验证脚本

echo "=========================================="
echo "TTQuant 系统状态验证"
echo "=========================================="
echo ""

echo "1. 检查容器运行状态"
echo "------------------------------------------"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'NAMES|strategy|md-okx|gateway-okx|timescaledb|grafana|prometheus'
echo ""

echo "2. 检查策略引擎日志（最近20条）"
echo "------------------------------------------"
docker logs --tail 20 ttquant-strategy-engine
echo ""

echo "3. 检查数据库连接"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT version();"
echo ""

echo "4. 检查最近1小时的订单数量"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT COUNT(*) as order_count FROM orders WHERE time > NOW() - INTERVAL '1 hour';"
echo ""

echo "5. 查看最近5条订单"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT strategy_id, symbol, side, price, volume, time FROM orders ORDER BY time DESC LIMIT 5;"
echo ""

echo "6. 各策略订单统计（最近24小时）"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT strategy_id, COUNT(*) as total_orders FROM orders WHERE time > NOW() - INTERVAL '24 hours' GROUP BY strategy_id;"
echo ""

echo "7. 检查成交记录（最近5条）"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT strategy_id, symbol, side, filled_price, filled_volume, status, time FROM trades ORDER BY time DESC LIMIT 5;"
echo ""

echo "8. 策略统计（最近24小时）"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT * FROM strategy_stats;"
echo ""

echo "9. 检查行情数据接收情况（最近1小时）"
echo "------------------------------------------"
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT symbol, exchange, COUNT(*) as tick_count, MIN(time) as first_tick, MAX(time) as last_tick FROM market_data WHERE time > NOW() - INTERVAL '1 hour' GROUP BY symbol, exchange ORDER BY symbol;"
echo ""

echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 访问 Grafana: http://$(hostname -I | awk '{print $1}'):3000"
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "2. 访问 Prometheus: http://$(hostname -I | awk '{print $1}'):9090"
echo ""
