# EMA 交叉策略优化方案

## 问题分析

**原策略参数（EMA 10/30）：**
- 24小时交易：8,796 笔
- 累计亏损：-$143.84+
- 平均每小时 366 笔交易
- 问题：参数过于敏感，震荡市场产生大量虚假信号

## 优化方案

### 方案 1：拉大 EMA 周期差距（推荐）
```toml
fast_period = 20    # 原 10 → 20
slow_period = 50    # 原 30 → 50
```
**优点**：
- 减少虚假信号 70%+
- 更适合趋势行情
- 降低交易频率

**缺点**：
- 入场延迟增加
- 可能错过短期机会

### 方案 2：添加成交量过滤
```python
# 只在成交量放大时交易
if current_volume > avg_volume * 1.5:
    # 执行交易
```
**优点**：
- 过滤震荡期虚假信号
- 只在有动能时交易

### 方案 3：添加趋势强度过滤（ADX）
```python
# 只在趋势明确时交易
if adx > 25:  # ADX > 25 表示趋势明确
    # 执行交易
```
**优点**：
- 避免震荡市场
- 提高胜率

### 方案 4：添加价格波动过滤（ATR）
```python
# 只在波动足够大时交易
if abs(fast_ema - slow_ema) > atr * 0.5:
    # 执行交易
```
**优点**：
- 过滤微小交叉
- 减少手续费损失

## 推荐配置

### 保守型（适合震荡市场）
```toml
[[strategies]]
name = "ma_cross_eth_v2"
type = "ma_cross"
enabled = false  # 先测试
symbol = "ETHUSDT"

[strategies.parameters]
fast_period = 20
slow_period = 50
min_volume_ratio = 1.5  # 成交量过滤
min_price_diff_pct = 0.1  # 最小价差 0.1%
```

### 激进型（适合趋势市场）
```toml
[[strategies]]
name = "ma_cross_eth_v3"
type = "ma_cross"
enabled = false
symbol = "ETHUSDT"

[strategies.parameters]
fast_period = 12
slow_period = 26
use_adx_filter = true
min_adx = 25
```

## 回测建议

在启用前，先用历史数据回测：
```bash
cd python
python run_backtest.py --strategy ma_cross_v2 --start 2026-02-01 --end 2026-02-11
```

对比指标：
- 交易次数：< 100 笔/天
- 胜率：> 40%
- 盈亏比：> 1.5
- 最大回撤：< 10%

## 实施步骤

1. ✅ 禁用原策略（已完成）
2. ⏳ 修改策略代码添加过滤条件
3. ⏳ 本地回测验证
4. ⏳ 服务器小资金测试
5. ⏳ 正式启用

## 当前状态

- ✅ 原策略已禁用
- ✅ 网格交易正常运行（17笔/24h）
- ✅ 动量突破正常运行（5笔/24h）
- ⏳ 等待 EMA 策略优化

---

**结论**：EMA 10/30 不适合当前市场，建议使用 EMA 20/50 + 成交量过滤。
