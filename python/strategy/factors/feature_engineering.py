"""
Feature Engineering - 特征工程

从市场数据中提取技术指标和统计特征
"""

from typing import Dict, List
from collections import deque
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FeatureEngineering:
    """
    特征工程类

    从原始市场数据提取特征：
    - 价格特征：收益率、波动率
    - 技术指标：MA、EMA、RSI、MACD、Bollinger Bands
    - 统计特征：偏度、峰度
    """

    def __init__(self, lookback_period: int = 50):
        """
        初始化特征工程

        Args:
            lookback_period: 回看周期
        """
        self.lookback_period = lookback_period
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}

    def update(self, symbol: str, price: float, volume: float):
        """
        更新市场数据

        Args:
            symbol: 交易对
            price: 价格
            volume: 成交量
        """
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback_period)
            self.volume_history[symbol] = deque(maxlen=self.lookback_period)

        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)

    def extract_features(self, symbol: str) -> Dict[str, np.ndarray]:
        """
        提取特征

        Args:
            symbol: 交易对

        Returns:
            特征字典
        """
        if symbol not in self.price_history:
            return {}

        prices = np.array(self.price_history[symbol])
        volumes = np.array(self.volume_history[symbol])

        if len(prices) < 2:
            return {}

        features = {}

        # 价格特征
        features['price'] = prices
        features['volume'] = volumes

        # 收益率
        returns = np.diff(prices) / prices[:-1]
        features['returns'] = np.concatenate([[0], returns])

        # 对数收益率
        log_returns = np.diff(np.log(prices))
        features['log_returns'] = np.concatenate([[0], log_returns])

        # 波动率（滚动标准差）
        if len(returns) >= 5:
            volatility = self._rolling_std(returns, window=5)
            features['volatility'] = np.concatenate([[0], volatility])
        else:
            features['volatility'] = np.zeros_like(prices)

        # 移动平均线
        features['ma_5'] = self._moving_average(prices, 5)
        features['ma_10'] = self._moving_average(prices, 10)
        features['ma_20'] = self._moving_average(prices, 20)

        # 指数移动平均线
        features['ema_5'] = self._exponential_moving_average(prices, 5)
        features['ema_10'] = self._exponential_moving_average(prices, 10)
        features['ema_20'] = self._exponential_moving_average(prices, 20)

        # RSI
        features['rsi_14'] = self._calculate_rsi(prices, 14)

        # MACD
        macd, signal, histogram = self._calculate_macd(prices)
        features['macd'] = macd
        features['macd_signal'] = signal
        features['macd_histogram'] = histogram

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(prices, 20, 2)
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower
        features['bb_width'] = (bb_upper - bb_lower) / (bb_middle + 1e-8)

        # 价格位置（相对于 Bollinger Bands）
        features['bb_position'] = (prices - bb_lower) / (bb_upper - bb_lower + 1e-8)

        # 成交量特征
        features['volume_ma_5'] = self._moving_average(volumes, 5)
        features['volume_ratio'] = volumes / (self._moving_average(volumes, 20) + 1e-8)

        # 统计特征
        if len(returns) >= 20:
            features['skewness'] = self._rolling_skewness(returns, 20)
            features['kurtosis'] = self._rolling_kurtosis(returns, 20)
        else:
            features['skewness'] = np.zeros_like(prices)
            features['kurtosis'] = np.zeros_like(prices)

        return features

    def _moving_average(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算移动平均"""
        if len(data) < window:
            return np.full_like(data, data.mean())

        ma = np.zeros_like(data)
        for i in range(len(data)):
            if i < window - 1:
                ma[i] = data[:i+1].mean()
            else:
                ma[i] = data[i-window+1:i+1].mean()
        return ma

    def _exponential_moving_average(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算指数移动平均"""
        alpha = 2.0 / (window + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """计算 RSI"""
        if len(prices) < period + 1:
            return np.full_like(prices, 50.0)

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gains = np.zeros(len(prices))
        avg_losses = np.zeros(len(prices))

        # 初始平均
        avg_gains[period] = gains[:period].mean()
        avg_losses[period] = losses[:period].mean()

        # 指数移动平均
        for i in range(period + 1, len(prices)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period

        rs = avg_gains / (avg_losses + 1e-8)
        rsi = 100 - (100 / (1 + rs))

        # 填充前面的值
        rsi[:period] = 50.0

        return rsi

    def _calculate_macd(self, prices: np.ndarray,
                       fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """计算 MACD"""
        ema_fast = self._exponential_moving_average(prices, fast)
        ema_slow = self._exponential_moving_average(prices, slow)
        macd = ema_fast - ema_slow
        signal_line = self._exponential_moving_average(macd, signal)
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _calculate_bollinger_bands(self, prices: np.ndarray,
                                  window: int = 20, num_std: float = 2.0) -> tuple:
        """计算 Bollinger Bands"""
        ma = self._moving_average(prices, window)
        std = np.zeros_like(prices)

        for i in range(len(prices)):
            if i < window - 1:
                std[i] = prices[:i+1].std()
            else:
                std[i] = prices[i-window+1:i+1].std()

        upper = ma + num_std * std
        lower = ma - num_std * std

        return upper, ma, lower

    def _rolling_std(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滚动标准差"""
        std = np.zeros(len(data))
        for i in range(len(data)):
            if i < window - 1:
                std[i] = data[:i+1].std()
            else:
                std[i] = data[i-window+1:i+1].std()
        return std

    def _rolling_skewness(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滚动偏度"""
        skew = np.zeros(len(data))
        for i in range(len(data)):
            if i < window - 1:
                window_data = data[:i+1]
            else:
                window_data = data[i-window+1:i+1]

            if len(window_data) >= 3:
                mean = window_data.mean()
                std = window_data.std()
                if std > 0:
                    skew[i] = ((window_data - mean) ** 3).mean() / (std ** 3)
        return skew

    def _rolling_kurtosis(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滚动峰度"""
        kurt = np.zeros(len(data))
        for i in range(len(data)):
            if i < window - 1:
                window_data = data[:i+1]
            else:
                window_data = data[i-window+1:i+1]

            if len(window_data) >= 4:
                mean = window_data.mean()
                std = window_data.std()
                if std > 0:
                    kurt[i] = ((window_data - mean) ** 4).mean() / (std ** 4) - 3
        return kurt

    def get_latest_features(self, symbol: str) -> Dict[str, float]:
        """
        获取最新的特征值（用于实时预测）

        Args:
            symbol: 交易对

        Returns:
            最新特征字典
        """
        features = self.extract_features(symbol)
        if not features:
            return {}

        latest = {}
        for key, values in features.items():
            if len(values) > 0:
                latest[key] = float(values[-1])

        return latest
