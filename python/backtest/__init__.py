"""
TTQuant Backtest Framework

回测框架模块，支持历史数据回测和性能分析。

核心组件：
- BacktestEngine: 回测引擎核心
- BacktestDataSource: 历史数据加载
- BacktestOrderGateway: 模拟订单执行
- PerformanceAnalytics: 性能分析

设计原则：
- 回测即实盘：与实盘策略引擎共享 BaseStrategy 接口
- 事件驱动：时间序列回放，模拟真实交易环境
- 高性能：使用 Polars 进行数据处理
"""

from .engine import BacktestEngine
from .data_source import BacktestDataSource
from .order_gateway import BacktestOrderGateway, SlippageModel
from .analytics import PerformanceAnalytics, BacktestReport

__all__ = [
    'BacktestEngine',
    'BacktestDataSource',
    'BacktestOrderGateway',
    'SlippageModel',
    'PerformanceAnalytics',
    'BacktestReport',
]
