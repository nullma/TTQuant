"""
端到端集成测试 - 模拟完整交易流程

模拟组件：
1. 行情数据生成器（模拟 Binance WebSocket）
2. Gateway（模拟订单处理和成交回报）
3. 策略引擎（真实的 EMA 交叉策略）

使用 ZMQ 进行进程间通信，验证完整的交易链路
"""

import zmq
import json
import time
import threading
import random
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.engine import StrategyEngine


class MockMarketDataPublisher:
    """模拟行情发布器"""

    def __init__(self, endpoint: str, symbols: list):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(endpoint)
        self.symbols = symbols
        self.running = False
        self.prices = {symbol: 50000.0 if 'BTC' in symbol else 3000.0 for symbol in symbols}
        print(f"[MockMD] Market data publisher started on {endpoint}")

    def start(self):
        """启动行情发布"""
        self.running = True
        thread = threading.Thread(target=self._publish_loop)
        thread.daemon = True
        thread.start()

    def _publish_loop(self):
        """发布行情循环"""
        tick_count = 0
        while self.running:
            for symbol in self.symbols:
                # 模拟价格波动
                change_pct = random.uniform(-0.002, 0.002)
                self.prices[symbol] *= (1 + change_pct)

                # 制造趋势（前 30 秒上涨，后 30 秒下跌）
                elapsed = tick_count * 0.1
                if elapsed < 30:
                    self.prices[symbol] *= 1.0005  # 上涨趋势
                else:
                    self.prices[symbol] *= 0.9995  # 下跌趋势

                md = {
                    'symbol': symbol,
                    'last_price': self.prices[symbol],
                    'volume': random.uniform(0.5, 2.0),
                    'exchange_time': int(time.time() * 1e9),
                    'local_time': int(time.time() * 1e9),
                    'exchange': 'binance'
                }

                topic = f"md.{symbol}.binance"
                self.socket.send_string(topic, zmq.SNDMORE)
                self.socket.send_string(json.dumps(md))

            tick_count += 1
            time.sleep(0.1)  # 10 Hz

    def stop(self):
        """停止发布"""
        self.running = False
        self.socket.close()


class MockGateway:
    """模拟交易网关"""

    def __init__(self, order_endpoint: str, trade_endpoint: str):
        self.context = zmq.Context()

        # 订单接收（PULL）
        self.order_socket = self.context.socket(zmq.PULL)
        self.order_socket.bind(order_endpoint)

        # 成交回报发布（PUB）
        self.trade_socket = self.context.socket(zmq.PUB)
        self.trade_socket.bind(trade_endpoint)

        self.running = False
        self.order_count = 0

        print(f"[MockGW] Gateway started")
        print(f"[MockGW]   Order endpoint: {order_endpoint}")
        print(f"[MockGW]   Trade endpoint: {trade_endpoint}")

    def start(self):
        """启动网关"""
        self.running = True
        thread = threading.Thread(target=self._process_orders)
        thread.daemon = True
        thread.start()

    def _process_orders(self):
        """处理订单"""
        while self.running:
            try:
                # 非阻塞接收
                if self.order_socket.poll(100):
                    order_json = self.order_socket.recv_string()
                    order = json.loads(order_json)

                    self.order_count += 1

                    print(f"[MockGW] Order #{self.order_count}: {order['side']} {order['volume']} "
                          f"{order['symbol']} @ ${order['price']:.2f}")

                    # 模拟成交（添加滑点和手续费）
                    slippage = 1.0001 if order['side'] == 'BUY' else 0.9999
                    filled_price = order['price'] * slippage
                    commission = filled_price * order['volume'] * 0.001

                    trade = {
                        'trade_id': f"TRADE_{self.order_count}",
                        'order_id': order['order_id'],
                        'strategy_id': order['strategy_id'],
                        'symbol': order['symbol'],
                        'side': order['side'],
                        'filled_price': filled_price,
                        'filled_volume': order['volume'],
                        'trade_time': int(time.time() * 1e9),
                        'status': 'FILLED',
                        'error_code': 0,
                        'error_message': '',
                        'is_retryable': False,
                        'commission': commission
                    }

                    # 发布成交回报
                    topic = f"trade.{order['symbol']}.binance"
                    self.trade_socket.send_string(topic, zmq.SNDMORE)
                    self.trade_socket.send_string(json.dumps(trade))

                    print(f"[MockGW] Trade #{self.order_count}: FILLED @ ${filled_price:.2f} "
                          f"(commission: ${commission:.4f})")

            except Exception as e:
                print(f"[MockGW] Error: {e}")

    def stop(self):
        """停止网关"""
        self.running = False
        self.order_socket.close()
        self.trade_socket.close()


def run_integration_test():
    """运行集成测试"""
    print("=" * 70)
    print("TTQuant End-to-End Integration Test")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # 配置
    md_endpoint = "tcp://127.0.0.1:15555"
    order_endpoint = "tcp://127.0.0.1:15556"
    trade_endpoint = "tcp://127.0.0.1:15557"
    symbols = ['BTCUSDT']

    # 启动模拟行情发布器
    md_publisher = MockMarketDataPublisher(md_endpoint, symbols)
    md_publisher.start()
    time.sleep(1.0)  # 等待绑定

    # 启动模拟网关
    gateway = MockGateway(order_endpoint, trade_endpoint)
    gateway.start()
    time.sleep(1.0)  # 等待绑定

    # 配置策略引擎（使用相同的地址）
    engine_config = {
        'md_endpoints': [md_endpoint],
        'trade_endpoint': trade_endpoint,
        'order_endpoint': order_endpoint,
        'symbols': symbols
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
    print("Running strategy for 60 seconds...")
    print("=" * 70)
    print()

    # 在单独的线程中运行引擎
    engine_thread = threading.Thread(target=engine.run)
    engine_thread.daemon = True
    engine_thread.start()

    # 运行 60 秒
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n[WARNING] User interrupted")

    # 停止所有组件
    print()
    print("=" * 70)
    print("Stopping components...")
    print("=" * 70)

    engine.running = False
    md_publisher.stop()
    gateway.stop()

    time.sleep(1)

    # 打印结果
    print()
    print("=" * 70)
    print("Test Results")
    print("=" * 70)
    print(f"Total orders: {gateway.order_count}")
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
    run_integration_test()
