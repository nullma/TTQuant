"""
快速改进方案 - 优化 ML 模型性能

基于 Phase 1 的发现，实施以下改进：
1. 添加更多特征
2. 优化模型参数（减少过拟合）
3. 改进标签设计
4. 添加交易过滤
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_advanced_features(df):
    """计算高级特征"""
    features = {}

    prices = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    volumes = df['volume'].values

    # 基础特征
    features['returns'] = np.concatenate([[0], np.diff(prices) / prices[:-1]])

    # 多周期动量
    for period in [5, 10, 20, 30]:
        momentum = np.zeros(len(prices))
        momentum[period:] = (prices[period:] / prices[:-period]) - 1
        features[f'momentum_{period}'] = momentum

    # ATR (Average True Range)
    tr = np.maximum(highs - lows,
                    np.maximum(np.abs(highs - np.roll(prices, 1)),
                              np.abs(lows - np.roll(prices, 1))))
    atr = np.zeros(len(prices))
    for i in range(14, len(prices)):
        atr[i] = np.mean(tr[i-14:i])
    features['atr'] = atr

    # 波动率（多周期）
    for period in [10, 20, 30]:
        vol = np.zeros(len(prices))
        for i in range(period, len(prices)):
            vol[i] = np.std(features['returns'][i-period:i])
        features[f'volatility_{period}'] = vol

    # 价格位置（相对于高低点）
    for period in [20, 50]:
        price_position = np.zeros(len(prices))
        for i in range(period, len(prices)):
            high_max = np.max(highs[i-period:i])
            low_min = np.min(lows[i-period:i])
            if high_max > low_min:
                price_position[i] = (prices[i] - low_min) / (high_max - low_min)
        features[f'price_position_{period}'] = price_position

    # 成交量特征
    vol_ma = np.zeros(len(volumes))
    for i in range(20, len(volumes)):
        vol_ma[i] = np.mean(volumes[i-20:i])
    features['volume_ratio'] = volumes / (vol_ma + 1e-10)

    # OBV (On-Balance Volume)
    obv = np.zeros(len(prices))
    for i in range(1, len(prices)):
        if prices[i] > prices[i-1]:
            obv[i] = obv[i-1] + volumes[i]
        elif prices[i] < prices[i-1]:
            obv[i] = obv[i-1] - volumes[i]
        else:
            obv[i] = obv[i-1]
    features['obv'] = obv / (np.max(np.abs(obv)) + 1e-10)

    # RSI
    def calculate_rsi(prices, period=14):
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gains = np.zeros(len(prices))
        avg_losses = np.zeros(len(prices))

        for i in range(period, len(prices)):
            avg_gains[i] = np.mean(gains[i-period:i])
            avg_losses[i] = np.mean(losses[i-period:i])

        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    features['rsi_14'] = calculate_rsi(prices, 14)

    return features


def create_improved_labels(prices, threshold=0.01):
    """
    改进的标签设计

    只在明确趋势时生成信号：
    - 涨幅 > threshold: 买入 (1)
    - 跌幅 < -threshold: 卖出 (-1)
    - 其他: 持有 (0)
    """
    returns = np.concatenate([[0], np.diff(prices) / prices[:-1]])

    labels = np.zeros(len(prices), dtype=int)
    labels[returns > threshold] = 1
    labels[returns < -threshold] = -1

    return labels


def train_improved_model(df, test_size=0.2):
    """训练改进的模型"""
    logger.info("计算高级特征...")
    features = calculate_advanced_features(df)

    # 创建特征矩阵
    feature_names = list(features.keys())
    X = np.column_stack([features[name] for name in feature_names])

    # 创建改进的标签
    prices = df['close'].values
    y = create_improved_labels(prices, threshold=0.01)

    # 移除 NaN
    valid_idx = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
    X = X[valid_idx]
    y = y[valid_idx]

    logger.info(f"有效样本: {len(y)}")
    logger.info(f"标签分布: 买入={np.sum(y==1)}, 持有={np.sum(y==0)}, 卖出={np.sum(y==-1)}")

    # 时间序列分割
    n_train = int(len(y) * (1 - test_size))
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 训练模型（减少过拟合）
    logger.info("训练改进的 Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,  # 降低深度
        min_samples_split=50,  # 增加最小分割样本
        min_samples_leaf=20,  # 增加叶子节点最小样本
        max_features='sqrt',  # 限制特征数量
        class_weight='balanced',  # 平衡类别权重
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train_scaled, y_train)

    # 评估
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)

    logger.info(f"训练准确率: {train_score:.4f}")
    logger.info(f"测试准确率: {test_score:.4f}")

    # 特征重要性
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]

    logger.info("\n前 10 个重要特征:")
    for i in range(min(10, len(feature_names))):
        idx = indices[i]
        logger.info(f"  {feature_names[idx]}: {importances[idx]:.4f}")

    # 保存模型
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names
    }

    os.makedirs('models/improved', exist_ok=True)
    with open('models/improved/model.pkl', 'wb') as f:
        pickle.dump(model_data, f)

    logger.info("\n✓ 模型已保存到: models/improved/model.pkl")

    return model, scaler, feature_names


def main():
    """主函数"""
    print("="*70)
    print("快速改进方案 - 优化 ML 模型")
    print("="*70)

    # 加载数据
    data_file = 'data/historical/BTCUSDT_1h_365d_okx.csv'
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    logger.info(f"\n数据概览:")
    logger.info(f"  记录数: {len(df)}")
    logger.info(f"  时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    logger.info(f"  价格范围: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")

    # 训练改进的模型
    model, scaler, feature_names = train_improved_model(df, test_size=0.2)

    print("\n"+"="*70)
    print("训练完成！")
    print("="*70)
    print("\n下一步:")
    print("  1. 运行回测: python backtest_improved.py")
    print("  2. 对比改进前后的结果")
    print("  3. 继续优化特征和参数")


if __name__ == '__main__':
    main()
