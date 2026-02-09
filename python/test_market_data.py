"""
测试行情接收
"""
import zmq
import sys
sys.path.insert(0, '../rust/common/proto')

# 简单的测试脚本，不依赖 Protobuf
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5555")
socket.subscribe(b"md.")

print("Listening for market data on tcp://localhost:5555...")
print("Press Ctrl+C to stop\n")

try:
    while True:
        msg = socket.recv_multipart()
        topic = msg[0].decode()
        # data = msg[1]  # Protobuf 数据

        print(f"Received: {topic}")

except KeyboardInterrupt:
    print("\nStopped")
finally:
    socket.close()
    context.term()
