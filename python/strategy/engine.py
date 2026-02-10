"""
StrategyEngine - 策略引擎核心

职责：
1. 订阅行情数据（ZMQ SUB）
2. 分发行情到策略
3. 接收策略订单并发送到 Gateway（ZMQ PUSH）
4. 接收成交回报并分发到策略（ZMQ SUB）
"""

import zmq
import json
import time
import signal
import sys
from typing import Dict, List
from .base_strategy import BaseStrategy, MarketData, Trade, Order
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class OrderGateway:
    """订单网关（ZMQ PUSH）"""

    def __init__(self, endpoint: str):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.connect(endpoint)
        logger.info(f"Order gateway connected to {endpoint}")

    def send_order(self, order: Order):
        """发送订单（JSON 格式）"""
        order_dict = {
            'order_id': order.order_id,
            'strategy_id': order.strategy_id,
            'symbol': order.symbol,
            'price': order.price,
            'volume': order.volume,
            'side': order.side,
            'timestamp': order.timestamp
        }
        self.socket.send_json(order_dict)
        logger.info(f"[Order] {order.side} {order.volume} {order.symbol} @ ${order.price}")


class StrategyEngine:
    """策略引擎"""

    def __init__(self, config: Dict):
        self.config = config
        self.strategies: Dict[str, BaseStrategy] = {}
        self.running = False

        # ZMQ Context
        self.context = zmq.Context()

        # 行情订阅（SUB）
        self.md_sub = self.context.socket(zmq.SUB)
        md_endpoints = config.get('md_endpoints', ['tcp://localhost:5555'])
        for endpoint in md_endpoints:
            self.md_sub.connect(endpoint)
            logger.info(f"Connected to market data: {endpoint}")

        # 订阅所有交易对
        symbols = config.get('symbols', [])
        for symbol in symbols:
            topic = f"md.{symbol}"
            self.md_sub.setsockopt_string(zmq.SUBSCRIBE, topic)
            logger.info(f"Subscribed to {topic}")

        # 成交回报订阅（SUB）
        self.trade_sub = self.context.socket(zmq.SUB)
        trade_endpoint = config.get('trade_endpoint', 'tcp://localhost:5557')
        self.trade_sub.connect(trade_endpoint)
        self.trade_sub.setsockopt_string(zmq.SUBSCRIBE, "trade.")
        logger.info(f"Connected to trade feed: {trade_endpoint}")

        # 订单网关（PUSH）
        order_endpoint = config.get('order_endpoint', 'tcp://localhost:5556')
        self.order_gateway = OrderGateway(order_endpoint)

        # Poller
        self.poller = zmq.Poller()
        self.poller.register(self.md_sub, zmq.POLLIN)
        self.poller.register(self.trade_sub, zmq.POLLIN)

        # 统计
        self.stats = {
            'md_count': 0,
            'trade_count': 0,
            'order_count': 0,
            'start_time': None
        }

    def add_strategy(self, strategy: BaseStrategy):
        """添加策略"""
        strategy.set_order_gateway(self.order_gateway)
        self.strategies[strategy.strategy_id] = strategy
        logger.info(f"Strategy added: {strategy.strategy_id}")

    def run(self):
        """运行策略引擎"""
        self.running = True
        self.stats['start_time'] = time.time()

        logger.info("=" * 60)
        logger.info("Strategy Engine Started")
        logger.info("=" * 60)
        logger.info(f"Strategies: {list(self.strategies.keys())}")
        logger.info("=" * 60)

        # 信号处理（仅在主线程中注册）
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # 在非主线程中运行，跳过信号处理
            logger.warning("Running in non-main thread, signal handlers not registered")

        try:
            while self.running:
                socks = dict(self.poller.poll(1000))

                # 处理行情数据
                if self.md_sub in socks:
                    self._handle_market_data()

                # 处理成交回报
                if self.trade_sub in socks:
                    self._handle_trade()

        except Exception as e:
            logger.error(f"Engine error: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _handle_market_data(self):
        """处理行情数据"""
        try:
            topic = self.md_sub.recv_string()
            data = self.md_sub.recv_string()
            md_dict = json.loads(data)

            md = MarketData(
                symbol=md_dict['symbol'],
                last_price=md_dict['last_price'],
                volume=md_dict['volume'],
                exchange_time=md_dict['exchange_time'],
                local_time=md_dict['local_time'],
                exchange=md_dict['exchange']
            )

            self.stats['md_count'] += 1

            # 分发到所有策略
            for strategy in self.strategies.values():
                strategy.on_market_data(md)

                # 更新未实现盈亏
                strategy.portfolio.update_unrealized_pnl(md.symbol, md.last_price)

        except Exception as e:
            logger.error(f"Failed to handle market data: {e}")

    def _handle_trade(self):
        """处理成交回报"""
        try:
            topic = self.trade_sub.recv_string()
            data = self.trade_sub.recv_string()
            trade_dict = json.loads(data)

            trade = Trade(
                trade_id=trade_dict['trade_id'],
                order_id=trade_dict['order_id'],
                strategy_id=trade_dict['strategy_id'],
                symbol=trade_dict['symbol'],
                side=trade_dict['side'],
                filled_price=trade_dict['filled_price'],
                filled_volume=trade_dict['filled_volume'],
                trade_time=trade_dict['trade_time'],
                status=trade_dict['status'],
                error_code=trade_dict['error_code'],
                error_message=trade_dict['error_message'],
                is_retryable=trade_dict['is_retryable'],
                commission=trade_dict['commission']
            )

            self.stats['trade_count'] += 1

            # 分发到对应策略
            strategy_id = trade.strategy_id
            if strategy_id in self.strategies:
                strategy = self.strategies[strategy_id]
                strategy.on_trade(trade)

                # 更新持仓
                if trade.status == 'FILLED':
                    strategy.portfolio.update_position(trade)
                    logger.info(
                        f"[Trade] {trade.side} {trade.filled_volume} {trade.symbol} @ "
                        f"${trade.filled_price:.2f} | PnL: ${strategy.get_total_pnl():.2f}"
                    )
                else:
                    logger.warning(f"[Trade] REJECTED: {trade.error_message}")

        except Exception as e:
            logger.error(f"Failed to handle trade: {e}")

    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _shutdown(self):
        """关闭引擎"""
        logger.info("=" * 60)
        logger.info("Strategy Engine Stopped")
        logger.info("=" * 60)

        # 统计信息
        elapsed = time.time() - self.stats['start_time']
        logger.info(f"Runtime: {elapsed:.1f}s")
        logger.info(f"Market data received: {self.stats['md_count']}")
        logger.info(f"Trades executed: {self.stats['trade_count']}")

        # 策略盈亏
        for strategy_id, strategy in self.strategies.items():
            pnl = strategy.get_total_pnl()
            logger.info(f"Strategy {strategy_id} PnL: ${pnl:.2f}")

        logger.info("=" * 60)

        # 关闭 ZMQ
        self.md_sub.close()
        self.trade_sub.close()
        self.order_gateway.socket.close()
        self.context.term()


if __name__ == "__main__":
    # 示例配置
    config = {
        'md_endpoints': ['tcp://localhost:5555'],
        'trade_endpoint': 'tcp://localhost:5557',
        'order_endpoint': 'tcp://localhost:5556',
        'symbols': ['BTCUSDT', 'ETHUSDT']
    }

    engine = StrategyEngine(config)

    # 这里需要添加具体策略
    # from strategies.ema_cross import EMACrossStrategy
    # strategy = EMACrossStrategy('ema_cross_1', {...})
    # engine.add_strategy(strategy)

    engine.run()
