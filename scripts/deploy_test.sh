#!/bin/bash
# TTQuant 测试环境部署脚本

set -e

echo "========================================================================"
echo "TTQuant 测试环境部署"
echo "========================================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker
echo -e "\n${YELLOW}[1/6]${NC} 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker 环境正常"

# 检查环境变量文件
echo -e "\n${YELLOW}[2/6]${NC} 检查配置文件..."
if [ ! -f .env.test ]; then
    echo -e "${YELLOW}⚠${NC}  .env.test 不存在，创建默认配置..."
    cat > .env.test << EOF
# 数据库
DB_PASSWORD=ttquant123

# Grafana
GRAFANA_PASSWORD=admin123

# OKX API（可选，纸面交易不需要）
OKX_API_KEY=
OKX_API_SECRET=
OKX_PASSPHRASE=

# Binance API（可选）
BINANCE_TESTNET_KEY=
BINANCE_TESTNET_SECRET=
EOF
    echo -e "${GREEN}✓${NC} 已创建 .env.test"
fi

# 加载环境变量
export $(cat .env.test | grep -v '^#' | xargs)

# 停止现有容器
echo -e "\n${YELLOW}[3/6]${NC} 停止现有容器..."
docker-compose -f docker-compose.test.yml down 2>/dev/null || true
echo -e "${GREEN}✓${NC} 已停止现有容器"

# 构建镜像
echo -e "\n${YELLOW}[4/6]${NC} 构建 Docker 镜像..."
docker-compose -f docker-compose.test.yml build
echo -e "${GREEN}✓${NC} 镜像构建完成"

# 启动服务
echo -e "\n${YELLOW}[5/6]${NC} 启动服务..."
docker-compose -f docker-compose.test.yml up -d

# 等待服务就绪
echo -e "\n${YELLOW}[6/6]${NC} 等待服务启动..."
echo "等待 TimescaleDB..."
sleep 10

# 检查服务状态
echo -e "\n${GREEN}✓${NC} 检查服务状态..."
docker-compose -f docker-compose.test.yml ps

# 显示访问信息
echo ""
echo "========================================================================"
echo "部署完成！"
echo "========================================================================"
echo ""
echo "服务访问地址:"
echo "  📊 Grafana:        http://localhost:3000"
echo "     用户名: admin"
echo "     密码: ${GRAFANA_PASSWORD}"
echo ""
echo "  📈 Prometheus:     http://localhost:9090"
echo "  🔍 风险监控:       http://localhost:8001/metrics"
echo "  💾 TimescaleDB:    localhost:5432"
echo "     数据库: ttquant_test"
echo "     用户名: ttquant"
echo ""
echo "常用命令:"
echo "  查看日志:   docker-compose -f docker-compose.test.yml logs -f [service]"
echo "  停止服务:   docker-compose -f docker-compose.test.yml down"
echo "  重启服务:   docker-compose -f docker-compose.test.yml restart [service]"
echo ""
echo "========================================================================"
