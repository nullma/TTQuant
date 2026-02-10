#!/bin/bash
# EC2 最小化部署脚本
# 适用于磁盘空间有限的环境（8GB）

set -e

echo "=========================================="
echo "TTQuant 最小化部署（仅 OKX）"
echo "=========================================="
echo ""

# 检查是否在项目根目录
if [ ! -f "docker/docker-compose.minimal.yml" ]; then
    echo "❌ 错误：请在 TTQuant 项目根目录下运行此脚本"
    exit 1
fi

# 1. 配置环境变量
echo "⚙️  [1/5] 配置环境变量..."
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

# 2. 清理旧资源
echo "🧹 [2/5] 清理旧资源..."
cd docker
docker compose -f docker-compose.minimal.yml down 2>/dev/null || true
docker system prune -f
cd ..

# 3. 启动服务
echo "🚀 [3/5] 启动服务..."
cd docker
docker compose -f docker-compose.minimal.yml up -d timescaledb prometheus grafana

echo "⏳ 等待数据库启动..."
sleep 15

# 4. 启动 OKX 服务
echo "📊 [4/5] 启动 OKX 行情服务..."
docker compose -f docker-compose.minimal.yml up -d md-okx

echo "⏳ 等待服务启动..."
sleep 10

# 5. 验证服务状态
echo "🔍 [5/5] 验证服务状态..."
echo ""
docker compose -f docker-compose.minimal.yml ps
echo ""

cd ..

# 检查关键服务
FAILED=0

if ! docker compose -f docker/docker-compose.minimal.yml ps | grep -q "timescaledb.*running"; then
    echo "❌ TimescaleDB 未运行"
    FAILED=1
fi

if ! docker compose -f docker/docker-compose.minimal.yml ps | grep -q "md-okx.*running"; then
    echo "⚠️  OKX Market Data 正在启动（首次启动需要编译，约 5-10 分钟）"
fi

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
    echo "查看 OKX 日志（首次启动会编译代码）："
    echo "  cd docker"
    echo "  docker compose -f docker-compose.minimal.yml logs -f md-okx"
    echo ""
    echo "验证 OKX 连接（等待编译完成后）："
    echo "  bash deploy/verify-okx-minimal.sh"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "⚠️  部署完成，但部分服务未正常启动"
    echo "=========================================="
    echo ""
    echo "查看错误日志："
    echo "  cd docker"
    echo "  docker compose -f docker-compose.minimal.yml logs"
    echo ""
fi
