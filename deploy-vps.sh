#!/bin/bash
# =========================================================
# TTQuant 生产环境部署脚本（搬瓦工/VPS）
# 用法: bash deploy-vps.sh
# =========================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  TTQuant 生产环境部署${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# ----------------------------------------------------------
# 1. 检查依赖
# ----------------------------------------------------------
echo -e "${YELLOW}[1/7] 检查依赖...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "安装命令: curl -fsSL https://get.docker.com | sh"
    echo "然后运行: sudo usermod -aG docker \$USER"
    exit 1
fi

if ! docker compose version &> /dev/null 2>&1; then
    echo -e "${RED}错误: Docker Compose V2 未安装${NC}"
    echo "Docker 20.10+ 自带 compose 插件，请更新 Docker"
    exit 1
fi

echo -e "${GREEN}  ✓ Docker $(docker --version | cut -d' ' -f3)${NC}"
echo -e "${GREEN}  ✓ Docker Compose $(docker compose version --short)${NC}"

# ----------------------------------------------------------
# 2. 检查 .env 文件
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[2/7] 检查环境配置...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        echo -e "${YELLOW}  未找到 .env，从 .env.production 复制模板...${NC}"
        cp .env.production .env
        echo -e "${RED}  ⚠ 请编辑 .env 文件，填入真实的 API 密钥和密码！${NC}"
        echo -e "${RED}  运行: nano .env${NC}"
        exit 1
    else
        echo -e "${RED}错误: 未找到 .env 或 .env.production 文件${NC}"
        exit 1
    fi
fi

# 检查是否还有未修改的 CHANGE_ME 值
if grep -q "CHANGE_ME" .env; then
    echo -e "${RED}  ⚠ .env 文件中仍有未修改的 CHANGE_ME 值！${NC}"
    echo -e "${RED}  请编辑 .env 并替换所有 CHANGE_ME 值: nano .env${NC}"
    echo ""
    grep "CHANGE_ME" .env
    exit 1
fi

echo -e "${GREEN}  ✓ .env 配置文件就绪${NC}"

# ----------------------------------------------------------
# 3. 使用生产配置
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[3/7] 应用生产配置...${NC}"

# 使用生产风控配置
if [ -f config/risk.prod.toml ]; then
    cp config/risk.prod.toml config/risk.toml
    echo -e "${GREEN}  ✓ 已应用生产风控配置 (risk.prod.toml)${NC}"
fi

# 使用生产行情配置
if [ -f config/markets.prod.toml ]; then
    cp config/markets.prod.toml config/markets.toml
    echo -e "${GREEN}  ✓ 已应用生产行情配置 (markets.prod.toml)${NC}"
fi

# ----------------------------------------------------------
# 4. 构建镜像
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[4/7] 构建 Docker 镜像（首次约 10-15 分钟）...${NC}"
docker compose -f docker/docker-compose.prod.yml build --parallel
echo -e "${GREEN}  ✓ 镜像构建完成${NC}"

# ----------------------------------------------------------
# 5. 启动数据库
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[5/7] 启动数据库...${NC}"
docker compose -f docker/docker-compose.prod.yml up -d timescaledb
echo "  等待数据库健康检查..."

# 等待数据库就绪（最多 60 秒）
for i in $(seq 1 60); do
    if docker compose -f docker/docker-compose.prod.yml exec -T timescaledb pg_isready -U ttquant > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ 数据库就绪 (${i}s)${NC}"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo -e "${RED}  ✗ 数据库启动超时！${NC}"
        docker compose -f docker/docker-compose.prod.yml logs timescaledb
        exit 1
    fi
    sleep 1
done

# ----------------------------------------------------------
# 6. 启动所有服务
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[6/7] 启动所有服务...${NC}"
docker compose -f docker/docker-compose.prod.yml up -d
echo "  等待服务启动..."
sleep 10
echo -e "${GREEN}  ✓ 所有服务已启动${NC}"

# ----------------------------------------------------------
# 7. 验证状态
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[7/7] 验证服务状态...${NC}"
echo ""
docker compose -f docker/docker-compose.prod.yml ps
echo ""

# 健康检查
echo -e "${BLUE}  健康检查:${NC}"
check_health() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ $name: UP${NC}"
    else
        echo -e "  ${YELLOW}⚠ $name: STARTING${NC}"
    fi
}

check_health "MD-Binance  " "http://127.0.0.1:8080/health"
check_health "MD-OKX      " "http://127.0.0.1:8082/health"
check_health "GW-Binance  " "http://127.0.0.1:8081/health"
check_health "GW-OKX      " "http://127.0.0.1:8083/health"
check_health "Prometheus  " "http://127.0.0.1:9090/-/healthy"
check_health "Grafana     " "http://127.0.0.1:3000/api/health"

# ----------------------------------------------------------
# 完成信息
# ----------------------------------------------------------
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  ✅ TTQuant 生产环境部署完成！${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  ${BLUE}服务端口:${NC}"
echo "  ┌─────────────────────────────────────────────┐"
echo "  │ Grafana 面板:   http://<VPS-IP>:3000        │"
echo "  │ Binance 行情:   tcp://<VPS-IP>:5555         │"
echo "  │ OKX 行情:       tcp://<VPS-IP>:5558         │"
echo "  │ Binance 网关:   tcp://<VPS-IP>:5556 (PULL)  │"
echo "  │                 tcp://<VPS-IP>:5557 (PUB)   │"
echo "  │ OKX 网关:       tcp://<VPS-IP>:5559 (PULL)  │"
echo "  │                 tcp://<VPS-IP>:5560 (PUB)   │"
echo "  └─────────────────────────────────────────────┘"
echo ""
echo -e "  ${BLUE}常用命令:${NC}"
echo "  查看日志:   docker compose -f docker/docker-compose.prod.yml logs -f"
echo "  查看状态:   docker compose -f docker/docker-compose.prod.yml ps"
echo "  停止服务:   docker compose -f docker/docker-compose.prod.yml down"
echo "  重启服务:   docker compose -f docker/docker-compose.prod.yml restart"
echo "  备份数据:   bash scripts/backup.sh"
echo ""
echo -e "  ${YELLOW}⚠ 首次部署后建议设置 crontab 自动备份:${NC}"
echo '  echo "0 3 * * * cd '"$SCRIPT_DIR"' && bash scripts/backup.sh" | crontab -'
echo ""
