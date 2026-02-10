# OKX API 配置指南

## 1. 获取 OKX API 凭证

### 1.1 注册 OKX 账户
1. 访问 [OKX 官网](https://www.okx.com/)
2. 注册并完成 KYC 认证

### 1.2 创建 API Key
1. 登录 OKX 账户
2. 进入 **个人中心** → **API 管理**
3. 点击 **创建 API Key**
4. 设置以下权限：
   - ✅ **读取** (Read)
   - ✅ **交易** (Trade)
   - ❌ **提现** (Withdraw) - 不建议开启
5. 设置 IP 白名单（可选，但强烈建议）
6. 记录以下信息：
   - **API Key**
   - **Secret Key**
   - **Passphrase** (OKX 特有，创建时设置)

⚠️ **重要提示**：
- Secret Key 只显示一次，请妥善保存
- Passphrase 是您自己设置的密码，不是账户密码
- 不要将 API 凭证提交到 Git 仓库

---

## 2. 配置环境变量

### 2.1 创建 `.env` 文件
在项目根目录创建 `.env` 文件（已在 `.gitignore` 中）：

```bash
# OKX API 凭证
OKX_API_KEY=your_api_key_here
OKX_SECRET_KEY=your_secret_key_here
OKX_PASSPHRASE=your_passphrase_here

# 是否使用测试网（true=模拟盘，false=实盘）
OKX_TESTNET=true

# 数据库密码
DB_PASSWORD=ttquant_local_2024

# Grafana 密码
GRAFANA_PASSWORD=admin
```

### 2.2 测试网 vs 实盘

**测试网（模拟盘）**：
- 使用虚拟资金，不会产生真实交易
- API 端点相同，但使用模拟盘账户
- 需要在 OKX 网站上单独开通模拟盘
- 设置：`OKX_TESTNET=true`

**实盘**：
- 使用真实资金，会产生真实交易
- ⚠️ **风险警告**：请确保策略经过充分测试
- 设置：`OKX_TESTNET=false`

---

## 3. 启动服务

### 3.1 使用 Docker Compose
```bash
cd /c/Users/11915/Desktop/TTQuant

# 启动所有服务
docker compose -f docker/docker-compose.yml up -d

# 仅启动 OKX 服务
docker compose -f docker/docker-compose.yml up -d md-okx gateway-okx
```

### 3.2 查看日志
```bash
# 查看 OKX Market Data 日志
docker compose -f docker/docker-compose.yml logs -f md-okx

# 查看 OKX Gateway 日志
docker compose -f docker/docker-compose.yml logs -f gateway-okx
```

---

## 4. 验证配置

### 4.1 检查行情数据
```bash
# 运行测试脚本
cd python
python test_okx_simple.py
```

预期输出：
```
Listening for OKX market data...
[1] BTCUSDT: $69429.50 (exchange: okx)
[2] ETHUSDT: $2027.30 (exchange: okx)
...
✅ Received 5 OKX market data messages
```

### 4.2 检查数据库
```bash
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
  "SELECT exchange, symbol, COUNT(*) FROM market_data WHERE exchange='okx' GROUP BY exchange, symbol;"
```

### 4.3 测试下单（模拟模式）
```bash
cd python
python test_e2e_quick.py
```

---

## 5. 安全建议

### 5.1 API 权限最小化
- ✅ 只开启必要的权限（读取 + 交易）
- ❌ 不要开启提现权限
- ✅ 设置 IP 白名单

### 5.2 资金管理
- 初期使用小额资金测试
- 设置止损和仓位限制
- 定期检查交易记录

### 5.3 监控告警
- 配置 Grafana 监控面板
- 设置异常交易告警
- 监控账户余额变化

---

## 6. 常见问题

### Q1: API 签名错误
**错误信息**：`Invalid signature`

**解决方案**：
1. 检查 API Key、Secret Key、Passphrase 是否正确
2. 确认系统时间准确（时间偏差 > 30 秒会导致签名失败）
3. 检查 Secret Key 是否包含空格或换行符

### Q2: IP 限制
**错误信息**：`IP address not in whitelist`

**解决方案**：
1. 在 OKX API 管理页面添加服务器 IP
2. 或者不设置 IP 白名单（不推荐）

### Q3: 模拟盘无法下单
**错误信息**：`Insufficient balance`

**解决方案**：
1. 登录 OKX 网站
2. 进入模拟盘账户
3. 充值虚拟资金

### Q4: 订单被拒绝
**错误信息**：`Order rejected`

**可能原因**：
- 交易对不存在或已下架
- 订单数量不符合最小/最大限制
- 价格精度不正确
- 账户余额不足

---

## 7. 性能优化

### 7.1 行情数据优化
- 批量写入数据库（当前：100 条/批次）
- 使用内存池减少内存分配
- ZMQ 零拷贝传输

### 7.2 订单处理优化
- 异步下单，不阻塞策略执行
- 订单缓存，避免重复查询
- 风控前置，快速拒绝无效订单

### 7.3 数据库优化
- TimescaleDB 时序数据库
- 自动分区和压缩
- 索引优化（symbol + time）

---

## 8. 监控指标

### 8.1 Grafana 面板
访问：http://localhost:3000
- 用户名：admin
- 密码：见 `.env` 文件中的 `GRAFANA_PASSWORD`

### 8.2 Prometheus 指标
访问：http://localhost:9090

**OKX Market Data 指标**：
- `process_cpu_seconds_total{exchange="okx"}` - CPU 使用率
- `process_resident_memory_bytes{exchange="okx"}` - 内存使用
- `process_threads{exchange="okx"}` - 线程数
- `process_open_fds{exchange="okx"}` - 打开的文件描述符

**OKX Gateway 指标**：
- 同上，service="gateway"

---

## 9. 故障排查

### 9.1 查看容器状态
```bash
docker compose -f docker/docker-compose.yml ps
```

### 9.2 查看容器日志
```bash
# 最近 100 行日志
docker compose -f docker/docker-compose.yml logs --tail=100 md-okx

# 实时日志
docker compose -f docker/docker-compose.yml logs -f gateway-okx
```

### 9.3 进入容器调试
```bash
docker exec -it ttquant-md-okx /bin/bash
docker exec -it ttquant-gateway-okx /bin/bash
```

### 9.4 重启服务
```bash
# 重启单个服务
docker compose -f docker/docker-compose.yml restart md-okx

# 重启所有服务
docker compose -f docker/docker-compose.yml restart
```

---

## 10. 下一步

- [ ] 配置真实 API 凭证
- [ ] 在模拟盘测试策略
- [ ] 配置监控告警
- [ ] 添加更多交易对
- [ ] 优化策略参数
- [ ] 实盘小额测试
- [ ] 逐步增加仓位

---

## 参考资料

- [OKX API 文档](https://www.okx.com/docs-v5/zh/)
- [OKX WebSocket API](https://www.okx.com/docs-v5/zh/#websocket-api)
- [OKX REST API](https://www.okx.com/docs-v5/zh/#rest-api)
- [TTQuant 项目文档](../README.md)
