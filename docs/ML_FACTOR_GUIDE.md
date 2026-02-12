# 机器学习因子集成 - 使用指南

## 概述

TTQuant 的机器学习因子模块提供了完整的 ML 模型训练、管理和预测功能，可以将机器学习模型无缝集成到量化交易策略中。

---

## 核心组件

### 1. BaseFactor - 因子基类
所有因子的抽象基类，定义了统一的接口。

### 2. FeatureEngineering - 特征工程
从原始市场数据提取技术指标和统计特征：
- 价格特征：收益率、波动率
- 技术指标：MA、EMA、RSI、MACD、Bollinger Bands
- 统计特征：偏度、峰度、成交量比率

### 3. MLFactor - 机器学习因子
使用 scikit-learn 模型预测市场方向：
- 支持随机森林 (Random Forest)
- 支持梯度提升 (Gradient Boosting)
- 自动特征标准化
- 模型持久化和加载

### 4. ModelManager - 模型管理器
管理模型的保存、加载和版本控制。

### 5. MLStrategy - ML 策略
集成 ML 因子的完整交易策略示例。

---

## 快速开始

### 步骤 1: 训练 ML 模型

```bash
cd python
python train_ml_factor.py
```

这将：
1. 生成或加载历史数据
2. 提取技术特征
3. 创建训练标签
4. 训练随机森林模型
5. 保存模型到 `models/` 目录

**输出示例**:
```
============================================================
Training ML Factor Model
============================================================
Loading historical data...
Loaded 1000 samples
Extracting features...
Extracted 20 features
Feature names: ['price', 'volume', 'returns', 'volatility', ...]
Creating labels...
Label distribution: UP=512 (51.2%), DOWN=488 (48.8%)
Creating ML factor...
MLFactor initialized: btcusdt_ml_factor
  Model type: random_forest
  Features: ['returns', 'volatility', 'rsi_14', 'macd', 'bb_position', 'volume_ratio']
  Prediction horizon: 1
Training model...
Training completed:
  Train samples: 800
  Test samples: 200
  Train accuracy: 0.9875
  Test accuracy: 0.5650
============================================================
Model saved to: models/btcusdt_ml_factor/
============================================================
```

### 步骤 2: 使用 ML 策略

#### 方式 A: 在回测中使用

```python
from strategy.strategies.ml_strategy import MLStrategy
from backtest.engine import BacktestEngine
import yaml

# 加载配置
with open('config/ml_strategy_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 创建策略
strategy = MLStrategy(
    strategy_id='ml_strategy_btc',
    config=config
)

# 运行回测
engine = BacktestEngine(config={
    'initial_capital': 100000,
    'commission_rate': 0.0003,
    'slippage_bps': 5.0
})

engine.add_strategy(strategy)
engine.run(start_date='2024-01-01', end_date='2024-12-31')

# 查看结果
results = engine.get_results()
print(f"Total return: {results['total_return']:.2%}")
print(f"Sharpe ratio: {results['sharpe_ratio']:.4f}")
```

#### 方式 B: 在实盘中使用

```python
from strategy.strategies.ml_strategy import MLStrategy
from strategy.engine import StrategyEngine
import yaml

# 加载配置
with open('config/ml_strategy_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 创建策略引擎
engine = StrategyEngine(config={
    'zmq_md_sub': 'tcp://localhost:5555',
    'zmq_order_push': 'tcp://localhost:5558',
    'zmq_trade_sub': 'tcp://localhost:5559'
})

# 添加 ML 策略
strategy = MLStrategy(
    strategy_id='ml_strategy_btc',
    config=config
)
engine.add_strategy(strategy)

# 启动引擎
engine.run()
```

### 步骤 3: 监控和评估

查看模型信息：
```python
from strategy.factors.model_manager import ModelManager

manager = ModelManager(model_dir='models')

# 列出所有模型
models = manager.list_models()
print(f"Available models: {models}")

# 查看模型详情
info = manager.get_model_info('btcusdt_ml_factor')
print(f"Model info: {info}")
```

