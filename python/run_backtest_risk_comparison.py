"""
风控效果对比回测

对比测试：
1. 无风控的 EMA 交叉策略
2. 有风控的 EMA 交叉策略（止损 2%，止盈 5%）

目标：验证风控能否减少亏损、降低回撤
"""

import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backtest.engine import create_backtest_engine
from backtest.order_gateway import SlippageModel
from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.risk_manager import RiskManager, RiskConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def run_backtest_without_risk():
    """运行无风控回测"""
    logger.info("\n" + "=" * 80)
    logger.info("Backtest 1: WITHOUT Risk Management")
    logger.info("=" * 80)

    # 数据库配置
    db_password = os.getenv('DB_PASSWORD', 'changeme')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_uri = f"postgresql://ttquant:{db_password}@{db_host}:5432/ttquant_trading"

    # 回测参数
    SYMBOLS = ['BTCUSDT']
    START_DATE = datetime(2026, 2, 10)
    END_DATE = datetime(2026, 2, 11)
    EXCHANGE = 'okx'
    INITIAL_CAPITAL = 100000.0

    # 创建回测引擎
    engine = create_backtest_engine(
        db_uri=db_uri,
        symbols=SYMBOLS,
        start_date=START_DATE,
        end_date=END_DATE,
        exchange=EXCHANGE,
        initial_capital=INITIAL_CAPITAL,
        slippage_model=SlippageModel.PERCENTAGE,
        slippage_value=0.0005,
        maker_fee=0.0002,
        taker_fee=0.0004
    )

    # 创建策略（无风控）
    strategy_config = {
        'symbol': 'BTCUSDT',
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 1
    }
    strategy = EMACrossStrategy('ema_cross_no_risk', strategy_config)
    engine.add_strategy(strategy)

    # 运行回测
    reports = engine.run()
    result = reports['ema_cross_no_risk']

    logger.info("\n" + "=" * 80)
    logger.info("Results WITHOUT Risk Management:")
    logger.info("=" * 80)
    logger.info(f"Total Return:   {result.total_return:>10.2f}%")
    logger.info(f"Max Drawdown:   {result.max_drawdown:>10.2f}%")
    logger.info(f"Sharpe Ratio:   {result.sharpe_ratio:>10.2f}")
    logger.info(f"Total Trades:   {result.total_trades:>10}")
    logger.info(f"Win Rate:       {result.win_rate:>10.2f}%")
    logger.info(f"Total PnL:      ${result.total_pnl:>10.2f}")

    return result


def run_backtest_with_risk():
    """运行有风控回测"""
    logger.info("\n" + "=" * 80)
    logger.info("Backtest 2: WITH Risk Management")
    logger.info("=" * 80)

    # 数据库配置
    db_password = os.getenv('DB_PASSWORD', 'changeme')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_uri = f"postgresql://ttquant:{db_password}@{db_host}:5432/ttquant_trading"

    # 回测参数
    SYMBOLS = ['BTCUSDT']
    START_DATE = datetime(2026, 2, 10)
    END_DATE = datetime(2026, 2, 11)
    EXCHANGE = 'okx'
    INITIAL_CAPITAL = 100000.0

    # 创建回测引擎
    engine = create_backtest_engine(
        db_uri=db_uri,
        symbols=SYMBOLS,
        start_date=START_DATE,
        end_date=END_DATE,
        exchange=EXCHANGE,
        initial_capital=INITIAL_CAPITAL,
        slippage_model=SlippageModel.PERCENTAGE,
        slippage_value=0.0005,
        maker_fee=0.0002,
        taker_fee=0.0004
    )

    # 创建策略
    strategy_config = {
        'symbol': 'BTCUSDT',
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 1
    }
    strategy = EMACrossStrategy('ema_cross_with_risk', strategy_config)

    # 创建风控管理器
    risk_config = RiskConfig(
        stop_loss_pct=0.02,      # 2% 止损
        take_profit_pct=0.05,    # 5% 止盈
        max_position_pct=0.3,    # 单品种最大 30% 仓位
        daily_loss_limit=5000.0, # 每日最大亏损 $5000
        max_positions=5,
        enabled=True
    )
    risk_manager = RiskManager(risk_config, initial_capital=INITIAL_CAPITAL)
    strategy.set_risk_manager(risk_manager)

    logger.info("Risk Management Settings:")
    logger.info(f"  Stop Loss:        {risk_config.stop_loss_pct * 100:.1f}%")
    logger.info(f"  Take Profit:      {risk_config.take_profit_pct * 100:.1f}%")
    logger.info(f"  Max Position:     {risk_config.max_position_pct * 100:.1f}%")
    logger.info(f"  Daily Loss Limit: ${risk_config.daily_loss_limit:.2f}")

    # 添加策略到引擎
    engine.add_strategy(strategy)

    # 运行回测
    reports = engine.run()
    result = reports['ema_cross_with_risk']

    logger.info("\n" + "=" * 80)
    logger.info("Results WITH Risk Management:")
    logger.info("=" * 80)
    logger.info(f"Total Return:   {result.total_return:>10.2f}%")
    logger.info(f"Max Drawdown:   {result.max_drawdown:>10.2f}%")
    logger.info(f"Sharpe Ratio:   {result.sharpe_ratio:>10.2f}")
    logger.info(f"Total Trades:   {result.total_trades:>10}")
    logger.info(f"Win Rate:       {result.win_rate:>10.2f}%")
    logger.info(f"Total PnL:      ${result.total_pnl:>10.2f}")

    # 风控统计
    stats = risk_manager.get_stats()
    logger.info("\nRisk Management Stats:")
    logger.info(f"  Daily PnL:        ${stats['daily_pnl']:>10.2f}")
    logger.info(f"  Daily Trades:     {stats['daily_trades']:>10}")
    logger.info(f"  Active Positions: {stats['active_positions']:>10}")

    return result


