"""
WorldQuant Alpha101 因子库
参考：https://github.com/RicardoMYang/WorldQuantAlpha101

所有因子使用 RefOperator 确保不使用未来数据
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from .ref_operator import RefOperator


class Alpha101:
    """
    WorldQuant Alpha101 因子实现

    所有因子计算确保：
    1. 使用 RefOperator 防止 Look-ahead Bias
    2. 时间对齐正确
    3. 返回值前面有足够的 NaN
    """

    def __init__(self):
        self.ref = RefOperator()

    # ==================== 辅助函数 ====================

    @staticmethod
    def ts_sum(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列求和（不使用未来数据）"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.sum(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_mean(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列均值"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.mean(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_std(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列标准差"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.std(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_max(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列最大值"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.max(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_min(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列最小值"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.min(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_argmax(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列最大值位置"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.argmax(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_argmin(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列最小值位置"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            result[i] = np.argmin(data[i - window + 1:i + 1])
        return result

    @staticmethod
    def ts_rank(data: np.ndarray, window: int) -> np.ndarray:
        """时间序列排名（当前值在窗口内的排名）"""
        result = np.full(len(data), np.nan, dtype=float)
        for i in range(window - 1, len(data)):
            window_data = data[i - window + 1:i + 1]
            result[i] = (window_data < data[i]).sum() / window
        return result

    @staticmethod
    def ts_corr(x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
        """时间序列相关系数"""
        result = np.full(len(x), np.nan, dtype=float)
        for i in range(window - 1, len(x)):
            x_window = x[i - window + 1:i + 1]
            y_window = y[i - window + 1:i + 1]
            if np.std(x_window) > 1e-10 and np.std(y_window) > 1e-10:
                result[i] = np.corrcoef(x_window, y_window)[0, 1]
        return result

    @staticmethod
    def ts_cov(x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
        """时间序列协方差"""
        result = np.full(len(x), np.nan, dtype=float)
        for i in range(window - 1, len(x)):
            x_window = x[i - window + 1:i + 1]
            y_window = y[i - window + 1:i + 1]
            result[i] = np.cov(x_window, y_window)[0, 1]
        return result

    @staticmethod
    def delta(data: np.ndarray, period: int = 1) -> np.ndarray:
        """差分"""
        return RefOperator.delta(data, period)

    @staticmethod
    def delay(data: np.ndarray, period: int = 1) -> np.ndarray:
        """延迟（向前引用）"""
        return RefOperator.ref(data, period)

    @staticmethod
    def rank(data: np.ndarray) -> np.ndarray:
        """横截面排名（归一化到 [0, 1]）"""
        return (data.argsort().argsort() + 1) / len(data)

    @staticmethod
    def scale(data: np.ndarray, a: float = 1.0) -> np.ndarray:
        """缩放到和为 a"""
        return data / (np.abs(data).sum() + 1e-10) * a

    @staticmethod
    def sign(data: np.ndarray) -> np.ndarray:
        """符号函数"""
        return np.sign(data)

    @staticmethod
    def log(data: np.ndarray) -> np.ndarray:
        """对数"""
        return np.log(np.abs(data) + 1e-10)

    @staticmethod
    def abs(data: np.ndarray) -> np.ndarray:
        """绝对值"""
        return np.abs(data)

    # ==================== Alpha 因子 ====================

    def alpha001(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#1: rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5
        """
        returns = self.ref.returns(close, 1)
        condition = returns < 0
        stddev = self.ts_std(returns, 20)
        power_data = np.where(condition, stddev, close) ** 2
        argmax = self.ts_argmax(power_data, 5)
        return self.rank(argmax) - 0.5

    def alpha002(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#2: -1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6)
        """
        log_vol = self.log(volume)
        delta_log_vol = self.delta(log_vol, 2)
        rank1 = self.rank(delta_log_vol)

        price_change = (close - open_) / (open_ + 1e-10)
        rank2 = self.rank(price_change)

        corr = self.ts_corr(rank1, rank2, 6)
        return -1 * corr

    def alpha003(self, open_: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#3: -1 * correlation(rank(open), rank(volume), 10)
        """
        rank_open = self.rank(open_)
        rank_volume = self.rank(volume)
        corr = self.ts_corr(rank_open, rank_volume, 10)
        return -1 * corr

    def alpha004(self, low: np.ndarray) -> np.ndarray:
        """
        Alpha#4: -1 * Ts_Rank(rank(low), 9)
        """
        rank_low = self.rank(low)
        ts_rank = self.ts_rank(rank_low, 9)
        return -1 * ts_rank

    def alpha005(self, open_: np.ndarray, vwap: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#5: rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap))))
        """
        vwap_mean = self.ts_mean(vwap, 10)
        rank1 = self.rank(open_ - vwap_mean)
        rank2 = self.rank(close - vwap)
        return rank1 * (-1 * self.abs(rank2))

    def alpha006(self, open_: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#6: -1 * correlation(open, volume, 10)
        """
        corr = self.ts_corr(open_, volume, 10)
        return -1 * corr

    def alpha007(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#7: ((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1 * 1))
        """
        adv20 = self.ts_mean(volume, 20)
        delta_close = self.delta(close, 7)
        abs_delta = self.abs(delta_close)
        ts_rank_val = self.ts_rank(abs_delta, 60)
        sign_delta = self.sign(delta_close)

        result = np.where(adv20 < volume, -1 * ts_rank_val * sign_delta, -1)
        return result

    def alpha008(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#8: -1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10)))
        """
        returns = self.ref.returns(close, 1)
        sum_open = self.ts_sum(open_, 5)
        sum_returns = self.ts_sum(returns, 5)
        product = sum_open * sum_returns
        delayed = self.delay(product, 10)
        return -1 * self.rank(product - delayed)

    def alpha009(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#9: ((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))
        """
        delta_close = self.delta(close, 1)
        ts_min_val = self.ts_min(delta_close, 5)
        ts_max_val = self.ts_max(delta_close, 5)

        result = np.where(ts_min_val > 0, delta_close,
                         np.where(ts_max_val < 0, delta_close, -1 * delta_close))
        return result

    def alpha010(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#10: rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))
        """
        delta_close = self.delta(close, 1)
        ts_min_val = self.ts_min(delta_close, 4)
        ts_max_val = self.ts_max(delta_close, 4)

        condition = np.where(ts_min_val > 0, delta_close,
                            np.where(ts_max_val < 0, delta_close, -1 * delta_close))
        return self.rank(condition)

    def alpha011(self, close: np.ndarray, low: np.ndarray, high: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#11: ((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3)))
        """
        diff = vwap - close
        rank1 = self.rank(self.ts_max(diff, 3))
        rank2 = self.rank(self.ts_min(diff, 3))
        rank3 = self.rank(self.delta(volume, 3))
        return (rank1 + rank2) * rank3

    def alpha012(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#12: sign(delta(volume, 1)) * (-1 * delta(close, 1))
        """
        return self.sign(self.delta(volume, 1)) * (-1 * self.delta(close, 1))

    def alpha013(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#13: -1 * rank(covariance(rank(close), rank(volume), 5))
        """
        rank_close = self.rank(close)
        rank_volume = self.rank(volume)
        cov = self.ts_cov(rank_close, rank_volume, 5)
        return -1 * self.rank(cov)

    def alpha014(self, open_: np.ndarray, volume: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#14: ((-1 * rank(delta(returns, 3))) * correlation(open, volume, 10))
        """
        returns = self.ref.returns(close, 1)
        rank_delta = self.rank(self.delta(returns, 3))
        corr = self.ts_corr(open_, volume, 10)
        return -1 * rank_delta * corr

    def alpha015(self, high: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#15: -1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3)
        """
        rank_high = self.rank(high)
        rank_volume = self.rank(volume)
        corr = self.ts_corr(rank_high, rank_volume, 3)
        rank_corr = self.rank(corr)
        return -1 * self.ts_sum(rank_corr, 3)

    def alpha016(self, high: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#16: -1 * rank(covariance(rank(high), rank(volume), 5))
        """
        rank_high = self.rank(high)
        rank_volume = self.rank(volume)
        cov = self.ts_cov(rank_high, rank_volume, 5)
        return -1 * self.rank(cov)

    def alpha017(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#17: (((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) * rank(ts_rank((volume / adv20), 5)))
        """
        adv20 = self.ts_mean(volume, 20)
        rank1 = self.rank(self.ts_rank(close, 10))
        delta1 = self.delta(close, 1)
        delta2 = self.delta(delta1, 1)
        rank2 = self.rank(delta2)
        rank3 = self.rank(self.ts_rank(volume / (adv20 + 1e-10), 5))
        return -1 * rank1 * rank2 * rank3

    def alpha018(self, open_: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#18: -1 * rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open, 10)))
        """
        diff = close - open_
        std = self.ts_std(self.abs(diff), 5)
        corr = self.ts_corr(close, open_, 10)
        return -1 * self.rank(std + diff + corr)

    def alpha019(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#19: ((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank((1 + sum(returns, 250)))))
        """
        returns = self.ref.returns(close, 1)
        delayed = self.delay(close, 7)
        delta_val = self.delta(close, 7)
        sign_val = self.sign((close - delayed) + delta_val)
        sum_returns = self.ts_sum(returns, 250)
        return -1 * sign_val * (1 + self.rank(1 + sum_returns))

    def alpha020(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#20: (((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open - delay(low, 1))))
        """
        rank1 = self.rank(open_ - self.delay(high, 1))
        rank2 = self.rank(open_ - self.delay(close, 1))
        rank3 = self.rank(open_ - self.delay(low, 1))
        return -1 * rank1 * rank2 * rank3

    def alpha021(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#21: ((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1 * 1) : (((sum(close, 2) / 2) < ((sum(close, 8) / 8) - stddev(close, 8))) ? 1 : (((1 < (volume / adv20)) || ((volume / adv20) == 1)) ? 1 : (-1 * 1))))
        """
        adv20 = self.ts_mean(volume, 20)
        mean8 = self.ts_mean(close, 8)
        std8 = self.ts_std(close, 8)
        mean2 = self.ts_mean(close, 2)

        condition1 = (mean8 + std8) < mean2
        condition2 = mean2 < (mean8 - std8)
        condition3 = (volume / (adv20 + 1e-10)) >= 1

        result = np.where(condition1, -1,
                         np.where(condition2, 1,
                                 np.where(condition3, 1, -1)))
        return result

    def alpha022(self, high: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#22: -1 * (delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20)))
        """
        corr = self.ts_corr(high, volume, 5)
        delta_corr = self.delta(corr, 5)
        std_close = self.ts_std(close, 20)
        return -1 * delta_corr * self.rank(std_close)

    def alpha023(self, high: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#23: (((sum(high, 20) / 20) < high) ? (-1 * delta(high, 2)) : 0)
        """
        mean_high = self.ts_mean(high, 20)
        delta_high = self.delta(high, 2)
        result = np.where(mean_high < high, -1 * delta_high, 0)
        return result

    def alpha024(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#24: ((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) || ((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1 * (close - ts_min(close, 100))) : (-1 * delta(close, 3)))
        """
        mean100 = self.ts_mean(close, 100)
        delta_mean = self.delta(mean100, 100)
        delayed = self.delay(close, 100)
        ratio = delta_mean / (delayed + 1e-10)

        ts_min_val = self.ts_min(close, 100)
        delta_close = self.delta(close, 3)

        result = np.where(ratio <= 0.05, -1 * (close - ts_min_val), -1 * delta_close)
        return result

    def alpha025(self, high: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#25: rank(((((-1 * returns) * adv20) * vwap) * (high - close)))
        """
        returns = self.ref.returns(close, 1)
        adv20 = self.ts_mean(volume, 20)
        # 使用 close 作为 vwap 的近似
        result = -1 * returns * adv20 * close * (high - close)
        return self.rank(result)

    def alpha026(self, high: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#26: -1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
        """
        ts_rank_vol = self.ts_rank(volume, 5)
        ts_rank_high = self.ts_rank(high, 5)
        corr = self.ts_corr(ts_rank_vol, ts_rank_high, 5)
        return -1 * self.ts_max(corr, 3)

    def alpha027(self, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#27: ((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1 * 1) : 1)
        """
        rank_vol = self.rank(volume)
        rank_vwap = self.rank(vwap)
        corr = self.ts_corr(rank_vol, rank_vwap, 6)
        sum_corr = self.ts_sum(corr, 2) / 2.0
        rank_sum = self.rank(sum_corr)
        result = np.where(rank_sum > 0.5, -1, 1)
        return result

    def alpha028(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#28: scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))
        """
        adv20 = self.ts_mean(volume, 20)
        corr = self.ts_corr(adv20, low, 5)
        hl_mid = (high + low) / 2
        result = corr + hl_mid - close
        return self.scale(result)

    def alpha029(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#29: (min(product(rank(rank(scale(log(sum(ts_min(rank(rank((-1 * rank(delta((close - 1), 5))))), 2), 1))))), 1), 5) + ts_rank(delay((-1 * returns), 6), 5))
        """
        returns = self.ref.returns(close, 1)
        delta_val = self.delta(close - 1, 5)
        rank1 = self.rank(-1 * self.rank(delta_val))
        rank2 = self.rank(self.rank(rank1))
        ts_min_val = self.ts_min(rank2, 2)
        sum_val = self.ts_sum(ts_min_val, 1)
        log_val = self.log(sum_val)
        scale_val = self.scale(log_val)
        rank3 = self.rank(self.rank(scale_val))
        product = rank3 * 1
        min_val = np.minimum(product, 5)

        delayed_returns = self.delay(-1 * returns, 6)
        ts_rank_val = self.ts_rank(delayed_returns, 5)

        return min_val + ts_rank_val

    def alpha030(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#30: (((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) + sign((delay(close, 2) - delay(close, 3)))))) * sum(volume, 5)) / sum(volume, 20))
        """
        sign1 = self.sign(close - self.delay(close, 1))
        sign2 = self.sign(self.delay(close, 1) - self.delay(close, 2))
        sign3 = self.sign(self.delay(close, 2) - self.delay(close, 3))
        sum_signs = sign1 + sign2 + sign3
        rank_val = self.rank(sum_signs)

        sum5 = self.ts_sum(volume, 5)
        sum20 = self.ts_sum(volume, 20)

        return (1.0 - rank_val) * sum5 / (sum20 + 1e-10)

    def alpha031(self, close: np.ndarray, low: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#31: ((rank(rank(rank(decay_linear((-1 * rank(rank(delta(close, 10)))), 10)))) + rank((-1 * delta(close, 3)))) + sign(scale(correlation(adv20, low, 12))))
        """
        adv20 = self.ts_mean(volume, 20)
        delta10 = self.delta(close, 10)
        rank1 = self.rank(self.rank(delta10))
        # decay_linear 简化为移动平均
        decay = self.ts_mean(-1 * rank1, 10)
        rank2 = self.rank(self.rank(self.rank(decay)))

        delta3 = self.delta(close, 3)
        rank3 = self.rank(-1 * delta3)

        corr = self.ts_corr(adv20, low, 12)
        scale_corr = self.scale(corr)
        sign_val = self.sign(scale_corr)

        return rank2 + rank3 + sign_val

    def alpha032(self, close: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#32: (scale(((sum(close, 7) / 7) - close)) + (20 * scale(correlation(vwap, delay(close, 5), 230))))
        """
        mean7 = self.ts_mean(close, 7)
        scale1 = self.scale(mean7 - close)

        delayed = self.delay(close, 5)
        corr = self.ts_corr(vwap, delayed, 230)
        scale2 = self.scale(corr)

        return scale1 + 20 * scale2

    def alpha033(self, open_: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#33: rank((-1 * ((1 - (open / close))^1)))
        """
        ratio = 1 - (open_ / (close + 1e-10))
        return self.rank(-1 * ratio)

    def alpha034(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#34: rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))
        """
        returns = self.ref.returns(close, 1)
        std2 = self.ts_std(returns, 2)
        std5 = self.ts_std(returns, 5)
        ratio = std2 / (std5 + 1e-10)
        rank1 = self.rank(ratio)

        delta_close = self.delta(close, 1)
        rank2 = self.rank(delta_close)

        return self.rank((1 - rank1) + (1 - rank2))

    def alpha035(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#35: ((Ts_Rank(volume, 32) * (1 - Ts_Rank(((close + high) - low), 16))) * (1 - Ts_Rank(returns, 32)))
        """
        returns = self.ref.returns(close, 1)
        ts_rank1 = self.ts_rank(volume, 32)
        ts_rank2 = self.ts_rank(close + high - low, 16)
        ts_rank3 = self.ts_rank(returns, 32)
        return ts_rank1 * (1 - ts_rank2) * (1 - ts_rank3)

    def alpha036(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#36: (((((2.21 * rank(correlation((close - open), delay(volume, 1), 15))) + (0.7 * rank((open - close)))) + (0.73 * rank(Ts_Rank(delay((-1 * returns), 6), 5)))) + rank(abs(correlation(vwap, adv20, 6)))) + (0.6 * rank((((sum(close, 200) / 200) - open) * (close - open)))))
        """
        returns = self.ref.returns(close, 1)
        adv20 = self.ts_mean(volume, 20)

        corr1 = self.ts_corr(close - open_, self.delay(volume, 1), 15)
        rank1 = 2.21 * self.rank(corr1)

        rank2 = 0.7 * self.rank(open_ - close)

        delayed_returns = self.delay(-1 * returns, 6)
        ts_rank_val = self.ts_rank(delayed_returns, 5)
        rank3 = 0.73 * self.rank(ts_rank_val)

        corr2 = self.ts_corr(vwap, adv20, 6)
        rank4 = self.rank(self.abs(corr2))

        mean200 = self.ts_mean(close, 200)
        rank5 = 0.6 * self.rank((mean200 - open_) * (close - open_))

        return rank1 + rank2 + rank3 + rank4 + rank5

    def alpha037(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#37: (rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close)))
        """
        delayed = self.delay(open_ - close, 1)
        corr = self.ts_corr(delayed, close, 200)
        rank1 = self.rank(corr)
        rank2 = self.rank(open_ - close)
        return rank1 + rank2

    def alpha038(self, open_: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Alpha#38: ((-1 * rank(Ts_Rank(close, 10))) * rank((close / open)))
        """
        ts_rank_val = self.ts_rank(close, 10)
        rank1 = self.rank(ts_rank_val)
        rank2 = self.rank(close / (open_ + 1e-10))
        return -1 * rank1 * rank2

    def alpha039(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#39: ((-1 * rank((delta(close, 7) * (1 - rank(decay_linear((volume / adv20), 9)))))) * (1 + rank(sum(returns, 250))))
        """
        returns = self.ref.returns(close, 1)
        adv20 = self.ts_mean(volume, 20)

        delta_close = self.delta(close, 7)
        vol_ratio = volume / (adv20 + 1e-10)
        # decay_linear 简化为移动平均
        decay = self.ts_mean(vol_ratio, 9)
        rank1 = self.rank(decay)

        rank2 = self.rank(delta_close * (1 - rank1))

        sum_returns = self.ts_sum(returns, 250)
        rank3 = self.rank(sum_returns)

        return -1 * rank2 * (1 + rank3)

    def alpha040(self, high: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#40: ((-1 * rank(stddev(high, 10))) * correlation(high, volume, 10))
        """
        std_high = self.ts_std(high, 10)
        rank_std = self.rank(std_high)
        corr = self.ts_corr(high, volume, 10)
        return -1 * rank_std * corr

    def alpha041(self, high: np.ndarray, low: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#41: (((high * low)^0.5) - vwap)
        """
        return np.sqrt(high * low + 1e-10) - vwap

    def alpha042(self, close: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#42: (rank((vwap - close)) / rank((vwap + close)))
        """
        rank1 = self.rank(vwap - close)
        rank2 = self.rank(vwap + close)
        return rank1 / (rank2 + 1e-10)

    def alpha043(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#43: (ts_rank((volume / adv20), 20) * ts_rank((-1 * delta(close, 7)), 8))
        """
        adv20 = self.ts_mean(volume, 20)
        ts_rank1 = self.ts_rank(volume / (adv20 + 1e-10), 20)
        delta_close = self.delta(close, 7)
        ts_rank2 = self.ts_rank(-1 * delta_close, 8)
        return ts_rank1 * ts_rank2

    def alpha044(self, high: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#44: (-1 * correlation(high, rank(volume), 5))
        """
        rank_vol = self.rank(volume)
        corr = self.ts_corr(high, rank_vol, 5)
        return -1 * corr

    def alpha045(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#45: (-1 * ((rank((sum(delay(close, 5), 20) / 20)) * correlation(close, volume, 2)) * rank(correlation(sum(close, 5), sum(close, 20), 2))))
        """
        delayed = self.delay(close, 5)
        sum_delayed = self.ts_sum(delayed, 20) / 20
        rank1 = self.rank(sum_delayed)

        corr1 = self.ts_corr(close, volume, 2)

        sum5 = self.ts_sum(close, 5)
        sum20 = self.ts_sum(close, 20)
        corr2 = self.ts_corr(sum5, sum20, 2)
        rank2 = self.rank(corr2)

        return -1 * rank1 * corr1 * rank2

    def alpha046(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#46: ((0.25 < (((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10))) ? (-1 * 1) : (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < 0) ? 1 : ((-1 * 1) * (close - delay(close, 1)))))
        """
        delayed10 = self.delay(close, 10)
        delayed20 = self.delay(close, 20)

        diff1 = (delayed20 - delayed10) / 10
        diff2 = (delayed10 - close) / 10
        condition = diff1 - diff2

        delta_close = close - self.delay(close, 1)

        result = np.where(condition > 0.25, -1,
                         np.where(condition < 0, 1, -1 * delta_close))
        return result

    def alpha047(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#47: ((((rank((1 / close)) * volume) / adv20) * ((high * rank((high - close))) / (sum(high, 5) / 5))) - rank((vwap - delay(vwap, 5))))
        """
        adv20 = self.ts_mean(volume, 20)

        rank1 = self.rank(1 / (close + 1e-10))
        part1 = (rank1 * volume) / (adv20 + 1e-10)

        rank2 = self.rank(high - close)
        mean_high = self.ts_mean(high, 5)
        part2 = (high * rank2) / (mean_high + 1e-10)

        delayed_vwap = self.delay(vwap, 5)
        rank3 = self.rank(vwap - delayed_vwap)

        return part1 * part2 - rank3

    def alpha048(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        Alpha#48: (indneutralize(((correlation(delta(close, 1), delta(delay(close, 1), 1), 250) * delta(close, 1)) / close), IndClass.subindustry) / sum(((delta(close, 1) / delay(close, 1))^2), 250))
        简化版本（去除行业中性化）
        """
        delta1 = self.delta(close, 1)
        delayed = self.delay(close, 1)
        delta2 = self.delta(delayed, 1)

        corr = self.ts_corr(delta1, delta2, 250)
        numerator = (corr * delta1) / (close + 1e-10)

        ratio = delta1 / (delayed + 1e-10)
        denominator = self.ts_sum(ratio ** 2, 250)

        return numerator / (denominator + 1e-10)

    def alpha049(self, close: np.ndarray) -> np.ndarray:
        """
        Alpha#49: (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1 * 0.1)) ? 1 : ((-1 * 1) * (close - delay(close, 1))))
        """
        delayed10 = self.delay(close, 10)
        delayed20 = self.delay(close, 20)

        diff1 = (delayed20 - delayed10) / 10
        diff2 = (delayed10 - close) / 10
        condition = diff1 - diff2

        delta_close = close - self.delay(close, 1)

        result = np.where(condition < -0.1, 1, -1 * delta_close)
        return result

    def alpha050(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """
        Alpha#50: (-1 * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5))
        """
        rank_vol = self.rank(volume)
        rank_vwap = self.rank(vwap)
        corr = self.ts_corr(rank_vol, rank_vwap, 5)
        rank_corr = self.rank(corr)
        return -1 * self.ts_max(rank_corr, 5)

    # ==================== Alpha 51-70 ====================

    def alpha051(self, close: np.ndarray) -> np.ndarray:
        """Alpha#51: (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1 * 0.05)) ? 1 : ((-1 * 1) * (close - delay(close, 1))))"""
        delayed10 = self.delay(close, 10)
        delayed20 = self.delay(close, 20)
        condition = ((delayed20 - delayed10) / 10 - (delayed10 - close) / 10) < -0.05
        return np.where(condition, 1, -1 * (close - self.delay(close, 1)))

    def alpha052(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#52: ((((-1 * ts_min(low, 5)) + delay(ts_min(low, 5), 5)) * rank(((sum(returns, 240) - sum(returns, 20)) / 220))) * ts_rank(volume, 5))"""
        returns = self.ref.returns(close, 1)
        ts_min_low = self.ts_min(low, 5)
        delayed_min = self.delay(ts_min_low, 5)
        sum240 = self.ts_sum(returns, 240)
        sum20 = self.ts_sum(returns, 20)
        rank_val = self.rank((sum240 - sum20) / 220)
        ts_rank_vol = self.ts_rank(volume, 5)
        return ((-1 * ts_min_low + delayed_min) * rank_val * ts_rank_vol)

    def alpha053(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """Alpha#53: (-1 * delta((((close - low) - (high - close)) / (close - low)), 9))"""
        numerator = (close - low) - (high - close)
        denominator = close - low + 1e-10
        return -1 * self.delta(numerator / denominator, 9)

    def alpha054(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """Alpha#54: ((-1 * ((low - close) * (open^5))) / ((low - high) * (close^5)))"""
        numerator = -1 * (low - close) * (open_ ** 5)
        denominator = (low - high + 1e-10) * (close ** 5 + 1e-10)
        return numerator / denominator

    def alpha055(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#55: (-1 * correlation(rank(((close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low, 12)))), rank(volume), 6))"""
        ts_min_low = self.ts_min(low, 12)
        ts_max_high = self.ts_max(high, 12)
        ratio = (close - ts_min_low) / (ts_max_high - ts_min_low + 1e-10)
        rank1 = self.rank(ratio)
        rank2 = self.rank(volume)
        return -1 * self.ts_corr(rank1, rank2, 6)

    def alpha056(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#56: (0 - (1 * (rank((sum(returns, 10) / sum(sum(returns, 2), 3))) * rank((returns * cap)))))"""
        returns = self.ref.returns(close, 1)
        sum10 = self.ts_sum(returns, 10)
        sum2 = self.ts_sum(returns, 2)
        sum_sum = self.ts_sum(sum2, 3)
        rank1 = self.rank(sum10 / (sum_sum + 1e-10))
        # cap 用 volume 近似
        rank2 = self.rank(returns * volume)
        return -1 * rank1 * rank2

    def alpha057(self, close: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#57: (0 - (1 * ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2))))"""
        ts_argmax_val = self.ts_argmax(close, 30)
        rank_val = self.rank(ts_argmax_val)
        decay = self.ts_mean(rank_val, 2)
        return -1 * (close - vwap) / (decay + 1e-10)

    def alpha058(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#58: (-1 * Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, IndClass.sector), volume, 3.92795), 7.89291), 5.50322))"""
        # 简化版本
        corr = self.ts_corr(close, volume, 4)
        decay = self.ts_mean(corr, 8)
        return -1 * self.ts_rank(decay, 6)

    def alpha059(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#59: (-1 * Ts_Rank(decay_linear(correlation(IndNeutralize(((vwap * 0.728317) + (vwap * (1 - 0.728317))), IndClass.industry), volume, 4.25197), 16.2289), 8.19648))"""
        # 简化版本
        corr = self.ts_corr(close, volume, 4)
        decay = self.ts_mean(corr, 16)
        return -1 * self.ts_rank(decay, 8)

    def alpha060(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#60: (0 - (1 * ((2 * scale(rank(((((close - low) - (high - close)) / (high - low)) * volume)))) - scale(rank(ts_argmax(close, 10))))))"""
        ratio = ((close - low) - (high - close)) / (high - low + 1e-10)
        rank1 = self.rank(ratio * volume)
        scale1 = self.scale(rank1)

        ts_argmax_val = self.ts_argmax(close, 10)
        rank2 = self.rank(ts_argmax_val)
        scale2 = self.scale(rank2)

        return -1 * (2 * scale1 - scale2)

    def alpha061(self, vwap: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#61: (rank((vwap - ts_min(vwap, 16.1219))) < rank(correlation(vwap, adv180, 17.9282)))"""
        adv180 = self.ts_mean(volume, 180)
        ts_min_vwap = self.ts_min(vwap, 16)
        rank1 = self.rank(vwap - ts_min_vwap)
        corr = self.ts_corr(vwap, adv180, 18)
        rank2 = self.rank(corr)
        return (rank1 < rank2).astype(float)

    def alpha062(self, high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#62: ((rank(correlation(vwap, sum(adv20, 22.4101), 9.91009)) < rank(((rank(open) + rank(open)) < (rank(((high + low) / 2)) + rank(high))))) * -1)"""
        adv20 = self.ts_mean(volume, 20)
        # 简化版本
        return -1 * self.rank(self.ts_corr(high, adv20, 10))

    def alpha063(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#63: ((rank(decay_linear(delta(IndNeutralize(close, IndClass.industry), 2.25164), 8.22237)) - rank(decay_linear(correlation(((vwap * 0.318108) + (open * (1 - 0.318108))), sum(adv180, 37.2467), 13.557), 12.2883))) * -1)"""
        # 简化版本
        delta_close = self.delta(close, 2)
        decay1 = self.ts_mean(delta_close, 8)
        rank1 = self.rank(decay1)

        adv180 = self.ts_mean(volume, 180)
        corr = self.ts_corr(close, adv180, 14)
        decay2 = self.ts_mean(corr, 12)
        rank2 = self.rank(decay2)

        return -1 * (rank1 - rank2)

    def alpha064(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#64: ((rank(correlation(sum(((open * 0.178404) + (low * (1 - 0.178404))), 12.7054), sum(adv120, 12.7054), 16.6208)) < rank(delta(((((high + low) / 2) * 0.178404) + (vwap * (1 - 0.178404))), 3.69741))) * -1)"""
        # 简化版本
        adv120 = self.ts_mean(volume, 120)
        weighted = open_ * 0.178 + low * 0.822
        sum_weighted = self.ts_sum(weighted, 13)
        sum_adv = self.ts_sum(adv120, 13)
        corr = self.ts_corr(sum_weighted, sum_adv, 17)
        rank1 = self.rank(corr)

        hl_mid = (high + low) / 2
        delta_val = self.delta(hl_mid, 4)
        rank2 = self.rank(delta_val)

        return -1 * (rank1 < rank2).astype(float)

    def alpha065(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#65: ((rank(correlation(((open * 0.00817205) + (vwap * (1 - 0.00817205))), sum(adv60, 8.6911), 6.40374)) < rank((open - ts_min(open, 13.635)))) * -1)"""
        adv60 = self.ts_mean(volume, 60)
        weighted = open_ * 0.008 + close * 0.992
        sum_adv = self.ts_sum(adv60, 9)
        corr = self.ts_corr(weighted, sum_adv, 6)
        rank1 = self.rank(corr)

        ts_min_open = self.ts_min(open_, 14)
        rank2 = self.rank(open_ - ts_min_open)

        return -1 * (rank1 < rank2).astype(float)

    def alpha066(self, close: np.ndarray, vwap: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#66: ((rank(decay_linear(delta(vwap, 3.51013), 7.23052)) + Ts_Rank(decay_linear(((((low * 0.96633) + (low * (1 - 0.96633))) - vwap) / (open - ((high + low) / 2))), 11.4157), 6.72611)) * -1)"""
        # 简化版本
        delta_vwap = self.delta(vwap, 4)
        decay1 = self.ts_mean(delta_vwap, 7)
        rank1 = self.rank(decay1)

        returns = self.ref.returns(close, 1)
        decay2 = self.ts_mean(returns, 11)
        ts_rank_val = self.ts_rank(decay2, 7)

        return -1 * (rank1 + ts_rank_val)

    def alpha067(self, high: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#67: ((rank((high - ts_min(high, 2.14593)))^rank(correlation(IndNeutralize(vwap, IndClass.sector), IndNeutralize(adv20, IndClass.subindustry), 6.02936))) * -1)"""
        # 简化版本
        adv20 = self.ts_mean(volume, 20)
        ts_min_high = self.ts_min(high, 2)
        rank1 = self.rank(high - ts_min_high)
        corr = self.ts_corr(close, adv20, 6)
        rank2 = self.rank(corr)
        return -1 * (rank1 ** rank2)

    def alpha068(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#68: ((Ts_Rank(correlation(rank(high), rank(adv15), 8.91644), 13.9333) < rank(delta(((close * 0.518371) + (low * (1 - 0.518371))), 1.06157))) * -1)"""
        adv15 = self.ts_mean(volume, 15)
        rank_high = self.rank(high)
        rank_adv = self.rank(adv15)
        corr = self.ts_corr(rank_high, rank_adv, 9)
        ts_rank_val = self.ts_rank(corr, 14)

        weighted = close * 0.518 + low * 0.482
        delta_val = self.delta(weighted, 1)
        rank_delta = self.rank(delta_val)

        return -1 * (ts_rank_val < rank_delta).astype(float)

    def alpha069(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#69: ((rank(ts_max(delta(IndNeutralize(vwap, IndClass.industry), 2.72412), 4.79344))^Ts_Rank(correlation(((close * 0.490655) + (vwap * (1 - 0.490655))), adv20, 4.92416), 9.0615)) * -1)"""
        # 简化版本
        adv20 = self.ts_mean(volume, 20)
        delta_close = self.delta(close, 3)
        ts_max_val = self.ts_max(delta_close, 5)
        rank1 = self.rank(ts_max_val)

        weighted = close * 0.491 + close * 0.509
        corr = self.ts_corr(weighted, adv20, 5)
        ts_rank_val = self.ts_rank(corr, 9)

        return -1 * (rank1 ** ts_rank_val)

    def alpha070(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#70: ((rank(delta(vwap, 1.29456))^Ts_Rank(correlation(IndNeutralize(close, IndClass.industry), adv50, 17.8256), 17.9171)) * -1)"""
        # 简化版本
        adv50 = self.ts_mean(volume, 50)
        delta_close = self.delta(close, 1)
        rank1 = self.rank(delta_close)

        corr = self.ts_corr(close, adv50, 18)
        ts_rank_val = self.ts_rank(corr, 18)

        return -1 * (rank1 ** ts_rank_val)

    # ==================== Alpha 71-90 ====================

    def alpha071(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#71: max(Ts_Rank(decay_linear(correlation(Ts_Rank(close, 3.43976), Ts_Rank(adv180, 12.0647), 18.0175), 4.20501), 15.6948), Ts_Rank(decay_linear((rank(((low + open) - (vwap + vwap)))^2), 16.4662), 4.4388))"""
        adv180 = self.ts_mean(volume, 180)
        ts_rank1 = self.ts_rank(close, 3)
        ts_rank2 = self.ts_rank(adv180, 12)
        corr = self.ts_corr(ts_rank1, ts_rank2, 18)
        decay1 = self.ts_mean(corr, 4)
        part1 = self.ts_rank(decay1, 16)

        returns = self.ref.returns(close, 1)
        decay2 = self.ts_mean(returns ** 2, 16)
        part2 = self.ts_rank(decay2, 4)

        return np.maximum(part1, part2)

    def alpha072(self, high: np.ndarray, low: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#72: (rank(decay_linear(correlation(((high + low) / 2), adv40, 8.93345), 10.1519)) / rank(decay_linear(correlation(Ts_Rank(vwap, 3.72469), Ts_Rank(volume, 18.5188), 6.86671), 2.95011)))"""
        adv40 = self.ts_mean(volume, 40)
        hl_mid = (high + low) / 2
        corr1 = self.ts_corr(hl_mid, adv40, 9)
        decay1 = self.ts_mean(corr1, 10)
        rank1 = self.rank(decay1)

        ts_rank_vwap = self.ts_rank(vwap, 4)
        ts_rank_vol = self.ts_rank(volume, 19)
        corr2 = self.ts_corr(ts_rank_vwap, ts_rank_vol, 7)
        decay2 = self.ts_mean(corr2, 3)
        rank2 = self.rank(decay2)

        return rank1 / (rank2 + 1e-10)

    def alpha073(self, open_: np.ndarray, low: np.ndarray, close: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#73: (max(rank(decay_linear(delta(vwap, 4.72775), 2.91864)), Ts_Rank(decay_linear(((delta(((open * 0.147155) + (low * (1 - 0.147155))), 2.03608) / ((open * 0.147155) + (low * (1 - 0.147155)))) * -1), 3.33829), 16.7411)) * -1)"""
        # 简化版本
        delta_vwap = self.delta(vwap, 5)
        decay1 = self.ts_mean(delta_vwap, 3)
        rank1 = self.rank(decay1)

        weighted = open_ * 0.147 + low * 0.853
        delta_weighted = self.delta(weighted, 2)
        ratio = -1 * delta_weighted / (weighted + 1e-10)
        decay2 = self.ts_mean(ratio, 3)
        ts_rank_val = self.ts_rank(decay2, 17)

        return -1 * np.maximum(rank1, ts_rank_val)

    def alpha074(self, high: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#74: ((rank(correlation(close, sum(adv30, 37.4843), 15.1365)) < rank(correlation(rank(((high * 0.0261661) + (vwap * (1 - 0.0261661)))), rank(volume), 11.4791))) * -1)"""
        adv30 = self.ts_mean(volume, 30)
        sum_adv = self.ts_sum(adv30, 37)
        corr1 = self.ts_corr(close, sum_adv, 15)
        rank1 = self.rank(corr1)

        weighted = high * 0.026 + vwap * 0.974
        rank_weighted = self.rank(weighted)
        rank_vol = self.rank(volume)
        corr2 = self.ts_corr(rank_weighted, rank_vol, 11)
        rank2 = self.rank(corr2)

        return -1 * (rank1 < rank2).astype(float)

    def alpha075(self, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#75: (rank(correlation(vwap, volume, 4.24304)) < rank(correlation(rank(low), rank(adv50), 12.4413)))"""
        adv50 = self.ts_mean(volume, 50)
        corr1 = self.ts_corr(vwap, volume, 4)
        rank1 = self.rank(corr1)

        rank_low = self.rank(low)
        rank_adv = self.rank(adv50)
        corr2 = self.ts_corr(rank_low, rank_adv, 12)
        rank2 = self.rank(corr2)

        return (rank1 < rank2).astype(float)

    def alpha076(self, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#76: (max(rank(decay_linear(delta(vwap, 1.24383), 11.8259)), Ts_Rank(decay_linear(Ts_Rank(correlation(IndNeutralize(low, IndClass.sector), adv81, 8.14941), 19.569), 17.1543), 19.383)) * -1)"""
        # 简化版本
        adv81 = self.ts_mean(volume, 81)
        delta_vwap = self.delta(vwap, 1)
        decay1 = self.ts_mean(delta_vwap, 12)
        rank1 = self.rank(decay1)

        corr = self.ts_corr(low, adv81, 8)
        ts_rank1 = self.ts_rank(corr, 20)
        decay2 = self.ts_mean(ts_rank1, 17)
        ts_rank2 = self.ts_rank(decay2, 19)

        return -1 * np.maximum(rank1, ts_rank2)

    def alpha077(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#77: min(rank(decay_linear(((((high + low) / 2) + high) - (vwap + high)), 20.0451)), rank(decay_linear(correlation(((high + low) / 2), adv40, 3.1614), 5.64125)))"""
        adv40 = self.ts_mean(volume, 40)
        hl_mid = (high + low) / 2
        diff = hl_mid + high - vwap - high
        decay1 = self.ts_mean(diff, 20)
        rank1 = self.rank(decay1)

        corr = self.ts_corr(hl_mid, adv40, 3)
        decay2 = self.ts_mean(corr, 6)
        rank2 = self.rank(decay2)

        return np.minimum(rank1, rank2)

    def alpha078(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#78: (rank(correlation(sum(((low * 0.352233) + (vwap * (1 - 0.352233))), 19.7428), sum(adv40, 19.7428), 6.83313))^rank(correlation(rank(vwap), rank(volume), 5.77492)))"""
        adv40 = self.ts_mean(volume, 40)
        weighted = low * 0.352 + vwap * 0.648
        sum_weighted = self.ts_sum(weighted, 20)
        sum_adv = self.ts_sum(adv40, 20)
        corr1 = self.ts_corr(sum_weighted, sum_adv, 7)
        rank1 = self.rank(corr1)

        rank_vwap = self.rank(vwap)
        rank_vol = self.rank(volume)
        corr2 = self.ts_corr(rank_vwap, rank_vol, 6)
        rank2 = self.rank(corr2)

        return rank1 ** rank2

    def alpha079(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#79: (rank(delta(IndNeutralize(((close * 0.60733) + (open * (1 - 0.60733))), IndClass.sector), 1.23438)) < rank(correlation(Ts_Rank(vwap, 3.60973), Ts_Rank(adv150, 9.18637), 14.6644)))"""
        # 简化版本
        adv150 = self.ts_mean(volume, 150)
        weighted = close * 0.607 + open_ * 0.393
        delta_val = self.delta(weighted, 1)
        rank1 = self.rank(delta_val)

        ts_rank_close = self.ts_rank(close, 4)
        ts_rank_adv = self.ts_rank(adv150, 9)
        corr = self.ts_corr(ts_rank_close, ts_rank_adv, 15)
        rank2 = self.rank(corr)

        return (rank1 < rank2).astype(float)

    def alpha080(self, open_: np.ndarray, high: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#80: ((rank(Sign(delta(IndNeutralize(((open * 0.868128) + (high * (1 - 0.868128))), IndClass.industry), 4.04545)))^Ts_Rank(correlation(high, adv10, 5.11456), 5.53756)) * -1)"""
        # 简化版本
        adv10 = self.ts_mean(volume, 10)
        weighted = open_ * 0.868 + high * 0.132
        delta_val = self.delta(weighted, 4)
        sign_val = self.sign(delta_val)
        rank1 = self.rank(sign_val)

        corr = self.ts_corr(high, adv10, 5)
        ts_rank_val = self.ts_rank(corr, 6)

        return -1 * (rank1 ** ts_rank_val)

    def alpha081(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#81: ((rank(Log(product(rank((rank(correlation(vwap, sum(adv10, 49.6054), 8.47743))^4)), 14.9655))) < rank(correlation(rank(vwap), rank(volume), 5.07914))) * -1)"""
        adv10 = self.ts_mean(volume, 10)
        corr = self.ts_corr(vwap, adv10, 8)
        rank_corr = self.rank(corr)
        return -1 * self.rank(rank_corr)

    def alpha082(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#82: (min(rank(decay_linear(delta(open, 1.46063), 14.8717)), Ts_Rank(decay_linear(correlation(IndNeutralize(volume, IndClass.sector), ((open * 0.634196) + (open * (1 - 0.634196))), 17.4842), 6.92131), 13.4283)) * -1)"""
        # 简化版本
        delta_open = self.delta(open_, 1)
        decay1 = self.ts_mean(delta_open, 15)
        rank1 = self.rank(decay1)

        corr = self.ts_corr(volume, open_, 17)
        decay2 = self.ts_mean(corr, 7)
        ts_rank_val = self.ts_rank(decay2, 13)

        return -1 * np.minimum(rank1, ts_rank_val)

    def alpha083(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#83: ((rank(delay(((high - low) / (sum(close, 5) / 5)), 2)) * rank(rank(volume))) / (((high - low) / (sum(close, 5) / 5)) / (vwap - close)))"""
        hl_range = high - low
        mean_close = self.ts_mean(close, 5)
        ratio = hl_range / (mean_close + 1e-10)
        delayed = self.delay(ratio, 2)
        rank1 = self.rank(delayed)
        rank2 = self.rank(self.rank(volume))
        numerator = rank1 * rank2
        denominator = ratio / (vwap - close + 1e-10)
        return numerator / (denominator + 1e-10)

    def alpha084(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#84: SignedPower(Ts_Rank((vwap - ts_max(vwap, 15.3217)), 20.7127), delta(close, 4.96796))"""
        ts_max_vwap = self.ts_max(vwap, 15)
        ts_rank_val = self.ts_rank(vwap - ts_max_vwap, 21)
        delta_close = self.delta(close, 5)
        return self.sign(ts_rank_val) * (np.abs(ts_rank_val) ** delta_close)

    def alpha085(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#85: (rank(correlation(((high * 0.876703) + (close * (1 - 0.876703))), adv30, 9.61331))^rank(correlation(Ts_Rank(((high + low) / 2), 3.70596), Ts_Rank(volume, 10.1595), 7.11408)))"""
        adv30 = self.ts_mean(volume, 30)
        weighted = high * 0.877 + close * 0.123
        corr1 = self.ts_corr(weighted, adv30, 10)
        rank1 = self.rank(corr1)

        hl_mid = (high + low) / 2
        ts_rank1 = self.ts_rank(hl_mid, 4)
        ts_rank2 = self.ts_rank(volume, 10)
        corr2 = self.ts_corr(ts_rank1, ts_rank2, 7)
        rank2 = self.rank(corr2)

        return rank1 ** rank2

    def alpha086(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#86: ((Ts_Rank(correlation(close, sum(adv20, 14.7444), 6.00049), 20.4195) < rank(((open + close) - (vwap + open)))) * -1)"""
        adv20 = self.ts_mean(volume, 20)
        sum_adv = self.ts_sum(adv20, 15)
        corr = self.ts_corr(close, sum_adv, 6)
        ts_rank_val = self.ts_rank(corr, 20)

        rank_val = self.rank((open_ + close) - (vwap + open_))

        return -1 * (ts_rank_val < rank_val).astype(float)

    def alpha087(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#87: (max(rank(decay_linear(delta(((close * 0.369701) + (vwap * (1 - 0.369701))), 1.91233), 2.65461)), Ts_Rank(decay_linear(abs(correlation(IndNeutralize(adv81, IndClass.industry), close, 13.4132)), 4.89768), 14.4535)) * -1)"""
        # 简化版本
        adv81 = self.ts_mean(volume, 81)
        weighted = close * 0.370 + vwap * 0.630
        delta_val = self.delta(weighted, 2)
        decay1 = self.ts_mean(delta_val, 3)
        rank1 = self.rank(decay1)

        corr = self.ts_corr(adv81, close, 13)
        abs_corr = self.abs(corr)
        decay2 = self.ts_mean(abs_corr, 5)
        ts_rank_val = self.ts_rank(decay2, 14)

        return -1 * np.maximum(rank1, ts_rank_val)

    def alpha088(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#88: min(rank(decay_linear(((rank(open) + rank(low)) - (rank(high) + rank(close))), 8.06882)), Ts_Rank(decay_linear(correlation(Ts_Rank(close, 8.44728), Ts_Rank(adv60, 20.6966), 8.01266), 6.65053), 2.61957))"""
        adv60 = self.ts_mean(volume, 60)
        rank_sum = self.rank(open_) + self.rank(low) - self.rank(high) - self.rank(close)
        decay1 = self.ts_mean(rank_sum, 8)
        rank1 = self.rank(decay1)

        ts_rank_close = self.ts_rank(close, 8)
        ts_rank_adv = self.ts_rank(adv60, 21)
        corr = self.ts_corr(ts_rank_close, ts_rank_adv, 8)
        decay2 = self.ts_mean(corr, 7)
        ts_rank_val = self.ts_rank(decay2, 3)

        return np.minimum(rank1, ts_rank_val)

    def alpha089(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#89: (Ts_Rank(decay_linear(correlation(((low * 0.967285) + (low * (1 - 0.967285))), adv10, 6.94279), 5.51607), 3.79744) - Ts_Rank(decay_linear(delta(IndNeutralize(vwap, IndClass.industry), 3.48158), 10.1466), 15.3012))"""
        # 简化版本
        adv10 = self.ts_mean(volume, 10)
        corr = self.ts_corr(close, adv10, 7)
        decay1 = self.ts_mean(corr, 6)
        ts_rank1 = self.ts_rank(decay1, 4)

        delta_vwap = self.delta(vwap, 3)
        decay2 = self.ts_mean(delta_vwap, 10)
        ts_rank2 = self.ts_rank(decay2, 15)

        return ts_rank1 - ts_rank2

    def alpha090(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#90: ((rank((close - ts_max(close, 4.66719)))^Ts_Rank(correlation(IndNeutralize(adv40, IndClass.subindustry), low, 5.38375), 3.21856)) * -1)"""
        # 简化版本
        adv40 = self.ts_mean(volume, 40)
        ts_max_close = self.ts_max(close, 5)
        rank1 = self.rank(close - ts_max_close)

        corr = self.ts_corr(adv40, close, 5)
        ts_rank_val = self.ts_rank(corr, 3)

        return -1 * (rank1 ** ts_rank_val)

    def alpha091(self, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#91: ((Ts_Rank(decay_linear(decay_linear(correlation(IndNeutralize(close, IndClass.industry), volume, 9.74928), 16.398), 3.83219), 4.8667) - rank(decay_linear(correlation(vwap, adv30, 4.01303), 2.6809))) * -1)"""
        # 简化版本
        adv30 = self.ts_mean(volume, 30)
        corr1 = self.ts_corr(close, volume, 10)
        decay1 = self.ts_mean(corr1, 16)
        decay2 = self.ts_mean(decay1, 4)
        ts_rank_val = self.ts_rank(decay2, 5)

        corr2 = self.ts_corr(vwap, adv30, 4)
        decay3 = self.ts_mean(corr2, 3)
        rank_val = self.rank(decay3)

        return -1 * (ts_rank_val - rank_val)

    def alpha092(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#92: min(Ts_Rank(decay_linear(((((high + low) / 2) + close) < (low + open)), 14.7221), 18.8683), Ts_Rank(decay_linear(correlation(rank(low), rank(adv30), 7.58555), 6.94024), 6.80584))"""
        adv30 = self.ts_mean(volume, 30)
        hl_mid = (high + low) / 2
        condition = (hl_mid + close) < (low + open_)
        decay1 = self.ts_mean(condition.astype(float), 15)
        ts_rank1 = self.ts_rank(decay1, 19)

        rank_low = self.rank(low)
        rank_adv = self.rank(adv30)
        corr = self.ts_corr(rank_low, rank_adv, 8)
        decay2 = self.ts_mean(corr, 7)
        ts_rank2 = self.ts_rank(decay2, 7)

        return np.minimum(ts_rank1, ts_rank2)

    def alpha093(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#93: (Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, IndClass.industry), adv81, 17.4193), 19.848), 7.54455) / rank(decay_linear(delta(((close * 0.524434) + (vwap * (1 - 0.524434))), 2.77377), 16.2664)))"""
        # 简化版本
        adv81 = self.ts_mean(volume, 81)
        corr = self.ts_corr(vwap, adv81, 17)
        decay1 = self.ts_mean(corr, 20)
        ts_rank_val = self.ts_rank(decay1, 8)

        weighted = close * 0.524 + vwap * 0.476
        delta_val = self.delta(weighted, 3)
        decay2 = self.ts_mean(delta_val, 16)
        rank_val = self.rank(decay2)

        return ts_rank_val / (rank_val + 1e-10)

    def alpha094(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#94: ((rank((vwap - ts_min(vwap, 11.5783)))^Ts_Rank(correlation(Ts_Rank(vwap, 19.6462), Ts_Rank(adv60, 4.02992), 18.0926), 2.70756)) * -1)"""
        adv60 = self.ts_mean(volume, 60)
        ts_min_vwap = self.ts_min(vwap, 12)
        rank1 = self.rank(vwap - ts_min_vwap)

        ts_rank_vwap = self.ts_rank(vwap, 20)
        ts_rank_adv = self.ts_rank(adv60, 4)
        corr = self.ts_corr(ts_rank_vwap, ts_rank_adv, 18)
        ts_rank_corr = self.ts_rank(corr, 3)

        return -1 * (rank1 ** ts_rank_corr)

    def alpha095(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#95: (rank((open - ts_min(open, 12.4105))) < Ts_Rank((rank(correlation(sum(((high + low) / 2), 19.1351), sum(adv40, 19.1351), 12.8742))^5), 11.7584))"""
        adv40 = self.ts_mean(volume, 40)
        ts_min_open = self.ts_min(open_, 12)
        rank1 = self.rank(open_ - ts_min_open)

        hl_mid = (high + low) / 2
        sum_hl = self.ts_sum(hl_mid, 19)
        sum_adv = self.ts_sum(adv40, 19)
        corr = self.ts_corr(sum_hl, sum_adv, 13)
        rank_corr = self.rank(corr)
        power = rank_corr ** 5
        ts_rank_val = self.ts_rank(power, 12)

        return (rank1 < ts_rank_val).astype(float)

    def alpha096(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#96: (max(Ts_Rank(decay_linear(correlation(rank(vwap), rank(volume), 3.83878), 4.16783), 8.38151), Ts_Rank(decay_linear(Ts_ArgMax(correlation(Ts_Rank(close, 7.45404), Ts_Rank(adv60, 4.13242), 3.65459), 12.6556), 14.0365), 13.4143)) * -1)"""
        adv60 = self.ts_mean(volume, 60)
        rank_vwap = self.rank(vwap)
        rank_vol = self.rank(volume)
        corr1 = self.ts_corr(rank_vwap, rank_vol, 4)
        decay1 = self.ts_mean(corr1, 4)
        ts_rank1 = self.ts_rank(decay1, 8)

        ts_rank_close = self.ts_rank(close, 7)
        ts_rank_adv = self.ts_rank(adv60, 4)
        corr2 = self.ts_corr(ts_rank_close, ts_rank_adv, 4)
        ts_argmax_val = self.ts_argmax(corr2, 13)
        decay2 = self.ts_mean(ts_argmax_val, 14)
        ts_rank2 = self.ts_rank(decay2, 13)

        return -1 * np.maximum(ts_rank1, ts_rank2)

    def alpha097(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#97: ((rank(decay_linear(delta(IndNeutralize(((low * 0.721001) + (vwap * (1 - 0.721001))), IndClass.industry), 3.3705), 20.4523)) - Ts_Rank(decay_linear(Ts_Rank(correlation(Ts_Rank(low, 7.87871), Ts_Rank(adv60, 17.255), 4.97547), 18.5925), 15.7152), 6.71659)) * -1)"""
        # 简化版本
        adv60 = self.ts_mean(volume, 60)
        weighted = low * 0.721 + close * 0.279
        delta_val = self.delta(weighted, 3)
        decay1 = self.ts_mean(delta_val, 20)
        rank1 = self.rank(decay1)

        ts_rank_low = self.ts_rank(low, 8)
        ts_rank_adv = self.ts_rank(adv60, 17)
        corr = self.ts_corr(ts_rank_low, ts_rank_adv, 5)
        ts_rank_corr = self.ts_rank(corr, 19)
        decay2 = self.ts_mean(ts_rank_corr, 16)
        ts_rank2 = self.ts_rank(decay2, 7)

        return -1 * (rank1 - ts_rank2)

    def alpha098(self, open_: np.ndarray, close: np.ndarray, volume: np.ndarray, vwap: np.ndarray) -> np.ndarray:
        """Alpha#98: (rank(decay_linear(correlation(vwap, sum(adv5, 26.4719), 4.58418), 7.18088)) - rank(decay_linear(Ts_Rank(Ts_ArgMin(correlation(rank(open), rank(adv15), 20.8187), 8.62571), 6.95668), 8.07206)))"""
        adv5 = self.ts_mean(volume, 5)
        adv15 = self.ts_mean(volume, 15)

        sum_adv5 = self.ts_sum(adv5, 26)
        corr1 = self.ts_corr(vwap, sum_adv5, 5)
        decay1 = self.ts_mean(corr1, 7)
        rank1 = self.rank(decay1)

        rank_open = self.rank(open_)
        rank_adv15 = self.rank(adv15)
        corr2 = self.ts_corr(rank_open, rank_adv15, 21)
        ts_argmin_val = self.ts_argmin(corr2, 9)
        ts_rank_val = self.ts_rank(ts_argmin_val, 7)
        decay2 = self.ts_mean(ts_rank_val, 8)
        rank2 = self.rank(decay2)

        return rank1 - rank2

    def alpha099(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#99: ((rank(correlation(sum(((high + low) / 2), 19.8975), sum(adv60, 19.8975), 8.8136)) < rank(correlation(low, volume, 6.28259))) * -1)"""
        adv60 = self.ts_mean(volume, 60)
        hl_mid = (high + low) / 2
        sum_hl = self.ts_sum(hl_mid, 20)
        sum_adv = self.ts_sum(adv60, 20)
        corr1 = self.ts_corr(sum_hl, sum_adv, 9)
        rank1 = self.rank(corr1)

        corr2 = self.ts_corr(low, volume, 6)
        rank2 = self.rank(corr2)

        return -1 * (rank1 < rank2).astype(float)

    def alpha100(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Alpha#100: (0 - (1 * (((1.5 * scale(indneutralize(indneutralize(rank(((((close - low) - (high - close)) / (high - low)) * volume)), IndClass.subindustry), IndClass.subindustry))) - scale(indneutralize((correlation(close, rank(adv20), 5) - rank(ts_argmin(close, 30))), IndClass.subindustry))) * (volume / adv20))))"""
        # 简化版本
        adv20 = self.ts_mean(volume, 20)
        ratio = ((close - low) - (high - close)) / (high - low + 1e-10)
        rank_val = self.rank(ratio * volume)
        scale1 = self.scale(rank_val)

        corr = self.ts_corr(close, self.rank(adv20), 5)
        ts_argmin_val = self.ts_argmin(close, 30)
        rank_argmin = self.rank(ts_argmin_val)
        scale2 = self.scale(corr - rank_argmin)

        result = (1.5 * scale1 - scale2) * (volume / (adv20 + 1e-10))
        return -1 * result

    def alpha101(self, open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """Alpha#101: ((close - open) / ((high - low) + .001))"""
        return (close - open_) / (high - low + 0.001)


# ==================== 因子筛选和正交化 ====================

class Alpha101Manager:
    """Alpha101 因子管理器：筛选和正交化"""

    def __init__(self):
        self.alpha = Alpha101()
        self.factor_names = [f"alpha{str(i).zfill(3)}" for i in range(1, 102)]

    def calculate_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有 101 个因子

        Args:
            data: 包含 OHLCV 数据的 DataFrame
                  必须包含列: open, high, low, close, volume
                  可选列: vwap (如果没有，用 close 近似)

        Returns:
            包含所有因子的 DataFrame
        """
        # 提取数据
        open_ = data['open'].values
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        volume = data['volume'].values
        vwap = data.get('vwap', close).values if 'vwap' in data.columns else close

        factors = pd.DataFrame(index=data.index)

        # 计算每个因子
        factor_methods = [
            ('alpha001', lambda: self.alpha.alpha001(close, volume)),
            ('alpha002', lambda: self.alpha.alpha002(open_, close, volume)),
            ('alpha003', lambda: self.alpha.alpha003(open_, volume)),
            ('alpha004', lambda: self.alpha.alpha004(low)),
            ('alpha005', lambda: self.alpha.alpha005(open_, vwap, close)),
            ('alpha006', lambda: self.alpha.alpha006(open_, volume)),
            ('alpha007', lambda: self.alpha.alpha007(close, volume)),
            ('alpha008', lambda: self.alpha.alpha008(open_, close, volume)),
            ('alpha009', lambda: self.alpha.alpha009(close)),
            ('alpha010', lambda: self.alpha.alpha010(close)),
            ('alpha011', lambda: self.alpha.alpha011(close, low, high, volume, vwap)),
            ('alpha012', lambda: self.alpha.alpha012(close, volume)),
            ('alpha013', lambda: self.alpha.alpha013(close, volume)),
            ('alpha014', lambda: self.alpha.alpha014(open_, volume, close)),
            ('alpha015', lambda: self.alpha.alpha015(high, volume)),
            ('alpha016', lambda: self.alpha.alpha016(high, volume)),
            ('alpha017', lambda: self.alpha.alpha017(close, volume, vwap)),
            ('alpha018', lambda: self.alpha.alpha018(open_, close)),
            ('alpha019', lambda: self.alpha.alpha019(close)),
            ('alpha020', lambda: self.alpha.alpha020(open_, high, low, close)),
            ('alpha021', lambda: self.alpha.alpha021(close, volume)),
            ('alpha022', lambda: self.alpha.alpha022(high, close, volume)),
            ('alpha023', lambda: self.alpha.alpha023(high, close)),
            ('alpha024', lambda: self.alpha.alpha024(close)),
            ('alpha025', lambda: self.alpha.alpha025(high, close, volume)),
            ('alpha026', lambda: self.alpha.alpha026(high, volume)),
            ('alpha027', lambda: self.alpha.alpha027(volume, vwap)),
            ('alpha028', lambda: self.alpha.alpha028(high, low, close, volume)),
            ('alpha029', lambda: self.alpha.alpha029(close, volume)),
            ('alpha030', lambda: self.alpha.alpha030(close, volume)),
            ('alpha031', lambda: self.alpha.alpha031(close, low, volume)),
            ('alpha032', lambda: self.alpha.alpha032(close, vwap)),
            ('alpha033', lambda: self.alpha.alpha033(open_, close)),
            ('alpha034', lambda: self.alpha.alpha034(close)),
            ('alpha035', lambda: self.alpha.alpha035(high, low, close, volume)),
            ('alpha036', lambda: self.alpha.alpha036(open_, close, volume, vwap)),
            ('alpha037', lambda: self.alpha.alpha037(open_, close, volume)),
            ('alpha038', lambda: self.alpha.alpha038(open_, close)),
            ('alpha039', lambda: self.alpha.alpha039(close, volume)),
            ('alpha040', lambda: self.alpha.alpha040(high, volume)),
            ('alpha041', lambda: self.alpha.alpha041(high, low, vwap)),
            ('alpha042', lambda: self.alpha.alpha042(close, vwap)),
            ('alpha043', lambda: self.alpha.alpha043(close, volume)),
            ('alpha044', lambda: self.alpha.alpha044(high, volume)),
            ('alpha045', lambda: self.alpha.alpha045(close, volume, vwap)),
            ('alpha046', lambda: self.alpha.alpha046(close)),
            ('alpha047', lambda: self.alpha.alpha047(high, low, close, volume, vwap)),
            ('alpha048', lambda: self.alpha.alpha048(close, volume)),
            ('alpha049', lambda: self.alpha.alpha049(close)),
            ('alpha050', lambda: self.alpha.alpha050(high, low, close, volume, vwap)),
            ('alpha051', lambda: self.alpha.alpha051(close)),
            ('alpha052', lambda: self.alpha.alpha052(high, low, close, volume)),
            ('alpha053', lambda: self.alpha.alpha053(high, low, close)),
            ('alpha054', lambda: self.alpha.alpha054(open_, high, low, close)),
            ('alpha055', lambda: self.alpha.alpha055(open_, high, low, close, volume)),
            ('alpha056', lambda: self.alpha.alpha056(open_, high, low, close, volume)),
            ('alpha057', lambda: self.alpha.alpha057(close, vwap)),
            ('alpha058', lambda: self.alpha.alpha058(close, volume)),
            ('alpha059', lambda: self.alpha.alpha059(close, volume)),
            ('alpha060', lambda: self.alpha.alpha060(high, low, close, volume)),
            ('alpha061', lambda: self.alpha.alpha061(vwap, volume)),
            ('alpha062', lambda: self.alpha.alpha062(high, low, volume)),
            ('alpha063', lambda: self.alpha.alpha063(high, low, close, volume)),
            ('alpha064', lambda: self.alpha.alpha064(open_, high, low, close, volume)),
            ('alpha065', lambda: self.alpha.alpha065(open_, close, volume)),
            ('alpha066', lambda: self.alpha.alpha066(close, vwap, volume)),
            ('alpha067', lambda: self.alpha.alpha067(high, close, volume)),
            ('alpha068', lambda: self.alpha.alpha068(high, low, close, volume)),
            ('alpha069', lambda: self.alpha.alpha069(open_, high, low, close, volume)),
            ('alpha070', lambda: self.alpha.alpha070(high, low, close, volume)),
            ('alpha071', lambda: self.alpha.alpha071(close, volume, vwap)),
            ('alpha072', lambda: self.alpha.alpha072(high, low, volume, vwap)),
            ('alpha073', lambda: self.alpha.alpha073(open_, low, close, vwap)),
            ('alpha074', lambda: self.alpha.alpha074(high, close, volume, vwap)),
            ('alpha075', lambda: self.alpha.alpha075(low, close, volume, vwap)),
            ('alpha076', lambda: self.alpha.alpha076(low, close, volume, vwap)),
            ('alpha077', lambda: self.alpha.alpha077(high, low, close, volume, vwap)),
            ('alpha078', lambda: self.alpha.alpha078(high, low, close, volume, vwap)),
            ('alpha079', lambda: self.alpha.alpha079(open_, close, volume)),
            ('alpha080', lambda: self.alpha.alpha080(open_, high, close, volume)),
            ('alpha081', lambda: self.alpha.alpha081(close, volume, vwap)),
            ('alpha082', lambda: self.alpha.alpha082(open_, close, volume)),
            ('alpha083', lambda: self.alpha.alpha083(high, low, close, volume, vwap)),
            ('alpha084', lambda: self.alpha.alpha084(close, volume, vwap)),
            ('alpha085', lambda: self.alpha.alpha085(high, low, close, volume)),
            ('alpha086', lambda: self.alpha.alpha086(open_, close, volume, vwap)),
            ('alpha087', lambda: self.alpha.alpha087(high, low, close, volume, vwap)),
            ('alpha088', lambda: self.alpha.alpha088(open_, high, low, close, volume)),
            ('alpha089', lambda: self.alpha.alpha089(close, volume, vwap)),
            ('alpha090', lambda: self.alpha.alpha090(close, volume, vwap)),
            ('alpha091', lambda: self.alpha.alpha091(close, volume, vwap)),
            ('alpha092', lambda: self.alpha.alpha092(open_, high, low, close, volume)),
            ('alpha093', lambda: self.alpha.alpha093(open_, high, low, close, volume, vwap)),
            ('alpha094', lambda: self.alpha.alpha094(open_, close, volume, vwap)),
            ('alpha095', lambda: self.alpha.alpha095(open_, high, low, close, volume)),
            ('alpha096', lambda: self.alpha.alpha096(open_, high, low, close, volume, vwap)),
            ('alpha097', lambda: self.alpha.alpha097(open_, high, low, close, volume)),
            ('alpha098', lambda: self.alpha.alpha098(open_, close, volume, vwap)),
            ('alpha099', lambda: self.alpha.alpha099(high, low, close, volume)),
            ('alpha100', lambda: self.alpha.alpha100(high, low, close, volume)),
            ('alpha101', lambda: self.alpha.alpha101(open_, high, low, close)),
        ]

        for factor_name, factor_func in factor_methods:
            try:
                factors[factor_name] = factor_func()
            except Exception as e:
                print(f"Error calculating {factor_name}: {e}")
                factors[factor_name] = np.full(len(data), np.nan)

        return factors

    def calculate_ic(self, factor_values: np.ndarray, returns: np.ndarray, method='spearman') -> float:
        """
        计算因子 IC (Information Coefficient)

        Args:
            factor_values: 因子值
            returns: 未来收益率
            method: 'spearman' 或 'pearson'

        Returns:
            IC 值
        """
        from scipy.stats import spearmanr, pearsonr

        # 移除 NaN
        mask = ~(np.isnan(factor_values) | np.isnan(returns))
        if mask.sum() < 10:
            return np.nan

        factor_clean = factor_values[mask]
        returns_clean = returns[mask]

        if method == 'spearman':
            ic, _ = spearmanr(factor_clean, returns_clean)
        else:
            ic, _ = pearsonr(factor_clean, returns_clean)

        return ic

    def filter_factors_by_ic(self, factors: pd.DataFrame, returns: pd.Series,
                            ic_threshold: float = 0.05) -> List[str]:
        """
        根据 IC 筛选因子

        Args:
            factors: 因子 DataFrame
            returns: 未来收益率 Series
            ic_threshold: IC 阈值

        Returns:
            通过筛选的因子名称列表
        """
        selected_factors = []

        for col in factors.columns:
            ic = self.calculate_ic(factors[col].values, returns.values)
            if not np.isnan(ic) and abs(ic) > ic_threshold:
                selected_factors.append(col)
                print(f"{col}: IC = {ic:.4f}")

        return selected_factors

    def orthogonalize_factors(self, factors: pd.DataFrame) -> pd.DataFrame:
        """
        因子正交化（施密特正交化）

        Args:
            factors: 因子 DataFrame

        Returns:
            正交化后的因子 DataFrame
        """
        from sklearn.preprocessing import StandardScaler

        # 标准化
        scaler = StandardScaler()
        factors_scaled = pd.DataFrame(
            scaler.fit_transform(factors.fillna(0)),
            index=factors.index,
            columns=factors.columns
        )

        # 施密特正交化
        orthogonal_factors = pd.DataFrame(index=factors.index)

        for i, col in enumerate(factors_scaled.columns):
            vec = factors_scaled[col].values.copy()

            # 减去在之前所有向量上的投影
            for j in range(i):
                prev_vec = orthogonal_factors.iloc[:, j].values
                projection = np.dot(vec, prev_vec) / (np.dot(prev_vec, prev_vec) + 1e-10)
                vec = vec - projection * prev_vec

            # 归一化
            norm = np.linalg.norm(vec)
            if norm > 1e-10:
                vec = vec / norm

            orthogonal_factors[col] = vec

        return orthogonal_factors

