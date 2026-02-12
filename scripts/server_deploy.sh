#!/bin/bash
# 服务器部署脚本 - 获取真实数据并训练模型

set -e

echo "========================================================================"
echo "TTQuant 服务器部署 - 真实数据获取和模型训练"
echo "========================================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 Python 环境
echo -e "\n${YELLOW}[1/5]${NC} 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION}"

# 安装依赖
echo -e "\n${YELLOW}[2/5]${NC} 安装 Python 依赖..."
cd python
pip3 install -r requirements.txt -q
echo -e "${GREEN}✓${NC} 依赖安装完成"

# 获取真实历史数据
echo -e "\n${YELLOW}[3/5]${NC} 从 OKX 获取真实历史数据..."
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
echo -e "\n${YELLOW}[4/5]${NC} 训练 ML 模型..."
python3 train_ml_with_real_data.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 模型训练完成"
else
    echo -e "${RED}❌ 模型训练失败${NC}"
    exit 1
fi

# 验证模型文件
echo -e "\n${YELLOW}[5/5]${NC} 验证模型文件..."
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
