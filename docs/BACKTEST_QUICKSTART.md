# TTQuant 回测框架 - 快速参考

## 快速开始

### 1. 安装依赖

```bash
cd python
pip install -r requirements.txt
```

### 2. 运行演示（无需数据库）

```bash
python demo_backtest.py
```

### 3. 运行真实回测（需要数据库）

```bash
# 配置环境变量
export DB_PASSWORD=your_password

# 运行回测
python run_backtest.py
```

## 核心 API

### 创建回测引擎

```python
from backtest.engine import create_backtest_engine
from backtest.order_gateway import SlippageModel

engine = create_backtest_engine(
    db_uri="postgresql://ttquant:password@localhost:5432/ttquant_trading",
    symbols=['BTCUSDT'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    exchange='binance',
    initial_capital=100000.0,
    slippage_model=SlippageModel.PERCENTAGE,
    slippage_value=0.0005,  # 0.05%
    maker_fee=0.0002,       # 0.02%
    taker_fee=0.0004,       # 0.04%
)
```

### 添加策略

```python
from strategy.strategies.ema_cross import EMACrossStrategy

strategy = EMACrossStrategy('ema_cross_btc', {
    'symbol': 'BTCUSDT',
    'fast_period': 5,
    'slow_period': 20,
    'trade_volume': 1,
})
engine.add_strategy(strategy)
```

### 运行回测

```python
reports = engine.run()
engine.export_results('backtest_results')
```

## 自定义策略模板

```python
from strategy.base_strategy import BaseStrategy, MarketData, Trade

class MyStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, config: dict):
        super().__init__(strategy_id, config)
        self.symbol = config['symbol']
        # 初始化参数

    def on_market_data(self, md: MarketData):
        """行情回调"""
        if md.symbol != self.symbol:
            return

        # 实现交易逻辑
        if self._should_buy(md):
            self.send_order(
                symbol=md.symbol,
                side='BUY',
                price=md.last_price,
                volume=1
            )

    def on_trade(self, trade: Trade):
        """成交回报"""
        if trade.status == 'FILLED':
            print(f"Filled: {trade.side} @ ${trade.filled_price:.2f}")

    def _should_buy(self, md: MarketData) -> bool:
        # 实现买入逻辑
        return False
```

## 配置选项

### 滑点模型

```python
from backtest.order_gateway import SlippageModel

# 无滑点
SlippageModel.NONE

# 固定滑点
SlippageModel.FIXED
slippage_value = 10.0  # $10

# 百分比滑点
SlippageModel.PERCENTAGE
slippage_value = 0.0005  # 0.05%
```

### 手续费

```python
from backtest.order_gateway import CommissionConfig

commission_config = CommissionConfig(
    maker_fee=0.0002,  # 0.02%
    taker_fee=0.0004,  # 0.04%
    min_commission=0.0
)
```

## 性能指标

回测报告包含以下指标：

### 收益指标
- Total Return: 总收益率
- Annual Return: 年化收益率
- Total PnL: 总盈亏
- Realized PnL: 已实现盈亏
- Unrealized PnL: 未实现盈亏

### 风险指标
- Sharpe Ratio: 夏普比率
- Max Drawdown: 最大回撤
- Volatility: 波动率（年化）

### 交易统计
- Total Trades: 总交易次数
- Win Rate: 胜率
- Profit Factor: 盈亏比
- Avg Win/Loss: 平均盈利/亏损

### 成本统计
- Total Commission: 总手续费
- Total Slippage: 总滑点成本

## 文件结构

```
python/
├── backtest/
│   ├── engine.py          # 回测引擎
│   ├── data_source.py     # 数据源
│   ├── order_gateway.py   # 订单网关
│   └── analytics.py       # 性能分析
├── run_backtest.py        # 主脚本
├── demo_backtest.py       # 演示脚本
└── test_backtest.py       # 单元测试
```

## 常用命令

```bash
# 运行单元测试
python test_backtest.py

# 运行演示
python demo_backtest.py

# 运行真实回测
python run_backtest.py

# 查看帮助
python run_backtest.py --help
```

## 故障排除

### 数据库连接失败
```bash
# 检查数据库
docker ps | grep timescaledb

# 测试连接
psql -h localhost -U ttquant -d ttquant_trading
```

### 内存不足
```python
# 减少数据量
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31)  # 只回测 1 个月
```

### 回测速度慢
```python
# 增加权益记录间隔
engine = BacktestEngine(
    ...,
    record_equity_interval=1000
)
```

## 更多信息

- 详细文档: `docs/BACKTEST_IMPLEMENTATION.md`
- 框架说明: `python/backtest/README.md`
- 示例代码: `python/demo_backtest.py`
