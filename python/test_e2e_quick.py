#!/usr/bin/env python3
"""
OKX 端到端快速测试 - 运行 30 秒
"""

import sys
import time
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategy.engine import StrategyEngine, OrderGateway
from strategy.strategies.ema_cross import EMACrossStrategy


def signal_handler(sig, frame):
    print("\n\n测试完成 (用户中断)")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

print("=" * 60)
print("OKX 端到端策略测试 (30秒)")
print("=" * 60)

# 创建策略引擎
engine = StrategyEngine(config={
    "md_endpoints": ["tcp://localhost:5558"],
    "trade_endpoint": "tcp://localhost:5560",
})

# 创建订单网关
gateway = OrderGateway("tcp://localhost:5559", use_protobuf=True)

# 创建策略
strategy = EMACrossStrategy("ema_okx_test", {
    "symbol": "BTCUSDT",
    "fast_period": 5,
    "slow_period": 20,
    "trade_volume": 1,
})
strategy.set_order_gateway(gateway)
engine.add_strategy(strategy)

print("\n策略配置:")
print("  - 交易对: BTCUSDT")
print("  - 快速EMA: 5, 慢速EMA: 20")
print("  - 交易量: 1")
print("\n运行中... (按 Ctrl+C 停止)")
print("=" * 60)

# 启动定时器
start_time = time.time()


def check_timeout():
    while time.time() - start_time < 30:
        time.sleep(1)
    print("\n\n30秒测试完成!")
    import os
    os._exit(0)


import threading
timer = threading.Thread(target=check_timeout, daemon=True)
timer.start()

# 运行引擎
try:
    engine.run()
except KeyboardInterrupt:
    print("\n\n测试完成!")
