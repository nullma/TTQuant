"""
TTQuant 模拟测试 - 不需要 Docker 或 Rust

这个脚本模拟整个系统的工作流程：
1. 模拟 Binance WebSocket 行情
2. 模拟 ZeroMQ 发布
3. 模拟策略引擎接收
"""

import time
import random
import json
from datetime import datetime

class MockMarketData:
    """模拟行情数据生成器"""

    def __init__(self, symbol, base_price):
        self.symbol = symbol
        self.price = base_price
        self.volume = 0

    def generate_tick(self):
        """生成一个 tick 数据"""
        # 模拟价格波动 (-0.1% 到 +0.1%)
        change = self.price * random.uniform(-0.001, 0.001)
        self.price += change
        self.volume = random.uniform(0.1, 10.0)

        return {
            'symbol': self.symbol,
            'last_price': round(self.price, 2),
            'volume': round(self.volume, 4),
            'exchange_time': int(time.time() * 1e9),
            'local_time': int(time.time() * 1e9),
            'exchange': 'binance'
        }

class MockZeroMQPublisher:
    """模拟 ZeroMQ Publisher"""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.message_count = 0

    def send(self, topic, data):
        """模拟发送消息"""
        self.message_count += 1
        # 在真实系统中，这里会通过 ZeroMQ 发送
        # 现在我们只是打印
        if self.message_count % 10 == 0:
            print(f"[Publisher] Sent {self.message_count} messages | "
                  f"Topic: {topic} | Price: ${data['last_price']}")

class MockStrategyEngine:
    """模拟策略引擎"""

    def __init__(self):
        self.positions = {}
        self.pnl = 0
        self.trade_count = 0

    def on_market_data(self, md):
        """处理行情数据"""
        # 简单的 EMA 交叉策略模拟
        symbol = md['symbol']
        price = md['last_price']

        # 模拟策略逻辑
        if random.random() < 0.05:  # 5% 概率产生信号
            if symbol not in self.positions:
                # 买入
                self.positions[symbol] = {
                    'entry_price': price,
                    'volume': 1,
                    'side': 'LONG'
                }
                self.trade_count += 1
                print(f"[Strategy] [BUY] {symbol} @ ${price}")
            else:
                # 卖出
                entry_price = self.positions[symbol]['entry_price']
                pnl = (price - entry_price) * self.positions[symbol]['volume']
                self.pnl += pnl
                del self.positions[symbol]
                self.trade_count += 1
                print(f"[Strategy] [SELL] {symbol} @ ${price} | PnL: ${pnl:.2f}")

def simulate_system(duration_seconds=30):
    """模拟整个系统运行"""

    print("=" * 60)
    print("TTQuant 系统模拟测试")
    print("=" * 60)
    print(f"模拟时长: {duration_seconds} 秒")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 初始化组件
    btc_data = MockMarketData("BTCUSDT", 50000.0)
    eth_data = MockMarketData("ETHUSDT", 3000.0)

    publisher = MockZeroMQPublisher("tcp://*:5555")
    strategy = MockStrategyEngine()

    start_time = time.time()
    tick_count = 0

    print("[System] Starting...")
    print()

    try:
        while time.time() - start_time < duration_seconds:
            # 生成 BTC 行情
            btc_tick = btc_data.generate_tick()
            topic_btc = f"md.{btc_tick['symbol']}.binance"
            publisher.send(topic_btc, btc_tick)
            strategy.on_market_data(btc_tick)
            tick_count += 1

            # 生成 ETH 行情
            eth_tick = eth_data.generate_tick()
            topic_eth = f"md.{eth_tick['symbol']}.binance"
            publisher.send(topic_eth, eth_tick)
            strategy.on_market_data(eth_tick)
            tick_count += 1

            # 模拟延迟（真实系统中由 WebSocket 控制）
            time.sleep(0.1)  # 100ms

    except KeyboardInterrupt:
        print("\n[WARNING] User interrupted")

    # 统计信息
    elapsed = time.time() - start_time
    rate = tick_count / elapsed

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print(f"运行时长: {elapsed:.1f} 秒")
    print(f"总消息数: {tick_count}")
    print(f"平均速率: {rate:.1f} msg/s")
    print(f"总交易数: {strategy.trade_count}")
    print(f"总盈亏: ${strategy.pnl:.2f}")
    print(f"持仓数: {len(strategy.positions)}")
    print("=" * 60)

    # 显示最终价格
    print()
    print("最终价格:")
    print(f"  BTCUSDT: ${btc_data.price:.2f}")
    print(f"  ETHUSDT: ${eth_data.price:.2f}")

    if strategy.positions:
        print()
        print("当前持仓:")
        for symbol, pos in strategy.positions.items():
            print(f"  {symbol}: {pos['side']} @ ${pos['entry_price']:.2f}")

if __name__ == "__main__":
    print()
    print("这是 TTQuant 系统的模拟测试")
    print("真实系统使用 Rust + ZeroMQ + Docker")
    print()

    # 运行 30 秒模拟
    simulate_system(duration_seconds=30)

    print()
    print("=" * 60)
    print("[TIP]")
    print("=" * 60)
    print("To run the real system, you need:")
    print("1. Install Docker Desktop")
    print("2. Run: make build && make up")
    print("3. View logs: make logs-test")
    print("=" * 60)
