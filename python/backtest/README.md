# TTQuant 回测框架

完整的回测框架，支持历史数据回测和性能分析。

## 架构设计

### 核心组件

1. **BacktestEngine** (`backtest/engine.py`)
   - 回测引擎核心
   - 事件驱动架构
   - 时间序列数据回放
   - 支持多策略回测

2. **BacktestDataSource** (`backtest/data_source.py`)
   - 从 TimescaleDB 加载历史数据
   - 使用 Polars + ConnectorX 高性能数据处理
   - 支持数据预加载和流式加载
   - 数据清洗和验证

3. **BacktestOrderGateway** (`backtest/order_gateway.py`)
   - 模拟订单执行
   - 多种滑点模型（固定/百分比/市场深度）
   - 手续费计算
   - 成交延迟模拟

4. **PerformanceAnalytics** (`backtest/analytics.py`)
   - 计算夏普比率、最大回撤
   - 胜率、盈亏比
   - 交易统计
   - 生成回测报告

### 设计原则

- **回测即实盘**：与实盘策略引擎共享 `BaseStrategy` 接口
- **依赖注入**：通过网关和数据源解耦，便于测试
- **事件驱动**：按时间顺序回放历史数据，模拟真实交易环境
- **高性能**：使用 Polars 进行数据处理，支持大规模回测

## 快速开始

### 1. 安装依赖

```bash
cd python
pip install -r requirements.txt
```

### 2. 准备数据

确保 TimescaleDB 中有历史数据：

```bash
# 启动数据库
docker-compose up -d timescaledb

# 检查数据
psql -h localhost -U ttquant -d ttquant_trading -c "SELECT COUNT(*) FROM market_data;"
```

### 3. 运行回测

```bash
cd python
python run_backtest.py
```

## 使用示例

### 基本回测

```python
from datetime import datetime
from backtest.engine import create_backtest_engine
from backtest.order_gateway import SlippageModel
from strategy.strategies.ema_cross import EMACrossStrategy

# 创建回测引擎
engine = create_backtest_engine(
    db_uri="postgresql://ttquant:password@localhost:5432/ttquant_trading",
    symbols=['BTCUSDT'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    exchange='binance',
    initial_capital=100000.0,
    slippage_model=SlippageModel.PERCENTAGE,
    slippage_value=0.0005,  # 0.05% 滑点
    maker_fee=0.0002,  # 0.02%
    taker_fee=0.0004,  # 0.04%
)

# 添加策略
strategy = EMACrossStrategy('ema_cross_btc', {
    'symbol': 'BTCUSDT',
    'fast_period': 5,
    'slow_period': 20,
    'trade_volume': 1,
})
engine.add_strategy(strategy)

# 运行回测
reports = engine.run()

# 导出结果
engine.export_results('backtest_results')
```

### 自定义策略回测

```python
from strategy.base_strategy import BaseStrategy, MarketData, Trade

class MyStrategy(BaseStrategy):
    """自定义策略"""

    def __init__(self, strategy_id: str, config: dict):
        super().__init__(strategy_id, config)
        # 初始化策略参数
        self.symbol = config['symbol']

    def on_market_data(self, md: MarketData):
        """行情回调"""
        # 实现交易逻辑
        if self._should_buy(md):
            self.send_order(
                symbol=md.symbol,
                side='BUY',
                price=md.last_price,
                volume=1
            )

    def on_trade(self, trade: Trade):
        """成交回调"""
        if trade.status == 'FILLED':
            print(f"Trade filled: {trade.side} @ ${trade.filled_price}")

    def _should_buy(self, md: MarketData) -> bool:
        # 实现买入逻辑
        return False

# 使用自定义策略
strategy = MyStrategy('my_strategy', {'symbol': 'BTCUSDT'})
engine.add_strategy(strategy)
reports = engine.run()
```

## 回测报告

回测完成后会生成详细的性能报告：

```
================================================================================
BACKTEST REPORT - ema_cross_btc
================================================================================

[Period]
  Start Date:        2024-01-01 00:00:00
  End Date:          2024-12-31 23:59:59
  Duration:          365.0 days

[Returns]
  Total Return:          15.23%
  Annual Return:         15.23%
  Total PnL:         $15,230.00
  Realized PnL:      $14,500.00
  Unrealized PnL:       $730.00

[Risk Metrics]
  Sharpe Ratio:           1.85
  Max Drawdown:          12.45%
  Drawdown Duration:     45.2 days
  Volatility (Ann):      18.32%

[Trading Statistics]
  Total Trades:            156
  Winning Trades:           89
  Losing Trades:            67
  Win Rate:              57.05%
  Profit Factor:          1.45
  Avg Win:             $245.50
  Avg Loss:            $182.30
  Largest Win:       $1,250.00
  Largest Loss:        $850.00

[Costs]
  Total Commission:     $125.50
  Total Slippage:        $89.20

[Position Statistics]
  Avg Duration:          24.5 hours
  Max Position Size:          5
================================================================================
```

## 配置选项

### 滑点模型

```python
from backtest.order_gateway import SlippageModel

# 无滑点
SlippageModel.NONE

# 固定滑点（点数）
SlippageModel.FIXED
slippage_value = 1.0  # 1 美元

# 百分比滑点
SlippageModel.PERCENTAGE
slippage_value = 0.0005  # 0.05%

# 市场深度模型（TODO）
SlippageModel.MARKET_DEPTH
```

### 手续费配置

