"""
Portfolio Manager - 多策略组合管理器

管理多个策略的资金分配、持仓和风险
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyAllocation:
    """策略资金分配"""
    strategy_id: str
    weight: float  # 权重 [0, 1]
    capital: float  # 分配资金
    max_position: float  # 最大持仓限制


class PortfolioManager:
    """
    组合管理器

    功能：
    - 管理多个策略的资金分配
    - 监控组合整体风险
    - 执行再平衡
    """

    def __init__(self, total_capital: float, config: Dict):
        self.total_capital = total_capital
        self.config = config
        self.allocations: Dict[str, StrategyAllocation] = {}
        self.strategy_positions: Dict[str, Dict] = {}

        logger.info(f"PortfolioManager initialized with capital: ${total_capital:,.2f}")

    def add_strategy(self, strategy_id: str, weight: float, max_position: float = None):
        """添加策略到组合"""
        if weight < 0 or weight > 1:
            raise ValueError(f"Invalid weight: {weight}")

        capital = self.total_capital * weight
        if max_position is None:
            max_position = capital * 0.95

        self.allocations[strategy_id] = StrategyAllocation(
            strategy_id=strategy_id,
            weight=weight,
            capital=capital,
            max_position=max_position
        )
        self.strategy_positions[strategy_id] = {}

        logger.info(f"Added strategy {strategy_id}: weight={weight:.2%}, capital=${capital:,.2f}")

    def get_allocation(self, strategy_id: str) -> Optional[StrategyAllocation]:
        """获取策略分配"""
        return self.allocations.get(strategy_id)

    def update_weights(self, new_weights: Dict[str, float]):
        """更新策略权重"""
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        for strategy_id, weight in new_weights.items():
            if strategy_id in self.allocations:
                old_weight = self.allocations[strategy_id].weight
                self.allocations[strategy_id].weight = weight
                self.allocations[strategy_id].capital = self.total_capital * weight
                logger.info(f"Updated {strategy_id}: {old_weight:.2%} -> {weight:.2%}")

    def get_portfolio_value(self) -> float:
        """计算组合总价值"""
        total = 0.0
        for strategy_id, positions in self.strategy_positions.items():
            for symbol, pos in positions.items():
                total += pos.get('value', 0.0)
        return total

    def get_portfolio_summary(self) -> Dict:
        """获取组合摘要"""
        return {
            'total_capital': self.total_capital,
            'portfolio_value': self.get_portfolio_value(),
            'num_strategies': len(self.allocations),
            'allocations': {sid: {'weight': alloc.weight, 'capital': alloc.capital}
                          for sid, alloc in self.allocations.items()}
        }
