#!/bin/bash
# 服务器部署脚本 - 获取真实数据并训练模型
# 适用于 Ubuntu 系统

set -e

echo "========================================================================"
echo "TTQuant 服务器部署 - 真实数据获取和模型训练"
echo "========================================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查操作系统
echo -e "\n${YELLOW}[1/6]${NC} 检查系统环境..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "${GREEN}✓${NC} 操作系统: $NAME $VERSION"
else
    echo -e "${YELLOW}⚠${NC}  无法检测操作系统版本"
fi
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi

# 检查 Python 环境
echo -e "\n${YELLOW}[2/6]${NC} 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    echo "在 Ubuntu 上安装: sudo apt-get update && sudo apt-get install -y python3 python3-pip"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION}"

# 安装系统依赖（Ubuntu）
echo -e "\n${YELLOW}[3/6]${NC} 检查系统依赖..."
if command -v apt-get &> /dev/null; then
    echo "检测到 Ubuntu/Debian 系统"
    if ! dpkg -l | grep -q python3-dev; then
        echo "安装 Python 开发包..."
        sudo apt-get update
        sudo apt-get install -y python3-dev python3-pip build-essential libpq-dev
    fi
    echo -e "${GREEN}✓${NC} 系统依赖已安装"
fi

# 安装 Python 依赖
echo -e "\n${YELLOW}[4/6]${NC} 安装 Python 依赖..."
cd python
pip3 install -r requirements.txt -q
echo -e "${GREEN}✓${NC} 依赖安装完成"

# 获取真实历史数据
echo -e "\n${YELLOW}[5/6]${NC} 从 OKX 获取真实历史数据..."
echo "交易对: BTC/USDT"
echo "周期: 1小时"
echo "天数: 365天"
echo ""

python3 data/fetch_historical_data.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 数据获取成功"
else
    echo -e "${RED}❌ 数据获取失败${NC}"
    echo "尝试使用模拟数据..."
    python3 data/generate_simulated_data.py
fi

# 训练 ML 模型
echo -e "\n${YELLOW}[6/6]${NC} 训练 ML 模型..."
python3 train_ml_with_real_data.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 模型训练完成"
else
    echo -e "${RED}❌ 模型训练失败${NC}"
    exit 1
fi

# 验证模型文件
echo -e "\n${YELLOW}[验证]${NC} 验证模型文件..."
if [ -f "models/btcusdt_rf_real/model.pkl" ]; then
    echo -e "${GREEN}✓${NC} Random Forest 模型已保存"
fi

if [ -f "models/btcusdt_gb_real/model.pkl" ]; then
    echo -e "${GREEN}✓${NC} Gradient Boosting 模型已保存"
fi

# 显示模型信息
echo ""
echo "========================================================================"
echo "部署完成！"
echo "========================================================================"
echo ""
echo "已完成:"
echo "  ✓ 获取真实历史数据"
echo "  ✓ 训练 ML 模型"
echo "  ✓ 保存模型文件"
echo ""
echo "模型位置:"
echo "  models/btcusdt_rf_real/"
echo "  models/btcusdt_gb_real/"
echo ""
echo "下一步:"
echo "  1. 查看模型性能: cat models/btcusdt_rf_real/metadata.json"
echo "  2. 运行回测: python backtest_with_ml.py"
echo "  3. 启动纸面交易: docker-compose -f docker-compose.test.yml up -d"
echo ""
echo "========================================================================"
