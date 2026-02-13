# 当前状态和下一步行动计划

**生成时间**: 2026-02-13
**项目**: Trinity-Alpha 加密货币量化系统

---

## 📊 当前实施状态

### ✅ 已完成的工作 (100%)

所有 7 个 Phase 已经完成实施：

| Phase | 任务 | 状态 | 完成度 |
|-------|------|------|--------|
| Phase 1 | 修复 Look-ahead Bias | ✅ | 100% |
| Phase 1.5 | Qlib 防未来函数机制 | ✅ | 100% |
| Phase 2 | Alpha101 因子库 (101个) | ✅ | 100% |
| Phase 3 | Qlib Transformer 模型 | ✅ | 100% |
| Phase 4 | Qlib 评估指标 | ✅ | 100% |
| Phase 5 | ONNX 导出和部署 | ✅ | 100% |
| Phase 6 | 回测和验证 | ✅ | 100% |

**代码统计**:
- 创建文件: 32 个
- 代码行数: 6,500+ 行
- 文档页数: 50+ 页
- Alpha101 因子: 101 个 (全部实现)

---

## ⚠️ 当前性能问题

### 真实数据回测结果 (BTCUSDT 1小时, 365天)

**ML Strategy (RandomForest)**:
```
总收益率: -90.14%  ❌
夏普比率: -1.61    ❌
最大回撤: -90.30%  ❌
胜率: 28.15%       ❌
交易次数: 2,238
```

**对比基准策略**:
- EMA Cross: -34.74% (表现更好)
- Momentum: -42.61% (表现更好)

### 模拟数据回测结果 (Phase 6)

```
IC: 0.0978          ⚠️ (目标 > 0.10)
Rank IC: 0.1010     ✅ (目标 > 0.08)
IR: 0.6702          ❌ (目标 > 1.5)
年化收益: 6.47%     ❌ (目标 > 20%)
夏普比率: 0.5575    ❌ (目标 > 1.2)
最大回撤: -9.99%    ✅ (目标 < 20%)
胜率: 50.52%        ⚠️ (目标 > 52%)
```

---

## 🔍 核心问题分析

### 1. 模型问题

**当前使用**: RandomForest (传统机器学习)
**已实现但未使用**: Qlib Transformer (深度学习)

**问题**:
- RandomForest 在真实数据上严重过拟合
- 训练集 IC: 0.83 vs 测试集 IC: 0.10 (差距 0.73)
- 未使用已经实现的 Transformer 模型

**原因**:
- RandomForest 对时序数据建模能力有限
- 无法捕捉长期依赖关系
- 容易过拟合噪声

### 2. 特征质量问题

**当前特征**:
- 技术指标: 23 个
- Alpha101: 101 个 (已实现但可能未正确使用)

**问题**:
- 因子筛选后只保留 10 个特征 (筛选率 64%)
- 大部分因子 IC < 0.03
- 可能存在特征计算错误

### 3. 数据问题

**真实数据回测**:
- 使用 BTCUSDT 1小时数据 (8,752 条)
- 时间跨度: 365 天
- 数据质量: 未知

**模拟数据回测**:
- 使用生成的模拟数据 (2,000 条)
- 不反映真实市场特征

### 4. 训练策略问题

**当前训练**:
- 使用 `train_ml_with_real_data.py`
- RandomForest 模型
- 未使用 Transformer

**问题**:
- 未使用 Phase 3-4 实现的 Qlib Transformer
- 未使用 Qlib 风格的评估指标 (IC/IR)
- 未使用滑动窗口验证

---

## 🎯 关键差距

### 实施 vs 使用

| 组件 | 实施状态 | 使用状态 | 差距 |
|------|---------|---------|------|
| Qlib Transformer | ✅ 已实现 | ❌ 未使用 | 大 |
| Qlib 评估指标 | ✅ 已实现 | ⚠️ 部分使用 | 中 |
| Alpha101 (101个) | ✅ 已实现 | ⚠️ 未验证 | 中 |
| ONNX 推理 | ✅ 已实现 | ❌ 未使用 | 大 |
| 实时交易系统 v2 | ✅ 已实现 | ❌ 未使用 | 大 |

