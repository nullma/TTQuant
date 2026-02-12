"""
Performance Attribution - 策略性能归因分析

分析策略收益来源和风险因子贡献
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """归因分析结果"""
    alpha: float  # 超额收益
    beta: float  # 市场敏感度
    factor_contributions: Dict[str, float]  # 因子贡献
    residual: float  # 残差收益
    r_squared: float  # 拟合优度


class PerformanceAttribution:
    """
    性能归因分析

    功能：
    - Alpha-Beta 分解
    - 多因子归因
    - 时间段归因
    - 交易成本归因
    """

    def __init__(self):
        self.equity_curve: List[Dict] = []
        self.trades: List = []
        self.benchmark_returns: Optional[pd.Series] = None
        logger.info("PerformanceAttribution initialized")

    def set_equity_curve(self, equity_curve: List[Dict]):
        """设置权益曲线"""
        self.equity_curve = equity_curve

    def set_trades(self, trades: List):
        """设置交易记录"""
        self.trades = trades

    def set_benchmark(self, benchmark_returns: pd.Series):
        """设置基准收益率"""
        self.benchmark_returns = benchmark_returns

    def alpha_beta_decomposition(self, risk_free_rate: float = 0.02) -> Optional[AttributionResult]:
        """Alpha-Beta 分解"""
        if not self.equity_curve or self.benchmark_returns is None:
            logger.warning("Insufficient data for alpha-beta decomposition")
            return None

        # 计算策略收益率
        df = pd.DataFrame(self.equity_curve)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        df['returns'] = df['equity'].pct_change()

        # 对齐策略收益和基准收益
        aligned = pd.DataFrame({
            'strategy': df['returns'],
            'benchmark': self.benchmark_returns
        }).dropna()

        if len(aligned) < 2:
            logger.warning("Insufficient aligned data for regression")
            return None

        # 计算超额收益
        daily_rf = risk_free_rate / 365.0
        strategy_excess = aligned['strategy'] - daily_rf
        benchmark_excess = aligned['benchmark'] - daily_rf

        # 线性回归
        beta = np.cov(strategy_excess, benchmark_excess)[0, 1] / np.var(benchmark_excess)
        alpha = np.mean(strategy_excess) - beta * np.mean(benchmark_excess)

        # 计算 R²
        y_pred = alpha + beta * benchmark_excess
        ss_res = np.sum((strategy_excess - y_pred) ** 2)
        ss_tot = np.sum((strategy_excess - np.mean(strategy_excess)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return AttributionResult(
            alpha=float(alpha * 365),
            beta=float(beta),
            factor_contributions={'market': beta * np.mean(benchmark_excess) * 365},
            residual=float(np.mean(strategy_excess - y_pred) * 365),
            r_squared=float(r_squared)
        )

    def capm_attribution(self, strategy_returns: np.ndarray,
                        market_returns: np.ndarray,
                        risk_free_rate: float = 0.0) -> AttributionResult:
        """
        CAPM 模型归因分析

        Args:
            strategy_returns: 策略收益率
            market_returns: 市场收益率
            risk_free_rate: 无风险利率

        Returns:
            归因结果
        """
        # 超额收益
        excess_strategy = strategy_returns - risk_free_rate
        excess_market = market_returns - risk_free_rate

        # 线性回归：策略超额收益 = alpha + beta * 市场超额收益
        X = excess_market.reshape(-1, 1)
        y = excess_strategy

        # 计算 beta
        covariance = np.cov(excess_strategy, excess_market)[0, 1]
        market_variance = np.var(excess_market)
        beta = covariance / market_variance if market_variance > 0 else 0.0

        # 计算 alpha
        alpha = np.mean(excess_strategy) - beta * np.mean(excess_market)

        # R-squared
        predicted = alpha + beta * excess_market
        ss_res = np.sum((excess_strategy - predicted) ** 2)
        ss_tot = np.sum((excess_strategy - np.mean(excess_strategy)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # 残差
        residual = np.mean(excess_strategy - predicted)

        return AttributionResult(
            alpha=alpha,
            beta=beta,
            factor_contributions={'market': beta * np.mean(excess_market)},
            residual=residual,
            r_squared=r_squared
        )

    def multi_factor_attribution(self, strategy_returns: np.ndarray,
                                factor_returns: Dict[str, np.ndarray]) -> AttributionResult:
        """
        多因子归因分析

        Args:
            strategy_returns: 策略收益率
            factor_returns: 因子收益率字典

        Returns:
            归因结果
        """
        # 构建因子矩阵
        factor_names = list(factor_returns.keys())
        X = np.column_stack([factor_returns[name] for name in factor_names])
        y = strategy_returns

        # 多元线性回归
        betas = np.linalg.lstsq(X, y, rcond=None)[0]

        # 计算 alpha
        predicted = X @ betas
        alpha = np.mean(y - predicted)

        # 因子贡献
        factor_contributions = {}
        for i, name in enumerate(factor_names):
            factor_contributions[name] = betas[i] * np.mean(factor_returns[name])

        # R-squared
        ss_res = np.sum((y - predicted) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # 残差
        residual = np.mean(y - predicted)

        return AttributionResult(
            alpha=alpha,
            beta=np.mean(betas),
            factor_contributions=factor_contributions,
            residual=residual,
            r_squared=r_squared
        )

    def time_period_attribution(self, returns: pd.Series,
                               periods: List[str] = ['daily', 'weekly', 'monthly']) -> Dict:
        """
        时间段归因分析

        Args:
            returns: 收益率序列（带时间索引）
            periods: 分析周期列表

        Returns:
            各周期的收益统计
        """
        results = {}

        for period in periods:
            if period == 'daily':
                period_returns = returns
            elif period == 'weekly':
                period_returns = returns.resample('W').sum()
            elif period == 'monthly':
                period_returns = returns.resample('M').sum()
            else:
                continue

            results[period] = {
                'mean_return': period_returns.mean(),
                'std_return': period_returns.std(),
                'sharpe_ratio': period_returns.mean() / period_returns.std() if period_returns.std() > 0 else 0,
                'positive_periods': (period_returns > 0).sum(),
                'negative_periods': (period_returns < 0).sum()
            }

        return results

    def factor_attribution(self, factor_exposures: Dict[str, float],
                          factor_returns: Dict[str, float]) -> List:
        """因子归因分析"""
        from dataclasses import dataclass

        @dataclass
        class FactorAttribution:
            factor_name: str
            contribution: float
            exposure: float
            factor_return: float

        results = []
        for factor_name in factor_exposures.keys():
            if factor_name not in factor_returns:
                continue

            exposure = factor_exposures[factor_name]
            factor_ret = factor_returns[factor_name]
            contribution = exposure * factor_ret

            results.append(FactorAttribution(
                factor_name=factor_name,
                contribution=float(contribution),
                exposure=float(exposure),
                factor_return=float(factor_ret)
            ))

        results.sort(key=lambda x: abs(x.contribution), reverse=True)
        return results

    def period_attribution(self, period_type: str = 'monthly') -> List:
        """时间段归因分析"""
        from dataclasses import dataclass

        @dataclass
        class PeriodAttribution:
            period: str
            start_date: any
            end_date: any
            return_pct: float
            contribution_to_total: float
            sharpe_ratio: float
            max_drawdown: float
            trade_count: int

        if not self.equity_curve:
            logger.warning("No equity curve data for period attribution")
            return []

        df = pd.DataFrame(self.equity_curve)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        df['returns'] = df['equity'].pct_change()

        freq_map = {'daily': 'D', 'weekly': 'W', 'monthly': 'ME', 'quarterly': 'QE'}
        freq = freq_map.get(period_type, 'M')

        results = []
        initial_equity = df['equity'].iloc[0]

        for period, group in df.groupby(pd.Grouper(freq=freq)):
            if len(group) < 2:
                continue

            start_equity = group['equity'].iloc[0]
            end_equity = group['equity'].iloc[-1]
            period_return = (end_equity - start_equity) / start_equity

            contribution = (end_equity - start_equity) / initial_equity

            period_returns = group['returns'].dropna()
            if len(period_returns) > 1:
                sharpe = np.mean(period_returns) / np.std(period_returns) * np.sqrt(252)
            else:
                sharpe = 0.0

            cummax = group['equity'].cummax()
            drawdown = (group['equity'] - cummax) / cummax
            max_dd = abs(drawdown.min())

            period_trades = [
                t for t in self.trades
                if group.index[0] <= pd.to_datetime(t.trade_time, unit='ns') <= group.index[-1]
            ]

            results.append(PeriodAttribution(
                period=period.strftime('%Y-%m-%d'),
                start_date=group.index[0].to_pydatetime(),
                end_date=group.index[-1].to_pydatetime(),
                return_pct=float(period_return),
                contribution_to_total=float(contribution),
                sharpe_ratio=float(sharpe),
                max_drawdown=float(max_dd),
                trade_count=len(period_trades)
            ))

        return results

    def cost_attribution(self, total_return: float, commission_cost: float,
                        slippage_cost: float, market_impact_cost: float = 0.0):
        """交易成本归因"""
        from dataclasses import dataclass

        @dataclass
        class CostAttribution:
            total_cost: float
            commission_cost: float
            slippage_cost: float
            market_impact_cost: float
            cost_as_pct_of_return: float
            cost_per_trade: float

        total_cost = commission_cost + slippage_cost + market_impact_cost
        cost_pct = (total_cost / total_return * 100) if total_return != 0 else 0.0
        trade_count = len(self.trades) if self.trades else 1
        cost_per_trade = total_cost / trade_count

        return CostAttribution(
            total_cost=float(total_cost),
            commission_cost=float(commission_cost),
            slippage_cost=float(slippage_cost),
            market_impact_cost=float(market_impact_cost),
            cost_as_pct_of_return=float(cost_pct),
            cost_per_trade=float(cost_per_trade)
        )

    def generate_attribution_report(self) -> Dict:
        """生成完整的归因分析报告"""
        report = {}

        if self.benchmark_returns is not None:
            alpha_beta = self.alpha_beta_decomposition()
            if alpha_beta:
                report['alpha_beta'] = {
                    'alpha': alpha_beta.alpha,
                    'beta': alpha_beta.beta,
                    'r_squared': alpha_beta.r_squared,
                    'residual': alpha_beta.residual,
                    'factor_contributions': alpha_beta.factor_contributions
                }

        monthly_attr = self.period_attribution('monthly')
        if monthly_attr:
            report['monthly_attribution'] = [
                {
                    'period': p.period,
                    'return_pct': p.return_pct,
                    'contribution': p.contribution_to_total,
                    'sharpe_ratio': p.sharpe_ratio,
                    'max_drawdown': p.max_drawdown,
                    'trade_count': p.trade_count
                }
                for p in monthly_attr
            ]

        return report

    def transaction_cost_attribution(self, gross_returns: np.ndarray,
                                    net_returns: np.ndarray) -> Dict:
        """
        交易成本归因

        Args:
            gross_returns: 毛收益率
            net_returns: 净收益率

        Returns:
            成本分析结果
        """
        cost_impact = gross_returns - net_returns

        return {
            'total_cost': np.sum(cost_impact),
            'avg_cost_per_trade': np.mean(cost_impact),
            'cost_as_pct_of_gross': np.sum(cost_impact) / np.sum(gross_returns) if np.sum(gross_returns) > 0 else 0,
            'max_cost': np.max(cost_impact),
            'min_cost': np.min(cost_impact)
        }
