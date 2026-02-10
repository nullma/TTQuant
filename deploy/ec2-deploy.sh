#!/bin/bash
# EC2 部署脚本
# 用途：在已配置好的 EC2 上部署 TTQuant 系统

set -e

echo "=========================================="
echo "TTQuant 系统部署"
echo "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "docker/docker-compose.yml" ]; then
    echo "❌ 错误：请在 TTQuant 项目根目录下运行此脚本"
    exit 1
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误：Docker 未安装"
    echo "   请先运行: bash deploy/ec2-setup.sh"
    exit 1
fi

# 检查 Docker 权限
if ! docker ps &> /dev/null; then
    echo "❌ 错误：当前用户无 Docker 权限"
    echo "   请重新登录或运行: newgrp docker"
    exit 1
fi

# 1. 配置环境变量
echo "⚙️  [1/6] 配置环境变量..."
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env

    # 生成随机密码
    DB_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    GRAFANA_PASS=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)

    # 更新密码
    sed -i "s/DB_PASSWORD=changeme/DB_PASSWORD=$DB_PASS/" .env
    sed -i "s/GRAFANA_PASSWORD=changeme/GRAFANA_PASSWORD=$GRAFANA_PASS/" .env

    echo "✅ .env 文件已创建"
    echo "   数据库密码: $DB_PASS"
    echo "   Grafana 密码: $GRAFANA_PASS"
    echo ""
    echo "⚠️  请保存这些密码！"
    echo ""
else
    echo "✅ .env 文件已存在"
fi

# 2. 停止旧服务（如果存在）
echo "🛑 [2/6] 停止旧服务..."
cd docker
docker compose down 2>/dev/null || true
cd ..

# 3. 拉取最新代码
echo "📥 [3/6] 拉取最新代码..."
if [ -d ".git" ]; then
    git pull
    echo "✅ 代码已更新"
else
    echo "⚠️  不是 Git 仓库，跳过更新"
fi

# 4. 构建镜像
echo "🔨 [4/6] 构建 Docker 镜像..."
cd docker
docker compose build --no-cache
echo "✅ 镜像构建完成"

# 5. 启动服务
echo "🚀 [5/6] 启动服务..."
docker compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 6. 验证服务状态
echo "🔍 [6/6] 验证服务状态..."
echo ""
docker compose ps
echo ""

# 检查关键服务
FAILED=0

if ! docker compose ps | grep -q "timescaledb.*running"; then
    echo "❌ TimescaleDB 未运行"
    FAILED=1
fi

if ! docker compose ps | grep -q "md-okx.*running"; then
    echo "❌ OKX Market Data 未运行"
    FAILED=1
fi

if ! docker compose ps | grep -q "gateway-okx.*running"; then
    echo "❌ OKX Gateway 未运行"
    FAILED=1
fi

cd ..

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 部署成功！"
    echo "=========================================="
    echo ""
    echo "服务访问地址："
    echo "  Grafana:    http://$(curl -s ifconfig.me):3000"
    echo "  Prometheus: http://$(curl -s ifconfig.me):9090"
    echo ""
    echo "查看日志："
    echo "  cd docker"
    echo "  docker compose logs -f md-okx"
    echo ""
    echo "验证 OKX 连接："
    echo "  bash deploy/verify-okx.sh"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "⚠️  部署完成，但部分服务未正常启动"
    echo "=========================================="
    echo ""
    echo "查看错误日志："
    echo "  cd docker"
    echo "  docker compose logs"
    echo ""
fi
