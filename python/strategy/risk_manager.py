"""
风控管理模块

功能：
1. 止损止盈（Stop Loss / Take Profit）
2. 仓位管理（Position Sizing）
3. 每日亏损限制（Daily Loss Limit）
4. 最大持仓限制（Max Position Limit）
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """风控配置"""
    # 止损止盈
    stop_loss_pct: float = 0.02  # 止损百分比（2%）
    take_profit_pct: float = 0.05  # 止盈百分比（5%）

    # 仓位管理
    max_position_pct: float = 0.3  # 单个品种最大仓位（30%）
    max_total_position_pct: float = 0.8  # 总仓位限制（80%）

    # 每日亏损限制
    daily_loss_limit: float = 5000.0  # 每日最大亏损（美元）

    # 最大持仓数量
    max_positions: int = 5  # 最多同时持有5个品种

    # 是否启用风控
    enabled: bool = True


@dataclass
class PositionRisk:
    """持仓风险信息"""
    symbol: str
    entry_price: float
    current_price: float
    volume: int
    unrealized_pnl: float
    stop_loss_price: float
    take_profit_price: float
    should_close: bool = False
    close_reason: str = ""


class RiskManager:
    """风控管理器"""

    def __init__(self, config: RiskConfig, initial_capital: float = 100000.0):
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # 每日统计
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()

        # 持仓跟踪
        self.position_risks: Dict[str, PositionRisk] = {}

        logger.info("Risk Manager initialized")
        logger.info(f"  Stop Loss: {config.stop_loss_pct * 100:.1f}%")
        logger.info(f"  Take Profit: {config.take_profit_pct * 100:.1f}%")
        logger.info(f"  Max Position: {config.max_position_pct * 100:.1f}%")
        logger.info(f"  Daily Loss Limit: ${config.daily_loss_limit:.2f}")

    def reset_daily_stats(self):
        """重置每日统计"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info(f"Daily stats reset. Previous day PnL: ${self.daily_pnl:.2f}, Trades: {self.daily_trades}")
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = today

    def check_daily_loss_limit(self) -> bool:
        """检查是否触及每日亏损限制"""
        self.reset_daily_stats()

        if not self.config.enabled:
            return True

        if self.daily_pnl < -self.config.daily_loss_limit:
            logger.warning(f"Daily loss limit reached: ${self.daily_pnl:.2f} < ${-self.config.daily_loss_limit:.2f}")
            return False

        return True

    def check_position_limit(self, symbol: str, volume: int, price: float) -> bool:
        """检查仓位限制"""
        if not self.config.enabled:
            return True

        # 检查持仓数量限制
        if symbol not in self.position_risks and len(self.position_risks) >= self.config.max_positions:
            logger.warning(f"Max positions reached: {len(self.position_risks)} >= {self.config.max_positions}")
            return False

        # 检查单个品种仓位限制
        position_value = volume * price
        max_position_value = self.current_capital * self.config.max_position_pct

        if position_value > max_position_value:
            logger.warning(f"Position size too large: ${position_value:.2f} > ${max_position_value:.2f}")
            return False

        # 检查总仓位限制
        total_position_value = sum(
            abs(risk.volume * risk.current_price)
            for risk in self.position_risks.values()
        )
        total_position_value += position_value
        max_total_value = self.current_capital * self.config.max_total_position_pct

        if total_position_value > max_total_value:
            logger.warning(f"Total position too large: ${total_position_value:.2f} > ${max_total_value:.2f}")
            return False

        return True

    def update_position(self, symbol: str, entry_price: float, volume: int, side: str):
        """更新持仓信息"""
        if volume == 0:
            # 平仓
            if symbol in self.position_risks:
                del self.position_risks[symbol]
            return

        # 计算止损止盈价格
        if side == 'BUY':
            stop_loss_price = entry_price * (1 - self.config.stop_loss_pct)
            take_profit_price = entry_price * (1 + self.config.take_profit_pct)
        else:  # SELL
            stop_loss_price = entry_price * (1 + self.config.stop_loss_pct)
            take_profit_price = entry_price * (1 - self.config.take_profit_pct)

        self.position_risks[symbol] = PositionRisk(
            symbol=symbol,
            entry_price=entry_price,
            current_price=entry_price,
            volume=volume if side == 'BUY' else -volume,
            unrealized_pnl=0.0,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price
        )

        logger.info(f"Position updated: {symbol} @ ${entry_price:.2f}")
        logger.info(f"  Stop Loss: ${stop_loss_price:.2f}")
        logger.info(f"  Take Profit: ${take_profit_price:.2f}")

    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[PositionRisk]:
        """检查止损止盈"""
        if not self.config.enabled:
            return None

        if symbol not in self.position_risks:
            return None

        risk = self.position_risks[symbol]
        risk.current_price = current_price
        risk.unrealized_pnl = (current_price - risk.entry_price) * risk.volume

        # 多头持仓
        if risk.volume > 0:
            # 止损
            if current_price <= risk.stop_loss_price:
                risk.should_close = True
                risk.close_reason = f"Stop Loss triggered: ${current_price:.2f} <= ${risk.stop_loss_price:.2f}"
                logger.warning(risk.close_reason)
                return risk

            # 止盈
            if current_price >= risk.take_profit_price:
                risk.should_close = True
                risk.close_reason = f"Take Profit triggered: ${current_price:.2f} >= ${risk.take_profit_price:.2f}"
                logger.info(risk.close_reason)
                return risk

        # 空头持仓
        elif risk.volume < 0:
            # 止损
            if current_price >= risk.stop_loss_price:
                risk.should_close = True
                risk.close_reason = f"Stop Loss triggered: ${current_price:.2f} >= ${risk.stop_loss_price:.2f}"
                logger.warning(risk.close_reason)
                return risk

            # 止盈
            if current_price <= risk.take_profit_price:
                risk.should_close = True
                risk.close_reason = f"Take Profit triggered: ${current_price:.2f} <= ${risk.take_profit_price:.2f}"
                logger.info(risk.close_reason)
                return risk

        return None

    def update_pnl(self, realized_pnl: float):
        """更新盈亏"""
        self.reset_daily_stats()
        self.daily_pnl += realized_pnl
        self.daily_trades += 1
        self.current_capital += realized_pnl

    def get_position_size(self, symbol: str, price: float, risk_per_trade: float = 0.01) -> int:
        """
        计算建议仓位大小

        Args:
            symbol: 交易对
            price: 当前价格
            risk_per_trade: 每笔交易风险（默认1%）

        Returns:
            建议的交易数量
        """
        if not self.config.enabled:
            # 默认使用固定金额
            return int(1000 / price)

        # 基于风险的仓位计算
        risk_amount = self.current_capital * risk_per_trade
        stop_loss_distance = price * self.config.stop_loss_pct

        if stop_loss_distance == 0:
            return 0

        volume = int(risk_amount / stop_loss_distance)

        # 确保不超过仓位限制
        max_volume = int(self.current_capital * self.config.max_position_pct / price)
        volume = min(volume, max_volume)

        return max(1, volume)  # 至少1手

    def get_stats(self) -> Dict:
        """获取风控统计信息"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_pnl': self.current_capital - self.initial_capital,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'active_positions': len(self.position_risks),
            'max_positions': self.config.max_positions,
            'daily_loss_limit': self.config.daily_loss_limit,
            'daily_loss_remaining': self.config.daily_loss_limit + self.daily_pnl
        }
