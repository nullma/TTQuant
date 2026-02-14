"""
使用训练好的 Transformer 模型进行回测
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# IMPORTANT: Import PyTorch BEFORE NumPy to avoid DLL conflicts on Windows
TORCH_AVAILABLE = False
TORCH_ERROR = None
try:
    import torch
    from torch.utils.data import TensorDataset, DataLoader
    from models.qlib_transformer import QlibTransformer as QlibStyleTransformer
    TORCH_AVAILABLE = True
except (ImportError, OSError) as e:
    import traceback
    TORCH_ERROR = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

import numpy as np
import pandas as pd
import logging
import argparse
import json
from datetime import datetime

# Qlib 风格组件
from strategy.factors.qlib_style_data_handler import DataMasking, TimeSeriesSplitter
from strategy.factors.ref_operator import RefOperator
from models.qlib_metrics import QlibMetrics

# 导入训练脚本的函数
from train_transformer_with_real_data import (
    load_historical_data,
    prepare_features_and_labels,
    create_sequences
)

if not TORCH_AVAILABLE:
    print(f"警告: PyTorch 加载失败 ({TORCH_ERROR})，将使用 RandomForest 备选")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_model(model_path, n_features, seq_len, d_model=128, nhead=4, num_layers=2):
    """加载训练好的模型"""
    if not TORCH_AVAILABLE:
        logger.error("PyTorch 未安装")
        return None

    logger.info(f"加载模型: {model_path}")

    model = QlibStyleTransformer(
        input_dim=n_features,
        d_model=d_model,
        nhead=nhead,
        num_layers=num_layers,
        max_seq_len=seq_len
    )

    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()

    logger.info("模型加载成功")
    return model


def evaluate_model(model, test_loader, device='cpu'):
    """评估模型 (Qlib 风格)"""
    logger.info("\n" + "="*70)
    logger.info("模型评估")
    logger.info("="*70)

    model.to(device)
    model.eval()

    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x = batch_x.to(device)
            outputs = model(batch_x)
            all_predictions.append(outputs.cpu().numpy())
            all_labels.append(batch_y.numpy())

    predictions = np.concatenate(all_predictions).flatten()
    labels = np.concatenate(all_labels).flatten()

    # Qlib 风格评估
    metrics = QlibMetrics()

    results = {
        'ic': metrics.information_coefficient(predictions, labels),
        'rank_ic': metrics.rank_ic(predictions, labels),
        'quantile_analysis': metrics.quantile_analysis(predictions, labels, n_quantiles=5)
    }

    # 计算 IR (需要时间序列)
    # 这里简化处理，实际应该按时间窗口计算 IC 序列
    results['ir'] = results['ic'] / (0.05 + 1e-10)  # 简化版

    logger.info(f"IC: {results['ic']:.4f}")
    logger.info(f"Rank IC: {results['rank_ic']:.4f}")
    logger.info(f"IR: {results['ir']:.4f}")

    logger.info("\nQuantile Analysis:")
    qa = results['quantile_analysis']
    for i, ret in enumerate(qa['quantile_returns']):
        logger.info(f"  Quantile {i}: {ret:.4f}")
    logger.info(f"  Top Quantile 收益: {qa['top_quantile_return']:.4f}")
    logger.info(f"  Bottom Quantile 收益: {qa['bottom_quantile_return']:.4f}")
    logger.info(f"  Long-Short 收益: {qa['long_short_return']:.4f}")

    return predictions, labels, results


def simulate_trading(predictions, prices, timestamps, transaction_cost=0.001):
    """交易模拟"""
    logger.info("\n" + "="*70)
    logger.info("交易模拟")
    logger.info("="*70)

    # 生成信号
    signals = (predictions > 0).astype(int)  # 1: 买入, 0: 卖出/空仓

    # 初始化
    capital = 100000.0
    position = 0  # 0: 空仓, 1: 持仓
    cash = capital
    equity = capital
    equity_curve = [capital]
    trades = []

    for i in range(1, len(signals)):
        # 当前价格
        price = prices[i]

        # 信号变化
        if signals[i] == 1 and position == 0:
            # 买入
            shares = cash / price
            cost = shares * price * transaction_cost
            cash -= (shares * price + cost)
            position = 1
            trades.append({
                'timestamp': timestamps[i],
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'cost': cost
            })

        elif signals[i] == 0 and position == 1:
            # 卖出
            shares = (capital - cash) / prices[i-1]  # 根据上一次买入价计算份额
            revenue = shares * price
            cost = revenue * transaction_cost
            cash += (revenue - cost)
            position = 0
            trades.append({
                'timestamp': timestamps[i],
                'action': 'SELL',
                'price': price,
                'shares': shares,
                'cost': cost
            })

        # 更新权益
        if position == 1:
            shares = (capital - cash) / prices[i-1]
            equity = cash + shares * price
        else:
            equity = cash

        equity_curve.append(equity)

    # 计算指标
    equity_curve = np.array(equity_curve)
    returns = np.diff(equity_curve) / equity_curve[:-1]

    total_return = (equity_curve[-1] - capital) / capital * 100
    sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252 * 24)  # 假设小时数据

    # 最大回撤
    cummax = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - cummax) / cummax * 100
    max_drawdown = np.min(drawdown)

    # 胜率
    winning_trades = sum(1 for t in trades if t['action'] == 'SELL' and
                        trades[trades.index(t)-1]['price'] < t['price'])
    total_trades = len([t for t in trades if t['action'] == 'SELL'])
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0

    results = {
        'total_return': total_return,
        'annual_return': total_return / (len(prices) / (365 * 24)) if len(prices) > 365 * 24 else total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'equity_curve': equity_curve.tolist(),
        'trades': trades
    }

    logger.info(f"总收益率: {total_return:.2f}%")
    logger.info(f"年化收益率: {results['annual_return']:.2f}%")
    logger.info(f"夏普比率: {sharpe_ratio:.4f}")
    logger.info(f"最大回撤: {max_drawdown:.2f}%")
    logger.info(f"胜率: {win_rate:.2f}%")
    logger.info(f"交易次数: {len(trades)}")

    return results


def backtest_transformer(args):
    """完整回测流程"""
    logger.info("\n" + "="*70)
    logger.info("Transformer 模型回测")
    logger.info("="*70)

    # 1. 加载数据
    df = load_historical_data(args.data)

    # 2. 准备特征和标签
    features, labels = prepare_features_and_labels(df, args.ic_threshold)

    # 3. 时间序列分割
    splitter = TimeSeriesSplitter()
    X_train, X_test, y_train, y_test = splitter.split(
        features, labels, test_size=args.test_size, gap=1
    )

    # 获取测试集对应的价格和时间戳
    test_start_idx = len(y_train) + 1
    test_df = df.iloc[test_start_idx:test_start_idx + len(y_test)].reset_index(drop=True)

    # 4. 创建序列数据
    X_test_seq, y_test_seq = create_sequences(X_test, y_test, args.seq_len)

    # 获取对应的价格和时间戳
    test_prices = test_df['close'].values[args.seq_len:]
    test_timestamps = test_df['timestamp'].values[args.seq_len:]

    logger.info(f"测试集序列: {X_test_seq.shape}")
    logger.info(f"测试集价格: {len(test_prices)}")

    # 5. 创建 DataLoader
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test_seq),
        torch.FloatTensor(y_test_seq)
    )
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

    # 6. 加载模型
    model = load_model(
        args.model_path,
        n_features=features.shape[1],
        seq_len=args.seq_len,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers
    )

    if model is None:
        logger.error("模型加载失败")
        return

    # 7. 评估模型
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    predictions, labels_eval, eval_metrics = evaluate_model(model, test_loader, device)

    # 8. 交易模拟
    trading_results = simulate_trading(
        predictions,
        test_prices,
        test_timestamps,
        transaction_cost=args.transaction_cost
    )

    # 9. 保存结果
    qa = eval_metrics['quantile_analysis']
    results = {
        'timestamp': datetime.now().isoformat(),
        'model': 'Qlib Transformer',
        'data_file': args.data,
        'test_samples': len(y_test_seq),
        'evaluation_metrics': {
            'ic': float(eval_metrics['ic']),
            'rank_ic': float(eval_metrics['rank_ic']),
            'ir': float(eval_metrics['ir']),
            'quantile_analysis': {
                'quantile_returns': qa['quantile_returns'].tolist(),
                'quantile_counts': qa['quantile_counts'].tolist(),
                'top_quantile_return': float(qa['top_quantile_return']),
                'bottom_quantile_return': float(qa['bottom_quantile_return']),
                'long_short_return': float(qa['long_short_return'])
            }
        },
        'trading_metrics': {
            'total_return': trading_results['total_return'],
            'annual_return': trading_results['annual_return'],
            'sharpe_ratio': trading_results['sharpe_ratio'],
            'max_drawdown': trading_results['max_drawdown'],
            'win_rate': trading_results['win_rate'],
            'total_trades': trading_results['total_trades']
        }
    }

    output_file = 'transformer_backtest_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n结果已保存: {output_file}")

    return results


def backtest_randomforest_fallback(args):
    """备选: RandomForest 回测"""
    logger.info("\n" + "="*70)
    logger.info("RandomForest 模型回测 (备选)")
    logger.info("="*70)

    import joblib
    from sklearn.metrics import mean_squared_error

    # 1. 加载数据
    df = load_historical_data(args.data)

    # 2. 准备特征和标签
    features, labels = prepare_features_and_labels(df, args.ic_threshold)

    # 3. 时间序列分割
    n_train = int(len(labels) * (1 - args.test_size))
    X_test = features.values[n_train:]
    y_test = labels[n_train:]

    test_df = df.iloc[n_train:n_train + len(y_test)].reset_index(drop=True)
    test_prices = test_df['close'].values
    test_timestamps = test_df['timestamp'].values

    # 4. 加载模型
    model_path = args.model_path.replace('.pth', '.pkl')
    logger.info(f"加载模型: {model_path}")
    model = joblib.load(model_path)

    # 5. 预测
    predictions = model.predict(X_test)

    # 6. 评估
    ic = np.corrcoef(predictions, y_test)[0, 1]
    mse = mean_squared_error(y_test, predictions)

    logger.info(f"IC: {ic:.4f}")
    logger.info(f"MSE: {mse:.6f}")

    # 7. 交易模拟
    trading_results = simulate_trading(
        predictions,
        test_prices,
        test_timestamps,
        transaction_cost=args.transaction_cost
    )

    # 8. 保存结果
    results = {
        'timestamp': datetime.now().isoformat(),
        'model': 'RandomForest',
        'data_file': args.data,
        'test_samples': len(y_test),
        'evaluation_metrics': {
            'ic': float(ic),
            'mse': float(mse)
        },
        'trading_metrics': {
            'total_return': trading_results['total_return'],
            'annual_return': trading_results['annual_return'],
            'sharpe_ratio': trading_results['sharpe_ratio'],
            'max_drawdown': trading_results['max_drawdown'],
            'win_rate': trading_results['win_rate'],
            'total_trades': trading_results['total_trades']
        }
    }

    output_file = 'randomforest_backtest_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n结果已保存: {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Transformer 模型回测')

    # 数据参数
    parser.add_argument('--data', type=str,
                       default='data/historical/BTCUSDT_1h_365d_okx.csv',
                       help='数据文件路径')
    parser.add_argument('--model-path', type=str,
                       default='models/transformer_real_data.pth',
                       help='模型文件路径')
    parser.add_argument('--ic-threshold', type=float, default=0.03,
                       help='因子筛选 IC 阈值')
    parser.add_argument('--test-size', type=float, default=0.2,
                       help='测试集比例')
    parser.add_argument('--transaction-cost', type=float, default=0.001,
                       help='交易成本 (0.1%)')

    # 模型参数
    parser.add_argument('--seq-len', type=int, default=60,
                       help='序列长度')
    parser.add_argument('--d-model', type=int, default=128,
                       help='模型维度')
    parser.add_argument('--nhead', type=int, default=4,
                       help='注意力头数')
    parser.add_argument('--num-layers', type=int, default=2,
                       help='Transformer 层数')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='批次大小')

    args = parser.parse_args()

    if TORCH_AVAILABLE:
        results = backtest_transformer(args)
    else:
        results = backtest_randomforest_fallback(args)

    logger.info("\n" + "="*70)
    logger.info("回测完成!")
    logger.info("="*70)


if __name__ == '__main__':
    main()
