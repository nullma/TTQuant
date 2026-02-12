"""
Factors Module - 因子库

提供技术指标、统计因子和机器学习因子
"""

from .base_factor import BaseFactor, FactorValue
from .feature_engineering import FeatureEngineering
from .model_manager import ModelManager
from .ml_factor import MLFactor, create_labels_from_returns

__all__ = [
    'BaseFactor',
    'FactorValue',
    'FeatureEngineering',
    'ModelManager',
    'MLFactor',
    'create_labels_from_returns'
]
