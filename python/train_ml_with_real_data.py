"""
使用真实/模拟历史数据训练 ML 因子模型
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from datetime import datetime
import logging

from strategy.factors.feature_engineering import FeatureEngineering
from strategy.factors.ml_factor import MLFactor
from strategy.factors.model_manager import ModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_historical_data(file_path):
    """加载历史数据"""
    logger.info(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    logger.info(f"Loaded {len(df)} records")
    return df


def calculate_ma(prices, period):
    """计算移动平均"""
    ma = np.zeros(len(prices))
    for i in range(period-1, len(prices)):
        ma[i] = np.mean(prices[i-period+1:i+1])
    return ma


def calculate_ema(prices, period):
    """计算指数移动平均"""
    ema = np.zeros(len(prices))
    ema[0] = prices[0]
    multiplier = 2 / (period + 1)
    for i in range(1, len(prices)):
        ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
    return ema


def prepare_training_data(df, symbol='BTCUSDT', lookback=50):
    """准备训练数据"""
    logger.info("Preparing training data...")

    # 特征工程
    feature_eng = FeatureEngineering(lookback_period=lookback)

    # 提取特征
    features = {}
    for col in ['open', 'high', 'low', 'close', 'volume']:
        features[col] = df[col].values

    # 计算技术指标
    prices = df['close'].values
    volumes = df['volume'].values

    # 收益率
    features['returns'] = np.concatenate([[0], np.diff(prices) / prices[:-1]])

    # 波动率
    returns = np.concatenate([[0], np.diff(prices) / prices[:-1]])
    volatility = np.zeros(len(prices))
    for i in range(20, len(prices)):
        volatility[i] = np.std(returns[i-20:i])
    features['volatility'] = volatility

    # RSI
    features['rsi_14'] = feature_eng._calculate_rsi(prices, 14)

    # MACD
    macd, signal, hist = feature_eng._calculate_macd(prices)
    features['macd'] = macd
    features['macd_signal'] = signal
    features['macd_histogram'] = hist

    # 布林带
    bb_upper, bb_middle, bb_lower = feature_eng._calculate_bollinger_bands(prices, 20, 2)
    features['bb_upper'] = bb_upper
    features['bb_middle'] = bb_middle
    features['bb_lower'] = bb_lower
    features['bb_position'] = (prices - bb_lower) / (bb_upper - bb_lower + 1e-10)

    # 移动平均
    features['ma_5'] = calculate_ma(prices, 5)
    features['ma_10'] = calculate_ma(prices, 10)
    features['ma_20'] = calculate_ma(prices, 20)
    features['ma_50'] = calculate_ma(prices, 50)

    # EMA
    features['ema_12'] = calculate_ema(prices, 12)
    features['ema_26'] = calculate_ema(prices, 26)

    # 成交量指标
    features['volume_ratio'] = volumes / (calculate_ma(volumes, 20) + 1e-10)

    # 价格动量
    features['momentum_5'] = np.concatenate([np.zeros(5), prices[5:] / prices[:-5] - 1])
    features['momentum_10'] = np.concatenate([np.zeros(10), prices[10:] / prices[:-10] - 1])

    logger.info(f"Extracted {len(features)} features")

    # 创建标签（未来收益）
    future_returns = np.concatenate([np.diff(prices) / prices[:-1], [0]])
    labels = (future_returns > 0).astype(int)  # 1 = 上涨, 0 = 下跌

    logger.info(f"Created labels: {np.sum(labels)} up, {len(labels) - np.sum(labels)} down")

    return features, labels


def train_and_evaluate(features, labels, test_size=0.2):
    """训练和评估模型"""
    logger.info("Training ML models...")

    # 分割数据
    n_samples = len(labels)
    n_train = int(n_samples * (1 - test_size))

    # 准备特征矩阵
    feature_names = list(features.keys())
    X = np.column_stack([features[name] for name in feature_names])

    # 移除 NaN
    valid_idx = ~np.isnan(X).any(axis=1) & ~np.isnan(labels)
    X = X[valid_idx]
    y = labels[valid_idx]

    logger.info(f"Valid samples: {len(y)} (removed {n_samples - len(y)} NaN)")

    # 分割
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    logger.info(f"Train: {len(y_train)}, Test: {len(y_test)}")

    # 训练 Random Forest
    logger.info("\n" + "="*70)
    logger.info("Training Random Forest...")
    logger.info("="*70)

    rf_factor = MLFactor(
        factor_id='btcusdt_rf_real',
        config={
            'model_type': 'random_forest',
            'feature_names': feature_names,
            'lookback_period': 50,
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 20,
        }
    )

    rf_factor.train(features, y)

    # 手动评估
    from sklearn.metrics import accuracy_score
    X_rf = np.column_stack([features[name] for name in feature_names])
    X_rf = X_rf[valid_idx]
    X_rf_train, X_rf_test = X_rf[:n_train], X_rf[n_train:]

    # 预测
    from sklearn.preprocessing import StandardScaler
    scaler_rf = StandardScaler()
    X_rf_train_scaled = scaler_rf.fit_transform(X_rf_train)
    X_rf_test_scaled = scaler_rf.transform(X_rf_test)

    y_train_pred = rf_factor.model.predict(X_rf_train_scaled)
    y_test_pred = rf_factor.model.predict(X_rf_test_scaled)

    rf_metrics = {
        'train_accuracy': accuracy_score(y_train, y_train_pred),
        'test_accuracy': accuracy_score(y_test, y_test_pred),
    }

    logger.info(f"Random Forest Results:")
    logger.info(f"  Train Accuracy: {rf_metrics['train_accuracy']:.4f}")
    logger.info(f"  Test Accuracy: {rf_metrics['test_accuracy']:.4f}")
    logger.info(f"  Train AUC: {rf_metrics.get('train_auc', 0):.4f}")
    logger.info(f"  Test AUC: {rf_metrics.get('test_auc', 0):.4f}")

    # 训练 Gradient Boosting
    logger.info("\n" + "="*70)
    logger.info("Training Gradient Boosting...")
    logger.info("="*70)

    gb_factor = MLFactor(
        factor_id='btcusdt_gb_real',
        config={
            'model_type': 'gradient_boosting',
            'feature_names': feature_names,
            'lookback_period': 50,
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
        }
    )

    gb_factor.train(features, y)

    # 手动评估 GB
    X_gb = np.column_stack([features[name] for name in feature_names])
    X_gb = X_gb[valid_idx]
    X_gb_train, X_gb_test = X_gb[:n_train], X_gb[n_train:]

    scaler_gb = StandardScaler()
    X_gb_train_scaled = scaler_gb.fit_transform(X_gb_train)
    X_gb_test_scaled = scaler_gb.transform(X_gb_test)

    y_train_pred_gb = gb_factor.model.predict(X_gb_train_scaled)
    y_test_pred_gb = gb_factor.model.predict(X_gb_test_scaled)

    gb_metrics = {
        'train_accuracy': accuracy_score(y_train, y_train_pred_gb),
        'test_accuracy': accuracy_score(y_test, y_test_pred_gb),
    }

    logger.info(f"Gradient Boosting Results:")
    logger.info(f"  Train Accuracy: {gb_metrics['train_accuracy']:.4f}")
    logger.info(f"  Test Accuracy: {gb_metrics['test_accuracy']:.4f}")
    logger.info(f"  Train AUC: {gb_metrics.get('train_auc', 0):.4f}")
    logger.info(f"  Test AUC: {gb_metrics.get('test_auc', 0):.4f}")

    # 选择最佳模型
    if rf_metrics['test_accuracy'] > gb_metrics['test_accuracy']:
        best_model = rf_factor
        best_metrics = rf_metrics
        best_name = "Random Forest"
    else:
        best_model = gb_factor
        best_metrics = gb_metrics
        best_name = "Gradient Boosting"

    logger.info(f"\n✓ Best Model: {best_name}")

    return best_model, best_metrics, {'rf': rf_metrics, 'gb': gb_metrics}


def main():
    """主函数"""
    print("=" * 70)
    print("ML 因子模型训练（真实/模拟数据）")
    print("=" * 70)

    # 加载数据
    data_file = 'data/historical/BTCUSDT_1h_365d_okx.csv'
    df = load_historical_data(data_file)

    print(f"\n数据概览:")
    print(f"  记录数: {len(df)}")
    print(f"  时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    print(f"  价格范围: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")

    # 准备训练数据
    features, labels = prepare_training_data(df, symbol='BTCUSDT', lookback=50)

    # 训练和评估
    best_model, best_metrics, all_metrics = train_and_evaluate(features, labels, test_size=0.2)

    # 保存最佳模型
    model_manager = ModelManager(models_dir='models')
    model_path = model_manager.save_model(
        model=best_model.model,
        model_id=best_model.factor_id,
        metadata={
            'train_accuracy': best_metrics['train_accuracy'],
            'test_accuracy': best_metrics['test_accuracy'],
            'feature_names': best_model.config['feature_names'],
            'training_date': datetime.now().isoformat(),
            'data_file': data_file,
            'n_samples': len(labels),
        }
    )

    # 生成报告
    print("\n" + "=" * 70)
    print("训练总结")
    print("=" * 70)

    print(f"\n数据集:")
    print(f"  总样本数: {len(labels)}")
    print(f"  训练集: {int(len(labels) * 0.8)}")
    print(f"  测试集: {int(len(labels) * 0.2)}")
    print(f"  特征数: {len(features)}")

    print(f"\n模型对比:")
    print(f"{'模型':<20} {'训练准确率':>12} {'测试准确率':>12}")
    print("-" * 50)
    print(f"{'Random Forest':<20} {all_metrics['rf']['train_accuracy']:>11.2%} {all_metrics['rf']['test_accuracy']:>11.2%}")
    print(f"{'Gradient Boosting':<20} {all_metrics['gb']['train_accuracy']:>11.2%} {all_metrics['gb']['test_accuracy']:>11.2%}")

    print(f"\n最佳模型: {best_model.factor_id}")
    print(f"  训练准确率: {best_metrics['train_accuracy']:.2%}")
    print(f"  测试准确率: {best_metrics['test_accuracy']:.2%}")
    print(f"  模型路径: {model_path}")

    print("\n" + "=" * 70)
    print("训练完成！")
    print("=" * 70)

    print(f"\n下一步:")
    print(f"  1. 使用模型进行回测: python backtest_with_ml.py")
    print(f"  2. 查看特征重要性")
    print(f"  3. 优化模型参数")


if __name__ == '__main__':
    main()
