"""
示例：集成 Prometheus 指标的策略引擎

演示如何在策略引擎中使用 metrics 模块
"""

import sys
import os
import time
import logging

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategy.engine import StrategyEngine
from strategy.base_strategy import BaseStrategy, MarketData, Order
from strategy.metrics import start_metrics_server, EngineMetrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleStrategy(BaseStrategy):
    """简单的示例策略"""

    def __init__(self, strategy_id: str, config: dict):
        super().__init__(strategy_id, config)
        self.last_price = {}

    def on_market_data(self, md: MarketData):
        """处理行情数据"""
        self.last_price[md.symbol] = md.last_price

        # 简单的交易逻辑（仅作演示）
        if md.symbol == "BTCUSDT":
            # 假设在某个价格点买入
            if md.last_price < 50000 and self.portfolio.get_position(md.symbol) == 0:
                order = Order(
                    order_id=f"order_{int(time.time() * 1000)}",
                    strategy_id=self.strategy_id,
                    symbol=md.symbol,
                    price=md.last_price,
                    volume=0.01,
                    side="BUY",
                    timestamp=int(time.time() * 1000)
                )
                self.send_order(order)


def main():
    """主函数"""
    # 1. 启动 Metrics HTTP 服务器
    logger.info("Starting metrics server...")
    start_metrics_server(port=8000)

    # 2. 创建引擎指标收集器
    engine_metrics = EngineMetrics()

    # 3. 配置策略引擎
    config = {
        'md_endpoints': ['tcp://localhost:5555'],
        'trade_endpoint': 'tcp://localhost:5557',
        'order_endpoint': 'tcp://localhost:5556',
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'use_protobuf': True
    }

    # 4. 创建策略引擎
    engine = StrategyEngine(config)

    # 5. 创建并添加策略
    strategy_config = {
        'initial_capital': 10000.0,
        'max_position_size': 1.0
    }
    strategy = SimpleStrategy('simple_strategy_1', strategy_config)
    engine.add_strategy(strategy)

    # 注册策略到指标收集器
    engine_metrics.add_strategy(strategy.strategy_id)

    # 6. 集成指标收集到引擎
    # 修改引擎的处理函数以记录指标
    original_handle_md = engine._handle_market_data
    original_handle_trade = engine._handle_trade

    def handle_md_with_metrics():
        """带指标记录的行情处理"""
        start_time = time.time()
        original_handle_md()

        # 记录指标
        for strategy_id, strategy in engine.strategies.items():
            # 更新策略指标
            strategy_metrics = engine_metrics.get_strategy_metrics(strategy_id)

            # 更新 PnL
            realized_pnl = strategy.portfolio.realized_pnl
            unrealized_pnl = sum(strategy.portfolio.unrealized_pnl.values())
            strategy_metrics.update_pnl(realized_pnl, unrealized_pnl)

            # 更新持仓
            for symbol, position in strategy.portfolio.positions.items():
                if symbol in strategy.last_price:
                    value = position * strategy.last_price[symbol]
                    strategy_metrics.update_position(symbol, position, value)
                    strategy_metrics.update_unrealized_pnl(
                        symbol,
                        strategy.portfolio.unrealized_pnl.get(symbol, 0.0)
                    )

        # 记录延迟
        latency_ms = (time.time() - start_time) * 1000
        for strategy_id in engine.strategies.keys():
            engine_metrics.record_strategy_latency(strategy_id, latency_ms)

    def handle_trade_with_metrics():
        """带指标记录的成交处理"""
        original_handle_trade()

        # 记录成交指标
        for strategy_id, strategy in engine.strategies.items():
            strategy_metrics = engine_metrics.get_strategy_metrics(strategy_id)

            # 更新最大回撤
            max_dd = abs(min(strategy.portfolio.pnl_history, default=0.0))
            strategy_metrics.update_max_drawdown(max_dd)

    # 替换处理函数
    engine._handle_market_data = handle_md_with_metrics
    engine._handle_trade = handle_trade_with_metrics

    # 7. 启动后台任务更新运行时间
    import threading

    def update_uptime():
        start_time = time.time()
        while engine.running:
            uptime = time.time() - start_time
            engine_metrics.update_uptime(uptime)
            time.sleep(1)

    uptime_thread = threading.Thread(target=update_uptime, daemon=True)
    uptime_thread.start()

    # 8. 运行引擎
    logger.info("=" * 60)
    logger.info("Strategy Engine with Metrics Started")
    logger.info("=" * 60)
    logger.info(f"Metrics endpoint: http://localhost:8000/metrics")
    logger.info("=" * 60)

    try:
        engine.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        logger.info("Engine stopped")


if __name__ == "__main__":
    main()
