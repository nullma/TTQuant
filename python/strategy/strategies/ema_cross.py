"""
EMA Cross Strategy - EMA 均线交叉策略

策略逻辑：
- 快线（EMA5）上穿慢线（EMA20）：买入信号
- 快线（EMA5）下穿慢线（EMA20）：卖出信号
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.base_strategy import BaseStrategy, MarketData, Trade
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class EMA:
    """指数移动平均线"""

    def __init__(self, period: int):
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self.value = None

    def update(self, price: float) -> float:
        """更新 EMA 值"""
        if self.value is None:
            self.value = price
        else:
            self.value = self.alpha * price + (1 - self.alpha) * self.value
        return self.value

    def get(self) -> float:
        """获取当前 EMA 值"""
        return self.value if self.value is not None else 0.0


class EMACrossStrategy(BaseStrategy):
    """EMA 交叉策略"""

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)

        # 策略参数
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.fast_period = config.get('fast_period', 5)
        self.slow_period = config.get('slow_period', 20)
        self.trade_volume = config.get('trade_volume', 1)

        # EMA 指标
        self.ema_fast = EMA(self.fast_period)
        self.ema_slow = EMA(self.slow_period)

        # 上一次的交叉状态
        self.last_cross = None  # 'golden' or 'death'

        logger.info(f"EMA Cross Strategy initialized: {self.symbol}")
        logger.info(f"  Fast EMA: {self.fast_period}")
        logger.info(f"  Slow EMA: {self.slow_period}")
        logger.info(f"  Trade volume: {self.trade_volume}")

    def on_market_data(self, md: MarketData):
        """行情回调"""
        # 只处理目标交易对
        if md.symbol != self.symbol:
            return

        # 更新 EMA
        price = md.last_price
        fast = self.ema_fast.update(price)
        slow = self.ema_slow.update(price)

        # 需要等待 EMA 初始化
        if self.ema_slow.value is None:
            return

        # 检测交叉
        current_cross = 'golden' if fast > slow else 'death'

        # 金叉：快线上穿慢线 -> 买入
        if self.last_cross == 'death' and current_cross == 'golden':
            position = self.get_position(self.symbol)
            current_volume = position.volume if position else 0

            # 如果是空仓或空头，则买入
            if current_volume <= 0:
                logger.info(
                    f"[Signal] Golden Cross detected: "
                    f"EMA{self.fast_period}={fast:.2f} > EMA{self.slow_period}={slow:.2f}"
                )
                self.send_order(
                    symbol=self.symbol,
                    side='BUY',
                    price=price,
                    volume=self.trade_volume
                )

        # 死叉：快线下穿慢线 -> 卖出
        elif self.last_cross == 'golden' and current_cross == 'death':
            position = self.get_position(self.symbol)
            current_volume = position.volume if position else 0

            # 如果持有多头，则卖出
            if current_volume > 0:
                logger.info(
                    f"[Signal] Death Cross detected: "
                    f"EMA{self.fast_period}={fast:.2f} < EMA{self.slow_period}={slow:.2f}"
                )
                self.send_order(
                    symbol=self.symbol,
                    side='SELL',
                    price=price,
                    volume=current_volume
                )

        self.last_cross = current_cross

    def on_trade(self, trade: Trade):
        """成交回报回调"""
        if trade.status == 'FILLED':
            position = self.get_position(self.symbol)
            if position:
                logger.info(
                    f"[Position] {self.symbol}: {position.volume} @ ${position.avg_price:.2f} | "
                    f"Unrealized PnL: ${position.unrealized_pnl:.2f}"
                )
        else:
            logger.warning(f"[Trade] Order rejected: {trade.error_message}")


if __name__ == "__main__":
    # 测试策略
    from strategy.engine import StrategyEngine

    config = {
        'md_endpoints': ['tcp://localhost:5555'],
        'trade_endpoint': 'tcp://localhost:5557',
        'order_endpoint': 'tcp://localhost:5556',
        'symbols': ['BTCUSDT']
    }

    engine = StrategyEngine(config)

    # 添加 EMA 交叉策略
    strategy_config = {
        'symbol': 'BTCUSDT',
        'fast_period': 5,
        'slow_period': 20,
        'trade_volume': 1
    }
    strategy = EMACrossStrategy('ema_cross_btc', strategy_config)
    engine.add_strategy(strategy)

    # 运行引擎
    engine.run()
