"""
Momentum Strategy - 动量突破策略

策略逻辑:
- 计算价格动量（价格变化率）
- 当动量突破阈值且成交量放大时买入
- 当动量反转时卖出
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.base_strategy import BaseStrategy, MarketData, Trade
from typing import Dict, Any, List
import logging
import math

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """动量突破策略"""

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)

        # 策略参数
        self.symbol = config.get('symbol', 'SOLUSDT')
        self.lookback_period = config.get('lookback_period', 20)
        self.breakout_threshold = config.get('breakout_threshold', 1.5)
        self.volume_threshold = config.get('volume_threshold', 1.2)
        self.order_amount_usdt = config.get('order_amount_usdt', 150)
        self.max_position_usdt = config.get('max_position_usdt', 1500)
        self.stop_loss_percent = config.get('stop_loss_percent', 4.0)
        self.take_profit_percent = config.get('take_profit_percent', 8.0)

        # 历史数据
        self.price_history: List[float] = []
        self.volume_history: List[float] = []

        # 状态
        self.in_position = False

        logger.info(f"Momentum Strategy initialized: {self.symbol}")
        logger.info(f"  Lookback period: {self.lookback_period}")
        logger.info(f"  Breakout threshold: {self.breakout_threshold}σ")
        logger.info(f"  Volume threshold: {self.volume_threshold}x")

    def calculate_momentum(self) -> float:
        """计算动量（标准化）"""
        if len(self.price_history) < 2:
            return 0.0

        # 计算价格变化率
        returns = []
        for i in range(1, len(self.price_history)):
            ret = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
            returns.append(ret)

        if not returns:
            return 0.0

        # 计算均值和标准差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        # 当前动量（标准化）
        if std_dev > 0:
            current_return = returns[-1]
            momentum = (current_return - mean_return) / std_dev
        else:
            momentum = 0.0

        return momentum

    def calculate_volume_ratio(self) -> float:
        """计算成交量比率"""
        if len(self.volume_history) < 2:
            return 1.0

        avg_volume = sum(self.volume_history[:-1]) / len(self.volume_history[:-1])
        if avg_volume > 0:
            return self.volume_history[-1] / avg_volume
        return 1.0

    def on_market_data(self, md: MarketData):
        """行情回调"""
        if md.symbol != self.symbol:
            return

        price = md.last_price
        volume = md.volume

        # 更新历史数据
        self.price_history.append(price)
        self.volume_history.append(volume)

        # 保持固定长度
        if len(self.price_history) > self.lookback_period:
            self.price_history.pop(0)
        if len(self.volume_history) > self.lookback_period:
            self.volume_history.pop(0)

        # 需要足够的历史数据
        if len(self.price_history) < self.lookback_period:
            return

        # 计算指标
        momentum = self.calculate_momentum()
        volume_ratio = self.calculate_volume_ratio()

        position = self.get_position(self.symbol)
        current_volume = position.volume if position else 0

        # 买入信号：正动量突破 + 成交量放大
        if not self.in_position and momentum > self.breakout_threshold and volume_ratio > self.volume_threshold:
            current_value = current_volume * price if current_volume > 0 else 0

            if current_value < self.max_position_usdt:
                trade_volume = int(self.order_amount_usdt / price)
                logger.info(
                    f"[Signal] Momentum breakout: momentum={momentum:.2f}σ, "
                    f"volume_ratio={volume_ratio:.2f}x"
                )
                self.send_order(
                    symbol=self.symbol,
                    side='BUY',
                    price=price,
                    volume=trade_volume
                )
                self.in_position = True

        # 卖出信号：负动量突破（反转）
        elif self.in_position and momentum < -self.breakout_threshold:
            if current_volume > 0:
                logger.info(f"[Signal] Momentum reversal: momentum={momentum:.2f}σ")
                self.send_order(
                    symbol=self.symbol,
                    side='SELL',
                    price=price,
                    volume=current_volume
                )
                self.in_position = False

        # 风控检查
        if position and position.volume > 0:
            pnl_percent = (price - position.avg_price) / position.avg_price * 100

            # 止损
            if pnl_percent <= -self.stop_loss_percent:
                logger.warning(f"[Risk] Stop loss triggered: {pnl_percent:.2f}%")
                self.send_order(
                    symbol=self.symbol,
                    side='SELL',
                    price=price,
                    volume=position.volume
                )
                self.in_position = False

            # 止盈
            elif pnl_percent >= self.take_profit_percent:
                logger.info(f"[Risk] Take profit triggered: {pnl_percent:.2f}%")
                self.send_order(
                    symbol=self.symbol,
                    side='SELL',
                    price=price,
                    volume=position.volume
                )
                self.in_position = False

    def on_trade(self, trade: Trade):
        """成交回报回调"""
        if trade.status == 'FILLED':
            position = self.get_position(self.symbol)
            if position:
                logger.info(
                    f"[Position] {self.symbol}: {position.volume} @ ${position.avg_price:.2f} | "
                    f"PnL: ${position.realized_pnl + position.unrealized_pnl:.2f}"
                )
        else:
            logger.warning(f"[Trade] Order rejected: {trade.error_message}")
