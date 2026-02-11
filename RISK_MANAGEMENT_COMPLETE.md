# 风控管理功能实现完成

## 实现内容

### 1. 核心模块

**`strategy/risk_manager.py`** - 风控管理器
- ✅ 止损止盈（Stop Loss / Take Profit）
- ✅ 仓位管理（Position Sizing）
- ✅ 每日亏损限制（Daily Loss Limit）
- ✅ 最大持仓限制（Max Position Limit）
- ✅ 智能仓位计算（基于风险的仓位大小）

### 2. 集成到策略基类

**`strategy/base_strategy.py`** - 修改
- ✅ 添加 `set_risk_manager()` 方法
- ✅ `send_order()` 集成风控检查
- ✅ 添加 `check_risk_triggers()` 方法检查止损止盈

### 3. 集成到策略引擎

**`strategy/engine.py`** - 修改
- ✅ 从配置文件读取风控参数
- ✅ 自动为所有策略设置风控管理器
- ✅ 支持启用/禁用风控

### 4. 配置文件

**`config/strategies.risk.toml`** - 带风控的配置示例
```toml
[risk_management]
enabled = true
initial_capital = 100000.0
stop_loss_pct = 0.02
take_profit_pct = 0.05
max_position_pct = 0.3
daily_loss_limit = 5000.0
max_positions = 5
```

### 5. 文档

**`docs/RISK_MANAGEMENT.md`** - 完整的使用文档
- 参数说明
- 使用示例
- 注意事项
- 回测对比方法

### 6. 测试

**`python/test_risk_management.py`** - 单元测试
- ✅ 测试止损触发
- ✅ 测试止盈触发
- ✅ 测试仓位限制
- ✅ 测试每日亏损限制
- ✅ 测试仓位计算

**测试结果：全部通过 ✓**

## 功能特性

### 1. 止损止盈

**多头持仓**：
- 止损：价格 ≤ 入场价 × (1 - stop_loss_pct)
- 止盈：价格 ≥ 入场价 × (1 + take_profit_pct)

**空头持仓**：
- 止损：价格 ≥ 入场价 × (1 + stop_loss_pct)
- 止盈：价格 ≤ 入场价 × (1 - take_profit_pct)

**示例**（入场价 $100,000，止损 2%，止盈 5%）：
- 多头止损：$98,000
- 多头止盈：$105,000

### 2. 仓位管理

**单品种限制**：
- 单个交易对持仓价值 ≤ 总资金 × max_position_pct
- 默认 30%，即 $30,000（总资金 $100,000）

**总仓位限制**：
- 所有持仓总价值 ≤ 总资金 × max_total_position_pct
- 默认 80%，即 $80,000

**持仓数量限制**：
- 最多同时持有 max_positions 个品种
- 默认 5 个

### 3. 每日亏损限制

- 当日累计亏损 ≥ daily_loss_limit 时停止交易
- 每日 00:00 自动重置
- 默认 $5,000

### 4. 智能仓位计算

基于风险的仓位大小：
```
建议数量 = (总资金 × 每笔风险%) / (价格 × 止损%)
```

**示例**（总资金 $100,000，风险 1%，止损 2%）：
- 风险金额 = $100,000 × 1% = $1,000
- 止损距离 = 价格 × 2%
- 建议数量 = $1,000 / 止损距离

## 使用方法

### 方法 1：在配置文件中启用

编辑 `config/strategies.toml`，添加：

```toml
[risk_management]
enabled = true
initial_capital = 100000.0
stop_loss_pct = 0.02
take_profit_pct = 0.05
max_position_pct = 0.3
daily_loss_limit = 5000.0
max_positions = 5
```

### 方法 2：在策略中使用

```python
from strategy.risk_manager import RiskManager, RiskConfig

# 创建风控管理器
risk_config = RiskConfig(stop_loss_pct=0.02, take_profit_pct=0.05)
risk_manager = RiskManager(risk_config, initial_capital=100000.0)

# 设置到策略
strategy.set_risk_manager(risk_manager)

# 在 on_market_data 中检查风控
def on_market_data(self, md):
    # 检查止损止盈
    if self.check_risk_triggers(md.symbol, md.last_price):
        return  # 已触发平仓

    # 策略逻辑...
```

## 下一步

1. **在回测中测试风控效果**
   - 对比有无风控的策略表现
   - 验证风控参数的合理性

2. **部署到服务器**
   - 提交代码到 Git
   - 在服务器上启用风控

3. **监控风控统计**
   - 添加 Grafana 面板显示风控指标
   - 记录止损止盈触发次数

## 文件清单

新增文件：
- `python/strategy/risk_manager.py` - 风控管理器
- `config/strategies.risk.toml` - 带风控的配置
- `docs/RISK_MANAGEMENT.md` - 使用文档
- `python/test_risk_management.py` - 单元测试

修改文件：
- `python/strategy/base_strategy.py` - 集成风控
- `python/strategy/engine.py` - 集成风控

## 测试验证

```bash
cd python
python test_risk_management.py
```

**结果：All tests passed! ✓**

---

**风控管理功能已完成并测试通过！**
