"""
Qlib 风格的数据处理器
确保特征和标签之间有严格的时间间隔，防止数据泄露
"""

import numpy as np
import pandas as pd
from typing import Tuple
from .ref_operator import RefOperator


class DataMasking:
    """
    参考 Qlib 的 Data Masking
    确保特征和标签之间有严格的时间间隔
    """

    def __init__(self, feature_gap: int = 1, label_gap: int = 1):
        """
        Args:
            feature_gap: 特征计算的时间间隔（默认1，表示 t 时刻特征只能看到 t-1）
            label_gap: 标签生成的时间间隔（默认1，表示 t 时刻标签是 t+1 的收益）
        """
        self.feature_gap = feature_gap
        self.label_gap = label_gap

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备特征，确保 t 时刻的特征只使用 t-feature_gap 以前的数据

        Args:
            df: 原始数据，必须包含 OHLCV 列

        Returns:
            特征 DataFrame
        """
        features = {}

        # 提取价格和成交量
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values

        # 1. 收益率特征（使用 Ref 算子）
        features['returns_1'] = RefOperator.returns(close, self.feature_gap)
        features['returns_5'] = RefOperator.returns(close, 5 + self.feature_gap - 1)
        features['returns_10'] = RefOperator.returns(close, 10 + self.feature_gap - 1)

        # 2. 移动平均特征
        for period in [5, 10, 20, 60]:
            ma = RefOperator.rolling_mean(close, period, self.feature_gap)
            features[f'ma_{period}'] = ma
            # MA 偏离度
            features[f'ma_{period}_ratio'] = (close - ma) / (ma + 1e-10)

        # 3. 波动率特征
        for period in [5, 10, 20]:
            features[f'volatility_{period}'] = RefOperator.rolling_std(
                close, period, self.feature_gap
            )

        # 4. 价格位置特征（当前价格在 N 日高低点的位置）
        for period in [5, 10, 20]:
            high_max = RefOperator.rolling_max(high, period, self.feature_gap)
            low_min = RefOperator.rolling_min(low, period, self.feature_gap)
            features[f'price_position_{period}'] = (
                (close - low_min) / (high_max - low_min + 1e-10)
            )

        # 5. 成交量特征
        for period in [5, 10, 20]:
            vol_ma = RefOperator.rolling_mean(volume, period, self.feature_gap)
            features[f'volume_ratio_{period}'] = volume / (vol_ma + 1e-10)

        # 6. 动量特征
        for period in [5, 10, 20]:
            features[f'momentum_{period}'] = RefOperator.delta(close, period + self.feature_gap - 1)

        return pd.DataFrame(features, index=df.index)

    def prepare_labels(self, df: pd.DataFrame, horizon: int = 1) -> np.ndarray:
        """
        准备标签，确保 t 时刻的标签是 t+label_gap 的收益

        Args:
            df: 原始数据
            horizon: 预测时间跨度（默认1，预测下一个时刻）

        Returns:
            标签数组
        """
        prices = df['close'].values
        total_gap = self.label_gap + horizon - 1

        # 标签：预测 total_gap 个时刻后的收益率
        labels = np.full(len(prices), np.nan, dtype=float)
        labels[:-total_gap] = (
            prices[total_gap:] - prices[:-total_gap]
        ) / prices[:-total_gap]

        return labels

    def align_data(
        self,
        features: pd.DataFrame,
        labels: np.ndarray
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        对齐特征和标签，移除无效数据

        Args:
            features: 特征 DataFrame
            labels: 标签数组

        Returns:
            (对齐后的特征, 对齐后的标签)
        """
        # 移除特征或标签为 NaN 的行
        valid_mask = ~(features.isna().any(axis=1) | np.isnan(labels))

        return features[valid_mask], labels[valid_mask]


class TimeSeriesSplitter:
    """
    时间序列分割，确保训练集在测试集之前
    """

    @staticmethod
    def split(
        X: pd.DataFrame,
        y: np.ndarray,
        test_size: float = 0.2,
        gap: int = 0
    ) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
        """
        时间序列分割

        Args:
            X: 特征
            y: 标签
            test_size: 测试集比例
            gap: 训练集和测试集之间的间隔（避免数据泄露）

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        n = len(X)
        n_train = int(n * (1 - test_size))

        # 训练集：[0, n_train)
        X_train = X.iloc[:n_train]
        y_train = y[:n_train]

        # 测试集：[n_train + gap, n)
        X_test = X.iloc[n_train + gap:]
        y_test = y[n_train + gap:]

        return X_train, X_test, y_train, y_test

    @staticmethod
    def walk_forward_split(
        X: pd.DataFrame,
        y: np.ndarray,
        n_splits: int = 5,
        test_size: int = None
    ):
        """
        滑动窗口分割（Walk-Forward Validation）

        Args:
            X: 特征
            y: 标签
            n_splits: 分割数量
            test_size: 测试集大小（如果为 None，自动计算）

        Yields:
            (train_idx, test_idx) 元组
        """
        n = len(X)

        if test_size is None:
            test_size = n // (n_splits + 1)

        for i in range(n_splits):
            # 训练集：从开始到当前位置
            train_end = n - (n_splits - i) * test_size
            train_idx = np.arange(0, train_end)

            # 测试集：当前位置之后的 test_size 个样本
            test_start = train_end
            test_end = min(test_start + test_size, n)
            test_idx = np.arange(test_start, test_end)

            yield train_idx, test_idx