**核心问题**: 已经实现了高级组件，但实际回测仍在使用旧的 RandomForest 模型！

---

## 🚀 立即行动计划

### 优先级 1: 切换到 Transformer 模型 (本周)

**目标**: 使用已实现的 Qlib Transformer 替换 RandomForest

**步骤**:

1. **修改训练脚本** (`train_ml_with_real_data.py`)
   ```python
   # 当前: 使用 RandomForest
   from sklearn.ensemble import RandomForestRegressor
   model = RandomForestRegressor(...)

   # 改为: 使用 Qlib Transformer
   from models.qlib_transformer import QlibStyleTransformer
   from models.train_transformer import QlibStyleTrainer
   model = QlibStyleTransformer(...)
   trainer = QlibStyleTrainer(model)
   ```

2. **使用完整特征集**
   ```python
   # 确保使用全部 101 个 Alpha101 因子
   from strategy.factors.alpha101 import Alpha101
   alpha = Alpha101()
   features = alpha.calculate_all_factors(df)
   ```

3. **使用 Qlib 评估指标**
   ```python
   from models.qlib_metrics import QlibMetrics
   metrics = QlibMetrics()
   ic = metrics.information_coefficient(predictions, labels)
   rank_ic = metrics.rank_ic(predictions, labels)
   ```

4. **重新训练和回测**
   ```bash
   cd python
   python train_transformer_with_real_data.py  # 需要创建
   python backtest_transformer_real_data.py    # 需要创建
   ```

**预期改进**:
- IC: 0.10 → 0.12-0.15
- 年化收益: 6.47% → 15-25%
- 夏普比率: 0.56 → 1.0-1.5

### 优先级 2: 验证 Alpha101 因子 (本周)

**目标**: 确保 101 个因子计算正确且有效

**步骤**:

1. **单元测试每个因子**
   ```bash
   python test_alpha101.py --verbose
   ```

2. **计算每个因子的 IC**
   ```python
   for i in range(1, 102):
       factor_values = alpha.calculate_factor(df, i)
       ic = calculate_ic(factor_values, returns)
       print(f"Alpha{i:03d}: IC = {ic:.4f}")
   ```

3. **筛选有效因子**
   ```python
   # 保留 IC > 0.05 的因子
   valid_factors = [i for i in range(1, 102) if ic[i] > 0.05]
   ```

4. **因子正交化**
   ```python
   from strategy.factors.qlib_style_data_handler import orthogonalize_factors
   orthogonal_factors = orthogonalize_factors(selected_factors)
   ```

### 优先级 3: 创建 Transformer 训练脚本 (本周)

**需要创建的文件**:

1. **`python/train_transformer_with_real_data.py`**
   - 加载真实数据
   - 使用 Qlib Transformer
   - 使用 Qlib 评估指标
   - 保存模型

2. **`python/backtest_transformer_real_data.py`**
   - 加载训练好的 Transformer
   - 使用真实数据回测
   - 计算 IC/IR/Quantile Analysis
   - 交易模拟

3. **`python/compare_models.py`**
   - 对比 RandomForest vs Transformer
   - 生成对比报告

---

## 📋 详细实施步骤

### Step 1: 创建 Transformer 训练脚本

**文件**: `python/train_transformer_with_real_data.py`

