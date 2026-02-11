"""
Grid Trading Strategy - 网格交易策略

策略逻辑:
- 在当前价格上下设置多个买卖网格
- 价格下跌时买入，价格上涨时卖出
- 适合震荡行情
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.base_strategy import BaseStrategy, MarketData, Trade
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class GridLevel:
    """网格层级"""
    def __init__(self, price: float, volume: int):
        self.price = price
        self.volume = volume
        self.filled = False


class GridTradingStrategy(BaseStrategy):
    """网格交易策略"""

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)

        # 策略参数
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.grid_count = config.get('grid_count', 10)
        self.price_range_percent = config.get('price_range_percent', 2.0)
        self.order_amount_usdt = config.get('order_amount_usdt', 100)
        self.max_position_usdt = config.get('max_position_usdt', 5000)
        self.stop_loss_percent = config.get('stop_loss_percent', 5.0)
        self.take_profit_percent = config.get('take_profit_percent', 10.0)

        # 网格状态
        self.center_price = None
        self.buy_grids: List[GridLevel] = []
        self.sell_grids: List[GridLevel] = []
        self.initialized = False

        logger.info(f"Grid Trading Strategy initialized: {self.symbol}")
        logger.info(f"  Grid count: {self.grid_count}")
        logger.info(f"  Price range: ±{self.price_range_percent}%")
        logger.info(f"  Order amount: ${self.order_amount_usdt}")

    def initialize_grids(self, current_price: float):
        """初始化网格"""
        self.center_price = current_price

        # 计算价格范围
        price_step = (current_price * self.price_range_percent / 100) / self.grid_count

        # 创建买入网格（低于当前价）
        self.buy_grids = []
        for i in range(1, self.grid_count + 1):
            price = current_price - price_step * i
            volume = int(self.order_amount_usdt / price)
            self.buy_grids.append(GridLevel(price, volume))

        # 创建卖出网格（高于当前价）
        self.sell_grids = []
        for i in range(1, self.grid_count + 1):
            price = current_price + price_step * i
            volume = int(self.order_amount_usdt / price)
            self.sell_grids.append(GridLevel(price, volume))

        self.initialized = True
        logger.info(f"Grids initialized at center price: ${current_price:.2f}")
        logger.info(f"  Buy grids: ${self.buy_grids[-1].price:.2f} - ${self.buy_grids[0].price:.2f}")
        logger.info(f"  Sell grids: ${self.sell_grids[0].price:.2f} - ${self.sell_grids[-1].price:.2f}")

    def on_market_data(self, md: MarketData):
        """行情回调"""
        if md.symbol != self.symbol:
            return

        price = md.last_price

        # 初始化网格
        if not self.initialized:
            self.initialize_grids(price)
            return

        # 检查买入网格
        for grid in self.buy_grids:
            if not grid.filled and price <= grid.price:
                position = self.get_position(self.symbol)
                current_value = position.volume * position.avg_price if position else 0

                # 检查持仓限制
                if current_value + self.order_amount_usdt <= self.max_position_usdt:
                    logger.info(f"[Signal] Buy grid triggered at ${grid.price:.2f}")
                    self.send_order(
                        symbol=self.symbol,
                        side='BUY',
                        price=grid.price,
                        volume=grid.volume
                    )
                    grid.filled = True

        # 检查卖出网格
        for grid in self.sell_grids:
            if not grid.filled and price >= grid.price:
                position = self.get_position(self.symbol)
                if position and position.volume >= grid.volume:
                    logger.info(f"[Signal] Sell grid triggered at ${grid.price:.2f}")
                    self.send_order(
                        symbol=self.symbol,
                        side='SELL',
                        price=grid.price,
                        volume=grid.volume
                    )
                    grid.filled = True

        # 检查止损止盈
        position = self.get_position(self.symbol)
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

            # 止盈
            elif pnl_percent >= self.take_profit_percent:
                logger.info(f"[Risk] Take profit triggered: {pnl_percent:.2f}%")
                self.send_order(
                    symbol=self.symbol,
                    side='SELL',
                    price=price,
                    volume=position.volume
                )

    def on_trade(self, trade: Trade):
        """成交回报回调"""
        if trade.status == 'FILLED':
            # 重置对应的网格
            if trade.side == 'BUY':
                for grid in self.buy_grids:
                    if abs(grid.price - trade.filled_price) < 0.01:
                        grid.filled = False
            else:
                for grid in self.sell_grids:
                    if abs(grid.price - trade.filled_price) < 0.01:
                        grid.filled = False

            position = self.get_position(self.symbol)
            if position:
                logger.info(
                    f"[Position] {self.symbol}: {position.volume} @ ${position.avg_price:.2f} | "
                    f"PnL: ${position.realized_pnl + position.unrealized_pnl:.2f}"
                )
        else:
            logger.warning(f"[Trade] Order rejected: {trade.error_message}")
