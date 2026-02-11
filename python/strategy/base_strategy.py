"""
BaseStrategy - 策略基类

设计原则：回测即实盘
- 所有策略继承此基类
- 通过依赖注入切换数据源和订单网关
- 回测和实盘共用同一套策略代码
- 集成风控管理
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """行情数据"""
    symbol: str
    last_price: float
    volume: float
    exchange_time: int
    local_time: int
    exchange: str


@dataclass
class Order:
    """订单"""
    order_id: str
    strategy_id: str
    symbol: str
    price: float
    volume: int
    side: str  # BUY/SELL
    timestamp: int


@dataclass
class Trade:
    """成交回报"""
    trade_id: str
    order_id: str
    strategy_id: str
    symbol: str
    side: str
    filled_price: float
    filled_volume: int
    trade_time: int
    status: str  # FILLED/REJECTED
    error_code: int
    error_message: str
    is_retryable: bool
    commission: float


@dataclass
class Position:
    """持仓"""
    symbol: str
    volume: int  # 正数=多头，负数=空头
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float


class Portfolio:
    """持仓管理"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.cash = 0.0
        self.total_pnl = 0.0

    def update_position(self, trade: Trade):
        """根据成交更新持仓"""
        symbol = trade.symbol

        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                volume=0,
                avg_price=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0
            )

        pos = self.positions[symbol]

        # 计算持仓变化
        delta = trade.filled_volume if trade.side == 'BUY' else -trade.filled_volume

        # 开仓或加仓
        if pos.volume == 0 or (pos.volume > 0 and delta > 0) or (pos.volume < 0 and delta < 0):
            total_cost = pos.avg_price * abs(pos.volume) + trade.filled_price * abs(delta)
            pos.volume += delta
            pos.avg_price = total_cost / abs(pos.volume) if pos.volume != 0 else 0.0

        # 平仓或减仓
        else:
            close_volume = min(abs(delta), abs(pos.volume))
            pnl = (trade.filled_price - pos.avg_price) * close_volume
            if pos.volume < 0:
                pnl = -pnl

            pos.realized_pnl += pnl - trade.commission
            self.total_pnl += pnl - trade.commission
            pos.volume += delta

            if pos.volume == 0:
                pos.avg_price = 0.0

        # 扣除手续费
        self.cash -= trade.commission

    def update_unrealized_pnl(self, symbol: str, current_price: float):
        """更新未实现盈亏"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.volume != 0:
                pos.unrealized_pnl = (current_price - pos.avg_price) * pos.volume

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)

    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.total_pnl + unrealized


class BaseStrategy(ABC):
    """
    策略基类

    所有策略必须继承此类并实现：
    - on_market_data: 行情回调
    - on_trade: 成交回报回调
    """

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.config = config
        self.portfolio = Portfolio()
        self._order_gateway = None
        self._order_counter = 0
        self._risk_manager = None  # 风控管理器（可选）

    def set_order_gateway(self, gateway):
        """设置订单网关（依赖注入）"""
        self._order_gateway = gateway

    def set_risk_manager(self, risk_manager):
        """设置风控管理器（可选）"""
        self._risk_manager = risk_manager
        logger.info(f"Risk manager enabled for strategy: {self.strategy_id}")

    @abstractmethod
    def on_market_data(self, md: MarketData):
        """
        行情回调

        子类必须实现此方法，处理行情数据并生成交易信号
        """
        pass

    @abstractmethod
    def on_trade(self, trade: Trade):
        """
        成交回报回调

        子类必须实现此方法，更新持仓状态
        """
        pass

    def send_order(self, symbol: str, side: str, price: float, volume: int):
        """
        发送订单（带风控检查）

        Args:
            symbol: 交易对
            side: BUY/SELL
            price: 价格
            volume: 数量
        """
        if self._order_gateway is None:
            raise RuntimeError("Order gateway not set")

        # 风控检查
        if self._risk_manager:
            # 检查每日亏损限制
            if not self._risk_manager.check_daily_loss_limit():
                logger.warning(f"[Risk] Order rejected: Daily loss limit reached")
                return

            # 检查仓位限制（仅对开仓订单）
            pos = self.get_position(symbol)
            is_opening = (pos is None or pos.volume == 0) or \
                        (pos.volume > 0 and side == 'BUY') or \
                        (pos.volume < 0 and side == 'SELL')

            if is_opening and not self._risk_manager.check_position_limit(symbol, volume, price):
                logger.warning(f"[Risk] Order rejected: Position limit exceeded")
                return

        self._order_counter += 1
        order = Order(
            order_id=f"{self.strategy_id}_{self._order_counter}",
            strategy_id=self.strategy_id,
            symbol=symbol,
            price=price,
            volume=volume,
            side=side,
            timestamp=int(time.time() * 1e9)
        )

        self._order_gateway.send_order(order)

    def check_risk_triggers(self, symbol: str, current_price: float):
        """
        检查风控触发条件（止损止盈）

        Args:
            symbol: 交易对
            current_price: 当前价格

        Returns:
            是否需要平仓
        """
        if not self._risk_manager:
            return False

        risk = self._risk_manager.check_stop_loss_take_profit(symbol, current_price)
        if risk and risk.should_close:
            logger.info(f"[Risk] {risk.close_reason}")
            # 平仓
            side = 'SELL' if risk.volume > 0 else 'BUY'
            self.send_order(symbol, side, current_price, abs(risk.volume))
            return True

        return False

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.portfolio.get_position(symbol)

    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        return self.portfolio.get_total_pnl()