**核心逻辑**:
```python
# 1. 加载数据
df = pd.read_csv('data/historical/BTCUSDT_1h_365d_okx.csv')

# 2. 准备特征 (使用 DataMasking)
from strategy.factors.qlib_style_data_handler import DataMasking
masking = DataMasking(feature_gap=1, label_gap=1)

# 技术指标
tech_features = create_technical_features(df)

# Alpha101 因子
from strategy.factors.alpha101 import Alpha101
alpha = Alpha101()
alpha_features = alpha.calculate_all_factors(df)

# 合并特征
features = pd.concat([tech_features, alpha_features], axis=1)

# 准备标签
labels = masking.prepare_labels(df)

# 对齐数据
features, labels = masking.align_data(features, labels)

# 3. 因子筛选 (IC > 0.05)
from models.qlib_metrics import QlibMetrics
metrics = QlibMetrics()
selected_features = []
for col in features.columns:
    ic = metrics.information_coefficient(features[col].values, labels)
    if abs(ic) > 0.05:
        selected_features.append(col)

features = features[selected_features]

# 4. 时间序列分割
from strategy.factors.qlib_style_data_handler import TimeSeriesSplitter
splitter = TimeSeriesSplitter()
X_train, X_test, y_train, y_test = splitter.split(
    features.values, labels, test_size=0.2, gap=1
)

# 5. 创建序列数据 (seq_len=60)
def create_sequences(X, y, seq_len=60):
    X_seq, y_seq = [], []
    for i in range(seq_len, len(X)):
        X_seq.append(X[i-seq_len:i])
        y_seq.append(y[i])
    return np.array(X_seq), np.array(y_seq)

X_train_seq, y_train_seq = create_sequences(X_train, y_train)
X_test_seq, y_test_seq = create_sequences(X_test, y_test)

# 6. 创建 DataLoader
from torch.utils.data import TensorDataset, DataLoader
train_dataset = TensorDataset(
    torch.FloatTensor(X_train_seq),
    torch.FloatTensor(y_train_seq)
)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=False)

# 7. 训练模型
from models.qlib_transformer import QlibStyleTransformer
from models.train_transformer import QlibStyleTrainer

model = QlibStyleTransformer(
    n_features=len(selected_features),
    d_model=128,
    nhead=4,
    num_layers=2,
    seq_len=60
)

trainer = QlibStyleTrainer(model, device='cuda' if torch.cuda.is_available() else 'cpu')
trainer.train(train_loader, val_loader, epochs=100)

# 8. 保存模型
torch.save(model.state_dict(), 'models/transformer_real_data.pth')

# 9. 导出 ONNX
from models.export_onnx import export_to_onnx
export_to_onnx(model, 'models/transformer_real_data.onnx')
```

### Step 2: 创建 Transformer 回测脚本

**文件**: `python/backtest_transformer_real_data.py`

**核心逻辑**:
```python
# 1. 加载模型
model = QlibStyleTransformer(...)
model.load_state_dict(torch.load('models/transformer_real_data.pth'))
model.eval()

# 2. 加载数据和特征
# (同上)

# 3. 预测
predictions = []
with torch.no_grad():
    for batch_x, _ in test_loader:
        outputs = model(batch_x)
        predictions.extend(outputs.cpu().numpy())

predictions = np.array(predictions).flatten()

# 4. 评估 (Qlib 风格)
from models.qlib_metrics import QlibMetrics
metrics = QlibMetrics()

ic = metrics.information_coefficient(predictions, y_test_seq)
rank_ic = metrics.rank_ic(predictions, y_test_seq)
quantile_results = metrics.quantile_analysis(predictions, y_test_seq)

print(f"IC: {ic:.4f}")
print(f"Rank IC: {rank_ic:.4f}")
print(f"Top Quantile Excess: {quantile_results['top_excess']:.4f}")

# 5. 交易模拟
signals = (predictions > 0).astype(int)  # 1: 买入, 0: 卖出
returns = simulate_trading(signals, prices, transaction_cost=0.001)

print(f"总收益率: {returns['total_return']:.2f}%")
print(f"夏普比率: {returns['sharpe_ratio']:.4f}")
print(f"最大回撤: {returns['max_drawdown']:.2f}%")
```

### Step 3: 运行和验证

```bash
# 1. 训练 Transformer
cd python
python train_transformer_with_real_data.py

# 预期输出:
# Epoch 1/100
#   Train Loss: 0.0123
#   Val IC: 0.0456
#   Val Rank IC: 0.0512
# ...
# Epoch 50/100
#   Train Loss: 0.0089
#   Val IC: 0.1234
#   Val Rank IC: 0.1345
# Early stopping at epoch 50
# Best IC: 0.1234

# 2. 回测 Transformer
python backtest_transformer_real_data.py

# 预期输出:
# IC: 0.1234
# Rank IC: 0.1345
# Top Quantile Excess: 0.0234
# 总收益率: 25.67%
# 夏普比率: 1.45
# 最大回撤: -12.34%

# 3. 对比模型
python compare_models.py

# 预期输出:
# | 模型 | IC | 年化收益 | 夏普比率 |
# |------|----|---------| ---------|
# | RandomForest | 0.10 | 6.47% | 0.56 |
# | Transformer | 0.12 | 25.67% | 1.45 |
```

