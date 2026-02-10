"""
Prometheus Metrics for TTQuant Strategy Engine

导出策略引擎的性能指标到 Prometheus
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# ==================== 策略指标 ====================

# 策略 PnL（已实现 + 未实现）
strategy_pnl_total = Gauge(
    'strategy_pnl_total',
    'Total strategy PnL (realized + unrealized) in USD',
    ['strategy_id']
)

# 已实现 PnL
strategy_realized_pnl = Gauge(
    'strategy_realized_pnl',
    'Realized PnL in USD',
    ['strategy_id']
)

# 未实现 PnL
strategy_unrealized_pnl = Gauge(
    'strategy_unrealized_pnl',
    'Unrealized PnL in USD',
    ['strategy_id', 'symbol']
)

# 持仓数量
strategy_position_size = Gauge(
    'strategy_position_size',
    'Current position size',
    ['strategy_id', 'symbol']
)

# 持仓价值（USD）
strategy_position_value = Gauge(
    'strategy_position_value_usd',
    'Current position value in USD',
    ['strategy_id', 'symbol']
)

# 交易次数
strategy_trades_total = Counter(
    'strategy_trades_total',
    'Total number of trades',
    ['strategy_id', 'symbol', 'side']
)

# 胜率
strategy_win_rate = Gauge(
    'strategy_win_rate',
    'Win rate (0-1)',
    ['strategy_id']
)

# 盈利交易数
strategy_winning_trades = Counter(
    'strategy_winning_trades_total',
    'Total number of winning trades',
    ['strategy_id']
)

# 亏损交易数
strategy_losing_trades = Counter(
    'strategy_losing_trades_total',
    'Total number of losing trades',
    ['strategy_id']
)

# 平均盈利
strategy_avg_profit = Gauge(
    'strategy_avg_profit_usd',
    'Average profit per winning trade in USD',
    ['strategy_id']
)

# 平均亏损
strategy_avg_loss = Gauge(
    'strategy_avg_loss_usd',
    'Average loss per losing trade in USD',
    ['strategy_id']
)

# 最大回撤
strategy_max_drawdown = Gauge(
    'strategy_max_drawdown_usd',
    'Maximum drawdown in USD',
    ['strategy_id']
)

# 夏普比率
strategy_sharpe_ratio = Gauge(
    'strategy_sharpe_ratio',
    'Sharpe ratio',
    ['strategy_id']
)

# ==================== 引擎指标 ====================

# 行情接收计数
engine_market_data_received = Counter(
    'engine_market_data_received_total',
    'Total market data messages received',
    ['symbol']
)

# 订单发送计数
engine_orders_sent = Counter(
    'engine_orders_sent_total',
    'Total orders sent',
    ['strategy_id', 'symbol', 'side']
)

# 成交回报接收计数
engine_trades_received = Counter(
    'engine_trades_received_total',
    'Total trade reports received',
    ['strategy_id', 'status']
)

# 策略执行延迟（毫秒）
engine_strategy_latency = Histogram(
    'engine_strategy_latency_ms',
    'Strategy execution latency in milliseconds',
    ['strategy_id'],
    buckets=[1, 5, 10, 50, 100, 500, 1000, 5000]
)

# 活跃策略数
engine_active_strategies = Gauge(
    'engine_active_strategies',
    'Number of active strategies'
)

# 引擎运行时间（秒）
engine_uptime_seconds = Gauge(
    'engine_uptime_seconds',
    'Engine uptime in seconds'
)


class StrategyMetrics:
    """策略指标收集器"""

    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.winning_trades_count = 0
        self.losing_trades_count = 0
        self.total_profit = 0.0
        self.total_loss = 0.0

    def update_pnl(self, realized_pnl: float, unrealized_pnl: float):
        """更新 PnL"""
        total_pnl = realized_pnl + unrealized_pnl
        strategy_pnl_total.labels(strategy_id=self.strategy_id).set(total_pnl)
        strategy_realized_pnl.labels(strategy_id=self.strategy_id).set(realized_pnl)

    def update_unrealized_pnl(self, symbol: str, unrealized_pnl: float):
        """更新未实现 PnL"""
        strategy_unrealized_pnl.labels(
            strategy_id=self.strategy_id,
            symbol=symbol
        ).set(unrealized_pnl)

    def update_position(self, symbol: str, size: float, value: float):
        """更新持仓"""
        strategy_position_size.labels(
            strategy_id=self.strategy_id,
            symbol=symbol
        ).set(size)

        strategy_position_value.labels(
            strategy_id=self.strategy_id,
            symbol=symbol
        ).set(value)

    def record_trade(self, symbol: str, side: str, pnl: float = 0.0):
        """记录交易"""
        strategy_trades_total.labels(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=side
        ).inc()

        # 更新胜率统计
        if pnl > 0:
            self.winning_trades_count += 1
            self.total_profit += pnl
            strategy_winning_trades.labels(strategy_id=self.strategy_id).inc()
        elif pnl < 0:
            self.losing_trades_count += 1
            self.total_loss += abs(pnl)
            strategy_losing_trades.labels(strategy_id=self.strategy_id).inc()

        # 更新胜率
        total_trades = self.winning_trades_count + self.losing_trades_count
        if total_trades > 0:
            win_rate = self.winning_trades_count / total_trades
            strategy_win_rate.labels(strategy_id=self.strategy_id).set(win_rate)

        # 更新平均盈利/亏损
        if self.winning_trades_count > 0:
            avg_profit = self.total_profit / self.winning_trades_count
            strategy_avg_profit.labels(strategy_id=self.strategy_id).set(avg_profit)

        if self.losing_trades_count > 0:
            avg_loss = self.total_loss / self.losing_trades_count
            strategy_avg_loss.labels(strategy_id=self.strategy_id).set(avg_loss)

    def update_max_drawdown(self, drawdown: float):
        """更新最大回撤"""
        strategy_max_drawdown.labels(strategy_id=self.strategy_id).set(drawdown)

    def update_sharpe_ratio(self, sharpe: float):
        """更新夏普比率"""
        strategy_sharpe_ratio.labels(strategy_id=self.strategy_id).set(sharpe)


class EngineMetrics:
    """引擎指标收集器"""

    def __init__(self):
        self.strategy_metrics: Dict[str, StrategyMetrics] = {}

    def add_strategy(self, strategy_id: str):
        """添加策略"""
        self.strategy_metrics[strategy_id] = StrategyMetrics(strategy_id)
        engine_active_strategies.set(len(self.strategy_metrics))

    def get_strategy_metrics(self, strategy_id: str) -> StrategyMetrics:
        """获取策略指标收集器"""
        if strategy_id not in self.strategy_metrics:
            self.add_strategy(strategy_id)
        return self.strategy_metrics[strategy_id]

    def record_market_data(self, symbol: str):
        """记录行情接收"""
        engine_market_data_received.labels(symbol=symbol).inc()

    def record_order_sent(self, strategy_id: str, symbol: str, side: str):
        """记录订单发送"""
        engine_orders_sent.labels(
            strategy_id=strategy_id,
            symbol=symbol,
            side=side
        ).inc()

    def record_trade_received(self, strategy_id: str, status: str):
        """记录成交回报"""
        engine_trades_received.labels(
            strategy_id=strategy_id,
            status=status
        ).inc()

    def record_strategy_latency(self, strategy_id: str, latency_ms: float):
        """记录策略执行延迟"""
        engine_strategy_latency.labels(strategy_id=strategy_id).observe(latency_ms)

    def update_uptime(self, uptime_seconds: float):
        """更新运行时间"""
        engine_uptime_seconds.set(uptime_seconds)


def start_metrics_server(port: int = 8000):
    """启动 Prometheus metrics HTTP 服务器"""
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        raise


if __name__ == "__main__":
    # 测试
    import time

    start_metrics_server(8000)

    # 模拟指标更新
    metrics = EngineMetrics()
    metrics.add_strategy("test_strategy")

    strategy_metrics = metrics.get_strategy_metrics("test_strategy")
    strategy_metrics.update_pnl(100.0, 50.0)
    strategy_metrics.update_position("BTCUSDT", 0.5, 25000.0)
    strategy_metrics.record_trade("BTCUSDT", "BUY", 10.0)

    print("Metrics server running on http://localhost:8000/metrics")
    print("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
            metrics.update_uptime(time.time())
    except KeyboardInterrupt:
        print("\nStopping...")
