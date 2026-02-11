#!/bin/bash
# 检查 md-okx 容器健康状态

echo "=========================================="
echo "检查 md-okx 容器状态"
echo "=========================================="
echo ""

echo "1. 容器状态"
echo "------------------------------------------"
docker ps -a | grep md-okx
echo ""

echo "2. 健康检查日志"
echo "------------------------------------------"
docker inspect ttquant-md-okx --format='{{json .State.Health}}' | jq '.'
echo ""

echo "3. 最近50条日志"
echo "------------------------------------------"
docker logs --tail 50 ttquant-md-okx
echo ""

echo "4. 检查 WebSocket 连接"
echo "------------------------------------------"
docker exec ttquant-md-okx sh -c "netstat -an | grep ESTABLISHED || ss -an | grep ESTABLISHED" 2>/dev/null || echo "无法检查网络连接"
echo ""

echo "5. 检查 ZMQ 端口"
echo "------------------------------------------"
docker exec ttquant-md-okx sh -c "netstat -ln | grep 5558 || ss -ln | grep 5558" 2>/dev/null || echo "无法检查端口"
echo ""

echo "=========================================="
echo "建议操作："
echo "如果容器 unhealthy，尝试重启："
echo "  docker-compose restart md-okx"
echo "=========================================="
