"""
使用真实数据进行完整回测
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from datetime import datetime
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleBacktest:
    """简单回测引擎"""

    def __init__(self, initial_capital=100000, commission=0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        self.reset()

    def reset(self):
        """重置状态"""
        self.capital = self.initial_capital
        self.position = 0  # 持仓数量
        self.trades = []
        self.equity_curve = []

    def execute_signal(self, timestamp, price, signal, size=1.0):
        """
        执行交易信号

        Args:
            timestamp: 时间戳
            price: 当前价格
            signal: 1=买入, -1=卖出, 0=持有
            size: 交易大小（资金比例）
        """
        if signal == 1 and self.position == 0:  # 买入
            # 计算可买数量
            max_qty = (self.capital * size) / price
            qty = max_qty * (1 - self.commission)  # 扣除手续费
            cost = qty * price

            if cost <= self.capital:
                self.position = qty
                self.capital -= cost
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'BUY',
                    'price': price,
                    'quantity': qty,
                    'cost': cost
                })

        elif signal == -1 and self.position > 0:  # 卖出
            proceeds = self.position * price * (1 - self.commission)
            self.capital += proceeds

            self.trades.append({
                'timestamp': timestamp,
                'type': 'SELL',
                'price': price,
                'quantity': self.position,
                'proceeds': proceeds
            })

            self.position = 0

        # 记录权益
        equity = self.capital + self.position * price
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': equity,
            'capital': self.capital,
            'position_value': self.position * price
        })

    def get_results(self):
        """获取回测结果"""
        if not self.equity_curve:
            return None

        df = pd.DataFrame(self.equity_curve)

        # 计算收益率
        returns = df['equity'].pct_change().dropna()

        # 计算指标
        total_return = (df['equity'].iloc[-1] / self.initial_capital - 1) * 100

        # 年化收益率（假设数据是1年）
        annual_return = total_return

        # 夏普比率（假设无风险利率2%）
        excess_returns = returns - 0.02/252  # 日化无风险利率
        sharpe = np.sqrt(252) * excess_returns.mean() / returns.std() if returns.std() > 0 else 0

        # 最大回撤
        cummax = df['equity'].cummax()
        drawdown = (df['equity'] - cummax) / cummax
        max_drawdown = drawdown.min() * 100

        # 胜率
        winning_trades = sum(1 for i in range(1, len(self.trades), 2)
                           if i < len(self.trades) and
                           self.trades[i]['proceeds'] > self.trades[i-1]['cost'])
        total_trades = len(self.trades) // 2
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'final_equity': df['equity'].iloc[-1],
            'equity_curve': df
        }


def load_ml_model(model_path):
    """加载 ML 模型"""
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
    # 模型文件包含 model 和 scaler
    if isinstance(data, dict):
        return data['model'], data.get('scaler')
    return data, None


def calculate_all_features(df):
    """计算所有24个特征"""
    from strategy.factors.feature_engineering import FeatureEngineering

    feature_eng = FeatureEngineering(lookback_period=50)
    features = {}

    # 基础数据
    for col in ['open', 'high', 'low', 'close', 'volume']:
        features[col] = df[col].values

    prices = df['close'].values
    volumes = df['volume'].values

    # 收益率
    features['returns'] = np.concatenate([[0], np.diff(prices) / prices[:-1]])

    # 波动率
    returns = features['returns']
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
    def calculate_ma(prices, period):
        ma = np.zeros(len(prices))
        for i in range(period-1, len(prices)):
            ma[i] = np.mean(prices[i-period+1:i+1])
        return ma

    features['ma_5'] = calculate_ma(prices, 5)
    features['ma_10'] = calculate_ma(prices, 10)
    features['ma_20'] = calculate_ma(prices, 20)
    features['ma_50'] = calculate_ma(prices, 50)

    # EMA
    def calculate_ema(prices, period):
        ema = np.zeros(len(prices))
        ema[0] = prices[0]
        multiplier = 2 / (period + 1)
        for i in range(1, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        return ema

    features['ema_12'] = calculate_ema(prices, 12)
    features['ema_26'] = calculate_ema(prices, 26)

    # 成交量指标
    features['volume_ratio'] = volumes / (calculate_ma(volumes, 20) + 1e-10)

    # 价格动量
    features['momentum_5'] = np.concatenate([np.zeros(5), prices[5:] / prices[:-5] - 1])
    features['momentum_10'] = np.concatenate([np.zeros(10), prices[10:] / prices[:-10] - 1])

    return features


def generate_ml_signals(df, model, scaler=None):
    """
    使用 ML 模型生成交易信号

    Returns:
        signals: 1=买入, -1=卖出, 0=持有
    """
    # 计算所有特征
    features = calculate_all_features(df)

    # 特征顺序必须与训练时一致
    feature_names = ['open', 'high', 'low', 'close', 'volume', 'returns', 'volatility',
                     'rsi_14', 'macd', 'macd_signal', 'macd_histogram', 'bb_upper',
                     'bb_middle', 'bb_lower', 'bb_position', 'ma_5', 'ma_10', 'ma_20',
                     'ma_50', 'ema_12', 'ema_26', 'volume_ratio', 'momentum_5', 'momentum_10']

    # 组合特征矩阵
    X = np.column_stack([features[name] for name in feature_names])

    # 移除 NaN
    valid_idx = ~np.isnan(X).any(axis=1)
    X_valid = X[valid_idx]

    # 标准化
    if scaler is not None:
        X_scaled = scaler.transform(X_valid)
    else:
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_valid)

    # 预测
    predictions = model.predict(X_scaled)

    # 转换为信号：1=上涨预测(买入), 0=下跌预测(卖出)
    signals = np.zeros(len(df))
    pred_idx = 0
    position = 0

    for i in range(len(df)):
        if not valid_idx[i]:
            signals[i] = 0
            continue

        if predictions[pred_idx] == 1 and position == 0:  # 预测上涨且无持仓
            signals[i] = 1  # 买入
            position = 1
        elif predictions[pred_idx] == 0 and position == 1:  # 预测下跌且有持仓
            signals[i] = -1  # 卖出
            position = 0
        else:
            signals[i] = 0  # 持有

        pred_idx += 1

    return signals, scaler


def generate_ema_signals(df, fast=12, slow=26):
    """EMA 交叉策略"""
    prices = df['close'].values

    # 计算 EMA
    def ema(prices, period):
        ema_values = np.zeros(len(prices))
        ema_values[0] = prices[0]
        multiplier = 2 / (period + 1)
        for i in range(1, len(prices)):
            ema_values[i] = (prices[i] - ema_values[i-1]) * multiplier + ema_values[i-1]
        return ema_values

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)

    # 生成信号
    signals = np.zeros(len(prices))
    position = 0

    for i in range(1, len(prices)):
        if ema_fast[i] > ema_slow[i] and ema_fast[i-1] <= ema_slow[i-1] and position == 0:
            signals[i] = 1  # 金叉买入
            position = 1
        elif ema_fast[i] < ema_slow[i] and ema_fast[i-1] >= ema_slow[i-1] and position == 1:
            signals[i] = -1  # 死叉卖出
            position = 0

    return signals


def generate_momentum_signals(df, period=20, threshold=0.02):
    """动量策略"""
    prices = df['close'].values
    signals = np.zeros(len(prices))
    position = 0

    for i in range(period, len(prices)):
        momentum = (prices[i] / prices[i-period]) - 1

        if momentum > threshold and position == 0:
            signals[i] = 1  # 买入
            position = 1
        elif momentum < -threshold and position == 1:
            signals[i] = -1  # 卖出
            position = 0

    return signals


def run_backtest(df, signals, strategy_name, initial_capital=100000):
    """运行回测 - 修复 Look-ahead Bias"""
    print(f"\n{'='*70}")
    print(f"回测策略: {strategy_name}")
    print(f"{'='*70}")

    backtest = SimpleBacktest(initial_capital=initial_capital)

    # 修复 Look-ahead Bias: 在 t 时刻生成信号，在 t+1 时刻的开盘价执行
    for i, row in df.iterrows():
        if i == 0:
            # 第一根K线无法执行（没有前一根信号）
            backtest.equity_curve.append({
                'timestamp': row['timestamp'],
                'equity': initial_capital,
                'capital': initial_capital,
                'position_value': 0
            })
            continue

        # 使用前一根K线的信号，在当前K线的开盘价执行
        prev_signal = signals[i-1]
        execution_price = row['open']  # 使用开盘价而非收盘价

        backtest.execute_signal(
            timestamp=row['timestamp'],
            price=execution_price,
            signal=prev_signal,
            size=0.95  # 使用95%资金
        )

    results = backtest.get_results()

    if results:
        print(f"\n回测结果:")
        print(f"  总收益率: {results['total_return']:.2f}%")
        print(f"  年化收益率: {results['annual_return']:.2f}%")
        print(f"  夏普比率: {results['sharpe_ratio']:.4f}")
        print(f"  最大回撤: {results['max_drawdown']:.2f}%")
        print(f"  交易次数: {results['total_trades']}")
        print(f"  胜率: {results['win_rate']:.2f}%")
        print(f"  最终权益: ${results['final_equity']:,.2f}")

    return results


def main():
    """主函数"""
    print("="*70)
    print("TTQuant 策略回测系统")
    print("="*70)

    # 加载数据
    print(f"\n加载真实历史数据...")
    data_file = 'data/historical/BTCUSDT_1h_365d_okx.csv'
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"✓ 加载 {len(df)} 条数据")
    print(f"  时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    print(f"  价格范围: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")

    initial_capital = 100000

    # 策略1: ML 策略
    print(f"\n{'='*70}")
    print("策略 1: 机器学习策略 (Random Forest)")
    print(f"{'='*70}")

    try:
        model, scaler = load_ml_model('models/btcusdt_rf_real/model.pkl')
        print("✓ 模型加载成功")

        ml_signals, _ = generate_ml_signals(df, model, scaler)
        ml_results = run_backtest(df, ml_signals, "ML Strategy (Random Forest)", initial_capital)
    except Exception as e:
        print(f"✗ ML 策略失败: {e}")
        ml_results = None

    # 策略2: EMA 交叉
    print(f"\n{'='*70}")
    print("策略 2: EMA 交叉策略 (12/26)")
    print(f"{'='*70}")

    ema_signals = generate_ema_signals(df, fast=12, slow=26)
    ema_results = run_backtest(df, ema_signals, "EMA Cross (12/26)", initial_capital)

    # 策略3: 动量策略
    print(f"\n{'='*70}")
    print("策略 3: 动量策略 (20日, 2%阈值)")
    print(f"{'='*70}")

    momentum_signals = generate_momentum_signals(df, period=20, threshold=0.02)
    momentum_results = run_backtest(df, momentum_signals, "Momentum (20d, 2%)", initial_capital)

    # 策略对比
    print(f"\n{'='*70}")
    print("策略对比总结")
    print(f"{'='*70}")

    print(f"\n{'策略':<30} {'总收益':>10} {'夏普比率':>10} {'最大回撤':>10} {'交易次数':>10} {'胜率':>10}")
    print("-"*80)

    strategies = []
    if ml_results:
        strategies.append(("ML Strategy (RF)", ml_results))
    strategies.append(("EMA Cross (12/26)", ema_results))
    strategies.append(("Momentum (20d, 2%)", momentum_results))

    for name, results in strategies:
        if results:
            print(f"{name:<30} {results['total_return']:>9.2f}% {results['sharpe_ratio']:>10.4f} "
                  f"{results['max_drawdown']:>9.2f}% {results['total_trades']:>10} {results['win_rate']:>9.2f}%")

    # 基准对比
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"{'Buy & Hold':<30} {buy_hold_return:>9.2f}% {'N/A':>10} {'N/A':>10} {'1':>10} {'N/A':>10}")

    print(f"\n{'='*70}")
    print("回测完成！")
    print(f"{'='*70}")

    # 保存结果
    print(f"\n保存回测结果...")
    results_summary = {
        'timestamp': datetime.now().isoformat(),
        'data_file': data_file,
        'data_points': len(df),
        'initial_capital': initial_capital,
        'strategies': {}
    }

    for name, results in strategies:
        if results:
            results_summary['strategies'][name] = {
                'total_return': results['total_return'],
                'sharpe_ratio': results['sharpe_ratio'],
                'max_drawdown': results['max_drawdown'],
                'total_trades': results['total_trades'],
                'win_rate': results['win_rate']
            }

    import json
    with open('backtest_results.json', 'w') as f:
        json.dump(results_summary, f, indent=2)

    print(f"✓ 结果已保存到: backtest_results.json")


if __name__ == '__main__':
    main()
