# TTQuant EC2 部署指南

本指南将帮助您在香港 EC2 实例上部署 TTQuant 量化交易系统，解决本地 Windows 环境的 TLS 连接问题。

## 📋 前置要求

### EC2 实例配置
- **区域**: 香港 (ap-east-1) 或其他亚洲区域
- **实例类型**: t3.medium 或更高 (2 vCPU, 4GB RAM)
- **操作系统**: Ubuntu 22.04 LTS 或 24.04 LTS
- **存储**: 至少 20GB EBS 卷
- **安全组**: 需要开放以下端口

### 安全组配置

| 端口 | 协议 | 用途 | 来源 |
|------|------|------|------|
| 22 | TCP | SSH | 您的 IP |
| 3000 | TCP | Grafana | 您的 IP |
| 9090 | TCP | Prometheus | 您的 IP |
| 5555-5560 | TCP | ZMQ (可选) | 内部 |
| 8080-8083 | TCP | 指标端点 (可选) | 您的 IP |

**安全建议**: 仅对您的 IP 地址开放端口，不要对 0.0.0.0/0 开放。

---

## 🚀 快速开始

### 步骤 1: 连接到 EC2

```bash
# 使用您的密钥文件连接
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 步骤 2: 初始化环境

```bash
# 下载初始化脚本
curl -O https://raw.githubusercontent.com/your-repo/TTQuant/main/deploy/ec2-setup.sh

# 运行初始化脚本
bash ec2-setup.sh

# 重新登录以使 Docker 权限生效
exit
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 步骤 3: 克隆代码

```bash
# 克隆您的代码仓库
git clone https://github.com/your-username/TTQuant.git
cd TTQuant
```

### 步骤 4: 部署系统

```bash
# 运行部署脚本
bash deploy/ec2-deploy.sh
```

部署脚本会自动：
- ✅ 创建 `.env` 文件并生成随机密码
- ✅ 构建 Docker 镜像
- ✅ 启动所有服务
- ✅ 验证服务状态

### 步骤 5: 验证 OKX 连接

```bash
# 运行验证脚本
bash deploy/verify-okx.sh
```

如果看到 "✅ 验证完成！OKX 连接正常"，说明部署成功！

---

## 📊 访问监控面板

### Grafana (数据可视化)
```
http://<your-ec2-ip>:3000
```
- 默认用户名: `admin`
- 默认密码: 查看 `.env` 文件中的 `GRAFANA_PASSWORD`

### Prometheus (指标查询)
```
http://<your-ec2-ip>:9090
```

---

## 🔧 常用命令

### 查看服务状态
```bash
cd TTQuant/docker
docker compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker compose logs

# 查看 OKX Market Data 日志
docker compose logs -f md-okx

# 查看 OKX Gateway 日志
docker compose logs -f gateway-okx
```

### 重启服务
```bash
# 重启所有服务
docker compose restart

# 重启单个服务
docker compose restart md-okx
```

### 停止服务
```bash
docker compose down
```

### 更新代码
```bash
# 拉取最新代码
git pull

# 重新部署
bash deploy/ec2-deploy.sh
```

---

## 🗄️ 数据库管理

### 连接数据库
```bash
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading
```

### 查看 OKX 行情数据
```sql
-- 查看最近的数据
SELECT * FROM market_data
WHERE exchange='okx'
ORDER BY time DESC
LIMIT 10;

-- 统计数据量
SELECT
    exchange,
    symbol,
    COUNT(*) as count,
    MAX(time) as last_update
FROM market_data
WHERE exchange='okx'
GROUP BY exchange, symbol;
```

### 备份数据库
```bash
docker exec ttquant-timescaledb pg_dump -U ttquant ttquant_trading > backup_$(date +%Y%m%d).sql
```

### 恢复数据库
```bash
cat backup_20240101.sql | docker exec -i ttquant-timescaledb psql -U ttquant -d ttquant_trading
```

---

## 🔐 配置 OKX API（可选）

如果您想进行真实交易（而不是模拟模式），需要配置 OKX API 凭证。

