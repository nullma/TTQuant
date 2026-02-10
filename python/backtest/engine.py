"""
BacktestEngine - 回测引擎核心

职责：
1. 时间管理（历史数据回放）
2. 事件驱动架构
3. 支持多策略回测
4. 性能分析和报告生成

设计原则：
- 与实盘策略引擎共享 BaseStrategy 接口
- 事件驱动：按时间顺序回放历史数据
- 依赖注入：通过 BacktestOrderGateway 和 BacktestDataSource 解耦
"""

import sys
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

# 添加 strategy 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from strategy.base_strategy import BaseStrategy, MarketData

from .data_source import BacktestDataSource
from .order_gateway import BacktestOrderGateway, SlippageModel, CommissionConfig
from .analytics import PerformanceAnalytics, BacktestReport

logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        data_source: BacktestDataSource,
        order_gateway: BacktestOrderGateway,
        initial_capital: float = 100000.0,
        record_equity_interval: int = 100,  # 每 N 个 tick 记录一次权益
    ):
        """
        初始化回测引擎

        Args:
            data_source: 数据源
            order_gateway: 订单网关
            initial_capital: 初始资金
            record_equity_interval: 权益记录间隔
        """
        self.data_source = data_source
        self.order_gateway = order_gateway
        self.initial_capital = initial_capital
        self.record_equity_interval = record_equity_interval

        # 策略列表
        self.strategies: Dict[str, BaseStrategy] = {}

        # 性能分析器
        self.analytics = PerformanceAnalytics(initial_capital)

        # 当前市场价格（用于计算未实现盈亏）
        self.current_prices: Dict[str, float] = {}

        # 统计
        self.stats = {
            'total_ticks': 0,
            'start_time': None,
            'end_time': None,
        }

        logger.info("BacktestEngine initialized")
        logger.info(f"  Initial capital: ${initial_capital:,.2f}")
        logger.info(f"  Equity record interval: {record_equity_interval} ticks")

    def add_strategy(self, strategy: BaseStrategy):
        """
        添加策略

        Args:
            strategy: 策略实例
        """
        # 设置订单网关（依赖注入）
        strategy.set_order_gateway(self)
        self.strategies[strategy.strategy_id] = strategy
        logger.info(f"Strategy added: {strategy.strategy_id}")

    def send_order(self, order):
        """
        发送订单（由策略调用）

        这个方法实现了与实盘 OrderGateway 相同的接口，
        但在回测中会立即使用当前价格模拟成交。

        Args:
            order: 订单对象
        """
        # 获取当前市场价格
        current_price = self.current_prices.get(order.symbol, order.price)

        # 通过回测网关模拟成交
        self.order_gateway.send_order(order, current_price)

    def run(self) -> Dict[str, BacktestReport]:
        """
        运行回测

        Returns:
            每个策略的回测报告
        """
        logger.info("=" * 80)
        logger.info("BACKTEST STARTED")
        logger.info("=" * 80)
        logger.info(f"Strategies: {list(self.strategies.keys())}")
        logger.info("=" * 80)

        # 设置订单网关的成交回调
        self.order_gateway.set_trade_callback(self._on_trade)

        # 获取数据迭代器
        data_iterator = self.data_source.get_iterator()

        # 回放历史数据
        tick_count = 0
        for market_data_dict in data_iterator:
            tick_count += 1
            self.stats['total_ticks'] = tick_count

            # 转换为 MarketData 对象
            md = MarketData(
                symbol=market_data_dict['symbol'],
                last_price=market_data_dict['last_price'],
                volume=market_data_dict['volume'],
                exchange_time=market_data_dict['exchange_time'],
                local_time=market_data_dict['local_time'],
                exchange=market_data_dict['exchange']
            )

            # 更新当前价格
            self.current_prices[md.symbol] = md.last_price

            # 记录时间范围
            if self.stats['start_time'] is None:
                self.stats['start_time'] = market_data_dict['time']
            self.stats['end_time'] = market_data_dict['time']

            # 分发行情到所有策略
            for strategy in self.strategies.values():
                strategy.on_market_data(md)

                # 更新未实现盈亏
                strategy.portfolio.update_unrealized_pnl(md.symbol, md.last_price)

            # 定期记录权益
            if tick_count % self.record_equity_interval == 0:
                self._record_equity(market_data_dict['time'])

            # 进度日志
            if tick_count % 10000 == 0:
                logger.info(f"Processed {tick_count:,} ticks...")

        # 最后记录一次权益
        if self.stats['end_time']:
            self._record_equity(self.stats['end_time'])

        logger.info(f"Backtest completed: {tick_count:,} ticks processed")

        # 生成报告
        reports = self._generate_reports()

        logger.info("=" * 80)
        logger.info("BACKTEST COMPLETED")
        logger.info("=" * 80)

        return reports

    def _on_trade(self, trade):
        """
        成交回报回调

        Args:
            trade: 成交对象
        """
        # 分发到对应策略
        strategy_id = trade.strategy_id
        if strategy_id in self.strategies:
            strategy = self.strategies[strategy_id]

            # 更新持仓
            if trade.status == 'FILLED':
                strategy.portfolio.update_position(trade)

            # 调用策略的成交回调
            strategy.on_trade(trade)

            # 记录到分析器
            self.analytics.record_trade(trade)

    def _record_equity(self, timestamp: datetime):
        """
        记录权益

        Args:
            timestamp: 时间戳
        """
        for strategy in self.strategies.values():
            equity = self.initial_capital + strategy.get_total_pnl()
            self.analytics.record_equity(
                timestamp=timestamp,
                equity=equity,
                positions=strategy.portfolio.positions
            )

    def _generate_reports(self) -> Dict[str, BacktestReport]:
        """
        生成回测报告

        Returns:
            策略 ID -> 回测报告
        """
        reports = {}

        for strategy_id, strategy in self.strategies.items():
            # 计算最终权益
            final_equity = self.initial_capital + strategy.get_total_pnl()

            # 生成报告
            report = self.analytics.generate_report(
                strategy_id=strategy_id,
                start_date=self.stats['start_time'],
                end_date=self.stats['end_time'],
                final_equity=final_equity,
                positions=strategy.portfolio.positions,
                gateway_stats=self.order_gateway.get_statistics()
            )

            reports[strategy_id] = report

            # 打印报告
            report.print_report()

        return reports

    def export_results(self, output_dir: str):
        """
        导出回测结果

        Args:
            output_dir: 输出目录
        """
        import os
        os.makedirs(output_dir, exist_ok=True)

        # 导出权益曲线
        equity_file = os.path.join(output_dir, 'equity_curve.csv')
        self.analytics.export_to_csv(equity_file)

        logger.info(f"Results exported to {output_dir}")


