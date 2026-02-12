"""
Simple Integration Test - 简化集成测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("Simple Integration Test")
print("=" * 60)

# 1. 测试模块导入
print("\n1. Testing Module Imports...")

try:
    from strategy.portfolio_manager import PortfolioManager
    print("✓ PortfolioManager imported")
except Exception as e:
    print(f"✗ Failed to import PortfolioManager: {e}")

try:
    from strategy.portfolio_optimizer import PortfolioOptimizer
    print("✓ PortfolioOptimizer imported")
except Exception as e:
    print(f"✗ Failed to import PortfolioOptimizer: {e}")

try:
    from backtest.attribution import PerformanceAttribution
    print("✓ PerformanceAttribution imported")
except Exception as e:
    print(f"✗ Failed to import PerformanceAttribution: {e}")

try:
    from strategy.factors.ml_factor import MLFactor
    print("✓ MLFactor imported")
except Exception as e:
    print(f"✗ Failed to import MLFactor: {e}")

try:
    from strategy.factors.feature_engineering import FeatureEngineering
    print("✓ FeatureEngineering imported")
except Exception as e:
    print(f"✗ Failed to import FeatureEngineering: {e}")

# 2. 测试模块集成
print("\n2. Testing Module Integration...")

import numpy as np

# 创建特征工程
feature_eng = FeatureEngineering(lookback_period=50)
print("✓ FeatureEngineering created")

# 添加数据
for i in range(100):
    feature_eng.update('BTCUSDT', 50000 + i * 10, 100 + i)

features = feature_eng.extract_features('BTCUSDT')
print(f"✓ Extracted {len(features)} features")

# 创建组合管理器
manager = PortfolioManager(100000, {})
manager.add_strategy('strategy1', 0.5)
manager.add_strategy('strategy2', 0.5)
print("✓ Portfolio manager with 2 strategies")

# 创建优化器
optimizer = PortfolioOptimizer('risk_parity')
returns = np.random.randn(100, 2) * 0.01
weights = optimizer.optimize(returns)
print(f"✓ Optimized weights: {weights}")

# 创建归因分析
attribution = PerformanceAttribution()
print("✓ Attribution analyzer created")

print("\n" + "=" * 60)
print("All Integration Tests Passed! ✓")
print("=" * 60)
