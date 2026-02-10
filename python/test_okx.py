#!/usr/bin/env python3
"""
OKX 交易所集成测试脚本

测试 OKX Market Data 和 Gateway 的端到端功能
"""

import sys
import time
import zmq
from pathlib import Path

# 添加 strategy 模块到路径
sys.path.insert(0, str(Path(__file__).parent))

from strategy.engine import StrategyEngine, OrderGateway
from strategy.strategies.ema_cross import EMACrossStrategy


def test_okx_market_data():
    """测试 OKX 行情接收"""
    print("=" * 60)
    print("测试 1: OKX Market Data 接收")
    print("=" * 60)

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5558")
    socket.setsockopt_string(zmq.SUBSCRIBE, "md.")

    print("连接到 OKX Market Data (tcp://localhost:5558)")
    print("等待行情数据...")

    received_count = 0
    start_time = time.time()

    try:
        while received_count < 10 and (time.time() - start_time) < 30:
            if socket.poll(1000):
                topic = socket.recv_string()
                data = socket.recv_pyobj()
                received_count += 1

                print(f"\n[{received_count}] 收到行情:")
                print(f"  Topic: {topic}")
                print(f"  Symbol: {data.symbol}")
                print(f"  Exchange: {data.exchange}")
                print(f"  Price: {data.last_price}")
                print(f"  Volume: {data.volume}")
                print(f"  Latency: {(data.local_time - data.exchange_time) / 1_000_000:.2f} ms")

        if received_count > 0:
            print(f"\n✅ 成功接收 {received_count} 条 OKX 行情数据")
            return True
        else:
            print("\n❌ 未接收到 OKX 行情数据")
            return False

    except KeyboardInterrupt:
        print("\n测试中断")
        return False
    finally:
        socket.close()
        context.term()


def test_okx_gateway():
    """测试 OKX Gateway 订单提交"""
    print("\n" + "=" * 60)
    print("测试 2: OKX Gateway 订单提交")
    print("=" * 60)

    try:
        gateway = OrderGateway(
            endpoint="tcp://localhost:5559",
            use_protobuf=True
        )

        # 创建测试订单
        from strategy.engine import Order

        order = Order(
            order_id="TEST_OKX_001",
            strategy_id="test_okx",
            symbol="BTCUSDT",
            side="BUY",
            price=50000.0,
            volume=1,
        )

        print(f"\n提交测试订单:")
        print(f"  Order ID: {order.order_id}")
        print(f"  Symbol: {order.symbol}")
        print(f"  Side: {order.side}")
        print(f"  Price: {order.price}")
        print(f"  Volume: {order.volume}")

        gateway.submit_order(order)
        print("\n✅ 订单提交成功")

        # 等待成交回报
        print("\n等待成交回报...")
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://localhost:5560")
        socket.setsockopt_string(zmq.SUBSCRIBE, "trade.")

        if socket.poll(5000):
            topic = socket.recv_string()
            trade = socket.recv_pyobj()

            print(f"\n收到成交回报:")
            print(f"  Topic: {topic}")
            print(f"  Trade ID: {trade.trade_id}")
            print(f"  Order ID: {trade.order_id}")
            print(f"  Symbol: {trade.symbol}")
            print(f"  Side: {trade.side}")
            print(f"  Filled Price: {trade.filled_price}")
            print(f"  Filled Volume: {trade.filled_volume}")
            print(f"  Status: {trade.status}")
            print(f"  Commission: {trade.commission}")

            socket.close()
            context.term()

            print("\n✅ 成交回报接收成功")
            return True
        else:
            socket.close()
            context.term()
            print("\n❌ 未收到成交回报")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_okx_strategy():
    """测试 OKX 策略运行"""
    print("\n" + "=" * 60)
    print("测试 3: OKX 策略端到端测试")
    print("=" * 60)

    try:
        # 创建策略引擎
        engine = StrategyEngine(
            md_endpoints=["tcp://localhost:5558"],  # OKX Market Data
            trade_endpoint="tcp://localhost:5560",  # OKX Gateway
        )

        # 创建订单网关
        gateway = OrderGateway(
            endpoint="tcp://localhost:5559",  # OKX Gateway
            use_protobuf=True
        )

        # 创建 EMA 交叉策略
        strategy = EMACrossStrategy(
            strategy_id="ema_cross_okx",
            config={
                "symbol": "BTCUSDT",
                "fast_period": 5,
                "slow_period": 20,
                "trade_volume": 1,
            }
        )
        strategy.set_order_gateway(gateway)

        engine.add_strategy(strategy)

        print("\n策略配置:")
        print(f"  Strategy ID: ema_cross_okx")
        print(f"  Symbol: BTCUSDT")
        print(f"  Fast EMA: 5")
        print(f"  Slow EMA: 20")
        print(f"  Trade Volume: 1")

        print("\n运行策略 60 秒...")
        engine.run(duration=60)

        print("\n✅ 策略运行完成")
        return True

    except KeyboardInterrupt:
        print("\n测试中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("OKX 交易所集成测试")
    print("=" * 60)

    results = []

    # 测试 1: Market Data
    results.append(("Market Data", test_okx_market_data()))

    # 测试 2: Gateway
    results.append(("Gateway", test_okx_gateway()))

    # 测试 3: Strategy
    results.append(("Strategy", test_okx_strategy()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20s}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
