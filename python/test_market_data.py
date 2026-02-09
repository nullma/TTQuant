"""
测试行情接收
"""
import zmq
import os
import time

# 从环境变量读取配置
zmq_endpoints = os.getenv("ZMQ_MD_ENDPOINTS", "tcp://localhost:5555").split(",")

context = zmq.Context()
socket = context.socket(zmq.SUB)

# 连接到所有行情端点
for endpoint in zmq_endpoints:
    endpoint = endpoint.strip()
    print(f"Connecting to {endpoint}...")
    socket.connect(endpoint)

# 订阅所有行情
socket.subscribe(b"md.")

print(f"Listening for market data on {zmq_endpoints}...")
print("Press Ctrl+C to stop\n")

message_count = 0
start_time = time.time()

try:
    while True:
        try:
            msg = socket.recv_multipart(flags=zmq.NOBLOCK)
            topic = msg[0].decode()
            # data = msg[1]  # Protobuf 数据

            message_count += 1
            elapsed = time.time() - start_time

            # 每秒统计一次
            if message_count % 10 == 0:
                rate = message_count / elapsed if elapsed > 0 else 0
                print(f"[{message_count:6d}] {topic:30s} | Rate: {rate:.1f} msg/s")

        except zmq.Again:
            time.sleep(0.01)  # 没有消息时短暂休眠

except KeyboardInterrupt:
    elapsed = time.time() - start_time
    rate = message_count / elapsed if elapsed > 0 else 0
    print(f"\n========================================")
    print(f"Stopped")
    print(f"Total messages: {message_count}")
    print(f"Duration: {elapsed:.1f}s")
    print(f"Average rate: {rate:.1f} msg/s")
    print(f"========================================")
finally:
    socket.close()
    context.term()
