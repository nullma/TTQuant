"""
TTQuant 回测示例

使用 EMA 交叉策略回测 2024 年数据

运行方式：
    python run_backtest.py

环境变量：
    DB_PASSWORD: 数据库密码（默认：changeme）
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backtest.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()

    # 数据库配置
    db_password = os.getenv('DB_PASSWORD', 'changeme')
    # Docker 环境中使用 timescaledb 主机名
    db_host = os.getenv('DB_HOST', 'timescaledb')
    db_uri = f"postgresql://ttquant:{db_password}@{db_host}:5432/ttquant_trading"

    # 回测参数
    SYMBOLS = ['BTCUSDT']
    START_DATE = datetime(2026, 2, 10)
    END_DATE = datetime(2026, 2, 11)
    EXCHANGE = 'okx'  # 使用 OKX 数据
    INITIAL_CAPITAL = 100000.0

    # 交易成本
    SLIPPAGE_MODEL = SlippageModel.PERCENTAGE
    SLIPPAGE_VALUE = 0.0005  # 0.05% 滑点
    MAKER_FEE = 0.0002  # 0.02% Maker 手续费
    TAKER_FEE = 0.0004  # 0.04% Taker 手续费

    logger.info("=" * 80)
    logger.info("TTQuant Backtest - EMA Cross Strategy")
    logger.info("=" * 80)
    logger.info(f"Symbols:        {SYMBOLS}")
    logger.info(f"Period:         {START_DATE.date()} to {END_DATE.date()}")
    logger.info(f"Exchange:       {EXCHANGE}")
    logger.info(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    logger.info(f"Slippage:       {SLIPPAGE_VALUE * 100:.3f}%")
    logger.info(f"Maker Fee:      {MAKER_FEE * 100:.3f}%")
    logger.info(f"Taker Fee:      {TAKER_FEE * 100:.3f}%")
    logger.info("=" * 80)

    try:
        # 创建回测引擎
        logger.info("Creating backtest engine...")
        engine = create_backtest_engine(
            db_uri=db_uri,
            symbols=SYMBOLS,
            start_date=START_DATE,
            end_date=END_DATE,
            exchange=EXCHANGE,
            initial_capital=INITIAL_CAPITAL,
            slippage_model=SLIPPAGE_MODEL,
            slippage_value=SLIPPAGE_VALUE,
            maker_fee=MAKER_FEE,
            taker_fee=TAKER_FEE,
        )

        # 添加 EMA 交叉策略
        logger.info("Adding EMA Cross strategy...")
        strategy_config = {
            'symbol': 'BTCUSDT',
            'fast_period': 5,
            'slow_period': 20,
            'trade_volume': 1,
        }
        strategy = EMACrossStrategy('ema_cross_btc', strategy_config)
        engine.add_strategy(strategy)

        # 运行回测
        logger.info("Starting backtest...")
        reports = engine.run()

        # 导出结果
        output_dir = 'backtest_results'
        logger.info(f"Exporting results to {output_dir}...")
        engine.export_results(output_dir)

        logger.info("=" * 80)
        logger.info("Backtest completed successfully!")
        logger.info("=" * 80)

        # 返回报告
        return reports

    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    reports = main()

    if reports:
        # 打印简要总结
        print("\n" + "=" * 80)
        print("BACKTEST SUMMARY")
        print("=" * 80)

        for strategy_id, report in reports.items():
            print(f"\nStrategy: {strategy_id}")
            print(f"  Total Return:   {report.total_return * 100:>8.2f}%")
            print(f"  Annual Return:  {report.annual_return * 100:>8.2f}%")
            print(f"  Sharpe Ratio:   {report.sharpe_ratio:>8.2f}")
            print(f"  Max Drawdown:   {report.max_drawdown * 100:>8.2f}%")
            print(f"  Win Rate:       {report.win_rate * 100:>8.2f}%")
            print(f"  Total Trades:   {report.total_trades:>8}")

        print("\n" + "=" * 80)
    else:
        print("\nBacktest failed. Check backtest.log for details.")
        sys.exit(1)
