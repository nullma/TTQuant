"""
使用真实历史数据训练 Qlib Transformer 模型
整合 Phase 1.5-4 的所有组件
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# IMPORTANT: Import PyTorch BEFORE NumPy to avoid DLL conflicts on Windows
# PyTorch 模型 (可选)
TORCH_AVAILABLE = False
TORCH_ERROR = None
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    from models.qlib_transformer import QlibTransformer as QlibStyleTransformer
    from models.qlib_metrics import QlibStyleTrainer
    TORCH_AVAILABLE = True
except (ImportError, OSError) as e:
    import traceback
    TORCH_ERROR = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

import numpy as np
import pandas as pd
from datetime import datetime
import logging
import argparse

# Qlib 风格组件
from strategy.factors.qlib_style_data_handler import DataMasking, TimeSeriesSplitter
from strategy.factors.ref_operator import RefOperator
from strategy.factors.alpha101 import Alpha101
from strategy.factors.feature_engineering import FeatureEngineering
from models.qlib_metrics import QlibMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if TORCH_AVAILABLE:
    logger.info("✓ PyTorch 加载成功，将使用 Transformer 模型")
else:
    logger.warning(f"PyTorch 加载失败 ({TORCH_ERROR})，将使用 RandomForest 作为备选")


def load_historical_data(file_path):
    """加载历史数据"""
    logger.info(f"加载数据: {file_path}")
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    logger.info(f"加载 {len(df)} 条记录")
    return df


def prepare_technical_features(df):
    """准备技术指标特征 (使用 Ref 算子)"""
    logger.info("计算技术指标...")

    ref = RefOperator()
    prices = df['close'].values
    volumes = df['volume'].values

    features = pd.DataFrame(index=df.index)

    # 收益率 (使用 Ref 算子)
    for period in [1, 5, 10]:
        features[f'returns_{period}'] = ref.returns(prices, period)

    # 移动平均比率
    for period in [5, 10, 20, 60]:
        ma = pd.Series(prices).rolling(period).mean().values
        features[f'ma_{period}_ratio'] = prices / (ma + 1e-10) - 1

    # 波动率
    for period in [5, 10, 20]:
        returns = ref.returns(prices, 1)
        vol = pd.Series(returns).rolling(period).std().values
        features[f'volatility_{period}'] = vol

    # 价格位置 (当前价格在 N 日内的位置)
    for period in [5, 10, 20]:
        high_n = pd.Series(prices).rolling(period).max().values
        low_n = pd.Series(prices).rolling(period).min().values
        features[f'price_position_{period}'] = (prices - low_n) / (high_n - low_n + 1e-10)

    # 成交量比率
    for period in [5, 10, 20]:
        vol_ma = pd.Series(volumes).rolling(period).mean().values
        features[f'volume_ratio_{period}'] = volumes / (vol_ma + 1e-10)

    # 动量
    for period in [5, 10, 20]:
        features[f'momentum_{period}'] = ref.delta(prices, period) / (prices + 1e-10)

    logger.info(f"技术指标: {len(features.columns)} 个")
    return features


def prepare_alpha101_features(df, ic_threshold=0.03):
    """准备 Alpha101 因子 (带 IC 筛选)"""
    logger.info("计算 Alpha101 因子...")

    alpha = Alpha101()

    # 准备数据
    open_ = df['open'].values
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    volume = df['volume'].values
    vwap = (high + low + close) / 3  # 简化的 VWAP

    # 计算所有因子
    all_factors = {}
    for i in range(1, 102):
        try:
            factor_name = f'alpha{i:03d}'
            method_name = f'alpha{i:03d}'

            if hasattr(alpha, method_name):
                method = getattr(alpha, method_name)

                # 尝试调用方法 (不同因子需要不同参数)
                try:
                    factor_values = method(close, volume)
                except TypeError:
                    try:
                        factor_values = method(open_, close, volume)
                    except TypeError:
                        try:
                            factor_values = method(open_, high, low, close, volume, vwap)
                        except TypeError:
                            try:
                                factor_values = method(close)
                            except TypeError:
                                try:
                                    factor_values = method(open_, close)
                                except TypeError:
                                    continue

                if factor_values is not None and not np.all(np.isnan(factor_values)):
                    all_factors[factor_name] = factor_values
        except Exception as e:
            logger.warning(f"Alpha{i:03d} 计算失败: {e}")

    logger.info(f"成功计算 {len(all_factors)} 个 Alpha101 因子")

    # IC 筛选 (如果有标签)
    if ic_threshold > 0:
        logger.info(f"使用 IC > {ic_threshold} 筛选因子...")

        # 准备标签用于筛选
        ref = RefOperator()
        prices = df['close'].values
        labels = ref.returns(prices, 1)  # 下一期收益率

        metrics = QlibMetrics()
        selected_factors = {}

        for name, values in all_factors.items():
            # 移除 NaN
            mask = ~(np.isnan(values) | np.isnan(labels))
            if mask.sum() < 100:  # 至少需要 100 个有效样本
                continue

            # 计算 IC
            ic = metrics.information_coefficient(values[mask], labels[mask])

            if abs(ic) > ic_threshold:
                selected_factors[name] = values
                logger.info(f"  {name}: IC = {ic:.4f} ✓")

        logger.info(f"筛选后保留 {len(selected_factors)} 个因子")
        return pd.DataFrame(selected_factors, index=df.index)

    return pd.DataFrame(all_factors, index=df.index)


def prepare_features_and_labels(df, ic_threshold=0.03):
    """准备完整特征集和标签"""
    logger.info("\n" + "="*70)
    logger.info("准备特征和标签")
    logger.info("="*70)

    # 1. 技术指标
    tech_features = prepare_technical_features(df)

    # 2. Alpha101 因子
    alpha_features = prepare_alpha101_features(df, ic_threshold)

    # 3. 合并特征
    features = pd.concat([tech_features, alpha_features], axis=1)
    logger.info(f"总特征数: {len(features.columns)}")

    # 4. 准备标签 (使用 DataMasking)
    masking = DataMasking(feature_gap=1, label_gap=1)
    labels = masking.prepare_labels(df)

    # 5. 对齐数据
    features, labels = masking.align_data(features, labels)

    logger.info(f"有效样本数: {len(labels)}")
    logger.info(f"特征维度: {features.shape}")

    return features, labels


def create_sequences(X, y, seq_len=60):
    """创建时间序列数据"""
    X_seq, y_seq = [], []
    for i in range(seq_len, len(X)):
        X_seq.append(X[i-seq_len:i])
        y_seq.append(y[i])
    return np.array(X_seq), np.array(y_seq)


def train_transformer(features, labels, args):
    """训练 Transformer 模型"""
    if not TORCH_AVAILABLE:
        logger.error("PyTorch 未安装，无法训练 Transformer")
        return train_randomforest_fallback(features, labels, args)

    logger.info("\n" + "="*70)
    logger.info("训练 Qlib Transformer 模型")
    logger.info("="*70)

    # 1. 时间序列分割
    splitter = TimeSeriesSplitter()
    X_train, X_test, y_train, y_test = splitter.split(
        features, labels, test_size=args.test_size, gap=1
    )

    logger.info(f"训练集: {len(y_train)} 样本")
    logger.info(f"测试集: {len(y_test)} 样本")

    # 2. 创建序列数据
    logger.info(f"创建序列数据 (seq_len={args.seq_len})...")
    X_train_seq, y_train_seq = create_sequences(X_train, y_train, args.seq_len)
    X_test_seq, y_test_seq = create_sequences(X_test, y_test, args.seq_len)

    logger.info(f"训练序列: {X_train_seq.shape}")
    logger.info(f"测试序列: {X_test_seq.shape}")

    # 3. 创建 DataLoader
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train_seq),
        torch.FloatTensor(y_train_seq)
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test_seq),
        torch.FloatTensor(y_test_seq)
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=False  # 时间序列不打乱
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False
    )

    # 4. 创建模型
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"使用设备: {device}")

    model = QlibStyleTransformer(
        input_dim=features.shape[1],
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        max_seq_len=args.seq_len,
        dropout=args.dropout
    )

    # 统计参数量
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"模型参数量: {n_params:,}")

    # 5. 训练
    model = model.to(device)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay
    )
    criterion = nn.MSELoss()

    logger.info(f"\n开始训练 (epochs={args.epochs})...")

    ic_history = []
    rank_ic_history = []
    best_ic = -np.inf
    best_epoch = 0

    for epoch in range(args.epochs):
        # 训练阶段
        model.train()
        train_loss = 0.0

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            y_pred = model(X_batch)
            loss = criterion(y_pred.squeeze(), y_batch)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)

        # 评估阶段
        model.eval()
        test_loss = 0.0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)

                y_pred = model(X_batch)
                loss = criterion(y_pred.squeeze(), y_batch)
                test_loss += loss.item()

                all_preds.extend(y_pred.squeeze().cpu().numpy())
                all_labels.extend(y_batch.cpu().numpy())

        test_loss /= len(test_loader)

        # 计算 IC 指标
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)

        metrics = QlibMetrics()
        ic = metrics.information_coefficient(all_preds, all_labels)
        rank_ic = metrics.rank_ic(all_preds, all_labels)

        ic_history.append(ic)
        rank_ic_history.append(rank_ic)

        # 记录最佳模型
        if ic > best_ic:
            best_ic = ic
            best_epoch = epoch

        # 打印进度
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(f"Epoch {epoch+1:3d}/{args.epochs} | "
                       f"Train Loss: {train_loss:.6f} | "
                       f"Test Loss: {test_loss:.6f} | "
                       f"IC: {ic:.4f} | "
                       f"Rank IC: {rank_ic:.4f}")

    # 6. 最终评估
    logger.info("\n" + "="*70)
    logger.info("最终评估")
    logger.info("="*70)

    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            y_pred = model(X_batch)
            all_preds.extend(y_pred.squeeze().cpu().numpy())
            all_labels.extend(y_batch.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    # 计算所有指标
    final_metrics = QlibMetrics.compute_all_metrics(all_preds, all_labels, n_quantiles=5)

    # 计算 IR
    ic_array = np.array(ic_history)
    ir = np.mean(ic_array) / (np.std(ic_array) + 1e-10)
    final_metrics['ir'] = ir

    logger.info(f"测试集 IC: {final_metrics['ic']:.4f}")
    logger.info(f"测试集 Rank IC: {final_metrics['rank_ic']:.4f}")
    logger.info(f"测试集 IR: {ir:.4f}")
    logger.info(f"Top Quantile 收益: {final_metrics['top_quantile_return']:.4f}")
    logger.info(f"Bottom Quantile 收益: {final_metrics['bottom_quantile_return']:.4f}")
    logger.info(f"Long-Short 收益: {final_metrics['long_short_return']:.4f}")
    logger.info(f"最佳 IC: {best_ic:.4f} (Epoch {best_epoch+1})")

    # 7. 保存模型
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(model_dir, exist_ok=True)

    model_path = os.path.join(model_dir, 'transformer_real_data.pth')
    torch.save(model.state_dict(), model_path)
    logger.info(f"\n模型已保存: {model_path}")

    # 8. 导出 ONNX
    try:
        from models.export_onnx import export_to_onnx
        onnx_path = os.path.join(model_dir, 'transformer_real_data.onnx')
        export_to_onnx(
            model,
            input_shape=(1, args.seq_len, features.shape[1]),
            output_path=onnx_path
        )
        logger.info(f"ONNX 模型已导出: {onnx_path}")
    except Exception as e:
        logger.warning(f"ONNX 导出失败: {e}")

    return model, final_metrics


def train_randomforest_fallback(features, labels, args):
    """备选: 使用 RandomForest (如果 PyTorch 不可用)"""
    logger.info("\n" + "="*70)
    logger.info("训练 RandomForest 模型 (备选)")
    logger.info("="*70)

    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_squared_error, r2_score
    except ImportError:
        logger.error("scikit-learn not installed, cannot run RandomForest fallback")
        return None, {}

    # 时间序列分割
    n_train = int(len(labels) * (1 - args.test_size))
    X_train = features.values[:n_train]
    X_test = features.values[n_train:]
    y_train = labels[:n_train]
    y_test = labels[n_train:]

    logger.info(f"训练集: {len(y_train)} 样本")
    logger.info(f"测试集: {len(y_test)} 样本")

    # 训练
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # 评估
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # 计算 IC
    ic = np.corrcoef(y_pred, y_test)[0, 1]

    logger.info(f"\n测试集 MSE: {mse:.6f}")
    logger.info(f"测试集 R²: {r2:.4f}")
    logger.info(f"测试集 IC: {ic:.4f}")

    # 保存模型
    import joblib
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'randomforest_real_data.pkl')
    joblib.dump(model, model_path)
    logger.info(f"\n模型已保存: {model_path}")

    return model, {'ic': ic, 'mse': mse, 'r2': r2}


def main():
    parser = argparse.ArgumentParser(description='训练 Qlib Transformer 模型')

    # 数据参数
    parser.add_argument('--data', type=str,
                       default='data/historical/BTCUSDT_1h_365d_okx.csv',
                       help='数据文件路径')
    parser.add_argument('--ic-threshold', type=float, default=0.03,
                       help='因子筛选 IC 阈值')
    parser.add_argument('--test-size', type=float, default=0.2,
                       help='测试集比例')

    # 模型参数
    parser.add_argument('--seq-len', type=int, default=60,
                       help='序列长度')
    parser.add_argument('--d-model', type=int, default=128,
                       help='模型维度')
    parser.add_argument('--nhead', type=int, default=4,
                       help='注意力头数')
    parser.add_argument('--num-layers', type=int, default=2,
                       help='Transformer 层数')
    parser.add_argument('--dropout', type=float, default=0.1,
                       help='Dropout 比例')

    # 训练参数
    parser.add_argument('--epochs', type=int, default=100,
                       help='训练轮数')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='批次大小')
    parser.add_argument('--learning-rate', type=float, default=1e-4,
                       help='学习率')
    parser.add_argument('--weight-decay', type=float, default=1e-5,
                       help='权重衰减')

    args = parser.parse_args()

    logger.info("\n" + "="*70)
    logger.info("Qlib Transformer 训练脚本")
    logger.info("="*70)
    logger.info(f"数据文件: {args.data}")
    logger.info(f"IC 阈值: {args.ic_threshold}")
    logger.info(f"测试集比例: {args.test_size}")
    logger.info(f"序列长度: {args.seq_len}")
    logger.info(f"模型维度: {args.d_model}")
    logger.info(f"注意力头数: {args.nhead}")
    logger.info(f"Transformer 层数: {args.num_layers}")
    logger.info(f"训练轮数: {args.epochs}")
    logger.info(f"批次大小: {args.batch_size}")

    # 1. 加载数据
    df = load_historical_data(args.data)

    # 2. 准备特征和标签
    features, labels = prepare_features_and_labels(df, args.ic_threshold)

    # 3. 训练模型
    model, metrics = train_transformer(features, labels, args)

    logger.info("\n" + "="*70)
    logger.info("训练完成!")
    logger.info("="*70)

    if TORCH_AVAILABLE:
        logger.info(f"最终 IC: {metrics['ic']:.4f}")
        logger.info(f"最终 Rank IC: {metrics['rank_ic']:.4f}")
        logger.info(f"最终 IR: {metrics['ir']:.4f}")
    else:
        logger.info(f"最终 IC: {metrics['ic']:.4f}")

    logger.info("\n下一步:")
    logger.info("1. 运行回测: python backtest_transformer_real_data.py")
    logger.info("2. 对比模型: python compare_models.py")


if __name__ == '__main__':
    main()
