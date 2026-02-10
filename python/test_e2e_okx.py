#!/usr/bin/env python3
"""
OKX 端到端策略测试
测试完整流程：OKX 行情 → EMA 策略 → OKX 下单 → 成交回报
"""

import sys
import time
import zmq
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategy.engine import StrategyEngine, OrderGateway
from strategy.strategies.ema_cross import EMACrossStrategy


def test_end_to_end():
    """端到端测试"""
    print("=" * 60)
    print("OKX 端到端策略测试")
    print("=" * 60)

    # 创建策略引擎（连接 OKX 行情）
    print("\n[1/4] 初始化策略引擎...")
    engine = StrategyEngine(config={
        "md_endpoints": ["tcp://localhost:5558"],  # OKX Market Data
        "trade_endpoint": "tcp://localhost:5560",  # OKX Trade Feed
    })
    print("    - 已连接 OKX Market Data (5558)")
    print("    - 已连接 OKX Trade Feed (5560)")

    # 创建订单网关（连接 OKX Gateway）
    print("\n[2/4] 初始化订单网关...")
    gateway = OrderGateway(
        endpoint="tcp://localhost:5559",  # OKX Gateway
        use_protobuf=True
    )
    print("    - 已连接 OKX Gateway (5559)")

    # 创建 EMA 交叉策略
    print("\n[3/4] 创建 EMA 交叉策略...")
    strategy = EMACrossStrategy(
        strategy_id="ema_cross_okx_test",
        config={
            "symbol": "BTCUSDT",
            "fast_period": 5,
            "slow_period": 20,
            "trade_volume": 1,
        }
    )
    strategy.set_order_gateway(gateway)
    engine.add_strategy(strategy)

    print("    - 策略 ID: ema_cross_okx_test")
    print("    - 交易对: BTCUSDT")
    print("    - 快速 EMA: 5")
    print("    - 慢速 EMA: 20")
    print("    - 交易量: 1")

    # 运行策略
    print("\n[4/4] 运行策略 (60 秒)...")
    print("-" * 60)

    try:
        # 设置定时器
        import threading
        stop_event = threading.Event()

        def stop_after_timeout():
            time.sleep(60)
            stop_event.set()
            engine.stop()

        timer = threading.Thread(target=stop_after_timeout, daemon=True)
        timer.start()

        engine.run()
        print("-" * 60)
        print("\n测试完成!")
        return True
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        return False
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)
