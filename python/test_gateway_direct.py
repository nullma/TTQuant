"""
Test Gateway - 直接测试网关订单处理
"""

import zmq
import json
import time

def test_gateway():
    print("=" * 60)
    print("TTQuant Gateway 测试")
    print("=" * 60)
    print()

    context = zmq.Context()

    # 连接到 Gateway 提交订单
    order_push = context.socket(zmq.PUSH)
    order_push.connect("tcp://localhost:5556")
    print("[Gateway] 已连接到订单接收端口: tcp://localhost:5556")

    # 订阅成交回报
    trade_sub = context.socket(zmq.SUB)
    trade_sub.connect("tcp://localhost:5557")
    trade_sub.setsockopt_string(zmq.SUBSCRIBE, "trade.")
    print("[Gateway] 已连接到成交回报端口: tcp://localhost:5557")
    print()

    # 等待连接建立
    time.sleep(1)

    # 提交测试订单
    orders = [
        {
            'order_id': 'TEST_001',
            'strategy_id': 'test_strategy',
            'symbol': 'BTCUSDT',
            'price': 50000.0,
            'volume': 1,
            'side': 'BUY',
            'timestamp': int(time.time() * 1e9)
        },
        {
            'order_id': 'TEST_002',
            'strategy_id': 'test_strategy',
            'symbol': 'ETHUSDT',
            'price': 3000.0,
            'volume': 10,
            'side': 'BUY',
            'timestamp': int(time.time() * 1e9)
        },
        {
            'order_id': 'TEST_003',
            'strategy_id': 'test_strategy',
            'symbol': 'BTCUSDT',
            'price': 50100.0,
            'volume': 1,
            'side': 'SELL',
            'timestamp': int(time.time() * 1e9)
        }
    ]

    print("提交订单:")
    print("-" * 60)
    for order in orders:
        order_push.send_json(order)
        print(f"[Order] {order['side']} {order['volume']} {order['symbol']} @ ${order['price']}")
        time.sleep(0.5)

    print()
    print("等待成交回报...")
    print("-" * 60)

    # 接收成交回报
    trade_count = 0
    poller = zmq.Poller()
    poller.register(trade_sub, zmq.POLLIN)

    timeout = 5000  # 5秒超时
    start_time = time.time()

    while trade_count < len(orders) and (time.time() - start_time) < 10:
        socks = dict(poller.poll(timeout))

        if trade_sub in socks:
            topic = trade_sub.recv_string()
            data = trade_sub.recv_string()
            trade = json.loads(data)

            trade_count += 1

            if trade['status'] == 'FILLED':
                print(f"[Trade #{trade_count}] FILLED")
                print(f"  Order ID: {trade['order_id']}")
                print(f"  Symbol: {trade['symbol']}")
                print(f"  Side: {trade['side']}")
                print(f"  Filled: {trade['filled_volume']} @ ${trade['filled_price']:.2f}")
                print(f"  Commission: ${trade['commission']:.4f}")
            else:
                print(f"[Trade #{trade_count}] REJECTED")
                print(f"  Order ID: {trade['order_id']}")
                print(f"  Error: {trade['error_message']}")
            print()

    print("=" * 60)
    print(f"测试完成: 提交 {len(orders)} 笔订单, 收到 {trade_count} 笔成交回报")
    print("=" * 60)

if __name__ == "__main__":
    test_gateway()
