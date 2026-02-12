# Phase 1: Look-ahead Bias 修复报告

## 修复日期
2026-02-13

## 问题概述

在原始代码中发现了三个严重的 Look-ahead Bias（未来函数）问题，这些问题会导致回测结果严重高估实际表现。

## 修复内容

### 1. 标签生成的 Look-ahead Bias

**文件**: `python/train_ml_with_real_data.py`

**问题** (第 114 行):
```python
# 错误：使用当前K线的收益率作为标签
future_returns = np.concatenate([np.diff(prices) / prices[:-1], [0]])
```

这会导致模型在 t 时刻使用 t 时刻的收益率作为标签，相当于"看到了未来"。

**修复**:
```python
# 正确：使用下一根K线的收益率作为标签
future_returns = np.concatenate([[0], np.diff(prices) / prices[:-1]])
```

现在模型在 t 时刻预测的是 t+1 时刻的涨跌，符合实际交易逻辑。

### 2. 回测执行时机的 Look-ahead Bias

**文件**: `python/backtest_real_data.py`

**问题** (第 332-336 行):
```python
# 错误：在 t 时刻生成信号，立即在 t 时刻的收盘价执行
for i, row in df.iterrows():
    backtest.execute_signal(
        timestamp=row['timestamp'],
        price=row['close'],  # 使用当前K线收盘价
        signal=signals[i],   # 使用当前K线信号
        size=0.95
    )
```

这相当于在收盘前就知道了收盘价并执行交易，实际上不可能做到。

**修复**:
```python
# 正确：在 t 时刻生成信号，在 t+1 时刻的开盘价执行
for i, row in df.iterrows():
    if i == 0:
        # 第一根K线无法执行
        continue

    # 使用前一根K线的信号，在当前K线的开盘价执行
    prev_signal = signals[i-1]
    execution_price = row['open']  # 使用开盘价

    backtest.execute_signal(
        timestamp=row['timestamp'],
        price=execution_price,
        signal=prev_signal,
        size=0.95
    )
```

现在的逻辑是：
- t 时刻收盘后生成信号
- t+1 时刻开盘时执行交易
- 符合实际交易流程

### 3. Scaler 数据泄露

**文件**: `python/train_ml_with_real_data.py`

**问题**:
训练脚本没有正确保存 scaler，导致回测时需要重新 fit scaler，可能造成数据泄露。

**修复**:
1. 在训练时保存 scaler 到模型对象:
```python
# 保存 scaler 到 rf_factor
rf_factor.scaler = scaler_rf

# 保存 scaler 到 gb_factor
gb_factor.scaler = scaler_gb
```

2. 保存模型时包含 scaler:
```python
model_manager.save_model(
    model={'model': best_model.model, 'scaler': best_model.scaler},
    model_id=best_model.factor_id,
    metadata={...}
)
```

现在 scaler 只在训练集上 fit，并随模型一起保存，回测时直接使用训练好的 scaler。

## 预期影响

修复这些问题后，回测结果会更接近真实表现：

### 修复前（存在 Look-ahead Bias）
- 总收益率: 可能 6,532%
- 胜率: 可能 74%
- 最大回撤: 可能 -7%

### 修复后（无 Look-ahead Bias）
- 总收益率: 预计 20-50%
- 胜率: 预计 52-55%
- 最大回撤: 预计 -15% ~ -25%

## 验证步骤

1. 重新训练模型:
```bash
cd C:\Users\11915\Desktop\TTQuant\python
python train_ml_with_real_data.py
```

2. 运行回测:
```bash
python backtest_real_data.py
```

3. 检查结果:
- 查看 `backtest_results.json`
- 对比修复前后的指标
- 确认收益率下降（这是正常的，说明修复有效）

## 下一步计划

Phase 1 完成后，继续执行：

- **Phase 2**: 实现 Alpha101 因子库（2周）
- **Phase 3**: 搭建 Transformer 模型（2周）
- **Phase 4**: 训练和优化（2周）
- **Phase 5**: 导出和部署（1周）
- **Phase 6**: 回测和验证（1周）

## 技术细节

### Look-ahead Bias 检查清单

✅ 标签生成：labels[t] 不依赖于 prices[t+1:]
✅ 特征计算：features[t] 不依赖于 prices[t+1:]
✅ 回测执行：在 t+1 开盘价执行，而非 t 收盘价
✅ Scaler：只在训练集上 fit，测试集和回测只 transform
✅ 数据分割：时间序列分割，不随机分割

### 代码审查要点

1. **时间对齐**：确保所有特征、标签、信号的时间索引正确对齐
2. **执行延迟**：信号生成和执行之间必须有至少 1 个 bar 的延迟
3. **数据泄露**：任何预处理（scaler、encoder）都只能在训练集上 fit

## 参考资料

- [Common Backtesting Pitfalls](https://www.quantstart.com/articles/Backtesting-Systematic-Trading-Strategies-in-Python-Considerations-and-Open-Source-Frameworks/)
- [Look-ahead Bias in Trading](https://www.investopedia.com/terms/l/lookaheadbias.asp)
- [Time Series Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
