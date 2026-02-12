"""
MLFactor - 机器学习因子

使用机器学习模型预测市场方向或收益率
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import logging

from .base_factor import BaseFactor, FactorValue
from .feature_engineering import FeatureEngineering
from .model_manager import ModelManager

logger = logging.getLogger(__name__)


class MLFactor(BaseFactor):
    """
    机器学习因子

    使用 scikit-learn 模型预测市场方向：
    - 1: 上涨
    - 0: 下跌
    - 置信度：模型预测概率
    """

    def __init__(self, factor_id: str, config: Dict[str, Any]):
        super().__init__(factor_id, config)

        # 模型配置
        self.model_type = config.get('model_type', 'random_forest')
        self.feature_names = config.get('feature_names', [
            'returns', 'volatility', 'rsi_14', 'macd', 'bb_position', 'volume_ratio'
        ])
        self.prediction_horizon = config.get('prediction_horizon', 1)

        # 模型和预处理器
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False

        # 模型管理器
        model_dir = config.get('model_dir', 'models')
        self.model_manager = ModelManager(model_dir)

        # 尝试加载已有模型
        if config.get('load_model', False):
            self._load_model()

        logger.info(f"MLFactor initialized: {factor_id}")
        logger.info(f"  Model type: {self.model_type}")
        logger.info(f"  Features: {self.feature_names}")
        logger.info(f"  Prediction horizon: {self.prediction_horizon}")

    def get_required_features(self) -> List[str]:
        """返回所需特征列表"""
        return self.feature_names

    def calculate(self, features: Dict[str, np.ndarray]) -> FactorValue:
        """
        计算因子值

        Args:
            features: 特征字典

        Returns:
            因子值对象
        """
        if not self.is_trained:
            logger.warning(f"Model not trained: {self.factor_id}")
            return FactorValue(
                symbol="",
                timestamp=0,
                value=0.0,
                confidence=0.0,
                metadata={'error': 'model_not_trained'}
            )

        # 验证特征
        if not self.validate_features(features):
            logger.warning(f"Invalid features: {self.factor_id}")
            return FactorValue(
                symbol="",
                timestamp=0,
                value=0.0,
                confidence=0.0,
                metadata={'error': 'invalid_features'}
            )

        # 提取最新特征
        X = self._extract_feature_vector(features)

        # 预测
        try:
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            confidence = float(max(probabilities))

            # 转换为因子值：1 (上涨) -> 1.0, 0 (下跌) -> -1.0
            factor_value = 1.0 if prediction == 1 else -1.0

            return FactorValue(
                symbol="",
                timestamp=0,
                value=factor_value,
                confidence=confidence,
                metadata={
                    'prediction': int(prediction),
                    'probabilities': probabilities.tolist()
                }
            )

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return FactorValue(
                symbol="",
                timestamp=0,
                value=0.0,
                confidence=0.0,
                metadata={'error': str(e)}
            )

    def train(self, features: Dict[str, np.ndarray], labels: np.ndarray,
              test_size: float = 0.2, random_state: int = 42):
        """
        训练模型

        Args:
            features: 特征字典
            labels: 标签数组 (1: 上涨, 0: 下跌)
            test_size: 测试集比例
            random_state: 随机种子
        """
        logger.info(f"Training model: {self.factor_id}")

        # 构建特征矩阵
        X = self._build_feature_matrix(features)
        y = labels

        # 检查数据
        if len(X) != len(y):
            raise ValueError(f"Feature and label length mismatch: {len(X)} vs {len(y)}")

        if len(X) < 100:
            logger.warning(f"Insufficient training data: {len(X)} samples")

        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        # 标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # 创建模型
        self.model = self._create_model()

        # 训练
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True

        # 评估
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)

        logger.info(f"Training completed:")
        logger.info(f"  Train samples: {len(X_train)}")
        logger.info(f"  Test samples: {len(X_test)}")
        logger.info(f"  Train accuracy: {train_score:.4f}")
        logger.info(f"  Test accuracy: {test_score:.4f}")

        # 保存模型
        metadata = {
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'train_accuracy': float(train_score),
            'test_accuracy': float(test_score),
            'prediction_horizon': self.prediction_horizon
        }
        self.model_manager.save_model(
            {'model': self.model, 'scaler': self.scaler},
            self.factor_id,
            metadata
        )

        return {
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }

    def _create_model(self):
        """创建模型"""
        if self.model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def _build_feature_matrix(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """构建特征矩阵"""
        feature_arrays = []
        for name in self.feature_names:
            if name not in features:
                raise ValueError(f"Feature not found: {name}")
            feature_arrays.append(features[name])

        # 转置：(n_features, n_samples) -> (n_samples, n_features)
        X = np.column_stack(feature_arrays)

        # 移除 NaN 和 Inf
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        return X

    def _extract_feature_vector(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """提取最新特征向量"""
        feature_values = []
        for name in self.feature_names:
            if name not in features:
                raise ValueError(f"Feature not found: {name}")
            # 取最后一个值
            value = features[name][-1] if len(features[name]) > 0 else 0.0
            feature_values.append(value)

        X = np.array([feature_values])
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        X = self.scaler.transform(X)

        return X

    def _load_model(self):
        """加载模型"""
        try:
            model_data, metadata = self.model_manager.load_model(self.factor_id)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = True
            logger.info(f"Model loaded: {self.factor_id}")
            logger.info(f"  Metadata: {metadata}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")


def create_labels_from_returns(returns: np.ndarray, horizon: int = 1) -> np.ndarray:
    """
    从收益率创建标签

    Args:
        returns: 收益率数组
        horizon: 预测周期

    Returns:
        标签数组 (1: 上涨, 0: 下跌)
    """
    labels = np.zeros(len(returns), dtype=int)

    for i in range(len(returns) - horizon):
        future_return = returns[i + horizon]
        labels[i] = 1 if future_return > 0 else 0

    return labels
