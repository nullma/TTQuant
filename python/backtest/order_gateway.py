"""
BacktestOrderGateway - 回测订单网关

职责：
1. 模拟订单执行
2. 滑点模型（固定/百分比/市场深度）
3. 手续费计算
4. 成交延迟模拟
"""

import time
import uuid
from typing import Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass
import logging
import sys
import os

# 添加 strategy 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from strategy.base_strategy import Order, Trade

logger = logging.getLogger(__name__)


class SlippageModel(Enum):
    """滑点模型"""
    NONE = "none"  # 无滑点
    FIXED = "fixed"  # 固定滑点（点数）
    PERCENTAGE = "percentage"  # 百分比滑点
    MARKET_DEPTH = "market_depth"  # 市场深度模型（未实现）


@dataclass
class CommissionConfig:
    """手续费配置"""
    maker_fee: float = 0.0002  # Maker 手续费率（0.02%）
    taker_fee: float = 0.0004  # Taker 手续费率（0.04%）
    min_commission: float = 0.0  # 最小手续费


class BacktestOrderGateway:
    """回测订单网关"""

    def __init__(
        self,
        slippage_model: SlippageModel = SlippageModel.PERCENTAGE,
        slippage_value: float = 0.0005,  # 0.05% 滑点
        commission_config: Optional[CommissionConfig] = None,
        fill_delay_ms: int = 0,  # 成交延迟（毫秒）
        reject_rate: float = 0.0,  # 订单拒绝率（0-1）
    ):
        """
        初始化回测订单网关

        Args:
            slippage_model: 滑点模型
            slippage_value: 滑点值（根据模型不同含义不同）
            commission_config: 手续费配置
            fill_delay_ms: 成交延迟（毫秒）
            reject_rate: 订单拒绝率
        """
        self.slippage_model = slippage_model
        self.slippage_value = slippage_value
        self.commission_config = commission_config or CommissionConfig()
        self.fill_delay_ms = fill_delay_ms
        self.reject_rate = reject_rate

        # 订单回调
        self.trade_callback: Optional[Callable[[Trade], None]] = None

        # 统计
        self.stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'rejected_orders': 0,
            'total_commission': 0.0,
            'total_slippage': 0.0,
        }

        logger.info(f"BacktestOrderGateway initialized")
        logger.info(f"  Slippage model: {slippage_model.value}")
        logger.info(f"  Slippage value: {slippage_value}")
        logger.info(f"  Maker fee: {commission_config.maker_fee * 100:.3f}%")
        logger.info(f"  Taker fee: {commission_config.taker_fee * 100:.3f}%")
        logger.info(f"  Fill delay: {fill_delay_ms}ms")
        logger.info(f"  Reject rate: {reject_rate * 100:.2f}%")

    def set_trade_callback(self, callback: Callable[[Trade], None]):
        """设置成交回调函数"""
        self.trade_callback = callback

    def send_order(self, order: Order, current_price: float):
        """
        发送订单（立即模拟成交）

        Args:
            order: 订单对象
            current_price: 当前市场价格
        """
        self.stats['total_orders'] += 1

        # 模拟订单拒绝
        import random
        if random.random() < self.reject_rate:
            self._reject_order(order, "Simulated rejection")
            return

        # 计算成交价格（考虑滑点）
        filled_price = self._calculate_filled_price(order, current_price)

        # 计算手续费
        commission = self._calculate_commission(order, filled_price)

        # 模拟成交延迟
        if self.fill_delay_ms > 0:
            time.sleep(self.fill_delay_ms / 1000.0)

        # 生成成交回报
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            order_id=order.order_id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=order.side,
            filled_price=filled_price,
            filled_volume=order.volume,
            trade_time=int(time.time() * 1e9),
            status='FILLED',
            error_code=0,
            error_message='',
            is_retryable=False,
            commission=commission
        )

        # 更新统计
        self.stats['filled_orders'] += 1
        self.stats['total_commission'] += commission

        # 计算滑点成本
        slippage_cost = abs(filled_price - order.price) * order.volume
        self.stats['total_slippage'] += slippage_cost

        # 回调
        if self.trade_callback:
            self.trade_callback(trade)

        logger.debug(
            f"[Fill] {order.side} {order.volume} {order.symbol} @ "
            f"${filled_price:.2f} (slippage: ${slippage_cost:.2f}, "
            f"commission: ${commission:.2f})"
        )

    def _calculate_filled_price(self, order: Order, current_price: float) -> float:
        """
        计算成交价格（考虑滑点）

        Args:
            order: 订单
            current_price: 当前市场价格

        Returns:
            成交价格
        """
        if self.slippage_model == SlippageModel.NONE:
            return order.price

        elif self.slippage_model == SlippageModel.FIXED:
            # 固定滑点（点数）
            if order.side == 'BUY':
                return order.price + self.slippage_value
            else:
                return order.price - self.slippage_value

        elif self.slippage_model == SlippageModel.PERCENTAGE:
            # 百分比滑点
            slippage = order.price * self.slippage_value
            if order.side == 'BUY':
                return order.price + slippage
            else:
                return order.price - slippage

        elif self.slippage_model == SlippageModel.MARKET_DEPTH:
            # 市场深度模型（简化版：使用当前价格）
            # TODO: 实现真实的市场深度模型
            return current_price

        else:
            return order.price

    def _calculate_commission(self, order: Order, filled_price: float) -> float:
        """
        计算手续费

        Args:
            order: 订单
            filled_price: 成交价格

        Returns:
            手续费金额
        """
        # 简化：所有订单按 Taker 费率计算
        # TODO: 区分 Maker 和 Taker
        trade_value = filled_price * order.volume
        commission = trade_value * self.commission_config.taker_fee

        # 最小手续费
        if commission < self.commission_config.min_commission:
            commission = self.commission_config.min_commission

        return commission

    def _reject_order(self, order: Order, reason: str):
        """
        拒绝订单

        Args:
            order: 订单
            reason: 拒绝原因
        """
        self.stats['rejected_orders'] += 1

        trade = Trade(
            trade_id=str(uuid.uuid4()),
            order_id=order.order_id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=order.side,
            filled_price=0.0,
            filled_volume=0,
            trade_time=int(time.time() * 1e9),
            status='REJECTED',
            error_code=1001,
            error_message=reason,
            is_retryable=False,
            commission=0.0
        )

        if self.trade_callback:
            self.trade_callback(trade)

        logger.warning(f"[Reject] {order.side} {order.volume} {order.symbol}: {reason}")

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'fill_rate': (
                self.stats['filled_orders'] / self.stats['total_orders']
                if self.stats['total_orders'] > 0 else 0.0
            ),
            'avg_commission': (
                self.stats['total_commission'] / self.stats['filled_orders']
                if self.stats['filled_orders'] > 0 else 0.0
            ),
            'avg_slippage': (
                self.stats['total_slippage'] / self.stats['filled_orders']
                if self.stats['filled_orders'] > 0 else 0.0
            ),
        }


if __name__ == "__main__":
    # 测试订单网关
    logging.basicConfig(level=logging.DEBUG)

    # 创建网关
    gateway = BacktestOrderGateway(
        slippage_model=SlippageModel.PERCENTAGE,
        slippage_value=0.0005,
        commission_config=CommissionConfig(
            maker_fee=0.0002,
            taker_fee=0.0004
        ),
        fill_delay_ms=10,
        reject_rate=0.01
    )

    # 设置回调
    def on_trade(trade: Trade):
        print(f"Trade: {trade.side} {trade.filled_volume} @ ${trade.filled_price:.2f}")

    gateway.set_trade_callback(on_trade)

    # 模拟订单
    order = Order(
        order_id="test_001",
        strategy_id="test_strategy",
        symbol="BTCUSDT",
        price=50000.0,
        volume=1,
        side="BUY",
        timestamp=int(time.time() * 1e9)
    )

    gateway.send_order(order, current_price=50000.0)

    # 打印统计
    print("\n=== Gateway Statistics ===")
    for key, value in gateway.get_statistics().items():
        print(f"{key}: {value}")
