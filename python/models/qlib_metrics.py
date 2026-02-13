"""
Qlib 风格评估指标
实现量化金融专业评估指标，包括 IC、Rank IC、IR 和 Quantile Analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
try:
    from scipy import stats
    _has_scipy = True
except ImportError:
    _has_scipy = False
from pathlib import Path

# matplotlib 是可选依赖
try:
    import matplotlib.pyplot as plt
    _has_matplotlib = True
except ImportError:
    _has_matplotlib = False


class QlibMetrics:
    """
    Qlib 风格的评估指标计算器
    """

    @staticmethod
    def information_coefficient(
        y_pred: np.ndarray,
        y_true: np.ndarray,
        method: str = 'pearson'
    ) -> float:
        """
        计算 Information Coefficient (IC)

        Args:
            y_pred: 预测值
            y_true: 真实值
            method: 相关系数方法 ('pearson' 或 'spearman')

        Returns:
            IC 值
        """
        # 移除 NaN 值
        mask = ~(np.isnan(y_pred) | np.isnan(y_true))
        y_pred_clean = y_pred[mask]
        y_true_clean = y_true[mask]

        if len(y_pred_clean) < 2:
            return np.nan

        if method == 'pearson':
            # Pearson 相关系数
            ic = np.corrcoef(y_pred_clean, y_true_clean)[0, 1]
        elif method == 'spearman':
            # Spearman 秩相关系数
            if _has_scipy:
                ic, _ = stats.spearmanr(y_pred_clean, y_true_clean)
            else:
                #如果没有 scipy，简单的 rank IC 替代（或者返回 NaN）
                #这里简单返回 Pearson 作为近似，或者实现一个简单的 rank
                # 为避免引入复杂性，暂返 NaN 并打印警告
                print("Warning: scipy not installed, cannot compute Rank IC exactly. Using Pearson as fallback.")
                ic = np.corrcoef(y_pred_clean, y_true_clean)[0, 1]
        else:
            raise ValueError(f"Unknown method: {method}")

        return ic

    @staticmethod
    def rank_ic(y_pred: np.ndarray, y_true: np.ndarray) -> float:
        """
        计算 Rank IC (Spearman 秩相关)

        Args:
            y_pred: 预测值
            y_true: 真实值

        Returns:
            Rank IC 值
        """
        return QlibMetrics.information_coefficient(y_pred, y_true, method='spearman')

    @staticmethod
    def information_ratio(ic_series: np.ndarray) -> float:
        """
        计算 Information Ratio (IR)
        IR = IC 均值 / IC 标准差

        Args:
            ic_series: IC 时间序列

        Returns:
            IR 值
        """
        ic_mean = np.nanmean(ic_series)
        ic_std = np.nanstd(ic_series)

        if ic_std == 0 or np.isnan(ic_std):
            return np.nan

        return ic_mean / ic_std

    @staticmethod
    def quantile_analysis(
        y_pred: np.ndarray,
        y_true: np.ndarray,
        n_quantiles: int = 5
    ) -> Dict[str, any]:
        """
        分位数分析
        将预测值分成 n 组，观察每组的平均收益

        Args:
            y_pred: 预测值
            y_true: 真实值（收益率）
            n_quantiles: 分位数数量

        Returns:
            分位数分析结果字典
        """
        # 移除 NaN 值
        mask = ~(np.isnan(y_pred) | np.isnan(y_true))
        y_pred_clean = y_pred[mask]
        y_true_clean = y_true[mask]

        if len(y_pred_clean) < n_quantiles:
            return {
                'quantile_returns': np.full(n_quantiles, np.nan),
                'quantile_counts': np.zeros(n_quantiles, dtype=int),
                'top_quantile_return': np.nan,
                'bottom_quantile_return': np.nan,
                'long_short_return': np.nan
            }

        # 根据预测值分组
        quantiles = pd.qcut(y_pred_clean, q=n_quantiles, labels=False, duplicates='drop')

        # 计算每组的平均收益
        quantile_returns = []
        quantile_counts = []

        for q in range(n_quantiles):
            mask_q = (quantiles == q)
            if mask_q.sum() > 0:
                quantile_returns.append(y_true_clean[mask_q].mean())
                quantile_counts.append(mask_q.sum())
            else:
                quantile_returns.append(np.nan)
                quantile_counts.append(0)

        quantile_returns = np.array(quantile_returns)
        quantile_counts = np.array(quantile_counts)

        # Top Quantile (预测最高的组)
        top_quantile_return = quantile_returns[-1]

        # Bottom Quantile (预测最低的组)
        bottom_quantile_return = quantile_returns[0]

        # Long-Short Return (做多 Top，做空 Bottom)
        long_short_return = top_quantile_return - bottom_quantile_return

        return {
            'quantile_returns': quantile_returns,
            'quantile_counts': quantile_counts,
            'top_quantile_return': top_quantile_return,
            'bottom_quantile_return': bottom_quantile_return,
            'long_short_return': long_short_return
        }

    @staticmethod
    def rolling_ic(
        y_pred: np.ndarray,
        y_true: np.ndarray,
        window: int = 20,
        method: str = 'pearson'
    ) -> np.ndarray:
        """
        计算滚动 IC

        Args:
            y_pred: 预测值
            y_true: 真实值
            window: 滚动窗口大小
            method: 相关系数方法

        Returns:
            滚动 IC 数组
        """
        n = len(y_pred)
        rolling_ics = np.full(n, np.nan)

        for i in range(window, n):
            pred_window = y_pred[i-window:i]
            true_window = y_true[i-window:i]
            rolling_ics[i] = QlibMetrics.information_coefficient(
                pred_window, true_window, method=method
            )

        return rolling_ics

    @staticmethod
    def compute_all_metrics(
        y_pred: np.ndarray,
        y_true: np.ndarray,
        n_quantiles: int = 5
    ) -> Dict[str, any]:
        """
        计算所有评估指标

        Args:
            y_pred: 预测值
            y_true: 真实值
            n_quantiles: 分位数数量

        Returns:
            所有指标的字典
        """
        # IC 指标
        ic = QlibMetrics.information_coefficient(y_pred, y_true, method='pearson')
        rank_ic = QlibMetrics.rank_ic(y_pred, y_true)

        # 分位数分析
        quantile_results = QlibMetrics.quantile_analysis(y_pred, y_true, n_quantiles)

        # 汇总结果
        metrics = {
            'ic': ic,
            'rank_ic': rank_ic,
            'quantile_returns': quantile_results['quantile_returns'],
            'quantile_counts': quantile_results['quantile_counts'],
            'top_quantile_return': quantile_results['top_quantile_return'],
            'bottom_quantile_return': quantile_results['bottom_quantile_return'],
            'long_short_return': quantile_results['long_short_return']
        }

        return metrics


class QlibMetricsVisualizer:
    """
    Qlib 指标可视化工具
    """

    @staticmethod
    def plot_quantile_analysis(
        quantile_returns: np.ndarray,
        quantile_counts: np.ndarray,
        save_path: Optional[str] = None
    ):
        """
        绘制分位数分析图表

        Args:
            quantile_returns: 每个分位数的平均收益
            quantile_counts: 每个分位数的样本数
            save_path: 保存路径（可选）
        """
        if not _has_matplotlib:
            print("警告: matplotlib 未安装，无法绘制图表")
            return

        n_quantiles = len(quantile_returns)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # 左图：分位数收益
        x = np.arange(n_quantiles)
        colors = ['red' if r < 0 else 'green' for r in quantile_returns]

        ax1.bar(x, quantile_returns, color=colors, alpha=0.7, edgecolor='black')
        ax1.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax1.set_xlabel('Quantile (0=Lowest Pred, {}=Highest Pred)'.format(n_quantiles-1))
        ax1.set_ylabel('Average Return')
        ax1.set_title('Quantile Analysis: Average Returns by Prediction Quantile')
        ax1.grid(True, alpha=0.3)

        # 添加数值标签
        for i, v in enumerate(quantile_returns):
            if not np.isnan(v):
                ax1.text(i, v, f'{v:.4f}', ha='center', va='bottom' if v > 0 else 'top')

        # 右图：分位数样本数
        ax2.bar(x, quantile_counts, color='steelblue', alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Quantile')
        ax2.set_ylabel('Sample Count')
        ax2.set_title('Sample Distribution by Quantile')
        ax2.grid(True, alpha=0.3)

        # 添加数值标签
        for i, v in enumerate(quantile_counts):
            ax2.text(i, v, str(v), ha='center', va='bottom')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")

        plt.show()

    @staticmethod
    def plot_rolling_ic(
        rolling_ic: np.ndarray,
        timestamps: Optional[pd.DatetimeIndex] = None,
        save_path: Optional[str] = None
    ):
        """
        绘制滚动 IC 图表

        Args:
            rolling_ic: 滚动 IC 数组
            timestamps: 时间戳（可选）
            save_path: 保存路径（可选）
        """
        if not _has_matplotlib:
            print("警告: matplotlib 未安装，无法绘制图表")
            return

        fig, ax = plt.subplots(figsize=(14, 6))

        x = timestamps if timestamps is not None else np.arange(len(rolling_ic))

        ax.plot(x, rolling_ic, color='steelblue', linewidth=1.5, label='Rolling IC')
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.axhline(y=np.nanmean(rolling_ic), color='red', linestyle='--',
                   linewidth=1, label=f'Mean IC: {np.nanmean(rolling_ic):.4f}')

        ax.set_xlabel('Time' if timestamps is not None else 'Sample Index')
        ax.set_ylabel('IC')
        ax.set_title('Rolling Information Coefficient')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")

        plt.show()

    @staticmethod
    def plot_ic_distribution(
        ic_series: np.ndarray,
        save_path: Optional[str] = None
    ):
        """
        绘制 IC 分布直方图

        Args:
            ic_series: IC 时间序列
            save_path: 保存路径（可选）
        """
        if not _has_matplotlib:
            print("警告: matplotlib 未安装，无法绘制图表")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        # 移除 NaN
        ic_clean = ic_series[~np.isnan(ic_series)]

        ax.hist(ic_clean, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
        ax.axvline(x=np.mean(ic_clean), color='red', linestyle='--',
                   linewidth=2, label=f'Mean: {np.mean(ic_clean):.4f}')
        ax.axvline(x=0, color='black', linestyle='--', linewidth=1)

        ax.set_xlabel('IC')
        ax.set_ylabel('Frequency')
        ax.set_title('IC Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 添加统计信息
        stats_text = f'Mean: {np.mean(ic_clean):.4f}\n'
        stats_text += f'Std: {np.std(ic_clean):.4f}\n'
        stats_text += f'IR: {np.mean(ic_clean) / np.std(ic_clean):.4f}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")

        plt.show()


class QlibStyleTrainer:
    """
    Qlib 风格的训练器
    集成 IC 指标、Early Stopping 和可视化
    """

    def __init__(
        self,
        model,
        early_stopping_rounds: int = 10,
        early_stopping_metric: str = 'ic',
        verbose: bool = True
    ):
        """
        Args:
            model: 机器学习模型（需要有 fit 和 predict 方法）
            early_stopping_rounds: Early Stopping 轮数
            early_stopping_metric: Early Stopping 指标 ('ic' 或 'rank_ic')
            verbose: 是否打印训练信息
        """
        self.model = model
        self.early_stopping_rounds = early_stopping_rounds
        self.early_stopping_metric = early_stopping_metric
        self.verbose = verbose

        # 训练历史
        self.history = {
            'train_ic': [],
            'val_ic': [],
            'train_rank_ic': [],
            'val_rank_ic': [],
            'train_loss': [],
            'val_loss': []
        }

        self.best_score = -np.inf
        self.best_epoch = 0
        self.no_improvement_count = 0

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_val: pd.DataFrame,
        y_val: np.ndarray,
        n_epochs: int = 100
    ):
        """
        训练模型（支持 Early Stopping）

        Args:
            X_train: 训练集特征
            y_train: 训练集标签
            X_val: 验证集特征
            y_val: 验证集标签
            n_epochs: 最大训练轮数

        Returns:
            训练历史
        """
        if self.verbose:
            print("=" * 60)
            print("开始训练（Qlib 风格）")
            print("=" * 60)

        # 对于不支持增量训练的模型，只训练一次
        if not hasattr(self.model, 'partial_fit'):
            self.model.fit(X_train, y_train)

            # 评估
            train_metrics = self._evaluate(X_train, y_train, prefix='train')
            val_metrics = self._evaluate(X_val, y_val, prefix='val')

            # 记录历史
            self._update_history(train_metrics, val_metrics)

            if self.verbose:
                self._print_metrics(0, train_metrics, val_metrics)

            return self.history

        # 对于支持增量训练的模型
        for epoch in range(n_epochs):
            # 训练一轮
            self.model.partial_fit(X_train, y_train)

            # 评估
            train_metrics = self._evaluate(X_train, y_train, prefix='train')
            val_metrics = self._evaluate(X_val, y_val, prefix='val')

            # 记录历史
            self._update_history(train_metrics, val_metrics)

            if self.verbose:
                self._print_metrics(epoch, train_metrics, val_metrics)

            # Early Stopping
            current_score = val_metrics[f'val_{self.early_stopping_metric}']

            if current_score > self.best_score:
                self.best_score = current_score
                self.best_epoch = epoch
                self.no_improvement_count = 0
            else:
                self.no_improvement_count += 1

            if self.no_improvement_count >= self.early_stopping_rounds:
                if self.verbose:
                    print(f"\nEarly Stopping at epoch {epoch}")
                    print(f"Best {self.early_stopping_metric}: {self.best_score:.4f} at epoch {self.best_epoch}")
                break

        return self.history

    def _evaluate(self, X: pd.DataFrame, y: np.ndarray, prefix: str = '') -> Dict[str, float]:
        """
        评估模型

        Args:
            X: 特征
            y: 标签
            prefix: 指标前缀

        Returns:
            评估指标字典
        """
        y_pred = self.model.predict(X)

        # 计算 IC 指标
        ic = QlibMetrics.information_coefficient(y_pred, y, method='pearson')
        rank_ic = QlibMetrics.rank_ic(y_pred, y)

        # 计算 MSE
        mse = np.mean((y_pred - y) ** 2)

        metrics = {
            f'{prefix}_ic': ic,
            f'{prefix}_rank_ic': rank_ic,
            f'{prefix}_loss': mse
        }

        return metrics

    def _update_history(self, train_metrics: Dict, val_metrics: Dict):
        """更新训练历史"""
        self.history['train_ic'].append(train_metrics['train_ic'])
        self.history['val_ic'].append(val_metrics['val_ic'])
        self.history['train_rank_ic'].append(train_metrics['train_rank_ic'])
        self.history['val_rank_ic'].append(val_metrics['val_rank_ic'])
        self.history['train_loss'].append(train_metrics['train_loss'])
        self.history['val_loss'].append(val_metrics['val_loss'])

    def _print_metrics(self, epoch: int, train_metrics: Dict, val_metrics: Dict):
        """打印训练指标"""
        print(f"Epoch {epoch:3d} | "
              f"Train IC: {train_metrics['train_ic']:7.4f} | "
              f"Val IC: {val_metrics['val_ic']:7.4f} | "
              f"Train RankIC: {train_metrics['train_rank_ic']:7.4f} | "
              f"Val RankIC: {val_metrics['val_rank_ic']:7.4f} | "
              f"Val Loss: {val_metrics['val_loss']:.6f}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        预测

        Args:
            X: 特征

        Returns:
            预测值
        """
        return self.model.predict(X)

    def evaluate_test(
        self,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        n_quantiles: int = 5,
        save_dir: Optional[str] = None
    ) -> Dict[str, any]:
        """
        在测试集上评估并生成报告

        Args:
            X_test: 测试集特征
            y_test: 测试集标签
            n_quantiles: 分位数数量
            save_dir: 保存目录（可选）

        Returns:
            评估指标字典
        """
        if self.verbose:
            print("\n" + "=" * 60)
            print("测试集评估")
            print("=" * 60)

        # 预测
        y_pred = self.predict(X_test)

        # 计算所有指标
        metrics = QlibMetrics.compute_all_metrics(y_pred, y_test, n_quantiles)

        # 打印结果
        if self.verbose:
            print(f"\nIC: {metrics['ic']:.4f}")
            print(f"Rank IC: {metrics['rank_ic']:.4f}")
            print(f"\nQuantile Analysis:")
            for i, (ret, count) in enumerate(zip(metrics['quantile_returns'], metrics['quantile_counts'])):
                print(f"  Quantile {i}: Return={ret:.4f}, Count={count}")
            print(f"\nTop Quantile Return: {metrics['top_quantile_return']:.4f}")
            print(f"Bottom Quantile Return: {metrics['bottom_quantile_return']:.4f}")
            print(f"Long-Short Return: {metrics['long_short_return']:.4f}")

        # 可视化
        if save_dir:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)

            # 分位数分析图
            QlibMetricsVisualizer.plot_quantile_analysis(
                metrics['quantile_returns'],
                metrics['quantile_counts'],
                save_path=str(save_dir / 'quantile_analysis.png')
            )

            # 滚动 IC 图
            rolling_ic = QlibMetrics.rolling_ic(y_pred, y_test, window=20)
            QlibMetricsVisualizer.plot_rolling_ic(
                rolling_ic,
                save_path=str(save_dir / 'rolling_ic.png')
            )

        return metrics

    def plot_training_history(self, save_path: Optional[str] = None):
        """
        绘制训练历史

        Args:
            save_path: 保存路径（可选）
        """
        if not _has_matplotlib:
            print("警告: matplotlib 未安装，无法绘制图表")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # IC
        axes[0, 0].plot(self.history['train_ic'], label='Train IC', color='blue')
        axes[0, 0].plot(self.history['val_ic'], label='Val IC', color='orange')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('IC')
        axes[0, 0].set_title('Information Coefficient')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Rank IC
        axes[0, 1].plot(self.history['train_rank_ic'], label='Train Rank IC', color='blue')
        axes[0, 1].plot(self.history['val_rank_ic'], label='Val Rank IC', color='orange')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Rank IC')
        axes[0, 1].set_title('Rank Information Coefficient')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # Loss
        axes[1, 0].plot(self.history['train_loss'], label='Train Loss', color='blue')
        axes[1, 0].plot(self.history['val_loss'], label='Val Loss', color='orange')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Loss (MSE)')
        axes[1, 0].set_title('Training Loss')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # IC vs Loss
        axes[1, 1].scatter(self.history['val_loss'], self.history['val_ic'], alpha=0.6)
        axes[1, 1].set_xlabel('Val Loss (MSE)')
        axes[1, 1].set_ylabel('Val IC')
        axes[1, 1].set_title('IC vs Loss')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"训练历史图已保存到: {save_path}")

        plt.show()

