"""
回测框架演示 - 使用模拟数据

此脚本演示如何使用回测框架，不需要真实的数据库数据。
适合快速测试和学习回测框架的使用。
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backtest.engine import BacktestEngine
from backtest.order_gateway import BacktestOrderGateway, SlippageModel, CommissionConfig
from backtest.analytics import PerformanceAnalytics
from strategy.base_strategy import BaseStrategy, MarketData, Trade

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class MockDataSource:
    """模拟数据源 - 生成随机价格数据"""

    def __init__(self, symbol: str, start_date: datetime, days: int, initial_price: float = 50000.0):
        self.symbol = symbol
        self.start_date = start_date
        self.days = days
        self.initial_price = initial_price

    def get_iterator(self):
        """生成模拟的市场数据"""
        np.random.seed(42)
        price = self.initial_price

        # 每天生成 1440 个数据点（每分钟一个）
        for day in range(self.days):
            for minute in range(1440):
                # 随机游走 + 趋势
                trend = 0.0001  # 轻微上涨趋势
                volatility = 0.002  # 波动率
                price_change = price * (trend + np.random.randn() * volatility)
                price = max(price + price_change, 1.0)  # 价格不能为负

                timestamp = self.start_date + timedelta(days=day, minutes=minute)

                yield {
                    'symbol': self.symbol,
                    'last_price': price,
                    'volume': np.random.uniform(0.1, 10.0),
                    'exchange_time': int(timestamp.timestamp() * 1e9),
                    'local_time': int(timestamp.timestamp() * 1e9),
                    'exchange': 'binance',
                    'time': timestamp
                }


class SimpleMomentumStrategy(BaseStrategy):
    """简单动量策略 - 演示用"""

    def __init__(self, strategy_id: str, config: dict):
        super().__init__(strategy_id, config)

        self.symbol = config['symbol']
        self.lookback = config.get('lookback', 20)  # 回看周期
        self.threshold = config.get('threshold', 0.02)  # 动量阈值（2%）

        self.prices = []  # 价格历史
        self.position = 0  # 当前持仓

        logger.info(f"SimpleMomentumStrategy initialized")
        logger.info(f"  Symbol: {self.symbol}")
        logger.info(f"  Lookback: {self.lookback}")
        logger.info(f"  Threshold: {self.threshold * 100:.1f}%")

    def on_market_data(self, md: MarketData):
        """行情回调"""
        if md.symbol != self.symbol:
            return

        # 记录价格
        self.prices.append(md.last_price)

        # 等待足够的数据
        if len(self.prices) < self.lookback:
            return

        # 只保留最近的数据
        if len(self.prices) > self.lookback:
            self.prices.pop(0)

        # 计算动量（当前价格 vs N 期前价格）
        momentum = (self.prices[-1] - self.prices[0]) / self.prices[0]

        # 获取当前持仓
        pos = self.get_position(self.symbol)
        current_volume = pos.volume if pos else 0

        # 交易逻辑
        if momentum > self.threshold and current_volume == 0:
            # 正动量且空仓 -> 买入
            logger.info(f"[Signal] BUY: momentum={momentum*100:.2f}%")
            self.send_order(
                symbol=self.symbol,
                side='BUY',
                price=md.last_price,
                volume=1
            )

        elif momentum < -self.threshold and current_volume > 0:
            # 负动量且持仓 -> 卖出
            logger.info(f"[Signal] SELL: momentum={momentum*100:.2f}%")
            self.send_order(
                symbol=self.symbol,
                side='SELL',
                price=md.last_price,
                volume=current_volume
            )

    def on_trade(self, trade: Trade):
        """成交回报回调"""
        if trade.status == 'FILLED':
            logger.info(
                f"[Trade] {trade.side} {trade.filled_volume} @ ${trade.filled_price:.2f} | "
                f"PnL: ${self.get_total_pnl():.2f}"
            )


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("TTQuant Backtest Demo - Mock Data")
    logger.info("=" * 80)

    # 回测参数
    SYMBOL = 'BTCUSDT'
    START_DATE = datetime(2024, 1, 1)
    DAYS = 30  # 回测 30 天
    INITIAL_CAPITAL = 100000.0

    logger.info(f"Symbol:         {SYMBOL}")
    logger.info(f"Period:         {START_DATE.date()} + {DAYS} days")
    logger.info(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    logger.info("=" * 80)

    # 创建模拟数据源
    data_source = MockDataSource(
        symbol=SYMBOL,
        start_date=START_DATE,
        days=DAYS,
        initial_price=50000.0
    )

    # 创建订单网关
    order_gateway = BacktestOrderGateway(
        slippage_model=SlippageModel.PERCENTAGE,
        slippage_value=0.0005,  # 0.05% 滑点
        commission_config=CommissionConfig(
            maker_fee=0.0002,
            taker_fee=0.0004
        )
    )

    # 创建回测引擎
    engine = BacktestEngine(
        data_source=data_source,
        order_gateway=order_gateway,
        initial_capital=INITIAL_CAPITAL,
        record_equity_interval=1000
    )

    # 添加策略
    strategy = SimpleMomentumStrategy('momentum_btc', {
        'symbol': SYMBOL,
        'lookback': 100,  # 100 分钟回看
        'threshold': 0.01,  # 1% 动量阈值
    })
    engine.add_strategy(strategy)

    # 运行回测
    logger.info("Starting backtest...")
    reports = engine.run()

    # 打印报告
    for strategy_id, report in reports.items():
        report.print_report()

    # 导出结果
    output_dir = 'demo_backtest_results'
    engine.export_results(output_dir)
    logger.info(f"Results exported to {output_dir}/")

    logger.info("=" * 80)
    logger.info("Demo completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
