"""
BacktestDataSource - 回测数据源

职责：
1. 从 TimescaleDB 加载历史数据
2. 使用 Polars 高性能数据处理
3. 支持数据预加载和流式加载
4. 数据清洗和验证
"""

import polars as pl
import connectorx as cx
from typing import List, Dict, Optional, Iterator
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BacktestDataSource:
    """回测数据源"""

    def __init__(
        self,
        db_uri: str,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        exchange: str = 'binance',
        preload: bool = True
    ):
        """
        初始化回测数据源

        Args:
            db_uri: 数据库连接字符串
            symbols: 交易对列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            exchange: 交易所名称
            preload: 是否预加载所有数据到内存
        """
        self.db_uri = db_uri
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.exchange = exchange
        self.preload = preload

        self.data: Optional[pl.DataFrame] = None
        self._current_index = 0

        logger.info(f"BacktestDataSource initialized")
        logger.info(f"  Symbols: {symbols}")
        logger.info(f"  Period: {start_date} to {end_date}")
        logger.info(f"  Exchange: {exchange}")
        logger.info(f"  Preload: {preload}")

        if preload:
            self._load_data()

    def _load_data(self):
        """从数据库加载历史数据"""
        logger.info("Loading historical data from TimescaleDB...")

        # 构建 SQL 查询
        symbols_str = "', '".join(self.symbols)
        query = f"""
        SELECT
            time,
            symbol,
            exchange,
            last_price,
            volume,
            EXTRACT(EPOCH FROM exchange_time) * 1000000000 as exchange_time,
            EXTRACT(EPOCH FROM local_time) * 1000000000 as local_time
        FROM market_data
        WHERE symbol IN ('{symbols_str}')
          AND exchange = '{self.exchange}'
          AND time >= '{self.start_date.isoformat()}'
          AND time <= '{self.end_date.isoformat()}'
        ORDER BY time ASC
        """

        try:
            # 使用 ConnectorX 高速加载数据到 Polars
            self.data = pl.read_database_uri(
                query=query,
                uri=self.db_uri,
                engine='connectorx'
            )

            # 数据验证
            if self.data.is_empty():
                logger.warning("No data loaded from database!")
                return

            # 数据清洗
            self.data = self._clean_data(self.data)

            logger.info(f"Loaded {len(self.data)} rows of market data")
            logger.info(f"Date range: {self.data['time'].min()} to {self.data['time'].max()}")
            logger.info(f"Memory usage: {self.data.estimated_size() / 1024 / 1024:.2f} MB")

            # 显示数据统计
            for symbol in self.symbols:
                count = len(self.data.filter(pl.col('symbol') == symbol))
                logger.info(f"  {symbol}: {count} ticks")

        except Exception as e:
            logger.error(f"Failed to load data: {e}", exc_info=True)
            raise

    def _clean_data(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        数据清洗

        - 删除空值
        - 删除异常价格（价格 <= 0）
        - 删除重复数据
        """
        original_count = len(df)

        # 删除空值
        df = df.drop_nulls(subset=['last_price', 'volume'])

        # 删除异常价格
        df = df.filter(pl.col('last_price') > 0)
        df = df.filter(pl.col('volume') >= 0)

        # 删除重复数据（基于 time + symbol）
        df = df.unique(subset=['time', 'symbol'], keep='first')

        cleaned_count = len(df)
        removed_count = original_count - cleaned_count

        if removed_count > 0:
            logger.warning(f"Removed {removed_count} invalid rows during cleaning")

        return df

    def get_iterator(self) -> Iterator[Dict]:
        """
        获取数据迭代器

        Returns:
            迭代器，每次返回一条市场数据
        """
        if self.data is None or self.data.is_empty():
            logger.warning("No data available for iteration")
            return

        # 转换为字典列表进行迭代
        for row in self.data.iter_rows(named=True):
            yield {
                'symbol': row['symbol'],
                'last_price': row['last_price'],
                'volume': row['volume'],
                'exchange_time': int(row['exchange_time']),
                'local_time': int(row['local_time']),
                'exchange': row['exchange'],
                'time': row['time']
            }

    def get_data_by_symbol(self, symbol: str) -> pl.DataFrame:
        """
        获取指定交易对的数据

        Args:
            symbol: 交易对

        Returns:
            Polars DataFrame
        """
        if self.data is None:
            return pl.DataFrame()

        return self.data.filter(pl.col('symbol') == symbol)

    def get_price_at_time(self, symbol: str, timestamp: datetime) -> Optional[float]:
        """
        获取指定时间的价格（用于回测分析）

        Args:
            symbol: 交易对
            timestamp: 时间戳

        Returns:
            价格，如果没有数据则返回 None
        """
        if self.data is None:
            return None

        # 查找最接近的价格
        filtered = self.data.filter(
            (pl.col('symbol') == symbol) &
            (pl.col('time') <= timestamp)
        ).sort('time', descending=True)

        if filtered.is_empty():
            return None

        return filtered['last_price'][0]

    def get_statistics(self) -> Dict:
        """
        获取数据统计信息

        Returns:
            统计信息字典
        """
        if self.data is None or self.data.is_empty():
            return {}

        stats = {
            'total_rows': len(self.data),
            'symbols': self.symbols,
            'start_date': str(self.data['time'].min()),
            'end_date': str(self.data['time'].max()),
            'exchange': self.exchange,
            'memory_mb': self.data.estimated_size() / 1024 / 1024,
        }

        # 每个交易对的统计
        symbol_stats = {}
        for symbol in self.symbols:
            symbol_data = self.data.filter(pl.col('symbol') == symbol)
            if not symbol_data.is_empty():
                symbol_stats[symbol] = {
                    'count': len(symbol_data),
                    'min_price': float(symbol_data['last_price'].min()),
                    'max_price': float(symbol_data['last_price'].max()),
                    'avg_price': float(symbol_data['last_price'].mean()),
                    'total_volume': float(symbol_data['volume'].sum()),
                }

        stats['symbol_stats'] = symbol_stats

        return stats

    def resample_to_klines(
        self,
        symbol: str,
        interval: str = '1m'
    ) -> pl.DataFrame:
        """
        将 Tick 数据重采样为 K 线数据

        Args:
            symbol: 交易对
            interval: K 线周期（1m, 5m, 15m, 1h, 1d）

        Returns:
            K 线数据 DataFrame
        """
        if self.data is None:
            return pl.DataFrame()

        symbol_data = self.data.filter(pl.col('symbol') == symbol)

        if symbol_data.is_empty():
            return pl.DataFrame()

        # 解析时间间隔
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
        }

        if interval not in interval_map:
            raise ValueError(f"Unsupported interval: {interval}")

        # 重采样为 OHLCV
        klines = symbol_data.group_by_dynamic(
            'time',
            every=interval_map[interval],
            closed='left'
        ).agg([
            pl.col('last_price').first().alias('open'),
            pl.col('last_price').max().alias('high'),
            pl.col('last_price').min().alias('low'),
            pl.col('last_price').last().alias('close'),
            pl.col('volume').sum().alias('volume'),
        ])

        return klines.sort('time')


if __name__ == "__main__":
    # 测试数据源
    import os
    from dotenv import load_dotenv

    load_dotenv()

    db_password = os.getenv('DB_PASSWORD', 'changeme')
    db_uri = f"postgresql://ttquant:{db_password}@localhost:5432/ttquant_trading"

    # 创建数据源
    data_source = BacktestDataSource(
        db_uri=db_uri,
        symbols=['BTCUSDT', 'ETHUSDT'],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        exchange='binance',
        preload=True
    )

    # 打印统计信息
    stats = data_source.get_statistics()
    print("\n=== Data Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 测试 K 线重采样
    klines = data_source.resample_to_klines('BTCUSDT', '1h')
    print(f"\n=== BTCUSDT 1h Klines ===")
    print(klines.head(10))
