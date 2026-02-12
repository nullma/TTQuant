"""
BaseFactor - 因子基类

设计原则：
- 所有因子继承此基类
- 支持特征计算和因子值输出
- 与 BaseStrategy 解耦，可独立使用
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class FactorValue:
    """因子值"""
    symbol: str
    timestamp: int
    value: float
    confidence: float = 1.0  # 置信度 [0, 1]
    metadata: Optional[Dict[str, Any]] = None


class BaseFactor(ABC):
    """
    因子基类

    所有因子必须实现：
    - calculate: 计算因子值
    - get_required_features: 返回所需特征列表
    """

    def __init__(self, factor_id: str, config: Dict[str, Any]):
        self.factor_id = factor_id
        self.config = config
        self.lookback_period = config.get('lookback_period', 20)

    @abstractmethod
    def calculate(self, features: Dict[str, np.ndarray]) -> FactorValue:
        """
        计算因子值

        Args:
            features: 特征字典，key 为特征名，value 为特征值数组

        Returns:
            因子值对象
        """
        pass

    @abstractmethod
    def get_required_features(self) -> List[str]:
        """
        返回所需特征列表

        Returns:
            特征名列表
        """
        pass

    def validate_features(self, features: Dict[str, np.ndarray]) -> bool:
        """
        验证特征是否完整

        Args:
            features: 特征字典

        Returns:
            是否通过验证
        """
        required = self.get_required_features()
        for feature_name in required:
            if feature_name not in features:
                return False
            if len(features[feature_name]) < self.lookback_period:
                return False
        return True
