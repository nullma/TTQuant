"""
TTQuant 多策略回测

回测所有三个策略：
1. 网格交易策略 (BTCUSDT)
2. 均线交叉策略 (ETHUSDT) - 测试不同参数
3. 动量突破策略 (SOLUSDT)

运行方式：
    python run_backtest_all.py
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backtest.engine import create_backtest_engine
from backtest.order_gateway import SlippageModel
from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.strategies.grid_trading import GridTradingStrategy
from strategy.strategies.momentum import MomentumStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backtest_all.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)


def backtest_strategy(db_uri, strategy_name, strategy, symbol, start_date, end_date, exchange, initial_capital):
    """回测单个策略"""
    logger.info("=" * 80)
    logger.info(f"Backtesting: {strategy_name}")
    logger.info("=" * 80)

    try:
        # 创建回测引擎
        engine = create_backtest_engine(
            db_uri=db_uri,
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
            initial_capital=initial_capital,
            slippage_model=SlippageModel.PERCENTAGE,
            slippage_value=0.0005,  # 0.05% 滑点
            maker_fee=0.0002,  # 0.02% Maker
            taker_fee=0.0004,  # 0.04% Taker
        )

        # 添加策略
        engine.add_strategy(strategy)

        # 运行回测
        logger.info("Running backtest...")
        reports = engine.run()

        # 导出结果
        output_dir = f'backtest_results/{strategy_name}'
        logger.info(f"Exporting results to {output_dir}...")
        engine.export_results(output_dir)

        return reports

    except Exception as e:
        logger.error(f"Backtest failed for {strategy_name}: {e}", exc_info=True)
        return None


def main():
    """主函数"""
    load_dotenv()

    # 数据库配置
    db_password = os.getenv('DB_PASSWORD', 'changeme')
    db_uri = f"postgresql://ttquant:{db_password}@timescaledb:5432/ttquant_trading"

    # 回测时间范围（使用最近可用的数据）
    # 注意：需要先确认数据库中有哪些时间段的数据
    START_DATE = datetime(2026, 2, 10)  # 最近2天的数据
    END_DATE = datetime(2026, 2, 11)
    EXCHANGE = 'okx'
    INITIAL_CAPITAL = 100000.0

    logger.info("=" * 80)
    logger.info("TTQuant Multi-Strategy Backtest")
    logger.info("=" * 80)
    logger.info(f"Period:         {START_DATE.date()} to {END_DATE.date()}")
    logger.info(f"Exchange:       {EXCHANGE}")
    logger.info(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    logger.info("=" * 80)

    all_reports = {}

    # 1. 回测网格交易策略
    logger.info("\n[1/4] Grid Trading Strategy (BTCUSDT)")
    grid_config = {
        'symbol': 'BTCUSDT',
        'grid_count': 10,
        'price_range_percent': 2.0,
        'order_amount_usdt': 100,
    }
    grid_strategy = GridTradingStrategy('grid_btc', grid_config)
    reports = backtest_strategy(
        db_uri, 'grid_trading_btc', grid_strategy,
        'BTCUSDT', START_DATE, END_DATE, EXCHANGE, INITIAL_CAPITAL
    )
    if reports:
        all_reports['grid_trading_btc'] = reports

    # 2. 回测均线交叉策略 - 原参数 (5/20)
    logger.info("\n[2/4] EMA Cross Strategy - Original (5/20)")
    ema_config_1 = {
        'symbol': 'ETHUSDT',
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 1,
    }
    ema_strategy_1 = EMACrossStrategy('ema_cross_5_20', ema_config_1)
    reports = backtest_strategy(
        db_uri, 'ema_cross_eth_5_20', ema_strategy_1,
        'ETHUSDT', START_DATE, END_DATE, EXCHANGE, INITIAL_CAPITAL
    )
    if reports:
        all_reports['ema_cross_5_20'] = reports

    # 3. 回测均线交叉策略 - 优化参数 (10/30)
    logger.info("\n[3/4] EMA Cross Strategy - Optimized (10/30)")
    ema_config_2 = {
        'symbol': 'ETHUSDT',
        'fast_period': 10,
        'slow_period': 30,
        'trade_volume': 1,
    }
    ema_strategy_2 = EMACrossStrategy('ema_cross_10_30', ema_config_2)
    reports = backtest_strategy(
        db_uri, 'ema_cross_eth_10_30', ema_strategy_2,
        'ETHUSDT', START_DATE, END_DATE, EXCHANGE, INITIAL_CAPITAL
    )
    if reports:
        all_reports['ema_cross_10_30'] = reports

    # 4. 回测动量突破策略
    logger.info("\n[4/4] Momentum Strategy (SOLUSDT)")
    momentum_config = {
        'symbol': 'SOLUSDT',
        'lookback_period': 20,
        'breakout_threshold': 1.5,
        'volume_threshold': 1.2,
        'trade_volume': 1,
    }
    momentum_strategy = MomentumStrategy('momentum_sol', momentum_config)
    reports = backtest_strategy(
        db_uri, 'momentum_sol', momentum_strategy,
        'SOLUSDT', START_DATE, END_DATE, EXCHANGE, INITIAL_CAPITAL
    )
    if reports:
        all_reports['momentum_sol'] = reports

    # 打印汇总报告
    print("\n" + "=" * 80)
    print("BACKTEST SUMMARY - ALL STRATEGIES")
    print("=" * 80)
    print(f"Period: {START_DATE.date()} to {END_DATE.date()}")
    print("=" * 80)

    if all_reports:
        for strategy_name, reports in all_reports.items():
            for strategy_id, report in reports.items():
                print(f"\n{strategy_name}:")
                print(f"  Total Return:   {report.total_return * 100:>8.2f}%")
                print(f"  Annual Return:  {report.annual_return * 100:>8.2f}%")
                print(f"  Sharpe Ratio:   {report.sharpe_ratio:>8.2f}")
                print(f"  Max Drawdown:   {report.max_drawdown * 100:>8.2f}%")
                print(f"  Win Rate:       {report.win_rate * 100:>8.2f}%")
                print(f"  Total Trades:   {report.total_trades:>8}")
                print(f"  Profit Factor:  {report.profit_factor:>8.2f}")
    else:
        print("\nNo successful backtests.")

    print("\n" + "=" * 80)
    print("Results exported to: backtest_results/")
    print("=" * 80)

    return all_reports


if __name__ == "__main__":
    reports = main()

    if not reports:
        print("\nAll backtests failed. Check backtest_all.log for details.")
        sys.exit(1)
