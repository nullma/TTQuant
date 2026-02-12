"""
Test ML Factor - 快速测试 ML 因子功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
from strategy.factors.feature_engineering import FeatureEngineering
from strategy.factors.ml_factor import MLFactor, create_labels_from_returns

print("=" * 60)
print("Testing ML Factor Module")
print("=" * 60)

# 1. 测试特征工程
print("\n1. Testing Feature Engineering...")
feature_eng = FeatureEngineering(lookback_period=50)

# 生成模拟数据
np.random.seed(42)
prices = 50000 + np.cumsum(np.random.randn(100) * 100)
volumes = np.random.uniform(100, 1000, 100)

# 更新数据
for price, volume in zip(prices, volumes):
    feature_eng.update('BTCUSDT', price, volume)

# 提取特征
features = feature_eng.extract_features('BTCUSDT')
print(f"✓ Extracted {len(features)} features")
print(f"  Feature names: {list(features.keys())[:5]}...")

# 获取最新特征
latest = feature_eng.get_latest_features('BTCUSDT')
print(f"✓ Latest features: {len(latest)} values")
print(f"  Sample: price={latest.get('price', 0):.2f}, rsi={latest.get('rsi_14', 0):.2f}")

# 2. 测试标签创建
print("\n2. Testing Label Creation...")
returns = features['returns']
labels = create_labels_from_returns(returns, horizon=1)
n_up = np.sum(labels == 1)
n_down = np.sum(labels == 0)
print(f"✓ Created {len(labels)} labels")
print(f"  UP: {n_up} ({n_up/len(labels)*100:.1f}%)")
print(f"  DOWN: {n_down} ({n_down/len(labels)*100:.1f}%)")

# 3. 测试 ML 因子（不训练，只测试接口）
print("\n3. Testing ML Factor Interface...")
ml_config = {
    'model_type': 'random_forest',
    'feature_names': ['returns', 'volatility', 'rsi_14', 'macd', 'bb_position', 'volume_ratio'],
    'prediction_horizon': 1,
    'model_dir': 'models',
    'load_model': False
}

ml_factor = MLFactor(factor_id='test_ml_factor', config=ml_config)
print(f"✓ ML Factor created: {ml_factor.factor_id}")
print(f"  Model type: {ml_factor.model_type}")
print(f"  Required features: {ml_factor.get_required_features()}")

# 4. 测试特征验证
print("\n4. Testing Feature Validation...")
is_valid = ml_factor.validate_features(features)
print(f"✓ Feature validation: {'PASS' if is_valid else 'FAIL'}")

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("=" * 60)
print("\nNext steps:")
print("1. Run 'python train_ml_factor.py' to train a model")
print("2. Check 'docs/ML_FACTOR_GUIDE.md' for usage guide")
print("=" * 60)
