"""
Risk Monitor - 实时风险监控

计算和导出风险指标到 Prometheus
"""

import numpy as np
import psycopg2
from prometheus_client import Gauge, start_http_server
from typing import Dict, List
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RiskMonitor:
    """
    实时风险监控

    功能：
    - 计算 VaR 和 CVaR
    - 监控最大回撤
    - 计算风险调整收益指标
    - 导出 Prometheus 指标
    """

    def __init__(self, db_config: Dict, port: int = 8001):
        self.db_config = db_config
        self.port = port

        # Prometheus 指标
        self.var_95 = Gauge('portfolio_var_95', 'Value at Risk (95%)')
        self.var_99 = Gauge('portfolio_var_99', 'Value at Risk (99%)')
        self.cvar_95 = Gauge('portfolio_cvar_95', 'Conditional VaR (95%)')
        self.max_drawdown = Gauge('portfolio_max_drawdown', 'Maximum Drawdown')
        self.current_drawdown = Gauge('portfolio_current_drawdown', 'Current Drawdown')
        self.sharpe_ratio = Gauge('portfolio_sharpe_ratio', 'Sharpe Ratio')
        self.sortino_ratio = Gauge('portfolio_sortino_ratio', 'Sortino Ratio')
        self.calmar_ratio = Gauge('portfolio_calmar_ratio', 'Calmar Ratio')
        self.volatility = Gauge('portfolio_volatility', 'Annualized Volatility')

        logger.info(f"RiskMonitor initialized on port {port}")

    def start(self):
        """启动监控服务"""
        start_http_server(self.port)
        logger.info(f"Prometheus metrics server started on port {self.port}")

        while True:
            try:
                self.update_metrics()
                time.sleep(60)  # 每分钟更新一次
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                time.sleep(60)

    def update_metrics(self):
        """更新所有风险指标"""
        # 从数据库获取最近的收益数据
        returns = self._fetch_recent_returns(days=30)

        if len(returns) < 10:
            logger.warning("Insufficient data for risk calculation")
            return

        # 计算 VaR
        var_95_value = self._calculate_var(returns, confidence=0.95)
        var_99_value = self._calculate_var(returns, confidence=0.99)
        self.var_95.set(var_95_value)
        self.var_99.set(var_99_value)

        # 计算 CVaR
        cvar_95_value = self._calculate_cvar(returns, confidence=0.95)
        self.cvar_95.set(cvar_95_value)

        # 计算回撤
        max_dd, current_dd = self._calculate_drawdown(returns)
        self.max_drawdown.set(max_dd)
        self.current_drawdown.set(current_dd)

        # 计算风险调整收益指标
        sharpe = self._calculate_sharpe_ratio(returns)
        sortino = self._calculate_sortino_ratio(returns)
        calmar = self._calculate_calmar_ratio(returns, max_dd)
        vol = self._calculate_volatility(returns)

        self.sharpe_ratio.set(sharpe)
        self.sortino_ratio.set(sortino)
        self.calmar_ratio.set(calmar)
        self.volatility.set(vol)

        logger.info(f"Metrics updated: VaR95={var_95_value:.4f}, MaxDD={max_dd:.4f}, Sharpe={sharpe:.4f}")

    def _fetch_recent_returns(self, days: int = 30) -> np.ndarray:
        """从数据库获取最近的收益数据"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            query = """
                SELECT time, SUM(filled_price * filled_volume) as pnl
                FROM trades
                WHERE time >= NOW() - INTERVAL '%s days'
                GROUP BY time
                ORDER BY time
            """
            cursor.execute(query, (days,))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            if not results:
                return np.array([])

            pnl_values = np.array([row[1] for row in results])
            returns = np.diff(pnl_values) / (np.abs(pnl_values[:-1]) + 1e-8)

            return returns

        except Exception as e:
            logger.error(f"Database error: {e}")
            return np.array([])

    def _calculate_var(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """计算 VaR"""
        return float(np.percentile(returns, (1 - confidence) * 100))

    def _calculate_cvar(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """计算 CVaR (条件 VaR)"""
        var = self._calculate_var(returns, confidence)
        return float(np.mean(returns[returns <= var]))

    def _calculate_drawdown(self, returns: np.ndarray) -> tuple:
        """计算最大回撤和当前回撤"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max

        max_drawdown = float(np.min(drawdown))
        current_drawdown = float(drawdown[-1])

        return max_drawdown, current_drawdown

    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """计算夏普比率"""
        excess_returns = returns - risk_free_rate
        if np.std(excess_returns) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))

    def _calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """计算索提诺比率"""
        excess_returns = returns - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252))

    def _calculate_calmar_ratio(self, returns: np.ndarray, max_drawdown: float) -> float:
        """计算卡玛比率"""
        annual_return = np.mean(returns) * 252
        if max_drawdown == 0:
            return 0.0
        return float(annual_return / abs(max_drawdown))

    def _calculate_volatility(self, returns: np.ndarray) -> float:
        """计算年化波动率"""
        return float(np.std(returns) * np.sqrt(252))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'ttquant_trading',
        'user': 'ttquant',
        'password': 'ttquant_password'
    }

    monitor = RiskMonitor(db_config)
    monitor.start()