def create_backtest_engine(
    db_uri: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    exchange: str = 'binance',
    initial_capital: float = 100000.0,
    slippage_model: SlippageModel = SlippageModel.PERCENTAGE,
    slippage_value: float = 0.0005,
    maker_fee: float = 0.0002,
    taker_fee: float = 0.0004,
) -> BacktestEngine:
    """
    创建回测引擎（工厂方法）

    Args:
        db_uri: 数据库连接字符串
        symbols: 交易对列表
        start_date: 回测开始日期
        end_date: 回测结束日期
        exchange: 交易所名称
        initial_capital: 初始资金
        slippage_model: 滑点模型
        slippage_value: 滑点值
        maker_fee: Maker 手续费率
        taker_fee: Taker 手续费率

    Returns:
        回测引擎实例
    """
    # 创建数据源
    data_source = BacktestDataSource(
        db_uri=db_uri,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        exchange=exchange,
        preload=True
    )

    # 创建订单网关
    order_gateway = BacktestOrderGateway(
        slippage_model=slippage_model,
        slippage_value=slippage_value,
        commission_config=CommissionConfig(
            maker_fee=maker_fee,
            taker_fee=taker_fee
        )
    )

    # 创建回测引擎
    engine = BacktestEngine(
        data_source=data_source,
        order_gateway=order_gateway,
        initial_capital=initial_capital
    )

    return engine


if __name__ == "__main__":
    # 测试回测引擎
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    db_password = os.getenv('DB_PASSWORD', 'changeme')
    db_uri = f"postgresql://ttquant:{db_password}@localhost:5432/ttquant_trading"

    # 创建回测引擎
    engine = create_backtest_engine(
        db_uri=db_uri,
        symbols=['BTCUSDT'],
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 7),
        exchange='binance',
        initial_capital=100000.0,
        slippage_model=SlippageModel.PERCENTAGE,
        slippage_value=0.0005,
        maker_fee=0.0002,
        taker_fee=0.0004,
    )

    # 添加策略（需要实现）
    # from strategy.strategies.ema_cross import EMACrossStrategy
    # strategy = EMACrossStrategy('ema_cross_btc', {...})
    # engine.add_strategy(strategy)

    # 运行回测
    # reports = engine.run()