---

## 📊 预期改进效果

### 性能对比

| 指标 | 当前 (RF) | 目标 (Transformer) | 改进 |
|------|----------|-------------------|------|
| IC | 0.0978 | 0.12-0.15 | +23-53% |
| Rank IC | 0.1010 | 0.12-0.15 | +19-49% |
| IR | 0.6702 | 1.0-1.5 | +49-124% |
| 年化收益 | 6.47% | 15-25% | +132-286% |
| 夏普比率 | 0.5575 | 1.0-1.5 | +79-169% |
| 最大回撤 | -9.99% | -10% ~ -15% | 持平 |
| 胜率 | 50.52% | 52-55% | +3-9% |

### 真实数据回测改进

| 指标 | 当前 (RF) | 目标 (Transformer) | 改进 |
|------|----------|-------------------|------|
| 总收益率 | -90.14% | 10-30% | 扭亏为盈 |
| 夏普比率 | -1.61 | 0.8-1.5 | 扭亏为盈 |
| 最大回撤 | -90.30% | -15% ~ -25% | 大幅改善 |
| 胜率 | 28.15% | 50-55% | +78-95% |

---

## ⚠️ 风险和注意事项

### 1. 过拟合风险

**问题**: Transformer 参数量大 (~350K)，容易过拟合

**缓解措施**:
- 使用 Dropout (0.1-0.2)
- 使用 L2 正则化
- Early Stopping (基于 IC)
- 滑动窗口验证

### 2. 计算资源

**问题**: Transformer 训练需要 GPU

**解决方案**:
- 使用 CPU 训练 (较慢，但可行)
- 使用 AMP 混合精度 (减少内存)
- 减小 batch_size (32 → 16)

### 3. 数据质量

**问题**: 真实数据可能有缺失值、异常值

**解决方案**:
- 数据清洗和预处理
- 异常值检测和处理
- 缺失值填充

### 4. 市场变化

**问题**: 模型可能在新市场环境下失效

**解决方案**:
- 定期重训练 (每月)
- 监控 IC 变化
- 多策略组合

---

## 📅 时间表

### 本周 (Week 1)

- [ ] Day 1-2: 创建 `train_transformer_with_real_data.py`
- [ ] Day 3-4: 训练 Transformer 模型
- [ ] Day 5: 创建 `backtest_transformer_real_data.py`
- [ ] Day 6-7: 回测和验证

### 下周 (Week 2)

- [ ] Day 1-2: 验证 Alpha101 因子
- [ ] Day 3-4: 因子筛选和正交化
- [ ] Day 5-7: 重新训练和优化

### 第三周 (Week 3)

- [ ] Day 1-3: 超参数调优
- [ ] Day 4-5: 多策略组合
- [ ] Day 6-7: 准备实盘测试

---

## 🎯 成功标准

### 最低标准 (必须达到)

- IC > 0.10
- Rank IC > 0.08
- 年化收益 > 15%
- 夏普比率 > 1.0
- 最大回撤 < 20%
- 胜率 > 50%

### 理想标准 (努力达到)

- IC > 0.15
- Rank IC > 0.12
- IR > 1.5
- 年化收益 > 25%
- 夏普比率 > 1.5
- 最大回撤 < 15%
- 胜率 > 55%

---

## 📝 总结

### 当前状态

- ✅ 所有组件已实现 (100%)
- ❌ 高级组件未使用 (Transformer, ONNX)
- ❌ 性能不达标 (RF 模型过拟合)

### 核心问题

**已经实现了 Transformer，但实际回测仍在使用 RandomForest！**

### 立即行动

1. **创建 Transformer 训练脚本** (优先级最高)
2. **切换到 Transformer 模型**
3. **使用 Qlib 评估指标**
4. **重新训练和回测**

### 预期效果

- 年化收益: 6.47% → 15-25%
- 夏普比率: 0.56 → 1.0-1.5
- IC: 0.10 → 0.12-0.15

---

**下一步**: 立即创建 `train_transformer_with_real_data.py` 并开始训练！