def compare_results(result1, result2):
    """对比结果"""
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON")
    logger.info("=" * 80)

    logger.info(f"{'Metric':<20} {'Without Risk':>15} {'With Risk':>15} {'Improvement':>15}")
    logger.info("-" * 80)

    # 总回报
    improvement = result2.total_return - result1.total_return
    logger.info(f"{'Total Return':<20} {result1.total_return:>14.2f}% {result2.total_return:>14.2f}% {improvement:>+14.2f}%")

    # 最大回撤
    improvement = result1.max_drawdown - result2.max_drawdown  # 回撤越小越好
    logger.info(f"{'Max Drawdown':<20} {result1.max_drawdown:>14.2f}% {result2.max_drawdown:>14.2f}% {improvement:>+14.2f}%")

    # 夏普比率
    improvement = result2.sharpe_ratio - result1.sharpe_ratio
    logger.info(f"{'Sharpe Ratio':<20} {result1.sharpe_ratio:>15.2f} {result2.sharpe_ratio:>15.2f} {improvement:>+15.2f}")

    # 交易次数
    improvement = result1.total_trades - result2.total_trades  # 减少过度交易
    logger.info(f"{'Total Trades':<20} {result1.total_trades:>15} {result2.total_trades:>15} {improvement:>+15}")

    # 胜率
    improvement = result2.win_rate - result1.win_rate
    logger.info(f"{'Win Rate':<20} {result1.win_rate:>14.2f}% {result2.win_rate:>14.2f}% {improvement:>+14.2f}%")

    # 总盈亏
    improvement = result2.total_pnl - result1.total_pnl
    logger.info(f"{'Total PnL':<20} ${result1.total_pnl:>14.2f} ${result2.total_pnl:>14.2f} ${improvement:>+14.2f}")

    logger.info("=" * 80)

    # 结论
    logger.info("\nConclusion:")
    if result2.total_return > result1.total_return and result2.max_drawdown < result1.max_drawdown:
        logger.info("✓ Risk management IMPROVED both return and drawdown!")
    elif result2.max_drawdown < result1.max_drawdown:
        logger.info("✓ Risk management REDUCED drawdown (better risk control)")
    elif result2.total_return > result1.total_return:
        logger.info("✓ Risk management IMPROVED return")
    else:
        logger.info("⚠ Risk management needs parameter tuning")


def main():
    """主函数"""
    logger.info("\n" + "=" * 80)
    logger.info("TTQuant Risk Management Backtest Comparison")
    logger.info("=" * 80)

    try:
        # 运行无风控回测
        result1 = run_backtest_without_risk()

        # 运行有风控回测
        result2 = run_backtest_with_risk()

        # 对比结果
        compare_results(result1, result2)

        logger.info("\n" + "=" * 80)
        logger.info("Backtest comparison completed!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