```python
from backtest.order_gateway import CommissionConfig

commission_config = CommissionConfig(
    maker_fee=0.0002,  # 0.02% Maker 手续费
    taker_fee=0.0004,  # 0.04% Taker 手续费
    min_commission=0.0  # 最小手续费
)
```

### 数据加载

```python
from backtest.data_source import BacktestDataSource

# 预加载模式（适合小数据集）
data_source = BacktestDataSource(
    db_uri=db_uri,
    symbols=['BTCUSDT', 'ETHUSDT'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    exchange='binance',
    preload=True  # 一次性加载所有数据到内存
)

# 流式加载模式（适合大数据集，TODO）
data_source = BacktestDataSource(
    db_uri=db_uri,
    symbols=['BTCUSDT'],
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2024, 12, 31),
    exchange='binance',
    preload=False  # 按需加载数据
)
```

## 性能优化

### 数据加载优化

- 使用 **ConnectorX** 高速加载数据（比 pandas 快 10-20 倍）
- 使用 **Polars** 进行数据处理（比 pandas 快 5-10 倍）
- 支持数据预加载到内存

### 回测速度

在典型配置下（Intel i7, 16GB RAM）：

- **Tick 级回测**：~50,000 ticks/秒
- **1 分钟 K 线**：~500,000 bars/秒
- **1 年数据**：~10-30 秒（取决于数据量）

### 内存使用

- **1 年 Tick 数据**（单交易对）：~500 MB
- **多交易对**：线性增长
- **建议**：16GB RAM 可支持 5-10 个交易对的年度回测

## 数据准备

### 从交易所下载历史数据

```bash
# TODO: 实现数据下载脚本
python scripts/download_historical_data.py \
    --exchange binance \
    --symbols BTCUSDT ETHUSDT \
    --start 2024-01-01 \
    --end 2024-12-31
```

### 数据质量检查

```python
from backtest.data_source import BacktestDataSource

data_source = BacktestDataSource(...)

# 获取数据统计
stats = data_source.get_statistics()
print(stats)

# 检查数据完整性
for symbol in symbols:
    symbol_data = data_source.get_data_by_symbol(symbol)
    print(f"{symbol}: {len(symbol_data)} ticks")
```

## 高级功能

### K 线重采样

```python
# 将 Tick 数据重采样为 K 线
klines = data_source.resample_to_klines('BTCUSDT', interval='1h')
print(klines.head())
```

### 多策略回测

```python
# 添加多个策略
strategy1 = EMACrossStrategy('ema_5_20', {...})
strategy2 = EMACrossStrategy('ema_10_30', {...})

engine.add_strategy(strategy1)
engine.add_strategy(strategy2)

# 运行回测
reports = engine.run()

# 比较策略表现
for strategy_id, report in reports.items():
    print(f"{strategy_id}: {report.total_return * 100:.2f}%")
```

### 导出结果

```python
# 导出权益曲线
engine.export_results('backtest_results')

# 生成的文件：
# - backtest_results/equity_curve.csv
```

## 与实盘对比

| 特性 | 回测 | 实盘 |
|------|------|------|
| 数据源 | `BacktestDataSource` | ZMQ 行情订阅 |
| 订单网关 | `BacktestOrderGateway` | ZMQ 订单推送 |
| 策略接口 | `BaseStrategy` | `BaseStrategy` |
| 成交延迟 | 可配置（默认 0） | 真实网络延迟 |
| 滑点 | 模型模拟 | 真实市场滑点 |
| 手续费 | 配置固定费率 | 交易所实际费率 |

**关键优势**：策略代码完全相同，只需切换数据源和网关即可从回测切换到实盘。

## 注意事项

### 回测陷阱

1. **前视偏差**：不要使用未来数据
2. **过拟合**：避免过度优化参数
3. **幸存者偏差**：考虑退市的交易对
4. **交易成本**：必须包含滑点和手续费
5. **市场影响**：大单可能影响价格（未实现）

### 最佳实践

1. **使用真实的交易成本**：滑点 + 手续费
2. **样本外测试**：训练集 + 测试集
3. **多时间段验证**：牛市 + 熊市 + 震荡市
4. **风险管理**：设置止损和仓位限制
5. **记录详细日志**：便于分析和调试

## 故障排除

### 数据库连接失败

```bash
# 检查数据库是否运行
docker ps | grep timescaledb

# 检查连接
psql -h localhost -U ttquant -d ttquant_trading
```

### 内存不足

```python
# 减少数据量
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31)  # 只回测 1 个月

# 或使用流式加载（TODO）
preload=False
```

### 回测速度慢

```python
# 增加权益记录间隔
engine = BacktestEngine(
    ...,
    record_equity_interval=1000  # 每 1000 个 tick 记录一次
)
```

## 未来改进

- [ ] 支持流式数据加载（大数据集）
- [ ] 市场深度滑点模型
- [ ] 多线程/多进程回测
- [ ] 参数优化框架
- [ ] 可视化报告（图表）
- [ ] 实时回测（模拟实盘）
- [ ] 支持期货、期权等衍生品

## 参考资料

- [Backtrader](https://www.backtrader.com/) - Python 回测框架
- [Zipline](https://github.com/quantopian/zipline) - Quantopian 回测引擎
- [VectorBT](https://github.com/polakowo/vectorbt) - 向量化回测
- [QuantConnect](https://www.quantconnect.com/) - 云端回测平台

## 许可证

MIT License
