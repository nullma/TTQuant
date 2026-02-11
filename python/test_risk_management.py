"""
测试风控管理功能

测试场景：
1. 止损触发
2. 止盈触发
3. 仓位限制
4. 每日亏损限制
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from strategy.risk_manager import RiskManager, RiskConfig
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def test_stop_loss():
    """测试止损"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 1: Stop Loss")
    logger.info("=" * 60)

    config = RiskConfig(stop_loss_pct=0.02, take_profit_pct=0.05, enabled=True)
    rm = RiskManager(config, initial_capital=100000.0)

    # 开多头仓位
    rm.update_position('BTCUSDT', entry_price=100000.0, volume=1, side='BUY')

    # 价格下跌 1% - 不触发
    risk = rm.check_stop_loss_take_profit('BTCUSDT', 99000.0)
    assert risk is None, "Should not trigger at -1%"
    logger.info("✓ Price -1%: No trigger")

    # 价格下跌 2.5% - 触发止损
    risk = rm.check_stop_loss_take_profit('BTCUSDT', 97500.0)
    assert risk is not None and risk.should_close, "Should trigger stop loss at -2.5%"
    logger.info(f"✓ Price -2.5%: {risk.close_reason}")


def test_take_profit():
    """测试止盈"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Take Profit")
    logger.info("=" * 60)

    config = RiskConfig(stop_loss_pct=0.02, take_profit_pct=0.05, enabled=True)
    rm = RiskManager(config, initial_capital=100000.0)

    # 开多头仓位
    rm.update_position('BTCUSDT', entry_price=100000.0, volume=1, side='BUY')

    # 价格上涨 3% - 不触发
    risk = rm.check_stop_loss_take_profit('BTCUSDT', 103000.0)
    assert risk is None, "Should not trigger at +3%"
    logger.info("✓ Price +3%: No trigger")

    # 价格上涨 6% - 触发止盈
    risk = rm.check_stop_loss_take_profit('BTCUSDT', 106000.0)
    assert risk is not None and risk.should_close, "Should trigger take profit at +6%"
    logger.info(f"✓ Price +6%: {risk.close_reason}")


def test_position_limit():
    """测试仓位限制"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Position Limit")
    logger.info("=" * 60)

    config = RiskConfig(max_position_pct=0.3, max_positions=3, enabled=True)
    rm = RiskManager(config, initial_capital=100000.0)

    # 测试单品种仓位限制（30% = $30,000）
    # 尝试开 $40,000 的仓位 - 应该被拒绝
    result = rm.check_position_limit('BTCUSDT', volume=1, price=40000.0)
    assert not result, "Should reject position > 30%"
    logger.info("✓ Position $40,000 (40%): Rejected")

    # 尝试开 $25,000 的仓位 - 应该通过
    result = rm.check_position_limit('BTCUSDT', volume=1, price=25000.0)
    assert result, "Should accept position < 30%"
    logger.info("✓ Position $25,000 (25%): Accepted")

    # 测试最大持仓数量限制
    rm.update_position('BTC', 25000.0, 1, 'BUY')
    rm.update_position('ETH', 25000.0, 1, 'BUY')
    rm.update_position('SOL', 25000.0, 1, 'BUY')

    # 尝试开第4个仓位 - 应该被拒绝
    result = rm.check_position_limit('BNB', volume=1, price=25000.0)
    assert not result, "Should reject 4th position (max=3)"
    logger.info("✓ 4th position: Rejected (max=3)")


def test_daily_loss_limit():
    """测试每日亏损限制"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Daily Loss Limit")
    logger.info("=" * 60)

    config = RiskConfig(daily_loss_limit=5000.0, enabled=True)
    rm = RiskManager(config, initial_capital=100000.0)

    # 亏损 $3000 - 应该通过
    rm.update_pnl(-3000.0)
    result = rm.check_daily_loss_limit()
    assert result, "Should allow trading at -$3000"
    logger.info("✓ Daily PnL -$3000: Trading allowed")

    # 再亏损 $2500（总计 -$5500）- 应该被拒绝
    rm.update_pnl(-2500.0)
    result = rm.check_daily_loss_limit()
    assert not result, "Should block trading at -$5500"
    logger.info("✓ Daily PnL -$5500: Trading blocked")


def test_position_sizing():
    """测试仓位计算"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 5: Position Sizing")
    logger.info("=" * 60)

    config = RiskConfig(
        stop_loss_pct=0.02,
        max_position_pct=0.3,
        enabled=True
    )
    rm = RiskManager(config, initial_capital=100000.0)

    # 计算建议仓位（风险 1% = $1000）
    # 止损距离 = $100,000 * 2% = $2000
    # 建议数量 = $1000 / $2000 = 0.5 手 -> 1 手（最小）
    volume = rm.get_position_size('BTCUSDT', price=100000.0, risk_per_trade=0.01)
    logger.info(f"✓ Suggested position size: {volume} @ $100,000")
    logger.info(f"  Risk per trade: 1% = $1,000")
    logger.info(f"  Stop loss distance: 2% = $2,000")


def main():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("TTQuant Risk Management Tests")
    logger.info("=" * 60)

    try:
        test_stop_loss()
        test_take_profit()
        test_position_limit()
        test_daily_loss_limit()
        test_position_sizing()

        logger.info("\n" + "=" * 60)
        logger.info("All tests passed! ✓")
        logger.info("=" * 60)

    except AssertionError as e:
        logger.error(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
