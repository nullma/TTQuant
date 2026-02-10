"""
测试真实 Gateway - 连接 Docker 中的 Rust Gateway

使用 Protobuf 通信
"""
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.engine import StrategyEngine


def test_real_gateway():
    """测试真实 Gateway"""
    print("=" * 70)
    print("TTQuant Real Gateway Integration Test")
    print("=" * 70)
    print()

    # 配置策略引擎（连接 Docker 服务）
    engine_config = {
        'md_endpoints': ['tcp://localhost:5555'],  # Market Data
        'trade_endpoint': 'tcp://localhost:5557',  # Trade Feed
        'order_endpoint': 'tcp://localhost:5556',  # Order Gateway
        'symbols': ['BTCUSDT'],
        'use_protobuf': True  # 使用 Protobuf 与 Gateway 通信
    }

    engine = StrategyEngine(engine_config)

    # 添加 EMA 交叉策略
    strategy_config = {
        'symbol': 'BTCUSDT',
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 1
    }
    strategy = EMACrossStrategy('ema_cross_btc', strategy_config)
    engine.add_strategy(strategy)

    print()
    print("=" * 70)
    print("Strategy engine connected to Docker services")
    print("=" * 70)
    print("Market Data: tcp://localhost:5555")
    print("Order Gateway: tcp://localhost:5556")
    print("Trade Feed: tcp://localhost:5557")
    print("=" * 70)
    print()
    print("Running for 60 seconds...")
    print("Press Ctrl+C to stop")
    print()

    # 运行引擎
    try:
        engine.run()
    except KeyboardInterrupt:
        print("\n\nStopping...")
        engine.running = False
        time.sleep(1)

    # 打印结果
    print()
    print("=" * 70)
    print("Test Results")
    print("=" * 70)
    print(f"Strategy PnL: ${strategy.get_total_pnl():.2f}")
    print()

    # 打印持仓
    position = strategy.get_position('BTCUSDT')
    if position:
        print("Final Position:")
        print(f"  Symbol: {position.symbol}")
        print(f"  Volume: {position.volume}")
        print(f"  Avg Price: ${position.avg_price:.2f}")
        print(f"  Realized PnL: ${position.realized_pnl:.2f}")
        print(f"  Unrealized PnL: ${position.unrealized_pnl:.2f}")
    else:
        print("No position")

    print("=" * 70)


if __name__ == "__main__":
    test_real_gateway()
