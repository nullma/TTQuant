"""
策略开发和回测示例

演示如何使用 TTQuant 系统进行策略开发、回测和性能分析
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 导入策略和回测模块
from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.strategies.grid_trading import GridTradingStrategy
from strategy.strategies.momentum import MomentumStrategy
from backtest.engine import BacktestEngine
from backtest.analytics import PerformanceAnalytics
from backtest.attribution import PerformanceAttribution
from strategy.portfolio_manager import PortfolioManager
from strategy.portfolio_optimizer import PortfolioOptimizer

print("=" * 70)
print("TTQuant 策略开发和回测示例")
print("=" * 70)

# 1. 生成模拟历史数据
print("\n1. 生成模拟历史数据...")

np.random.seed(42)
n_days = 252  # 一年交易日
start_date = datetime(2024, 1, 1)

# 生成价格数据（随机游走 + 趋势）
returns = np.random.randn(n_days) * 0.02 + 0.0005  # 日收益率，有正向漂移
prices = 50000 * np.cumprod(1 + returns)
volumes = np.random.uniform(100, 1000, n_days)

dates = [start_date + timedelta(days=i) for i in range(n_days)]

market_data = pd.DataFrame({
    'timestamp': dates,
    'price': prices,
    'volume': volumes
})

print(f"✓ 生成 {n_days} 天历史数据")
print(f"  起始价格: ${prices[0]:,.2f}")
print(f"  结束价格: ${prices[-1]:,.2f}")
print(f"  总收益率: {(prices[-1]/prices[0] - 1)*100:.2f}%")

# 2. 配置策略参数
print("\n2. 配置策略参数...")

strategies_config = {
    'ema_cross': {
        'strategy_id': 'ema_cross_btc',
        'symbol': 'BTCUSDT',
        'fast_period': 12,
        'slow_period': 26,
        'position_size': 0.1,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04
    },
    'grid_trading': {
        'strategy_id': 'grid_btc',
        'symbol': 'BTCUSDT',
        'grid_levels': 10,
        'grid_spacing_pct': 0.01,
        'position_size': 0.05
    },
    'momentum': {
        'strategy_id': 'momentum_btc',
        'symbol': 'BTCUSDT',
        'lookback_period': 20,
        'position_size': 0.1,
        'threshold': 0.02
    }
}

print("✓ 配置了 3 个策略:")
for name in strategies_config.keys():
    print(f"  - {name}")

# 3. 创建回测引擎
print("\n3. 创建回测引擎...")

backtest_config = {
    'initial_capital': 100000,
    'commission_rate': 0.0003,  # 0.03%
    'slippage_bps': 5.0  # 5个基点
}

engine = BacktestEngine(config=backtest_config)
print(f"✓ 回测引擎创建完成")
print(f"  初始资金: ${backtest_config['initial_capital']:,.2f}")
print(f"  手续费率: {backtest_config['commission_rate']*100:.3f}%")
print(f"  滑点: {backtest_config['slippage_bps']} bps")

# 4. 运行单策略回测
print("\n4. 运行单策略回测...")

print("\n4.1 EMA 交叉策略回测")
ema_strategy = EMACrossStrategy(
    strategy_id=strategies_config['ema_cross']['strategy_id'],
    config=strategies_config['ema_cross']
)

# 模拟回测（简化版本）
initial_equity = backtest_config['initial_capital']
equity_curve = [initial_equity]
position = 0
entry_price = 0

for i in range(1, len(prices)):
    current_price = prices[i]

    # 简单的 EMA 交叉逻辑
    if i > 26:
        fast_ema = np.mean(prices[i-12:i])
        slow_ema = np.mean(prices[i-26:i])

        # 金叉买入
        if fast_ema > slow_ema and position == 0:
            position = 0.1
            entry_price = current_price
        # 死叉卖出
        elif fast_ema < slow_ema and position > 0:
            pnl = (current_price - entry_price) * position * initial_equity / entry_price
            equity_curve.append(equity_curve[-1] + pnl)
            position = 0
        else:
            equity_curve.append(equity_curve[-1])
    else:
        equity_curve.append(equity_curve[-1])

# 计算性能指标
final_equity = equity_curve[-1]
total_return = (final_equity - initial_equity) / initial_equity
equity_returns = np.diff(equity_curve) / equity_curve[:-1]
sharpe_ratio = np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(252) if np.std(equity_returns) > 0 else 0

# 计算最大回撤
cummax = np.maximum.accumulate(equity_curve)
drawdown = (np.array(equity_curve) - cummax) / cummax
max_drawdown = np.min(drawdown)

print(f"✓ EMA 交叉策略回测完成:")
print(f"  最终权益: ${final_equity:,.2f}")
print(f"  总收益率: {total_return*100:.2f}%")
print(f"  夏普比率: {sharpe_ratio:.4f}")
print(f"  最大回撤: {max_drawdown*100:.2f}%")

# 5. 多策略组合优化
print("\n5. 多策略组合优化...")

# 生成3个策略的模拟收益率
strategy_returns = np.random.randn(252, 3) * 0.01
strategy_returns[:, 0] += 0.0005  # EMA 策略
strategy_returns[:, 1] += 0.0003  # Grid 策略
strategy_returns[:, 2] += 0.0004  # Momentum 策略

# 创建组合管理器
portfolio_manager = PortfolioManager(
    total_capital=100000,
    config={}
)

portfolio_manager.add_strategy('ema_cross', weight=0.33)
portfolio_manager.add_strategy('grid_trading', weight=0.33)
portfolio_manager.add_strategy('momentum', weight=0.34)

print("✓ 初始组合权重:")
for sid, alloc in portfolio_manager.allocations.items():
    print(f"  {sid}: {alloc.weight*100:.1f}% (${alloc.capital:,.2f})")

# 使用风险平价优化
optimizer = PortfolioOptimizer(method='risk_parity')
optimal_weights = optimizer.optimize(strategy_returns)

print("\n✓ 风险平价优化后权重:")
strategy_names = ['ema_cross', 'grid_trading', 'momentum']
for i, (name, weight) in enumerate(zip(strategy_names, optimal_weights)):
    print(f"  {name}: {weight*100:.1f}%")

# 更新权重
new_weights = {name: weight for name, weight in zip(strategy_names, optimal_weights)}
portfolio_manager.update_weights(new_weights)

# 6. 性能归因分析
print("\n6. 性能归因分析...")

attribution = PerformanceAttribution()

# 设置权益曲线
equity_data = [
    {'timestamp': date.isoformat(), 'equity': eq}
    for date, eq in zip(dates[:len(equity_curve)], equity_curve)
]
attribution.set_equity_curve(equity_data)

# 设置基准（市场收益）
benchmark_returns = pd.Series(
    returns[:len(equity_curve)-1],
    index=pd.DatetimeIndex(dates[:len(equity_curve)-1])
)
attribution.set_benchmark(benchmark_returns)

# Alpha-Beta 分解
alpha_beta = attribution.alpha_beta_decomposition(risk_free_rate=0.02)

if alpha_beta:
    print("✓ Alpha-Beta 分解:")
    print(f"  Alpha (年化): {alpha_beta.alpha*100:.2f}%")
    print(f"  Beta: {alpha_beta.beta:.4f}")
    print(f"  R²: {alpha_beta.r_squared:.4f}")

# 因子归因
factor_exposures = {'momentum': 0.4, 'mean_reversion': 0.3, 'volatility': 0.3}
factor_returns = {'momentum': 0.08, 'mean_reversion': 0.05, 'volatility': 0.03}

factor_attr = attribution.factor_attribution(factor_exposures, factor_returns)

print("\n✓ 因子归因:")
for attr in factor_attr:
    print(f"  {attr.factor_name}: 贡献 {attr.contribution*100:.2f}%")

# 7. 生成完整报告
print("\n7. 生成完整报告...")

report = {
    'backtest_config': backtest_config,
    'strategies': list(strategies_config.keys()),
    'performance': {
        'initial_capital': initial_equity,
        'final_equity': final_equity,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown
    },
    'portfolio_optimization': {
        'method': 'risk_parity',
        'optimal_weights': {name: float(w) for name, w in zip(strategy_names, optimal_weights)}
    },
    'attribution': {
        'alpha': alpha_beta.alpha if alpha_beta else None,
        'beta': alpha_beta.beta if alpha_beta else None,
        'factor_contributions': {attr.factor_name: attr.contribution for attr in factor_attr}
    }
}

print("✓ 报告生成完成")
print("\n" + "=" * 70)
print("回测总结")
print("=" * 70)
print(f"\n策略数量: {len(strategies_config)}")
print(f"回测周期: {n_days} 天")
print(f"初始资金: ${initial_equity:,.2f}")
print(f"最终权益: ${final_equity:,.2f}")
print(f"总收益率: {total_return*100:.2f}%")
print(f"年化收益: {(1 + total_return)**(252/n_days) - 1:.2%}")
print(f"夏普比率: {sharpe_ratio:.4f}")
print(f"最大回撤: {max_drawdown*100:.2f}%")

if alpha_beta:
    print(f"\nAlpha: {alpha_beta.alpha*100:.2f}%")
    print(f"Beta: {alpha_beta.beta:.4f}")

print("\n优化后组合权重:")
for name, weight in zip(strategy_names, optimal_weights):
    print(f"  {name}: {weight*100:.1f}%")

print("\n" + "=" * 70)
print("策略开发和回测示例完成！✓")
print("=" * 70)
print("\n下一步:")
print("1. 使用真实历史数据进行回测")
print("2. 调整策略参数优化性能")
print("3. 添加更多策略到组合")
print("4. 部署到生产环境进行实盘交易")
print("=" * 70)
