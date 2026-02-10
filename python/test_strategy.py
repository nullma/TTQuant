"""
测试策略引擎 - 使用模拟数据

不依赖 Docker，直接测试策略逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy.base_strategy import MarketData, Trade
from strategy.strategies.ema_cross import EMACrossStrategy
import time


def test_ema_cross_strategy():
    """测试 EMA 交叉策略"""
    print("=" * 60)
    print("EMA Cross Strategy Test")
    print("=" * 60)
    print()

    # 创建策略
    config = {
        'symbol': 'BTCUSDT',
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 1
    }
    strategy = EMACrossStrategy('test_ema', config)

    # 模拟订单网关
    class MockOrderGateway:
        def __init__(self):
            self.orders = []

        def send_order(self, order):
            self.orders.append(order)
            print(f"[Order] {order.side} {order.volume} {order.symbol} @ ${order.price:.2f}")

            # 模拟成交
            trade = Trade(
                trade_id=f"TRADE_{len(self.orders)}",
                order_id=order.order_id,
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                side=order.side,
                filled_price=order.price * 1.0001,  # 模拟滑点
                filled_volume=order.volume,
                trade_time=int(time.time() * 1e9),
                status='FILLED',
                error_code=0,
                error_message='',
                is_retryable=False,
                commission=order.price * order.volume * 0.001  # 0.1% 手续费
            )

            # 更新持仓
            strategy.portfolio.update_position(trade)
            strategy.on_trade(trade)

    gateway = MockOrderGateway()
    strategy.set_order_gateway(gateway)

    # 模拟价格序列（制造金叉和死叉）
    prices = [
        50000, 50100, 50200, 50300, 50400,  # 上涨趋势
        50500, 50600, 50700, 50800, 50900,
        51000, 51100, 51200, 51300, 51400,
        51500, 51600, 51700, 51800, 51900,
        52000, 52100, 52200, 52300, 52400,  # 继续上涨（金叉）
        52300, 52200, 52100, 52000, 51900,  # 开始下跌
        51800, 51700, 51600, 51500, 51400,
        51300, 51200, 51100, 51000, 50900,
        50800, 50700, 50600, 50500, 50400,  # 继续下跌（死叉）
        50300, 50200, 50100, 50000, 49900,
    ]

    print("Simulating price movements...")
    print("-" * 60)

    for i, price in enumerate(prices):
        md = MarketData(
            symbol='BTCUSDT',
            last_price=price,
            volume=1.0,
            exchange_time=int(time.time() * 1e9),
            local_time=int(time.time() * 1e9),
            exchange='binance'
        )

        strategy.on_market_data(md)

        # 每 10 个价格打印一次状态
        if (i + 1) % 10 == 0:
            fast = strategy.ema_fast.get()
            slow = strategy.ema_slow.get()
            print(f"[{i+1:2d}] Price: ${price:7.2f} | EMA5: ${fast:7.2f} | EMA20: ${slow:7.2f}")

    print()
    print("=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"Total orders: {len(gateway.orders)}")
    print(f"Total PnL: ${strategy.get_total_pnl():.2f}")
    print()

    # 打印所有订单
    print("Orders:")
    for order in gateway.orders:
        print(f"  {order.side} {order.volume} {order.symbol} @ ${order.price:.2f}")

    print()

    # 打印持仓
    position = strategy.get_position('BTCUSDT')
    if position:
        print(f"Final Position:")
        print(f"  Volume: {position.volume}")
        print(f"  Avg Price: ${position.avg_price:.2f}")
        print(f"  Realized PnL: ${position.realized_pnl:.2f}")
        print(f"  Unrealized PnL: ${position.unrealized_pnl:.2f}")
    else:
        print("No position")

    print("=" * 60)


if __name__ == "__main__":
    test_ema_cross_strategy()
