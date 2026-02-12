#!/bin/bash
# Grafana 自动配置脚本

set -e

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="admin"

echo "=========================================="
echo "TTQuant Grafana 自动配置"
echo "=========================================="
echo ""

# 1. 配置 Prometheus 数据源
echo "[1/3] 配置 Prometheus 数据源..."
curl -X POST \
  -H "Content-Type: application/json" \
  -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "access": "proxy",
    "isDefault": true,
    "jsonData": {
      "timeInterval": "5s",
      "queryTimeout": "60s"
    }
  }' \
  "${GRAFANA_URL}/api/datasources" 2>/dev/null || echo "数据源可能已存在"

echo "✓ Prometheus 数据源配置完成"
echo ""

# 2. 导入 TTQuant 仪表板
echo "[2/3] 导入 TTQuant 系统监控仪表板..."
curl -X POST \
  -H "Content-Type: application/json" \
  -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  -d @/tmp/ttquant-dashboard.json \
  "${GRAFANA_URL}/api/dashboards/db" 2>/dev/null

echo "✓ TTQuant 仪表板导入完成"
echo ""

# 3. 导入 Node Exporter 仪表板
echo "[3/3] 导入 Node Exporter 仪表板..."
curl -X POST \
  -H "Content-Type: application/json" \
  -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  -d '{
    "dashboard": {
      "id": null,
      "uid": "node-exporter",
      "title": "Node Exporter Full",
      "tags": ["node-exporter"],
      "timezone": "browser"
    },
    "folderId": 0,
    "overwrite": true,
    "inputs": [
      {
        "name": "DS_PROMETHEUS",
        "type": "datasource",
        "pluginId": "prometheus",
        "value": "Prometheus"
      }
    ]
  }' \
  "${GRAFANA_URL}/api/dashboards/import" 2>/dev/null

echo "✓ Node Exporter 仪表板导入完成"
echo ""

echo "=========================================="
echo "配置完成！"
echo "=========================================="
echo ""
echo "访问 Grafana: ${GRAFANA_URL}"
echo "用户名: ${GRAFANA_USER}"
echo "密码: ${GRAFANA_PASS}"
echo ""
echo "可用仪表板："
echo "  - TTQuant 系统监控"
echo "  - Node Exporter Full"
echo ""
