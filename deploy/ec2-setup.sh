#!/bin/bash
# EC2 环境初始化脚本
# 用途：在全新的 Ubuntu EC2 实例上安装所有必要的依赖

set -e  # 遇到错误立即退出

echo "=========================================="
echo "TTQuant EC2 环境初始化"
echo "=========================================="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then
    echo "❌ 请不要使用 root 用户运行此脚本"
    echo "   使用普通用户（如 ubuntu）运行"
    exit 1
fi

# 1. 更新系统
echo "📦 [1/5] 更新系统包..."
sudo apt update
sudo apt upgrade -y

# 2. 安装 Docker
echo "🐳 [2/5] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh

    # 添加当前用户到 docker 组
    sudo usermod -aG docker $USER
    echo "✅ Docker 安装完成"
    echo "⚠️  需要重新登录以使 docker 组权限生效"
else
    echo "✅ Docker 已安装: $(docker --version)"
fi

# 3. 安装 Docker Compose
echo "🔧 [3/5] 安装 Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    sudo apt install -y docker-compose-plugin
    echo "✅ Docker Compose 安装完成"
else
    echo "✅ Docker Compose 已安装: $(docker compose version)"
fi

# 4. 安装 Git
echo "📚 [4/5] 安装 Git..."
if ! command -v git &> /dev/null; then
    sudo apt install -y git
    echo "✅ Git 安装完成"
else
    echo "✅ Git 已安装: $(git --version)"
fi

# 5. 安装其他工具
echo "🛠️  [5/5] 安装其他工具..."
sudo apt install -y \
    curl \
    wget \
    vim \
    htop \
    net-tools \
    ca-certificates

echo ""
echo "=========================================="
echo "✅ 环境初始化完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 如果是首次安装 Docker，请重新登录以使权限生效："
echo "   exit"
echo "   ssh ubuntu@<your-ec2-ip>"
echo ""
echo "2. 克隆代码仓库："
echo "   git clone <your-repo-url> TTQuant"
echo "   cd TTQuant"
echo ""
echo "3. 运行部署脚本："
echo "   bash deploy/ec2-deploy.sh"
echo ""