### 1. 在 OKX 创建 API Key
1. 登录 [OKX](https://www.okx.com)
2. 进入 API 管理页面
3. 创建新的 API Key
4. 记录：API Key、Secret Key、Passphrase

### 2. 更新 .env 文件
```bash
cd TTQuant
vim .env
```

修改以下内容：
```bash
OKX_API_KEY=your_api_key_here
OKX_SECRET_KEY=your_secret_key_here
OKX_PASSPHRASE=your_passphrase_here
OKX_TESTNET=true  # 测试网，改为 false 使用生产环境
```

### 3. 重启服务
```bash
cd docker
docker compose restart gateway-okx
```

---

## 🐛 故障排查

### 问题 1: OKX WebSocket 连接失败

**症状**: 日志中看到 "TLS error" 或 "connection failed"

**解决方案**:
```bash
# 1. 检查网络连接
curl -I https://www.okx.com

# 2. 更新 CA 证书
docker compose down
docker compose build --no-cache md-okx
docker compose up -d md-okx

# 3. 查看详细日志
docker compose logs md-okx | grep -i "error\|tls"
```

### 问题 2: 数据库连接失败

**症状**: 服务无法启动，日志显示数据库连接错误

**解决方案**:
```bash
# 1. 检查数据库状态
docker compose ps timescaledb

# 2. 查看数据库日志
docker compose logs timescaledb

# 3. 重启数据库
docker compose restart timescaledb
```

### 问题 3: 端口被占用

**症状**: 服务启动失败，提示端口已被使用

**解决方案**:
```bash
# 查看端口占用
sudo netstat -tulpn | grep <port>

# 停止占用端口的进程
sudo kill <pid>

# 或修改 docker-compose.yml 中的端口映射
```

### 问题 4: 磁盘空间不足

**症状**: 服务运行一段时间后停止，日志显示磁盘满

**解决方案**:
```bash
# 查看磁盘使用
df -h

# 清理 Docker 资源
docker system prune -a

# 清理旧日志
docker compose logs --tail=0 > /dev/null
```

---

## 📈 性能优化

### 1. 调整日志级别
编辑 `docker/docker-compose.yml`，将 `RUST_LOG` 从 `info` 改为 `warn`:
```yaml
environment:
  RUST_LOG: warn  # 减少日志输出
```

### 2. 限制日志文件大小
日志配置已在 `docker-compose.yml` 中设置：
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "3"
```

### 3. 数据库优化
```sql
-- 连接到数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading

-- 创建额外的索引（如果查询慢）
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time
ON market_data (symbol, time DESC);

-- 设置数据保留策略（保留 30 天）
SELECT add_retention_policy('market_data', INTERVAL '30 days');
```

---

## 🔄 本地开发 + EC2 生产工作流

### 本地开发
```bash
# 在本地 Windows 修改代码
cd C:\Users\11915\Desktop\TTQuant

# 测试编译
cd docker
docker compose build md-okx

# 提交代码
git add .
git commit -m "feat: 添加新功能"
git push origin main
```

### EC2 部署
```bash
# SSH 到 EC2
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 更新代码
cd TTQuant
git pull

# 重新部署
bash deploy/ec2-deploy.sh

# 验证
bash deploy/verify-okx.sh
```

---

## 📞 获取帮助

### 查看系统状态
```bash
# 服务状态
cd TTQuant/docker
docker compose ps

# 系统资源
htop

# 磁盘使用
df -h

# 网络连接
netstat -tulpn
```

### 导出日志
```bash
# 导出所有日志
cd TTQuant/docker
docker compose logs > logs_$(date +%Y%m%d_%H%M%S).txt

# 导出 OKX 日志
docker compose logs md-okx > okx_logs_$(date +%Y%m%d_%H%M%S).txt
```

---

## 🎯 成功标准

部署成功后，您应该看到：

✅ 所有 Docker 容器运行正常
```bash
docker compose ps
# 所有服务状态为 "running"
```

✅ OKX WebSocket 连接成功
```bash
docker compose logs md-okx | grep "Connected to OKX WebSocket"
# 应该看到连接成功的日志
```

✅ 数据持续写入数据库
```bash
bash deploy/verify-okx.sh
# 应该看到 "✅ 验证完成！OKX 连接正常"
```

✅ Grafana 监控面板可访问
```
打开浏览器访问: http://<your-ec2-ip>:3000
```

---

## 📝 注意事项

1. **安全性**:
   - 不要将 `.env` 文件提交到 Git
   - 定期更新系统和 Docker
   - 使用强密码
   - 限制安全组访问

2. **成本控制**:
   - 使用 t3.medium 实例（按需）约 $0.05/小时
   - 考虑使用预留实例或 Savings Plans 降低成本
   - 监控数据传输费用

3. **数据备份**:
   - 定期备份数据库
   - 使用 EBS 快照
   - 考虑跨区域备份

4. **监控告警**:
   - 配置 Prometheus 告警规则
   - 设置 Slack/Email 通知
   - 监控系统资源使用

---

## 🔗 相关链接

- [OKX API 文档](https://www.okx.com/docs-v5/en/)
- [Docker 文档](https://docs.docker.com/)
- [TimescaleDB 文档](https://docs.timescale.com/)
- [Grafana 文档](https://grafana.com/docs/)

---

**祝您交易顺利！** 🚀
