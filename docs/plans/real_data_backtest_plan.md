# 真实数据回测实施计划

## 目标
使用真实历史数据进行回测，验证策略有效性

## 任务分解

### Phase 1: 数据获取 (30分钟)
- [ ] 创建数据下载脚本
- [ ] 从 Binance API 获取历史 K 线数据
- [ ] 数据清洗和预处理
- [ ] 保存到本地/数据库

**数据需求**:
- 交易对: BTCUSDT
- 时间范围: 最近 1 年（365天）
- K 线周期: 1小时
- 数据量: ~8760 条记录

### Phase 2: ML 模型训练 (20分钟)
- [ ] 使用真实数据提取特征
- [ ] 创建训练/测试集（80/20 分割）
- [ ] 训练 Random Forest 模型
- [ ] 训练 Gradient Boosting 模型
- [ ] 模型评估和对比
- [ ] 保存最佳模型

**目标指标**:
- 训练样本: 7000+
- 测试样本: 1700+
- 目标准确率: > 55%
- 目标 AUC: > 0.60

### Phase 3: 策略回测 (30分钟)
- [ ] 配置回测引擎（真实数据源）
- [ ] 回测 EMA 交叉策略
- [ ] 回测网格交易策略
- [ ] 回测动量策略
- [ ] 回测 ML 策略
- [ ] 生成性能报告

**回测配置**:
- 初始资金: $100,000
- 手续费: 0.1% (Binance 标准)
- 滑点: 0.05%
- 回测周期: 2024-01-01 至今

### Phase 4: 结果分析 (20分钟)
- [ ] 性能指标对比（真实 vs 模拟）
- [ ] Alpha-Beta 分解
- [ ] 因子归因分析
- [ ] 风险指标评估
- [ ] 生成完整报告

**分析维度**:
- 收益率对比
- 夏普比率对比
- 最大回撤对比
- 胜率和盈亏比
- 月度收益分布

## 技术实现

### 数据获取脚本
```python
# python/data/fetch_historical_data.py
import ccxt
import pandas as pd
from datetime import datetime, timedelta

def fetch_binance_data(symbol, timeframe, days):
    exchange = ccxt.binance()
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df
```

### 真实数据回测脚本
```python
# python/backtest_real_data.py
from data.fetch_historical_data import fetch_binance_data
from backtest.engine import BacktestEngine
from strategy.strategies.ml_strategy import MLStrategy

# 获取数据
data = fetch_binance_data('BTC/USDT', '1h', 365)

# 配置回测
engine = BacktestEngine(...)
strategy = MLStrategy(...)

# 运行回测
results = engine.run(strategy, data)
```

## 预期产出

1. **数据文件**:
   - `data/historical/BTCUSDT_1h_365d.csv`
   - ~8760 条 K 线数据

2. **训练模型**:
   - `models/btcusdt_ml_real/random_forest.pkl`
   - `models/btcusdt_ml_real/gradient_boosting.pkl`

3. **回测报告**:
   - `reports/real_data_backtest_report.md`
   - 包含所有策略的性能对比

4. **性能对比**:
   - `reports/simulated_vs_real_comparison.md`
   - 模拟数据 vs 真实数据结果对比

## 风险和注意事项

1. **API 限制**: Binance API 有速率限制，需要控制请求频率
2. **数据质量**: 需要检查缺失值和异常值
3. **过拟合**: 真实数据训练要注意过拟合问题
4. **市场环境**: 历史表现不代表未来收益

## 成功标准

- ✅ 成功获取 1 年真实历史数据
- ✅ ML 模型准确率 > 55%
- ✅ 至少 2 个策略在真实数据上盈利
- ✅ 夏普比率 > 1.0
- ✅ 最大回撤 < 20%

## 时间估算

总计: ~2 小时
- Phase 1: 30 分钟
- Phase 2: 20 分钟
- Phase 3: 30 分钟
- Phase 4: 20 分钟
- 调试和优化: 20 分钟
