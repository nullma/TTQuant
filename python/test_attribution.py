"""
Test Attribution - 测试性能归因分析模块
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from backtest.attribution import PerformanceAttribution

print("=" * 60)
print("Testing Performance Attribution Module")
print("=" * 60)

# 生成模拟数据
np.random.seed(42)

# 1. 生成权益曲线
print("\n1. Generating Test Data...")

start_date = datetime(2024, 1, 1)
n_days = 100
dates = [start_date + timedelta(days=i) for i in range(n_days)]

# 模拟策略权益曲线
initial_equity = 100000
returns = np.random.randn(n_days) * 0.02 + 0.001  # 日收益率，有正向漂移
equity_values = initial_equity * np.cumprod(1 + returns)

equity_curve = [
    {'timestamp': date.isoformat(), 'equity': equity}
    for date, equity in zip(dates, equity_values)
]

print(f"✓ Generated equity curve: {len(equity_curve)} days")
print(f"  Initial equity: ${initial_equity:,.2f}")
print(f"  Final equity: ${equity_values[-1]:,.2f}")
print(f"  Total return: {(equity_values[-1]/initial_equity - 1)*100:.2f}%")

# 2. 生成基准收益率
print("\n2. Generating Benchmark Returns...")

benchmark_returns = pd.Series(
    np.random.randn(n_days) * 0.015 + 0.0005,  # 基准收益率
    index=pd.DatetimeIndex(dates)
)

print(f"✓ Generated benchmark returns: {len(benchmark_returns)} days")
print(f"  Mean daily return: {benchmark_returns.mean():.4%}")
print(f"  Volatility: {benchmark_returns.std():.4%}")

# 3. 创建归因分析器
print("\n3. Testing PerformanceAttribution...")

attribution = PerformanceAttribution()
attribution.set_equity_curve(equity_curve)
attribution.set_benchmark(benchmark_returns)

print(f"✓ Attribution analyzer created")

# 4. 测试 Alpha-Beta 分解
print("\n4. Testing Alpha-Beta Decomposition...")

alpha_beta = attribution.alpha_beta_decomposition(risk_free_rate=0.02)

if alpha_beta:
    print(f"✓ Alpha-Beta decomposition completed:")
    print(f"  Alpha (annual): {alpha_beta.alpha:.4f} ({alpha_beta.alpha*100:.2f}%)")
    print(f"  Beta: {alpha_beta.beta:.4f}")
    print(f"  R²: {alpha_beta.r_squared:.4f}")
    print(f"  Residual: {alpha_beta.residual:.4f}")
    print(f"  Market contribution: {alpha_beta.factor_contributions.get('market', 0):.4f}")
else:
    print("✗ Alpha-Beta decomposition failed")

# 5. 测试因子归因
print("\n5. Testing Factor Attribution...")

factor_exposures = {
    'momentum': 0.5,
    'value': 0.3,
    'size': 0.2
}

factor_returns = {
    'momentum': 0.08,
    'value': 0.05,
    'size': 0.03
}

factor_attr = attribution.factor_attribution(factor_exposures, factor_returns)

print(f"✓ Factor attribution completed:")
for attr in factor_attr:
    print(f"  {attr.factor_name}: exposure={attr.exposure:.2f}, "
          f"return={attr.factor_return:.2%}, contribution={attr.contribution:.4f}")

# 6. 测试时间段归因
print("\n6. Testing Period Attribution...")

# 创建带时间索引的权益曲线
df = pd.DataFrame(equity_curve)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 生成模拟交易
class MockTrade:
    def __init__(self, trade_time):
        self.trade_time = trade_time

trades = [MockTrade(int(date.timestamp() * 1e9)) for date in dates[::10]]  # 每10天一笔交易
attribution.set_trades(trades)

monthly_attr = attribution.period_attribution('monthly')

print(f"✓ Period attribution completed: {len(monthly_attr)} periods")
for period in monthly_attr[:3]:  # 显示前3个月
    print(f"  {period.period}: return={period.return_pct:.2%}, "
          f"contribution={period.contribution_to_total:.2%}, "
          f"sharpe={period.sharpe_ratio:.4f}, "
          f"trades={period.trade_count}")

# 7. 测试成本归因
print("\n7. Testing Cost Attribution...")

total_return = (equity_values[-1] - initial_equity)
commission_cost = 150.0
slippage_cost = 80.0
market_impact_cost = 30.0

cost_attr = attribution.cost_attribution(
    total_return=total_return,
    commission_cost=commission_cost,
    slippage_cost=slippage_cost,
    market_impact_cost=market_impact_cost
)

print(f"✓ Cost attribution completed:")
print(f"  Total cost: ${cost_attr.total_cost:.2f}")
print(f"  Commission: ${cost_attr.commission_cost:.2f}")
print(f"  Slippage: ${cost_attr.slippage_cost:.2f}")
print(f"  Market impact: ${cost_attr.market_impact_cost:.2f}")
print(f"  Cost as % of return: {cost_attr.cost_as_pct_of_return:.2f}%")
print(f"  Cost per trade: ${cost_attr.cost_per_trade:.2f}")

# 8. 测试完整报告生成
print("\n8. Testing Full Attribution Report...")

report = attribution.generate_attribution_report()

print(f"✓ Full report generated:")
print(f"  Sections: {list(report.keys())}")

if 'alpha_beta' in report:
    print(f"  Alpha-Beta section: ✓")
if 'monthly_attribution' in report:
    print(f"  Monthly attribution: {len(report['monthly_attribution'])} periods")

# 9. 性能验证
print("\n9. Performance Validation...")

# 验证 Alpha-Beta 分解的合理性
if alpha_beta:
    assert -1 <= alpha_beta.beta <= 3, "Beta should be reasonable"
    assert 0 <= alpha_beta.r_squared <= 1, "R² should be between 0 and 1"
    print(f"✓ Alpha-Beta metrics are reasonable")

# 验证因子贡献总和
total_contribution = sum(attr.contribution for attr in factor_attr)
expected_contribution = sum(factor_exposures[f] * factor_returns[f] for f in factor_exposures)
assert abs(total_contribution - expected_contribution) < 0.001, "Factor contributions should match"
print(f"✓ Factor contributions validated")

# 验证成本归因
assert cost_attr.total_cost == commission_cost + slippage_cost + market_impact_cost
print(f"✓ Cost attribution validated")

print("\n" + "=" * 60)
print("All Attribution Tests Passed! ✓")
print("=" * 60)
