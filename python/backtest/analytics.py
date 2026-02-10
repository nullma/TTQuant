"""
PerformanceAnalytics - 性能分析模块

职责：
1. 计算夏普比率、最大回撤
2. 胜率、盈亏比
3. 交易统计
4. 生成回测报告
"""

import polars as pl
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import sys
import os

# 添加 strategy 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from strategy.base_strategy import Trade, Position

logger = logging.getLogger(__name__)


@dataclass
class BacktestReport:
    """回测报告"""
    # 基本信息
    strategy_id: str
    start_date: datetime
    end_date: datetime
    duration_days: float

    # 收益指标
    total_return: float  # 总收益率
    annual_return: float  # 年化收益率
    total_pnl: float  # 总盈亏
    realized_pnl: float  # 已实现盈亏
    unrealized_pnl: float  # 未实现盈亏

    # 风险指标
    sharpe_ratio: float  # 夏普比率
    max_drawdown: float  # 最大回撤
    max_drawdown_duration_days: float  # 最大回撤持续时间
    volatility: float  # 波动率（年化）

    # 交易统计
    total_trades: int  # 总交易次数
    winning_trades: int  # 盈利交易次数
    losing_trades: int  # 亏损交易次数
    win_rate: float  # 胜率
    profit_factor: float  # 盈亏比
    avg_win: float  # 平均盈利
    avg_loss: float  # 平均亏损
    largest_win: float  # 最大盈利
    largest_loss: float  # 最大亏损

    # 成本统计
    total_commission: float  # 总手续费
    total_slippage: float  # 总滑点成本

    # 持仓统计
    avg_position_duration_hours: float  # 平均持仓时间
    max_position_size: int  # 最大持仓量

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def print_report(self):
        """打印报告"""
        print("\n" + "=" * 80)
        print(f"BACKTEST REPORT - {self.strategy_id}")
        print("=" * 80)

        print(f"\n[Period]")
        print(f"  Start Date:        {self.start_date}")
        print(f"  End Date:          {self.end_date}")
        print(f"  Duration:          {self.duration_days:.1f} days")

        print(f"\n[Returns]")
        print(f"  Total Return:      {self.total_return * 100:>10.2f}%")
        print(f"  Annual Return:     {self.annual_return * 100:>10.2f}%")
        print(f"  Total PnL:         ${self.total_pnl:>10.2f}")
        print(f"  Realized PnL:      ${self.realized_pnl:>10.2f}")
        print(f"  Unrealized PnL:    ${self.unrealized_pnl:>10.2f}")

        print(f"\n[Risk Metrics]")
        print(f"  Sharpe Ratio:      {self.sharpe_ratio:>10.2f}")
        print(f"  Max Drawdown:      {self.max_drawdown * 100:>10.2f}%")
        print(f"  Drawdown Duration: {self.max_drawdown_duration_days:>10.1f} days")
        print(f"  Volatility (Ann):  {self.volatility * 100:>10.2f}%")

        print(f"\n[Trading Statistics]")
        print(f"  Total Trades:      {self.total_trades:>10}")
        print(f"  Winning Trades:    {self.winning_trades:>10}")
        print(f"  Losing Trades:     {self.losing_trades:>10}")
        print(f"  Win Rate:          {self.win_rate * 100:>10.2f}%")
        print(f"  Profit Factor:     {self.profit_factor:>10.2f}")
        print(f"  Avg Win:           ${self.avg_win:>10.2f}")
        print(f"  Avg Loss:          ${self.avg_loss:>10.2f}")
        print(f"  Largest Win:       ${self.largest_win:>10.2f}")
        print(f"  Largest Loss:      ${self.largest_loss:>10.2f}")

        print(f"\n[Costs]")
        print(f"  Total Commission:  ${self.total_commission:>10.2f}")
        print(f"  Total Slippage:    ${self.total_slippage:>10.2f}")

        print(f"\n[Position Statistics]")
        print(f"  Avg Duration:      {self.avg_position_duration_hours:>10.1f} hours")
        print(f"  Max Position Size: {self.max_position_size:>10}")

        print("\n" + "=" * 80)


