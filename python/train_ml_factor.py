"""
Train ML Factor - 训练机器学习因子模型

从历史数据训练 ML 模型用于预测市场方向
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import logging
from datetime import datetime

from strategy.factors.ml_factor import MLFactor, create_labels_from_returns
from strategy.factors.feature_engineering import FeatureEngineering

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_data(n_samples: int = 1000):
    """
    生成示例数据（实际使用时应从数据库加载历史数据）

    Args:
        n_samples: 样本数量

    Returns:
        价格和成交量数组
    """
    # 生成模拟价格数据（随机游走）
    np.random.seed(42)
    returns = np.random.randn(n_samples) * 0.02
    prices = 50000 * np.exp(np.cumsum(returns))

    # 生成模拟成交量数据
    volumes = np.random.uniform(100, 1000, n_samples)

    return prices, volumes


def train_ml_factor():
    """训练 ML 因子模型"""
    logger.info("=" * 60)
    logger.info("Training ML Factor Model")
    logger.info("=" * 60)

    # 1. 生成或加载历史数据
    logger.info("Loading historical data...")
    prices, volumes = generate_sample_data(n_samples=1000)
    logger.info(f"Loaded {len(prices)} samples")

    # 2. 特征工程
    logger.info("Extracting features...")
    feature_eng = FeatureEngineering(lookback_period=50)

    symbol = "BTCUSDT"
    for price, volume in zip(prices, volumes):
        feature_eng.update(symbol, price, volume)

    features = feature_eng.extract_features(symbol)
    logger.info(f"Extracted {len(features)} features")
    logger.info(f"Feature names: {list(features.keys())}")

    # 3. 创建标签
    logger.info("Creating labels...")
    returns = features['returns']
    labels = create_labels_from_returns(returns, horizon=1)

    # 统计标签分布
    n_up = np.sum(labels == 1)
    n_down = np.sum(labels == 0)
    logger.info(f"Label distribution: UP={n_up} ({n_up/len(labels)*100:.1f}%), DOWN={n_down} ({n_down/len(labels)*100:.1f}%)")

    # 4. 创建 ML 因子
    logger.info("Creating ML factor...")
    ml_config = {
        'model_type': 'random_forest',  # 或 'gradient_boosting'
        'feature_names': [
            'returns', 'volatility', 'rsi_14', 'macd',
            'bb_position', 'volume_ratio'
        ],
        'prediction_horizon': 1,
        'model_dir': 'models',
        'load_model': False
    }

    ml_factor = MLFactor(
        factor_id='btcusdt_ml_factor',
        config=ml_config
    )

    # 5. 训练模型
    logger.info("Training model...")
    train_result = ml_factor.train(
        features=features,
        labels=labels,
        test_size=0.2,
        random_state=42
    )

    logger.info("=" * 60)
    logger.info("Training Results:")
    logger.info(f"  Train samples: {train_result['train_samples']}")
    logger.info(f"  Test samples: {train_result['test_samples']}")
    logger.info(f"  Train accuracy: {train_result['train_accuracy']:.4f}")
    logger.info(f"  Test accuracy: {train_result['test_accuracy']:.4f}")
    logger.info("=" * 60)

    # 6. 测试预测
    logger.info("Testing prediction...")
    factor_value = ml_factor.calculate(features)
    logger.info(f"Prediction: {factor_value.value}")
    logger.info(f"Confidence: {factor_value.confidence:.4f}")
    logger.info(f"Metadata: {factor_value.metadata}")

    logger.info("=" * 60)
    logger.info("Training completed successfully!")
    logger.info(f"Model saved to: models/btcusdt_ml_factor/")
    logger.info("=" * 60)


if __name__ == '__main__':
    try:
        train_ml_factor()
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)
