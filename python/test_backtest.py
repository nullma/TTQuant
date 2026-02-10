"""
测试回测框架

简单的单元测试，验证回测框架的核心功能
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backtest.order_gateway import BacktestOrderGateway, SlippageModel, CommissionConfig
from backtest.analytics import PerformanceAnalytics
from strategy.base_strategy import Order, Trade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_order_gateway():
    """测试订单网关"""
    logger.info("=" * 60)
    logger.info("Testing BacktestOrderGateway")
    logger.info("=" * 60)

    # 创建网关
    gateway = BacktestOrderGateway(
        slippage_model=SlippageModel.PERCENTAGE,
        slippage_value=0.001,  # 0.1% 滑点
        commission_config=CommissionConfig(
            maker_fee=0.0002,
            taker_fee=0.0004
        )
    )

    # 记录成交
    trades = []

    def on_trade(trade: Trade):
        trades.append(trade)
        logger.info(f"Trade: {trade.side} {trade.filled_volume} @ ${trade.filled_price:.2f}")

    gateway.set_trade_callback(on_trade)

    # 发送买单
    buy_order = Order(
        order_id="test_001",
        strategy_id="test",
        symbol="BTCUSDT",
        price=50000.0,
        volume=1,
        side="BUY",
        timestamp=int(datetime.now().timestamp() * 1e9)
    )
    gateway.send_order(buy_order, current_price=50000.0)

    # 发送卖单
    sell_order = Order(
        order_id="test_002",
        strategy_id="test",
        symbol="BTCUSDT",
        price=51000.0,
        volume=1,
        side="SELL",
        timestamp=int(datetime.now().timestamp() * 1e9)
    )
    gateway.send_order(sell_order, current_price=51000.0)

    # 验证
    assert len(trades) == 2, "Should have 2 trades"
    assert trades[0].status == 'FILLED', "First trade should be filled"
    assert trades[1].status == 'FILLED', "Second trade should be filled"

    # 打印统计
    stats = gateway.get_statistics()
    logger.info("\nGateway Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("✓ Order gateway test passed\n")


def test_analytics():
    """测试性能分析"""
    logger.info("=" * 60)
    logger.info("Testing PerformanceAnalytics")
    logger.info("=" * 60)

    analytics = PerformanceAnalytics(initial_capital=100000.0)

    # 模拟权益曲线
    start = datetime(2024, 1, 1)
    np.random.seed(42)

    for i in range(365):
        timestamp = start + timedelta(days=i)
        # 模拟上涨趋势 + 随机波动
        equity = 100000 + i * 50 + np.random.randn() * 500
        analytics.record_equity(timestamp, equity, {})

    # 生成报告
    report = analytics.generate_report(
        strategy_id="test_strategy",
        start_date=start,
        end_date=start + timedelta(days=364),
        final_equity=118250.0,
        positions={},
        gateway_stats={
            'total_commission': 250.0,
            'total_slippage': 150.0
        }
    )

    # 验证
    assert report.total_return > 0, "Should have positive return"
    assert report.sharpe_ratio != 0, "Should have non-zero Sharpe ratio"
    assert report.max_drawdown >= 0, "Max drawdown should be non-negative"

    # 打印报告
    report.print_report()

    logger.info("✓ Analytics test passed\n")


def test_slippage_models():
    """测试不同的滑点模型"""
    logger.info("=" * 60)
    logger.info("Testing Slippage Models")
    logger.info("=" * 60)

    models = [
        (SlippageModel.NONE, 0.0, "No slippage"),
        (SlippageModel.FIXED, 10.0, "Fixed $10 slippage"),
        (SlippageModel.PERCENTAGE, 0.001, "0.1% slippage"),
    ]

    for model, value, description in models:
        logger.info(f"\nTesting: {description}")

        gateway = BacktestOrderGateway(
            slippage_model=model,
            slippage_value=value,
            commission_config=CommissionConfig()
        )

        filled_prices = []

        def on_trade(trade: Trade):
            filled_prices.append(trade.filled_price)

        gateway.set_trade_callback(on_trade)

        # 测试买单
        order = Order(
            order_id="test",
            strategy_id="test",
            symbol="BTCUSDT",
            price=50000.0,
            volume=1,
            side="BUY",
            timestamp=int(datetime.now().timestamp() * 1e9)
        )
        gateway.send_order(order, current_price=50000.0)

        logger.info(f"  Order price: $50,000.00")
        logger.info(f"  Filled price: ${filled_prices[0]:,.2f}")
        logger.info(f"  Slippage: ${filled_prices[0] - 50000:.2f}")

    logger.info("\n✓ Slippage models test passed\n")


def main():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("TTQuant Backtest Framework - Unit Tests")
    logger.info("=" * 60 + "\n")

    try:
        test_order_gateway()
        test_analytics()
        test_slippage_models()

        logger.info("=" * 60)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
