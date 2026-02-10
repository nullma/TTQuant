"""
混合测试 - 模拟行情 + 真实 Gateway

使用模拟行情发布器，但连接真实的 Docker Gateway
验证 Protobuf 通信和完整交易流程
"""
import zmq
import json
import time
import threading
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy.strategies.ema_cross import EMACrossStrategy
from strategy.engine import StrategyEngine


class MockMarketDataPublisher:
    """模拟行情发布器（发布到本地端口）"""

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


def run_hybrid_test():
    """运行混合测试"""
    print("=" * 70)
    print("TTQuant Hybrid Test - Mock MD + Real Gateway")
    print("=" * 70)
    print()

    # 配置
    mock_md_endpoint = "tcp://127.0.0.1:15555"  # 模拟行情端口
    real_order_endpoint = "tcp://localhost:5556"  # 真实 Gateway 订单端口
    real_trade_endpoint = "tcp://localhost:5557"  # 真实 Gateway 成交端口
    symbols = ['BTCUSDT']

    # 启动模拟行情发布器
    md_publisher = MockMarketDataPublisher(mock_md_endpoint, symbols)
    md_publisher.start()
    time.sleep(1.0)

    print("Components:")
    print(f"  Mock Market Data: {mock_md_endpoint}")
    print(f"  Real Gateway Orders: {real_order_endpoint}")
    print(f"  Real Gateway Trades: {real_trade_endpoint}")
    print()

    # 配置策略引擎
    engine_config = {
        'md_endpoints': [mock_md_endpoint],  # 使用模拟行情
        'trade_endpoint': real_trade_endpoint,  # 使用真实 Gateway
        'order_endpoint': real_order_endpoint,  # 使用真实 Gateway
        'symbols': symbols,
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
    print("Running for 60 seconds...")
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
    run_hybrid_test()