class PerformanceAnalytics:
    """性能分析器"""

    def __init__(self, initial_capital: float = 100000.0):
        """
        初始化性能分析器

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital

        # 记录数据
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []  # 权益曲线
        self.positions_history: List[Dict] = []  # 持仓历史

        logger.info(f"PerformanceAnalytics initialized with ${initial_capital:,.2f}")

    def record_trade(self, trade: Trade):
        """记录交易"""
        if trade.status == 'FILLED':
            self.trades.append(trade)

    def record_equity(self, timestamp: datetime, equity: float, positions: Dict[str, Position]):
        """
        记录权益

        Args:
            timestamp: 时间戳
            equity: 当前权益
            positions: 当前持仓
        """
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': equity,
        })

        # 记录持仓
        for symbol, pos in positions.items():
            if pos.volume != 0:
                self.positions_history.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'volume': pos.volume,
                    'avg_price': pos.avg_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                })

    def generate_report(
        self,
        strategy_id: str,
        start_date: datetime,
        end_date: datetime,
        final_equity: float,
        positions: Dict[str, Position],
        gateway_stats: Dict
    ) -> BacktestReport:
        """
        生成回测报告

        Args:
            strategy_id: 策略 ID
            start_date: 开始日期
            end_date: 结束日期
            final_equity: 最终权益
            positions: 最终持仓
            gateway_stats: 网关统计信息

        Returns:
            回测报告
        """
        logger.info("Generating backtest report...")

        # 计算持续时间
        duration = (end_date - start_date).total_seconds() / 86400  # 天数

        # 计算收益
        total_pnl = final_equity - self.initial_capital
        total_return = total_pnl / self.initial_capital
        annual_return = total_return * (365.0 / duration) if duration > 0 else 0.0

        # 计算已实现和未实现盈亏
        realized_pnl = sum(pos.realized_pnl for pos in positions.values())
        unrealized_pnl = sum(pos.unrealized_pnl for pos in positions.values())

        # 计算风险指标
        sharpe_ratio = self._calculate_sharpe_ratio()
        max_drawdown, max_dd_duration = self._calculate_max_drawdown()
        volatility = self._calculate_volatility()

        # 计算交易统计
        trade_stats = self._calculate_trade_statistics()

        # 持仓统计
        position_stats = self._calculate_position_statistics()

        report = BacktestReport(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration,
            total_return=total_return,
            annual_return=annual_return,
            total_pnl=total_pnl,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration_days=max_dd_duration,
            volatility=volatility,
            total_trades=trade_stats['total_trades'],
            winning_trades=trade_stats['winning_trades'],
            losing_trades=trade_stats['losing_trades'],
            win_rate=trade_stats['win_rate'],
            profit_factor=trade_stats['profit_factor'],
            avg_win=trade_stats['avg_win'],
            avg_loss=trade_stats['avg_loss'],
            largest_win=trade_stats['largest_win'],
            largest_loss=trade_stats['largest_loss'],
            total_commission=gateway_stats.get('total_commission', 0.0),
            total_slippage=gateway_stats.get('total_slippage', 0.0),
            avg_position_duration_hours=position_stats['avg_duration_hours'],
            max_position_size=position_stats['max_position_size'],
        )

        return report

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        计算夏普比率

        Args:
            risk_free_rate: 无风险利率（年化）

        Returns:
            夏普比率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        # 计算日收益率
        equities = [e['equity'] for e in self.equity_curve]
        returns = np.diff(equities) / equities[:-1]

        if len(returns) == 0:
            return 0.0

        # 计算平均收益和标准差
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # 年化夏普比率（假设每天一个数据点）
        daily_rf = risk_free_rate / 365.0
        sharpe = (avg_return - daily_rf) / std_return * np.sqrt(365)

        return float(sharpe)

    def _calculate_max_drawdown(self) -> tuple[float, float]:
        """
        计算最大回撤

        Returns:
            (最大回撤比例, 最大回撤持续时间（天）)
        """
        if len(self.equity_curve) < 2:
            return 0.0, 0.0

        equities = [e['equity'] for e in self.equity_curve]
        timestamps = [e['timestamp'] for e in self.equity_curve]

        # 计算回撤
        peak = equities[0]
        max_dd = 0.0
        max_dd_duration = 0.0
        peak_time = timestamps[0]

        for i, equity in enumerate(equities):
            if equity > peak:
                peak = equity
                peak_time = timestamps[i]
            else:
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd
                    duration = (timestamps[i] - peak_time).total_seconds() / 86400
                    max_dd_duration = duration

        return float(max_dd), float(max_dd_duration)

    def _calculate_volatility(self) -> float:
        """
        计算波动率（年化）

        Returns:
            年化波动率
        """
        if len(self.equity_curve) < 2:
            return 0.0

        equities = [e['equity'] for e in self.equity_curve]
        returns = np.diff(equities) / equities[:-1]

        if len(returns) == 0:
            return 0.0

        # 年化波动率
        volatility = np.std(returns) * np.sqrt(365)

        return float(volatility)

    def _calculate_trade_statistics(self) -> Dict:
        """计算交易统计"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
            }

        # 按交易对分组，计算每笔交易的盈亏
        # 简化版：假设每笔买入后都有对应的卖出
        trade_pnls = []
        positions = {}  # symbol -> (volume, avg_price)

        for trade in self.trades:
            symbol = trade.symbol

            if symbol not in positions:
                positions[symbol] = {'volume': 0, 'avg_price': 0.0}

            pos = positions[symbol]

            if trade.side == 'BUY':
                # 买入
                total_cost = pos['avg_price'] * pos['volume'] + trade.filled_price * trade.filled_volume
                pos['volume'] += trade.filled_volume
                pos['avg_price'] = total_cost / pos['volume'] if pos['volume'] > 0 else 0.0
            else:
                # 卖出
                if pos['volume'] > 0:
                    pnl = (trade.filled_price - pos['avg_price']) * trade.filled_volume - trade.commission
                    trade_pnls.append(pnl)
                    pos['volume'] -= trade.filled_volume

        if not trade_pnls:
            # 如果没有完整的交易对，使用简化统计
            total_trades = len(self.trades)
            return {
                'total_trades': total_trades,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
            }

        # 统计
        winning_trades = [p for p in trade_pnls if p > 0]
        losing_trades = [p for p in trade_pnls if p < 0]

        total_trades = len(trade_pnls)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0.0

        total_win = sum(winning_trades) if winning_trades else 0.0
        total_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = total_win / total_loss if total_loss > 0 else 0.0

        avg_win = total_win / win_count if win_count > 0 else 0.0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0.0

        largest_win = max(winning_trades) if winning_trades else 0.0
        largest_loss = abs(min(losing_trades)) if losing_trades else 0.0

        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
        }

    def _calculate_position_statistics(self) -> Dict:
        """计算持仓统计"""
        if not self.positions_history:
            return {
                'avg_duration_hours': 0.0,
                'max_position_size': 0,
            }

        # 计算平均持仓时间（简化版）
        # TODO: 更精确的持仓时间计算

        # 计算最大持仓量
        max_position_size = max(
            abs(p['volume']) for p in self.positions_history
        ) if self.positions_history else 0

        return {
            'avg_duration_hours': 0.0,  # TODO
            'max_position_size': max_position_size,
        }

    def export_to_csv(self, filepath: str):
        """导出权益曲线到 CSV"""
        if not self.equity_curve:
            logger.warning("No equity data to export")
            return

        df = pl.DataFrame(self.equity_curve)
        df.write_csv(filepath)
        logger.info(f"Equity curve exported to {filepath}")


if __name__ == "__main__":
    # 测试性能分析
    from datetime import timedelta

    analytics = PerformanceAnalytics(initial_capital=100000.0)

    # 模拟权益曲线
    start = datetime(2024, 1, 1)
    for i in range(100):
        timestamp = start + timedelta(days=i)
        equity = 100000 + i * 100 + np.random.randn() * 500
        analytics.record_equity(timestamp, equity, {})

    # 生成报告
    report = analytics.generate_report(
        strategy_id="test_strategy",
        start_date=start,
        end_date=start + timedelta(days=99),
        final_equity=110000.0,
        positions={},
        gateway_stats={'total_commission': 100.0, 'total_slippage': 50.0}
    )

    report.print_report()
