"""
Ref Operator - 参考 Qlib 的实现
确保 t 时刻的特征只能看到 t-1 以前的数据
"""

import numpy as np
import pandas as pd
from typing import Union


class RefOperator:
    """
    参考 Qlib 的 Ref 算子
    确保时间对齐，防止未来数据泄露
    """

    @staticmethod
    def ref(data: Union[np.ndarray, pd.Series], period: int = 1) -> np.ndarray:
        """
        向前引用数据 - 核心算子

        Args:
            data: 原始数据
            period: 引用周期（默认1，表示引用前一个时刻）

        Returns:
            引用后的数据，前 period 个值为 NaN

        Example:
            data = [1, 2, 3, 4, 5]
            ref(data, 1) = [nan, 1, 2, 3, 4]
            ref(data, 2) = [nan, nan, 1, 2, 3]
        """
        if isinstance(data, pd.Series):
            data = data.values

        result = np.empty_like(data, dtype=float)
        result[:period] = np.nan
        result[period:] = data[:-period]
        return result

    @staticmethod
    def delta(data: Union[np.ndarray, pd.Series], period: int = 1) -> np.ndarray:
        """
        计算差分（当前值 - period 前的值）
        确保不使用未来数据

        Args:
            data: 原始数据
            period: 差分周期

        Returns:
            差分后的数据

        Example:
            data = [1, 2, 3, 4, 5]
            delta(data, 1) = [nan, 1, 1, 1, 1]  # [nan, 2-1, 3-2, 4-3, 5-4]
        """
        if isinstance(data, pd.Series):
            data = data.values

        ref_data = RefOperator.ref(data, period)
        return data - ref_data

    @staticmethod
    def returns(prices: Union[np.ndarray, pd.Series], period: int = 1) -> np.ndarray:
        """
        计算收益率，确保不使用未来数据

        Args:
            prices: 价格序列
            period: 收益率周期

        Returns:
            收益率序列

        Example:
            prices = [100, 102, 101, 103, 105]
            returns(prices, 1) = [nan, 0.02, -0.0098, 0.0198, 0.0194]
        """
        if isinstance(prices, pd.Series):
            prices = prices.values

        ref_prices = RefOperator.ref(prices, period)
        return (prices - ref_prices) / (ref_prices + 1e-10)

    @staticmethod
    def rolling_mean(data: Union[np.ndarray, pd.Series], window: int, gap: int = 1) -> np.ndarray:
        """
        滚动平均，确保 t 时刻只使用 [t-window-gap+1, t-gap+1) 的数据

        Args:
            data: 原始数据
            window: 窗口大小
            gap: 时间间隔（默认1，表示不使用当前时刻数据）

        Returns:
            滚动平均

        Example:
            data = [1, 2, 3, 4, 5]
            rolling_mean(data, 3, gap=1) = [nan, nan, nan, 2, 3]
            # t=3: mean([1,2,3]) = 2
            # t=4: mean([2,3,4]) = 3
        """
        if isinstance(data, pd.Series):
            data = data.values

        result = np.full(len(data), np.nan, dtype=float)

        for i in range(window + gap - 1, len(data)):
            # 使用 [i-window-gap+1 : i-gap+1] 的数据
            start_idx = i - window - gap + 1
            end_idx = i - gap + 1
            result[i] = np.mean(data[start_idx:end_idx])

        return result

    @staticmethod
    def rolling_std(data: Union[np.ndarray, pd.Series], window: int, gap: int = 1) -> np.ndarray:
        """
        滚动标准差，确保不使用未来数据

        Args:
            data: 原始数据
            window: 窗口大小
            gap: 时间间隔

        Returns:
            滚动标准差
        """
        if isinstance(data, pd.Series):
            data = data.values

        result = np.full(len(data), np.nan, dtype=float)

        for i in range(window + gap - 1, len(data)):
            start_idx = i - window - gap + 1
            end_idx = i - gap + 1
            result[i] = np.std(data[start_idx:end_idx])

        return result

    @staticmethod
    def rolling_max(data: Union[np.ndarray, pd.Series], window: int, gap: int = 1) -> np.ndarray:
        """
        滚动最大值，确保不使用未来数据
        """
        if isinstance(data, pd.Series):
            data = data.values

        result = np.full(len(data), np.nan, dtype=float)

        for i in range(window + gap - 1, len(data)):
            start_idx = i - window - gap + 1
            end_idx = i - gap + 1
            result[i] = np.max(data[start_idx:end_idx])

        return result

    @staticmethod
    def rolling_min(data: Union[np.ndarray, pd.Series], window: int, gap: int = 1) -> np.ndarray:
        """
        滚动最小值，确保不使用未来数据
        """
        if isinstance(data, pd.Series):
            data = data.values

        result = np.full(len(data), np.nan, dtype=float)

        for i in range(window + gap - 1, len(data)):
            start_idx = i - window - gap + 1
            end_idx = i - gap + 1
            result[i] = np.min(data[start_idx:end_idx])

        return result
