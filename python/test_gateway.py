"""
TTQuant Gateway Test - Test order submission and trade execution

This script tests the Gateway module by:
1. Subscribing to market data
2. Generating test orders
3. Submitting orders to Gateway
4. Receiving trade confirmations
"""

import zmq
import time
import json
from datetime import datetime

# Protocol Buffers (simplified for testing)
class Order:
    def __init__(self, order_id, strategy_id, symbol, price, volume, side):
        self.order_id = order_id
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.price = price
        self.volume = volume
        self.side = side
        self.timestamp = int(time.time() * 1e9)

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'side': self.side,
            'timestamp': self.timestamp
        }

def test_gateway():
    print("=" * 60)
    print("TTQuant Gateway Test")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    context = zmq.Context()

    # Subscribe to market data
    md_sub = context.socket(zmq.SUB)
    md_endpoint = "tcp://md-binance:5555"
    md_sub.connect(md_endpoint)
    md_sub.setsockopt_string(zmq.SUBSCRIBE, "md.BTCUSDT")
    print(f"[MD] Connected to {md_endpoint}")

    # Connect to gateway for order submission
    order_push = context.socket(zmq.PUSH)
    order_endpoint = "tcp://gateway-binance:5556"
    order_push.connect(order_endpoint)
    print(f"[Gateway] Connected to {order_endpoint}")

    # Subscribe to trade confirmations
    trade_sub = context.socket(zmq.SUB)
    trade_endpoint = "tcp://gateway-binance:5557"
    trade_sub.connect(trade_endpoint)
    trade_sub.setsockopt_string(zmq.SUBSCRIBE, "trade.")
    print(f"[Trade] Connected to {trade_endpoint}")

    print()
    print("Waiting for market data...")
    print()

    order_count = 0
    trade_count = 0
    last_price = None

    # Use poller for non-blocking receive
    poller = zmq.Poller()
    poller.register(md_sub, zmq.POLLIN)
    poller.register(trade_sub, zmq.POLLIN)

    try:
        while True:
            socks = dict(poller.poll(1000))

            # Receive market data
            if md_sub in socks:
                topic = md_sub.recv_string()
                data = md_sub.recv_string()
                md = json.loads(data)
                last_price = md.get('last_price', 0)

                print(f"[MD] {md['symbol']} @ ${last_price:.2f}")

                # Generate test order every 10 seconds
                if order_count < 5 and int(time.time()) % 10 == 0:
                    order_count += 1
                    side = "BUY" if order_count % 2 == 1 else "SELL"

                    order = Order(
                        order_id=f"TEST_{order_count}",
                        strategy_id="test_strategy",
                        symbol="BTCUSDT",
                        price=last_price,
                        volume=1,
                        side=side
                    )

                    # Send order to gateway
                    order_push.send_json(order.to_dict())
                    print(f"[Order] Submitted: {side} BTCUSDT @ ${last_price:.2f}")

                    time.sleep(1)  # Avoid duplicate orders

            # Receive trade confirmations
            if trade_sub in socks:
                topic = trade_sub.recv_string()
                data = trade_sub.recv_string()
                trade = json.loads(data)

                trade_count += 1

                if trade['status'] == 'FILLED':
                    print(f"[Trade] FILLED: {trade['filled_volume']} {trade['symbol']} @ ${trade['filled_price']:.2f}")
                    print(f"        Commission: ${trade['commission']:.4f}")
                else:
                    print(f"[Trade] REJECTED: {trade['error_message']}")

                print()

            # Stop after 5 orders
            if order_count >= 5 and trade_count >= 5:
                break

    except KeyboardInterrupt:
        print("\n[WARNING] User interrupted")

    print()
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)
    print(f"Orders submitted: {order_count}")
    print(f"Trades received: {trade_count}")
    print("=" * 60)

if __name__ == "__main__":
    print()
    print("This is TTQuant Gateway test")
    print("Testing order submission and trade execution")
    print()

    test_gateway()

    print()
    print("=" * 60)
    print("[TIP]")
    print("=" * 60)
    print("To view Gateway logs:")
    print("  make logs-gateway")
    print()
    print("To view all services:")
    print("  make ps")
    print("=" * 60)
