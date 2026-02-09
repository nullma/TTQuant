#!/bin/bash
set -e

echo "========================================="
echo "TTQuant 量化交易系统部署脚本"
echo "========================================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "错误: .env 文件不存在"
    echo "请复制 .env.example 为 .env 并填入真实配置"
    exit 1
fi

# 检查必要的环境变量
source .env
required_vars=("DB_PASSWORD" "BINANCE_API_KEY" "BINANCE_SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" = "changeme" ]; then
        echo "错误: 环境变量 $var 未正确设置"
        exit 1
    fi
done

# 构建镜像
echo "正在构建 Docker 镜像..."
docker-compose -f docker/docker-compose.yml build

# 初始化数据库
echo "正在初始化数据库..."
docker-compose -f docker/docker-compose.yml up -d timescaledb
sleep 10  # 等待数据库启动

# 启动所有服务
echo "正在启动所有服务..."
docker-compose -f docker/docker-compose.yml up -d

# 等待服务健康检查
echo "等待服务启动..."
sleep 30

# 检查服务状态
echo "========================================="
echo "服务状态检查:"
echo "========================================="
docker-compose -f docker/docker-compose.yml ps

# 检查关键服务健康状态
services=("localhost:8080" "localhost:8081" "localhost:9090" "localhost:3000")
service_names=("md-binance" "gateway" "prometheus" "grafana")

for i in "${!services[@]}"; do
    service="${services[$i]}"
    name="${service_names[$i]}"

    if curl -f -s "http://$service/health" > /dev/null 2>&1 || \
       curl -f -s "http://$service" > /dev/null 2>&1; then
        echo "✓ $name 运行正常"
    else
        echo "✗ $name 健康检查失败"
    fi
done

echo "========================================="
echo "部署完成！"
echo "========================================="
echo "Grafana: http://localhost:3000"
echo "Prometheus: http://localhost:9090"
echo "========================================="
echo ""
echo "查看日志: docker-compose -f docker/docker-compose.yml logs -f"
echo "停止服务: docker-compose -f docker/docker-compose.yml down"
echo "========================================="
