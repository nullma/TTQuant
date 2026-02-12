"""
历史数据获取工具

从交易所 API 获取历史 K 线数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """历史数据获取器"""

    def __init__(self, exchange_name='binance'):
        """
        初始化数据获取器

        Args:
            exchange_name: 交易所名称（binance, okx 等）
        """
        self.exchange_name = exchange_name
        self.exchange = self._init_exchange(exchange_name)

    def _init_exchange(self, exchange_name):
        """初始化交易所连接"""
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'enableRateLimit': True,  # 启用速率限制
            'timeout': 30000,
        })
        logger.info(f"Initialized {exchange_name} exchange")
        return exchange

    def fetch_ohlcv(self, symbol, timeframe='1h', days=365, save_path=None):
        """
        获取 OHLCV 数据

        Args:
            symbol: 交易对（如 'BTC/USDT'）
            timeframe: K 线周期（1m, 5m, 15m, 1h, 4h, 1d）
            days: 获取天数
            save_path: 保存路径（可选）

        Returns:
            DataFrame: OHLCV 数据
        """
        logger.info(f"Fetching {symbol} {timeframe} data for {days} days...")

        # 计算起始时间
        since = self.exchange.parse8601(
            (datetime.now() - timedelta(days=days)).isoformat()
        )

        all_ohlcv = []
        current_since = since

        # 分批获取数据（避免单次请求数据量过大）
        while True:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=current_since,
                    limit=1000  # 每次最多 1000 条
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)
                logger.info(f"Fetched {len(ohlcv)} candles, total: {len(all_ohlcv)}")

                # 更新起始时间为最后一条数据的时间
                current_since = ohlcv[-1][0] + 1

                # 如果已经到达当前时间，停止
                if current_since >= self.exchange.milliseconds():
                    break

                # 避免触发速率限制
                time.sleep(self.exchange.rateLimit / 1000)

            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                break

        # 转换为 DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        # 转换时间戳
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 去重（可能有重复数据）
        df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)

        logger.info(f"Total {len(df)} candles fetched")
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
            'missing_values': df.isnull().sum().to_dict(),
        }
        return summary


def main():
    """主函数"""
    print("=" * 70)
    print("历史数据获取工具")
    print("=" * 70)

    # 配置
    symbol = 'BTC/USDT'
    timeframe = '1h'
    days = 365
    exchange = 'okx'  # 使用 OKX（在美国节点可访问）

    print(f"\n交易所: {exchange.upper()}")
    print(f"交易对: {symbol}")
    print(f"周期: {timeframe}")
    print(f"天数: {days}")

    # 创建数据获取器
    fetcher = HistoricalDataFetcher(exchange_name=exchange)

    # 获取数据
    save_path = f'data/historical/{symbol.replace("/", "")}_{timeframe}_{days}d_{exchange}.csv'
    df = fetcher.fetch_ohlcv(
        symbol=symbol,
        timeframe=timeframe,
        days=days,
        save_path=save_path
    )

    # 显示摘要
    print("\n" + "=" * 70)
    print("数据摘要")
    print("=" * 70)

    summary = fetcher.get_data_summary(df)
    print(f"\n总记录数: {summary['total_records']}")
    print(f"时间范围: {summary['start_date']} 至 {summary['end_date']}")
    print(f"持续天数: {summary['duration_days']} 天")

    print(f"\n价格范围:")
    print(f"  最低价: ${summary['price_range']['min']:,.2f}")
    print(f"  最高价: ${summary['price_range']['max']:,.2f}")
    print(f"  起始价: ${summary['price_range']['start']:,.2f}")
    print(f"  结束价: ${summary['price_range']['end']:,.2f}")
    print(f"  总收益: {(summary['price_range']['end']/summary['price_range']['start']-1)*100:.2f}%")

    print(f"\n成交量统计:")
    print(f"  平均: {summary['volume_stats']['mean']:,.2f}")
    print(f"  中位数: {summary['volume_stats']['median']:,.2f}")
    print(f"  总计: {summary['volume_stats']['total']:,.2f}")

    print(f"\n缺失值: {sum(summary['missing_values'].values())} 个")

    print("\n" + "=" * 70)
    print("数据获取完成！")
    print("=" * 70)
    print(f"\n数据已保存到: {save_path}")
    print(f"可以使用以下命令查看数据:")
    print(f"  import pandas as pd")
    print(f"  df = pd.read_csv('{save_path}')")
    print(f"  print(df.head())")


if __name__ == '__main__':
    main()