---

## 高级用法

### 自定义特征

修改 `config/ml_strategy_config.yaml`:

```yaml
feature_names:
  - "returns"
  - "volatility"
  - "rsi_14"
  - "macd"
  - "macd_histogram"
  - "bb_position"
  - "bb_width"
  - "volume_ratio"
  - "ema_5"
  - "ema_20"
```

### 使用梯度提升模型

```yaml
model_type: "gradient_boosting"
```

### 调整预测周期

```yaml
prediction_horizon: 5  # 预测未来 5 个周期
```

### 自定义模型参数

修改 `ml_factor.py` 中的 `_create_model()` 方法：

```python
def _create_model(self):
    if self.model_type == 'random_forest':
        return RandomForestClassifier(
            n_estimators=200,  # 增加树的数量
            max_depth=15,      # 增加深度
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
```

---

## 从数据库加载历史数据

实际使用时，应从 TimescaleDB 加载历史数据：

```python
import psycopg2
import numpy as np

def load_historical_data(symbol: str, days: int = 30):
    """从数据库加载历史数据"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ttquant_trading',
        user='ttquant',
        password='ttquant_password'
    )

    cursor = conn.cursor()
    query = """
        SELECT time, last_price, volume
        FROM market_data
        WHERE symbol = %s
          AND time >= NOW() - INTERVAL '%s days'
        ORDER BY time
    """
    cursor.execute(query, (symbol, days))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    times = [row[0] for row in results]
    prices = np.array([row[1] for row in results])
    volumes = np.array([row[2] for row in results])

    return times, prices, volumes

# 使用
times, prices, volumes = load_historical_data('BTCUSDT', days=30)
```

---

## 性能优化建议

### 1. 特征选择
- 使用特征重要性分析选择最有效的特征
- 避免使用高度相关的特征

```python
# 查看特征重要性
importances = ml_factor.model.feature_importances_
for name, importance in zip(ml_config['feature_names'], importances):
    print(f"{name}: {importance:.4f}")
```

### 2. 模型调优
- 使用交叉验证选择最佳参数
- 定期重新训练模型（如每周）

### 3. 在线学习
- 实现增量学习，定期更新模型
- 监控模型性能，及时发现模型退化

---

## 常见问题

### Q1: 模型准确率很高但实盘效果差？
**A**: 可能存在过拟合。建议：
- 减少模型复杂度（降低 max_depth）
- 增加训练数据量
- 使用更严格的交叉验证
- 添加正则化

### Q2: 如何处理类别不平衡？
**A**: 使用类别权重：

```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    class_weight='balanced',  # 自动平衡类别权重
    ...
)
```

### Q3: 预测延迟太高？
**A**: 优化建议：
- 减少特征数量
- 使用更简单的模型
- 预计算特征
- 使用模型量化

---

## 依赖包

确保安装以下依赖：

```bash
pip install scikit-learn>=1.3.0 numpy>=1.24.0 pyyaml>=6.0
```

---

## 文件结构

```
python/
├── strategy/
│   ├── factors/
│   │   ├── __init__.py
│   │   ├── base_factor.py          # 因子基类
│   │   ├── feature_engineering.py  # 特征工程
│   │   ├── ml_factor.py            # ML 因子
│   │   └── model_manager.py        # 模型管理
│   └── strategies/
│       └── ml_strategy.py          # ML 策略
├── train_ml_factor.py              # 训练脚本
└── models/                         # 模型保存目录
    └── btcusdt_ml_factor/
        ├── model.pkl               # 模型文件
        └── metadata.json           # 元数据

config/
└── ml_strategy_config.yaml         # 策略配置
```

---

## 下一步

1. 使用真实历史数据训练模型
2. 在回测中验证策略效果
3. 优化特征和模型参数
4. 部署到生产环境
5. 监控模型性能并定期重训练

---

**注意**: 机器学习模型的效果高度依赖于数据质量和特征工程。建议在充分回测验证后再用于实盘交易。
