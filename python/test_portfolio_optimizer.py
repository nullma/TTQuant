"""
Test Portfolio Optimizer - 测试组合优化模块
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
from strategy.portfolio_manager import PortfolioManager
from strategy.portfolio_optimizer import PortfolioOptimizer

print("=" * 60)
print("Testing Portfolio Optimization Module")
print("=" * 60)

# 1. 测试 PortfolioManager
print("\n1. Testing PortfolioManager...")

manager = PortfolioManager(total_capital=100000, config={})
print(f"✓ Created portfolio manager with capital: $100,000")

# 添加策略
manager.add_strategy('ema_cross', weight=0.4, max_position=38000)
manager.add_strategy('grid_trading', weight=0.3, max_position=28500)
manager.add_strategy('momentum', weight=0.3, max_position=28500)
print(f"✓ Added 3 strategies")

# 获取分配
alloc = manager.get_allocation('ema_cross')
print(f"✓ EMA Cross allocation: weight={alloc.weight:.2%}, capital=${alloc.capital:,.2f}")

# 获取组合摘要
summary = manager.get_portfolio_summary()
print(f"✓ Portfolio summary: {summary['num_strategies']} strategies, total=${summary['total_capital']:,.2f}")

# 2. 测试权重更新
print("\n2. Testing Weight Update...")

new_weights = {
    'ema_cross': 0.5,
    'grid_trading': 0.3,
    'momentum': 0.2
}
manager.update_weights(new_weights)
print(f"✓ Updated weights: {new_weights}")

alloc = manager.get_allocation('ema_cross')
print(f"✓ New EMA Cross allocation: weight={alloc.weight:.2%}, capital=${alloc.capital:,.2f}")

# 3. 测试 PortfolioOptimizer - 均值方差优化
print("\n3. Testing Mean-Variance Optimization...")

np.random.seed(42)
# 生成模拟收益率数据 (100 天, 3 个策略)
returns = np.random.randn(100, 3) * 0.01
returns[:, 0] += 0.0005  # 策略1有正向漂移
returns[:, 1] += 0.0003  # 策略2有小正向漂移

optimizer = PortfolioOptimizer(method='mean_variance')
optimal_weights = optimizer.optimize(returns, risk_aversion=1.0)

print(f"✓ Optimal weights (Mean-Variance):")
for i, w in enumerate(optimal_weights):
    print(f"  Strategy {i+1}: {w:.4f} ({w*100:.2f}%)")
print(f"  Sum: {optimal_weights.sum():.4f}")

# 验证权重和为1
assert abs(optimal_weights.sum() - 1.0) < 0.01, "Weights should sum to 1"
print(f"✓ Weight constraint satisfied")

# 4. 测试风险平价优化
print("\n4. Testing Risk Parity Optimization...")

optimizer = PortfolioOptimizer(method='risk_parity')
rp_weights = optimizer.optimize(returns)

print(f"✓ Optimal weights (Risk Parity):")
for i, w in enumerate(rp_weights):
    print(f"  Strategy {i+1}: {w:.4f} ({w*100:.2f}%)")
print(f"  Sum: {rp_weights.sum():.4f}")

assert abs(rp_weights.sum() - 1.0) < 0.01, "Weights should sum to 1"
print(f"✓ Weight constraint satisfied")

# 5. 测试最小方差优化
print("\n5. Testing Minimum Variance Optimization...")

optimizer = PortfolioOptimizer(method='min_variance')
mv_weights = optimizer.optimize(returns)

print(f"✓ Optimal weights (Min Variance):")
for i, w in enumerate(mv_weights):
    print(f"  Strategy {i+1}: {w:.4f} ({w*100:.2f}%)")
print(f"  Sum: {mv_weights.sum():.4f}")

assert abs(mv_weights.sum() - 1.0) < 0.01, "Weights should sum to 1"
print(f"✓ Weight constraint satisfied")

# 6. 测试最大夏普比率优化
print("\n6. Testing Maximum Sharpe Ratio Optimization...")

optimizer = PortfolioOptimizer(method='max_sharpe')
sharpe_weights = optimizer.optimize(returns, risk_free_rate=0.02)

print(f"✓ Optimal weights (Max Sharpe):")
for i, w in enumerate(sharpe_weights):
    print(f"  Strategy {i+1}: {w:.4f} ({w*100:.2f}%)")
print(f"  Sum: {sharpe_weights.sum():.4f}")

assert abs(sharpe_weights.sum() - 1.0) < 0.01, "Weights should sum to 1"
print(f"✓ Weight constraint satisfied")

# 7. 比较不同优化方法的结果
print("\n7. Comparing Optimization Methods...")

methods = {
    'Mean-Variance': optimal_weights,
    'Risk Parity': rp_weights,
    'Min Variance': mv_weights,
    'Max Sharpe': sharpe_weights
}

print(f"\n{'Method':<20} {'Strategy 1':<12} {'Strategy 2':<12} {'Strategy 3':<12}")
print("-" * 60)
for method, weights in methods.items():
    print(f"{method:<20} {weights[0]:>11.2%} {weights[1]:>11.2%} {weights[2]:>11.2%}")

# 8. 计算组合性能指标
print("\n8. Calculating Portfolio Performance...")

for method, weights in methods.items():
    portfolio_returns = (returns * weights).sum(axis=1)
    mean_return = portfolio_returns.mean() * 252  # 年化
    volatility = portfolio_returns.std() * np.sqrt(252)  # 年化
    sharpe = mean_return / volatility if volatility > 0 else 0

    print(f"\n{method}:")
    print(f"  Annual Return: {mean_return:.2%}")
    print(f"  Annual Volatility: {volatility:.2%}")
    print(f"  Sharpe Ratio: {sharpe:.4f}")

print("\n" + "=" * 60)
print("All Portfolio Optimization Tests Passed! ✓")
print("=" * 60)
