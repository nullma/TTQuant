"""
生成模拟历史数据（用于测试）

当无法访问交易所 API 时，生成高质量的模拟数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulatedDataGenerator:
    """模拟数据生成器"""

    def __init__(self, seed=42):
        """
        初始化生成器

        Args:
            seed: 随机种子
        """
        np.random.seed(seed)
        self.seed = seed

    def generate_realistic_ohlcv(
        self,
        symbol='BTCUSDT',
        start_date='2024-01-01',
        days=365,
        timeframe='1h',
        initial_price=50000,
        trend=0.0003,  # 每小时 0.03% 的趋势
        volatility=0.015,  # 1.5% 波动率
        save_path=None
    ):
        """
        生成真实感的 OHLCV 数据

        使用几何布朗运动 + 趋势 + 周期性模式

        Args:
            symbol: 交易对
            start_date: 起始日期
            days: 天数
            timeframe: 时间周期
            initial_price: 初始价格
            trend: 趋势（每周期）
            volatility: 波动率
            save_path: 保存路径

        Returns:
            DataFrame: OHLCV 数据
        """
        logger.info(f"Generating simulated {symbol} {timeframe} data for {days} days...")

        # 计算周期数
        periods_per_day = {'1m': 1440, '5m': 288, '15m': 96, '1h': 24, '4h': 6, '1d': 1}
        periods = days * periods_per_day.get(timeframe, 24)

        # 生成时间序列
        start = pd.to_datetime(start_date)
        if timeframe == '1h':
            timestamps = [start + timedelta(hours=i) for i in range(periods)]
        elif timeframe == '1d':
            timestamps = [start + timedelta(days=i) for i in range(periods)]
        else:
            # 简化处理
            timestamps = [start + timedelta(hours=i) for i in range(periods)]

        # 生成收盘价（几何布朗运动 + 趋势）
        returns = np.random.randn(periods) * volatility + trend

        # 添加周期性模式（日内模式、周模式）
        for i in range(periods):
            # 日内模式：亚洲、欧洲、美洲时段
            hour_of_day = i % 24
            if 0 <= hour_of_day < 8:  # 亚洲时段，波动较小
                returns[i] *= 0.8
            elif 8 <= hour_of_day < 16:  # 欧洲时段，波动正常
                returns[i] *= 1.0
            else:  # 美洲时段，波动较大
                returns[i] *= 1.2

            # 周模式：周末波动较小
            day_of_week = (i // 24) % 7
            if day_of_week >= 5:  # 周末
                returns[i] *= 0.6

        # 计算价格
        close_prices = initial_price * np.cumprod(1 + returns)

        # 生成 OHLC
        data = []
        for i, (ts, close) in enumerate(zip(timestamps, close_prices)):
            # 生成合理的 OHLC
            volatility_factor = abs(returns[i]) * 2
            high = close * (1 + np.random.uniform(0, volatility_factor))
            low = close * (1 - np.random.uniform(0, volatility_factor))

            if i == 0:
                open_price = initial_price
            else:
                open_price = close_prices[i-1]

            # 确保 OHLC 关系正确
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # 生成成交量（与价格波动相关）
            base_volume = 1000
            volume = base_volume * (1 + abs(returns[i]) * 10) * np.random.uniform(0.5, 1.5)

            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })

        df = pd.DataFrame(data)

        logger.info(f"Generated {len(df)} candles")
        logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        # 保存到文件
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            df.to_csv(save_path, index=False)
            logger.info(f"Data saved to {save_path}")

        return df

    def get_data_summary(self, df):
        """获取数据摘要"""
        summary = {
            'total_records': len(df),
            'start_date': df['timestamp'].min(),
            'end_date': df['timestamp'].max(),
            'duration_days': (df['timestamp'].max() - df['timestamp'].min()).days,
            'price_range': {
                'min': df['low'].min(),
                'max': df['high'].max(),
                'start': df['open'].iloc[0],
                'end': df['close'].iloc[-1],
            },
            'volume_stats': {
                'mean': df['volume'].mean(),
                'median': df['volume'].median(),
                'total': df['volume'].sum(),
            },
            'returns_stats': {
                'mean': df['close'].pct_change().mean(),
                'std': df['close'].pct_change().std(),
                'sharpe': df['close'].pct_change().mean() / df['close'].pct_change().std() * np.sqrt(24*365) if df['close'].pct_change().std() > 0 else 0,
            }
        }
        return summary


def main():
    """主函数"""
    print("=" * 70)
    print("模拟历史数据生成工具")
    print("=" * 70)

    # 配置
    symbol = 'BTCUSDT'
    timeframe = '1h'
    days = 365
    initial_price = 45000  # 2024年初 BTC 价格

    # 创建生成器
    generator = SimulatedDataGenerator(seed=42)

    # 生成数据
    save_path = f'data/historical/{symbol}_{timeframe}_{days}d_simulated.csv'
    df = generator.generate_realistic_ohlcv(
        symbol=symbol,
        start_date='2024-01-01',
        days=days,
        timeframe=timeframe,
        initial_price=initial_price,
        trend=0.0003,  # 年化约 26% 的上涨趋势
        volatility=0.015,  # 1.5% 波动率
        save_path=save_path
    )

    # 显示摘要
    print("\n" + "=" * 70)
    print("数据摘要")
    print("=" * 70)

    summary = generator.get_data_summary(df)
    print(f"\n总记录数: {summary['total_records']}")
    print(f"时间范围: {summary['start_date']} 至 {summary['end_date']}")
    print(f"持续天数: {summary['duration_days']} 天")

    print(f"\n价格范围:")
    print(f"  最低价: ${summary['price_range']['min']:,.2f}")
    print(f"  最高价: ${summary['price_range']['max']:,.2f}")
    print(f"  起始价: ${summary['price_range']['start']:,.2f}")
    print(f"  结束价: ${summary['price_range']['end']:,.2f}")
    total_return = (summary['price_range']['end']/summary['price_range']['start']-1)*100
    print(f"  总收益: {total_return:.2f}%")
    print(f"  年化收益: {(1 + total_return/100)**(365/summary['duration_days']) - 1:.2%}")

    print(f"\n成交量统计:")
    print(f"  平均: {summary['volume_stats']['mean']:,.2f}")
    print(f"  中位数: {summary['volume_stats']['median']:,.2f}")
    print(f"  总计: {summary['volume_stats']['total']:,.2f}")

    print(f"\n收益率统计:")
    print(f"  平均: {summary['returns_stats']['mean']:.4%}")
    print(f"  标准差: {summary['returns_stats']['std']:.4%}")
    print(f"  夏普比率: {summary['returns_stats']['sharpe']:.4f}")

    print("\n" + "=" * 70)
    print("数据生成完成！")
    print("=" * 70)
    print(f"\n数据已保存到: {save_path}")
    print(f"\n注意: 这是模拟数据，用于测试和演示")
    print(f"生产环境请使用真实历史数据")


if __name__ == '__main__':
    main()
