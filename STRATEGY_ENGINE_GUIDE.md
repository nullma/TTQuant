# TTQuant 策略引擎使用指南

## 概述

TTQuant 策略引擎现已完成，支持以下功能：

- ✅ 网格交易策略 (Grid Trading)
- ✅ 均线交叉策略 (MA Cross)
- ✅ 动量突破策略 (Momentum)
- ✅ 回测系统集成
- ✅ Grafana 可视化面板

## 快速开始

### 1. 启用策略

编辑 `config/strategies.toml`，将想要运行的策略设置为 `enabled = true`：

```toml
[[strategies]]
name = "grid_trading_btc"
type = "grid"
enabled = true  # 改为 true 启用
symbol = "BTCUSDT"
exchange = "okx"
```

### 2. 启动策略引擎

```bash
# 使用脚本启动（推荐）
bash scripts/start-strategy-engine.sh

# 或手动启动
cd docker
docker-compose up -d strategy-engine
```

### 3. 查看运行日志

```bash
docker logs -f ttquant-strategy-engine
```

### 4. 监控策略表现

访问 Grafana: http://localhost:3000

- OKX 实时数据面板
- 回测结果面板
- 系统监控面板

## 策略配置详解

### 网格交易策略

适合震荡行情，在价格上下波动时自动买卖获利。

```toml
[[strategies]]
name = "grid_trading_btc"
type = "grid"
enabled = true
symbol = "BTCUSDT"
exchange = "okx"

[strategies.parameters]
grid_count = 10              # 网格数量
price_range_percent = 2.0    # 价格范围 ±2%
order_amount_usdt = 100      # 每格订单金额
max_position_usdt = 5000     # 最大持仓
stop_loss_percent = 5.0      # 止损 5%
take_profit_percent = 10.0   # 止盈 10%
```

### 均线交叉策略

基于快慢均线交叉产生买卖信号。

```toml
[[strategies]]
name = "ma_cross_eth"
type = "ma_cross"
enabled = true
symbol = "ETHUSDT"
exchange = "okx"

[strategies.parameters]
fast_period = 5              # 快线周期
slow_period = 20             # 慢线周期
timeframe = "1m"             # K线周期
order_amount_usdt = 200      # 交易金额
max_position_usdt = 2000     # 最大持仓
stop_loss_percent = 3.0      # 止损 3%
take_profit_percent = 6.0    # 止盈 6%
```

### 动量突破策略

捕捉价格动量突破机会。

```toml
[[strategies]]
name = "momentum_sol"
type = "momentum"
enabled = true
symbol = "SOLUSDT"
exchange = "okx"

[strategies.parameters]
lookback_period = 20         # 回看周期
breakout_threshold = 1.5     # 突破阈值（标准差倍数）
volume_threshold = 1.2       # 成交量阈值
order_amount_usdt = 150      # 交易金额
max_position_usdt = 1500     # 最大持仓
stop_loss_percent = 4.0      # 止损 4%
take_profit_percent = 8.0    # 止盈 8%
```

## 全局配置

```toml
[global]
trading_mode = "paper"       # paper: 模拟交易, live: 实盘交易
max_total_position_usdt = 10000  # 总持仓上限
max_daily_loss_usdt = 500        # 单日最大亏损
max_drawdown_percent = 10.0      # 最大回撤
order_timeout_secs = 30          # 订单超时
retry_count = 3                  # 重试次数
log_level = "info"               # 日志级别
log_trades = true                # 记录交易
```

## 回测系统

### 运行回测

```bash
# 使用脚本运行
bash scripts/run-backtest.sh

# 或手动运行
cd docker
docker-compose --profile backtest up backtest
```

### 查看回测结果

1. **命令行输出**：回测完成后会显示关键指标
2. **文件报告**：保存在 `backtest_results/` 目录
3. **Grafana 面板**：http://localhost:3000/d/backtest

### 回测指标

- Total Return: 总收益率
- Annual Return: 年化收益率
- Sharpe Ratio: 夏普比率
- Max Drawdown: 最大回撤
- Win Rate: 胜率
- Total Trades: 总交易次数

## 数据库表结构

### market_data - 行情数据

已采集 25万+ 条实时数据，可用于回测。

### orders - 订单记录

策略引擎发出的所有订单。

### trades - 成交记录

订单的成交回报。

### positions - 持仓记录

实时持仓状态和盈亏。

## 常见问题

### Q: 策略引擎启动失败？

检查：
1. 行情服务是否运行：`docker ps | grep md-okx`
2. 网关服务是否运行：`docker ps | grep gateway-okx`
3. 配置文件是否正确：`config/strategies.toml`

### Q: 没有交易信号？

可能原因：
1. 策略未启用（`enabled = false`）
2. 市场条件不满足策略条件
3. 持仓已达上限

查看日志：`docker logs -f ttquant-strategy-engine`

### Q: 如何切换到实盘交易？

⚠️ **警告：实盘交易有风险！**

1. 确保已充分回测验证策略
2. 修改 `config/strategies.toml`：
   ```toml
   [global]
   trading_mode = "live"
   ```
3. 配置真实 API 密钥（`.env` 文件）
4. 重启策略引擎

### Q: 如何添加自定义策略？

1. 在 `python/strategy/strategies/` 创建新策略文件
2. 继承 `BaseStrategy` 类
3. 实现 `on_market_data()` 和 `on_trade()` 方法
4. 在 `run_strategy_engine.py` 注册策略类型
5. 在 `strategies.toml` 添加配置

## 性能优化建议

### 策略参数调优

1. **回测验证**：先用历史数据回测，找到最优参数
2. **小仓位测试**：实盘前用小金额测试
3. **逐步加仓**：确认策略有效后再增加仓位

### 风控设置

1. **止损止盈**：必须设置合理的止损止盈
2. **持仓限制**：控制单个策略和总持仓
3. **日亏损限制**：设置每日最大亏损

### 监控告警

1. **Grafana 面板**：实时监控策略表现
2. **日志分析**：定期检查策略日志
3. **告警设置**：配置 AlertManager 告警规则

## 下一步

1. ✅ 启用一个策略进行模拟交易
2. ✅ 观察策略运行情况（日志 + Grafana）
3. ✅ 使用历史数据进行回测
4. ✅ 根据回测结果调整参数
5. ⚠️ 小仓位实盘测试（可选）

## 技术支持

- 查看日志：`docker logs -f ttquant-strategy-engine`
- 查看文档：`docs/` 目录
- 系统状态：运行 `系统管理面板.bat`

---

**免责声明**：量化交易有风险，投资需谨慎。本系统仅供学习研究使用，不构成投资建议。
