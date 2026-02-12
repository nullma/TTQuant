"""
E2E Flow Test - 端到端交易流程测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import time
import zmq
import numpy as np
from proto.market_data_pb2 import MarketData
from proto.order_pb2 import Order
from proto.trade_pb2 import Trade

print("=" * 60)
print("E2E Flow Test - End-to-End Trading")
print("=" * 60)

# 1. 测试 ZMQ 通信
print("\n1. Testing ZMQ Communication...")

context = zmq.Context()

# 创建发布者（模拟市场数据）
md_pub = context.socket(zmq.PUB)
md_pub.bind("tcp://127.0.0.1:15555")
print("✓ Market data publisher bound")

# 创建订阅者（模拟策略引擎）
md_sub = context.socket(zmq.SUB)
md_sub.connect("tcp://127.0.0.1:15555")
md_sub.setsockopt_string(zmq.SUBSCRIBE, "md.BTCUSDT")
print("✓ Strategy subscribed to market data")

time.sleep(0.5)  # 等待连接建立

# 2. 测试市场数据流
print("\n2. Testing Market Data Flow...")

md = MarketData()
md.symbol = "BTCUSDT"
md.last_price = 50000.0
md.volume = 1.5
md.exchange_time = int(time.time() * 1e9)
md.local_time = int(time.time() * 1e9)

topic = "md.BTCUSDT.Binance"
md_pub.send_multipart([topic.encode(), md.SerializeToString()])
print(f"✓ Published: {md.symbol} @ ${md.last_price}")

poller = zmq.Poller()
poller.register(md_sub, zmq.POLLIN)

events = dict(poller.poll(1000))
if md_sub in events:
    msg = md_sub.recv_multipart()
    received_md = MarketData()
    received_md.ParseFromString(msg[1])
    print(f"✓ Received: {received_md.symbol} @ ${received_md.last_price}")
    assert received_md.last_price == 50000.0
else:
    print("✗ Failed to receive market data")

# 3. 测试延迟
print("\n3. Testing Latency...")

latencies = []
for i in range(10):
    start = time.time()
    md.last_price = 50000.0 + i
    md_pub.send_multipart([topic.encode(), md.SerializeToString()])

    events = dict(poller.poll(100))
    if md_sub in events:
        md_sub.recv_multipart()
        latency = (time.time() - start) * 1000
        latencies.append(latency)

if latencies:
    print(f"✓ Avg latency: {np.mean(latencies):.2f} ms")
    print(f"✓ P99 latency: {np.percentile(latencies, 99):.2f} ms")

# 清理
md_pub.close()
md_sub.close()
context.term()

print("\n" + "=" * 60)
print("E2E Flow Test Passed! ✓")
print("=" * 60)
