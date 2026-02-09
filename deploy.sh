#!/bin/bash
set -e

echo "========================================="
echo "TTQuant 量化交易系统部署脚本"
echo "========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi

# 使用 docker compose 或 docker-compose
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

# 检查 .env 文件（可选，使用默认值）
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在，使用默认配置"
    echo "如需自定义配置，请复制 .env.example 为 .env"
fi

# 构建镜像
echo "正在构建 Docker 镜像..."
$DOCKER_COMPOSE -f docker/docker-compose.yml build

# 初始化数据库
echo "正在初始化数据库..."
$DOCKER_COMPOSE -f docker/docker-compose.yml up -d timescaledb
echo "等待数据库启动..."
sleep 15

# 启动所有服务
echo "正在启动所有服务..."
$DOCKER_COMPOSE -f docker/docker-compose.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "========================================="
echo "服务状态:"
echo "========================================="
$DOCKER_COMPOSE -f docker/docker-compose.yml ps

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo "TimescaleDB: localhost:5432"
echo "Binance 行情: tcp://localhost:5555"
echo ""
echo "查看行情日志:"
echo "  $DOCKER_COMPOSE -f docker/docker-compose.yml logs -f md-binance"
echo ""
echo "查看测试客户端:"
echo "  $DOCKER_COMPOSE -f docker/docker-compose.yml logs -f test-client"
echo ""
echo "停止服务:"
echo "  $DOCKER_COMPOSE -f docker/docker-compose.yml down"
echo ""
echo "完全清理（包括数据）:"
echo "  $DOCKER_COMPOSE -f docker/docker-compose.yml down -v"
echo "========================================="
