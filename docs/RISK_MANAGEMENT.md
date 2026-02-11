# TTQuant 风控配置示例

## 风控参数说明

### 1. 止损止盈
- `stop_loss_pct`: 止损百分比（默认 2%）
  - 多头：当价格跌破入场价 * (1 - stop_loss_pct) 时触发止损
  - 空头：当价格涨破入场价 * (1 + stop_loss_pct) 时触发止损

- `take_profit_pct`: 止盈百分比（默认 5%）
  - 多头：当价格涨破入场价 * (1 + take_profit_pct) 时触发止盈
  - 空头：当价格跌破入场价 * (1 - take_profit_pct) 时触发止盈

### 2. 仓位管理
- `max_position_pct`: 单个品种最大仓位（默认 30%）
  - 单个交易对的持仓价值不能超过总资金的 30%

- `max_total_position_pct`: 总仓位限制（默认 80%）
  - 所有持仓的总价值不能超过总资金的 80%

### 3. 每日亏损限制
- `daily_loss_limit`: 每日最大亏损（默认 $5000）
  - 当日累计亏损达到此值时，停止所有交易
  - 每日 00:00 重置

### 4. 最大持仓数量
- `max_positions`: 最多同时持有的品种数量（默认 5）
  - 防止过度分散或集中

## 使用示例

### Python 代码中启用风控

```python
from strategy.risk_manager import RiskManager, RiskConfig
from strategy.strategies.grid_trading import GridTradingStrategy

# 创建风控配置
risk_config = RiskConfig(
    stop_loss_pct=0.02,      # 2% 止损
    take_profit_pct=0.05,    # 5% 止盈
    max_position_pct=0.3,    # 单品种最大 30% 仓位
    daily_loss_limit=5000.0, # 每日最大亏损 $5000
    max_positions=5,         # 最多 5 个持仓
    enabled=True             # 启用风控
)

# 创建风控管理器
risk_manager = RiskManager(risk_config, initial_capital=100000.0)

# 创建策略
strategy = GridTradingStrategy('grid_btc', config)
strategy.set_risk_manager(risk_manager)

# 在策略的 on_market_data 中检查风控
def on_market_data(self, md):
    # 先检查止损止盈
    if self.check_risk_triggers(md.symbol, md.last_price):
        return  # 已触发平仓，不再执行策略逻辑

    # 策略逻辑...
    if buy_signal:
        # 使用风控管理器计算建议仓位
        volume = self._risk_manager.get_position_size(md.symbol, md.last_price)
        self.send_order(md.symbol, 'BUY', md.last_price, volume)
```

### 在策略引擎中启用风控

修改 `strategy/engine.py`，为每个策略添加风控管理器：

```python
from strategy.risk_manager import RiskManager, RiskConfig

# 在 StrategyEngine.__init__ 中
risk_config = RiskConfig(
    stop_loss_pct=0.02,
    take_profit_pct=0.05,
    max_position_pct=0.3,
    daily_loss_limit=5000.0,
    max_positions=5,
    enabled=True
)
self.risk_manager = RiskManager(risk_config, initial_capital=100000.0)

# 为每个策略设置风控
for strategy in self.strategies.values():
    strategy.set_risk_manager(self.risk_manager)
```

## 风控统计

获取风控统计信息：

```python
stats = risk_manager.get_stats()
print(f"Current Capital: ${stats['current_capital']:.2f}")
print(f"Total PnL: ${stats['total_pnl']:.2f}")
print(f"Daily PnL: ${stats['daily_pnl']:.2f}")
print(f"Active Positions: {stats['active_positions']}/{stats['max_positions']}")
print(f"Daily Loss Remaining: ${stats['daily_loss_remaining']:.2f}")
```

## 注意事项

1. **止损止盈是基于入场价计算的**，不是基于最高/最低价
2. **每日亏损限制会在每天 00:00 自动重置**
3. **仓位限制只对开仓订单生效**，平仓订单不受限制
4. **风控可以通过 `enabled=False` 禁用**，用于回测对比
5. **建议在实盘前先用回测验证风控参数的合理性**

## 回测中使用风控

在回测中启用风控，对比有无风控的策略表现：

```python
# 无风控回测
engine1 = create_backtest_engine(strategy, ...)
result1 = engine1.run()

# 有风控回测
strategy.set_risk_manager(risk_manager)
engine2 = create_backtest_engine(strategy, ...)
result2 = engine2.run()

# 对比结果
print(f"Without Risk: Return={result1.total_return:.2f}%, MaxDD={result1.max_drawdown:.2f}%")
print(f"With Risk:    Return={result2.total_return:.2f}%, MaxDD={result2.max_drawdown:.2f}%")
```
