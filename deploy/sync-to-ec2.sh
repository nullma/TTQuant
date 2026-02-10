#!/bin/bash
# 本地到 EC2 同步脚本
# 用途：从本地 Windows 推送代码到 EC2 并自动部署

# 配置（请修改为您的实际值）
EC2_IP="43.198.18.252"
EC2_USER="ubuntu"
EC2_KEY="/c/Users/11915/Desktop/蓝洞科技/mawentao.pem"
EC2_PATH="/home/ubuntu/TTQuant"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "TTQuant 本地到 EC2 同步"
echo "=========================================="
echo ""

# 检查配置
if [ "$EC2_IP" = "your-ec2-ip" ]; then
    echo -e "${RED}❌ 错误：请先配置 EC2_IP${NC}"
    echo "   编辑此脚本，修改 EC2_IP 为您的 EC2 实例 IP"
    exit 1
fi

if [ "$EC2_KEY" = "path/to/your-key.pem" ]; then
    echo -e "${RED}❌ 错误：请先配置 EC2_KEY${NC}"
    echo "   编辑此脚本，修改 EC2_KEY 为您的 SSH 密钥路径"
    exit 1
fi

# 检查是否在项目根目录
if [ ! -f "docker/docker-compose.yml" ]; then
    echo -e "${RED}❌ 错误：请在 TTQuant 项目根目录下运行此脚本${NC}"
    exit 1
fi

# 1. 检查本地 Git 状态
echo -e "${YELLOW}📋 [1/5] 检查本地 Git 状态...${NC}"
if [ -d ".git" ]; then
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}⚠️  有未提交的更改${NC}"
        echo ""
        git status --short
        echo ""
        read -p "是否继续同步？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "已取消"
            exit 0
        fi
    else
        echo -e "${GREEN}✅ 工作区干净${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  不是 Git 仓库${NC}"
fi
echo ""

# 2. 推送到 Git 仓库（如果有）
echo -e "${YELLOW}📤 [2/5] 推送到 Git 仓库...${NC}"
if [ -d ".git" ]; then
    CURRENT_BRANCH=$(git branch --show-current)
    echo "当前分支: $CURRENT_BRANCH"

    read -p "是否推送到远程仓库？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin $CURRENT_BRANCH
        echo -e "${GREEN}✅ 已推送到远程仓库${NC}"
    else
        echo -e "${YELLOW}⏭️  跳过推送${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  跳过（不是 Git 仓库）${NC}"
fi
echo ""

# 3. 连接到 EC2 并拉取代码
echo -e "${YELLOW}📥 [3/5] 在 EC2 上拉取代码...${NC}"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_IP" << 'EOF'
cd TTQuant
if [ -d ".git" ]; then
    echo "拉取最新代码..."
    git pull
    echo "✅ 代码已更新"
else
    echo "⚠️  不是 Git 仓库，跳过"
fi
EOF
echo ""

# 4. 在 EC2 上重新部署
echo -e "${YELLOW}🚀 [4/5] 在 EC2 上重新部署...${NC}"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_IP" << 'EOF'
cd TTQuant
bash deploy/ec2-deploy.sh
EOF
echo ""

# 5. 验证部署
echo -e "${YELLOW}🔍 [5/5] 验证部署...${NC}"
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_IP" << 'EOF'
cd TTQuant
bash deploy/verify-okx.sh
EOF
echo ""

echo "=========================================="
echo -e "${GREEN}✅ 同步完成！${NC}"
echo "=========================================="
echo ""
echo "访问服务："
echo "  Grafana:    http://$EC2_IP:3000"
echo "  Prometheus: http://$EC2_IP:9090"
echo ""
