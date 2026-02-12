"""
Portfolio Optimizer - 组合优化算法

实现马科维茨均值方差优化和风险平价
"""

import numpy as np
from scipy.optimize import minimize
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """
    组合优化器

    支持的优化方法：
    - 马科维茨均值方差优化
    - 风险平价 (Risk Parity)
    - 最小方差
    - 最大夏普比率
    """

    def __init__(self, method: str = 'mean_variance'):
        self.method = method
        logger.info(f"PortfolioOptimizer initialized: method={method}")

    def optimize(self, returns: np.ndarray, **kwargs) -> np.ndarray:
        """
        优化组合权重

        Args:
            returns: 策略收益率矩阵 (n_samples, n_strategies)
            **kwargs: 优化参数

        Returns:
            最优权重数组
        """
        if self.method == 'mean_variance':
            return self._mean_variance_optimization(returns, **kwargs)
        elif self.method == 'risk_parity':
            return self._risk_parity_optimization(returns)
        elif self.method == 'min_variance':
            return self._min_variance_optimization(returns)
        elif self.method == 'max_sharpe':
            return self._max_sharpe_optimization(returns, **kwargs)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _mean_variance_optimization(self, returns: np.ndarray,
                                   risk_aversion: float = 1.0) -> np.ndarray:
        """马科维茨均值方差优化"""
        n_strategies = returns.shape[1]

        # 计算期望收益和协方差矩阵
        mean_returns = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns.T)

        # 目标函数：最大化 (收益 - 风险厌恶系数 * 方差)
        def objective(weights):
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            return -(portfolio_return - risk_aversion * portfolio_variance)

        # 约束条件
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = tuple((0, 1) for _ in range(n_strategies))

        # 初始权重（等权）
        initial_weights = np.array([1.0 / n_strategies] * n_strategies)

        # 优化
        result = minimize(objective, initial_weights, method='SLSQP',
                        bounds=bounds, constraints=constraints)

        if not result.success:
            logger.warning(f"Optimization failed: {result.message}")
            return initial_weights

        return result.x

    def _risk_parity_optimization(self, returns: np.ndarray) -> np.ndarray:
        """风险平价优化"""
        n_strategies = returns.shape[1]
        cov_matrix = np.cov(returns.T)

        # 目标函数：最小化风险贡献的差异
        def objective(weights):
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            marginal_contrib = np.dot(cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / portfolio_variance
            target_risk = 1.0 / n_strategies
            return np.sum((risk_contrib - target_risk) ** 2)

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = tuple((0, 1) for _ in range(n_strategies))
        initial_weights = np.array([1.0 / n_strategies] * n_strategies)

        result = minimize(objective, initial_weights, method='SLSQP',
                        bounds=bounds, constraints=constraints)

        return result.x if result.success else initial_weights

    def _min_variance_optimization(self, returns: np.ndarray) -> np.ndarray:
        """最小方差优化"""
        n_strategies = returns.shape[1]
        cov_matrix = np.cov(returns.T)

        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix, weights))

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = tuple((0, 1) for _ in range(n_strategies))
        initial_weights = np.array([1.0 / n_strategies] * n_strategies)

        result = minimize(objective, initial_weights, method='SLSQP',
                        bounds=bounds, constraints=constraints)

        return result.x if result.success else initial_weights

    def _max_sharpe_optimization(self, returns: np.ndarray,
                                risk_free_rate: float = 0.0) -> np.ndarray:
        """最大夏普比率优化"""
        n_strategies = returns.shape[1]
        mean_returns = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns.T)

        def objective(weights):
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_std = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (portfolio_return - risk_free_rate) / (portfolio_std + 1e-8)
            return -sharpe

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = tuple((0, 1) for _ in range(n_strategies))
        initial_weights = np.array([1.0 / n_strategies] * n_strategies)

        result = minimize(objective, initial_weights, method='SLSQP',
                        bounds=bounds, constraints=constraints)

        return result.x if result.success else initial_weights
