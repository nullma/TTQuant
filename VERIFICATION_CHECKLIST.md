# TTQuant 实施验证清单

## 文件创建验证

### Python 策略代码
- [x] `python/strategy/strategies/grid_trading.py` - 网格交易策略
- [x] `python/strategy/strategies/momentum.py` - 动量突破策略
- [x] `python/run_strategy_engine.py` - 策略引擎主程序

### Docker 配置
- [x] `docker/docker-compose.yml` - 添加 strategy-engine 服务
- [x] `docker/docker-compose.yml` - 添加 backtest 服务
- [x] `docker/docker-compose.yml` - 添加 backtest-results volume

### Grafana 面板
- [x] `monitoring/dashboards/backtest-dashboard.json` - 回测结果面板

### 部署脚本
- [x] `scripts/start-strategy-engine.sh` - 策略引擎启动脚本
- [x] `scripts/run-backtest.sh` - 回测运行脚本

### 文档
- [x] `STRATEGY_ENGINE_GUIDE.md` - 策略引擎使用指南
- [x] `IMPLEMENTATION_COMPLETE.md` - 实施完成报告

### 依赖更新
- [x] `python/requirements.txt` - 添加 toml==0.10.2

---

## 功能验证步骤

### 1. 策略引擎验证

```bash
# 1. 检查配置文件
cat config/strategies.toml

# 2. 启用一个策略（编辑文件，设置 enabled = true）

# 3. 构建镜像
cd docker
docker-compose build strategy-engine

# 4. 启动服务
docker-compose up -d strategy-engine

# 5. 查看日志
docker logs -f ttquant-strategy-engine

# 预期输出：
# - "TTQuant Strategy Engine Starting"
# - "Loaded X strategies"
# - "Strategy Engine Started"
# - 行情数据接收日志
```

### 2. 回测系统验证

```bash
# 1. 确保数据库运行
docker ps | grep timescaledb

# 2. 检查历史数据
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT COUNT(*) FROM market_data;"

# 3. 运行回测
cd docker
docker-compose --profile backtest up backtest

# 预期输出：
# - "Creating backtest engine..."
# - "Adding EMA Cross strategy..."
# - "Starting backtest..."
# - 回测结果统计
```

### 3. Grafana 面板验证

```bash
# 1. 访问 Grafana
# http://localhost:3000

# 2. 登录
# 用户名: admin
# 密码: admin123

# 3. 查看面板
# - OKX 实时数据面板（应显示实时价格）
# - 回测结果面板（运行回测后显示）

# 4. 检查数据源
# Configuration -> Data Sources -> PostgreSQL
# 应该已配置并连接成功
```

### 4. 容器状态验证

```bash
# 查看所有运行的容器
docker ps

# 预期看到以下容器：
# - ttquant-timescaledb (运行中)
# - ttquant-md-okx (运行中)
# - ttquant-gateway-okx (运行中)
# - ttquant-strategy-engine (运行中) ← 新增
# - ttquant-grafana (运行中)
# - ttquant-prometheus (运行中)
# - 其他监控容器...
```

### 5. 数据库表验证

```bash
# 连接到数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading

# 检查表结构
\dt

# 预期看到：
# - market_data (有数据)
# - orders (策略运行后有数据)
# - trades (策略运行后有数据)
# - positions (策略运行后有数据)

# 查看行情数据量
SELECT COUNT(*) FROM market_data;
# 应该显示 25万+ 条

# 退出
\q
```

---

## 测试场景

### 场景 1: 启动网格交易策略

1. 编辑 `config/strategies.toml`
2. 设置 `grid_trading_btc` 的 `enabled = true`
3. 运行 `bash scripts/start-strategy-engine.sh`
4. 选择 OKX 交易所
5. 选择模拟交易模式
6. 观察日志输出

**预期结果**:
- 策略引擎启动成功
- 连接到 OKX 行情
- 接收实时价格数据
- 初始化网格
- 根据价格变化触发买卖信号（模拟）

### 场景 2: 运行回测

1. 确保有历史数据（25万+ 条）
2. 运行 `bash scripts/run-backtest.sh`
3. 等待回测完成

**预期结果**:
- 加载历史数据
- 运行 EMA 交叉策略
- 生成回测报告
- 显示关键指标（收益率、夏普比率等）
- 结果保存到 `backtest_results/`

### 场景 3: Grafana 监控

1. 启动策略引擎
2. 访问 http://localhost:3000
3. 查看 "OKX 实时数据" 面板

**预期结果**:
- 显示实时价格曲线
- 显示数据接收速率
- 显示系统状态

---

## 故障排查

### 问题 1: 策略引擎启动失败

**可能原因**:
- 行情服务未运行
- 配置文件错误
- 依赖缺失

**解决方法**:
```bash
# 检查行情服务
docker ps | grep md-okx

# 如果未运行，启动它
cd docker
docker-compose up -d md-okx

# 检查配置文件语法
python -c "import toml; toml.load('config/strategies.toml')"

# 重新构建镜像
docker-compose build strategy-engine
```

### 问题 2: 没有交易信号

**可能原因**:
- 策略未启用
- 市场条件不满足
- 持仓已达上限

**解决方法**:
```bash
# 查看策略日志
docker logs -f ttquant-strategy-engine

# 检查配置
grep "enabled = true" config/strategies.toml

# 降低策略阈值（测试用）
# 编辑 strategies.toml，调整参数
```

### 问题 3: 回测失败

**可能原因**:
- 数据库未运行
- 历史数据不足
- 日期范围错误

**解决方法**:
```bash
# 检查数据库
docker ps | grep timescaledb

# 检查数据量
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c "SELECT COUNT(*), MIN(exchange_time), MAX(exchange_time) FROM market_data;"

# 调整回测日期范围
# 编辑 python/run_backtest.py
```

---

## 性能指标

### 策略引擎
- 行情处理延迟: < 10ms
- 订单发送延迟: < 5ms
- 内存使用: < 200MB
- CPU 使用: < 10%

### 回测系统
- 数据加载速度: 10万条/秒
- 回测速度: 1万条/秒
- 内存使用: < 500MB

### 数据库
- 写入速度: 100条/秒
- 查询延迟: < 100ms
- 存储压缩率: 90%+

---

## 完成标准

所有以下条件满足即为实施成功：

- [x] 所有文件已创建
- [ ] 策略引擎容器可以启动
- [ ] 策略引擎可以接收行情数据
- [ ] 策略可以生成交易信号（日志中可见）
- [ ] 回测系统可以运行
- [ ] 回测结果可以生成
- [ ] Grafana 面板可以访问
- [ ] 文档完整且准确

---

## 下一步行动

1. **立即测试**
   ```bash
   cd Desktop/TTQuant
   bash scripts/start-strategy-engine.sh
   ```

2. **观察运行**
   ```bash
   docker logs -f ttquant-strategy-engine
   ```

3. **运行回测**
   ```bash
   bash scripts/run-backtest.sh
   ```

4. **查看监控**
   - 访问 http://localhost:3000
   - 查看实时数据和回测结果

---

**验证日期**: 2026-02-11
**验证人员**: 待用户确认
**验证状态**: 待测试
