# TTQuant 混合部署方案指南

## 概述

本指南实施混合部署方案：
- **本地**: Docker 配置和测试
- **服务器**: 真实数据获取和模型训练
- **集成**: 完整系统部署

---

## Part 1: 本地 Docker 配置 ✅

### 已完成文件

1. **docker-compose.test.yml** - Docker Compose 配置
   - TimescaleDB (数据库)
   - Prometheus (监控)
   - Grafana (可视化)
   - Strategy Engine (策略引擎)
   - Risk Monitor (风险监控)

2. **python/Dockerfile** - Python 应用镜像

3. **python/requirements.txt** - Python 依赖（已更新）
   - 添加 scikit-learn, ccxt, scipy, structlog

4. **config/test.yaml** - 测试环境配置
   - 数据库连接
   - 交易所配置 (OKX)
   - 策略配置
   - 风险限额

5. **config/prometheus.yml** - Prometheus 配置

6. **scripts/deploy_test.sh** - 本地部署脚本

### 本地测试步骤

```bash
# 1. 创建环境变量文件
cd /path/to/TTQuant
cp .env.example .env.test  # 或使用脚本自动创建

# 2. 运行部署脚本
bash scripts/deploy_test.sh

# 3. 访问服务
# Grafana: http://localhost:3000 (admin/admin123)
# Prometheus: http://localhost:9090
# 风险监控: http://localhost:8001/metrics
```

---

## Part 2: 服务器部署 🚀

### 服务器要求

- **操作系统**: Ubuntu 20.04+ / CentOS 7+
- **内存**: 最少 4GB，推荐 8GB
- **磁盘**: 最少 20GB
- **网络**: 可访问 OKX API
- **软件**: Docker, Docker Compose, Python 3.11+

### 部署步骤

#### 1. 上传代码到服务器

```bash
# 方法 A: Git Clone
ssh user@server
git clone https://github.com/nullma/TTQuant.git
cd TTQuant

# 方法 B: SCP 上传
scp -r /path/to/TTQuant user@server:/home/user/
```

#### 2. 运行服务器部署脚本

```bash
# 在服务器上执行
cd TTQuant
chmod +x scripts/server_deploy.sh
bash scripts/server_deploy.sh
```

**脚本会自动**:
1. 检查 Python 环境
2. 安装依赖
3. 从 OKX 获取真实历史数据 (BTC/USDT, 1h, 365天)
4. 训练 ML 模型 (Random Forest + Gradient Boosting)
5. 保存模型文件

#### 3. 验证数据和模型

```bash
# 检查数据文件
ls -lh python/data/historical/
# 应该看到: BTCUSDT_1h_365d_okx.csv

# 检查模型文件
ls -lh python/models/btcusdt_rf_real/
# 应该看到: model.pkl, metadata.json

# 查看模型性能
cat python/models/btcusdt_rf_real/metadata.json
```

---

## Part 3: 数据同步（服务器 → 本地）

### 方法 A: SCP 下载

```bash
# 下载数据文件
scp user@server:/home/user/TTQuant/python/data/historical/*.csv \
    /path/to/local/TTQuant/python/data/historical/

# 下载模型文件
scp -r user@server:/home/user/TTQuant/python/models/btcusdt_*_real \
    /path/to/local/TTQuant/python/models/
```

### 方法 B: Git LFS（推荐用于团队）

```bash
# 在服务器上
cd TTQuant
git lfs track "*.pkl"
git lfs track "*.csv"
git add .gitattributes
git add python/models/
git commit -m "Add trained models"
git push

# 在本地
git pull
git lfs pull
```

### 方法 C: 对象存储（生产环境）

```bash
# 上传到 S3/OSS
aws s3 cp python/models/ s3://ttquant-models/ --recursive

# 本地下载
aws s3 sync s3://ttquant-models/ python/models/
```

---

## Part 4: 完整系统部署

### 在服务器上启动完整系统

```bash
# 1. 确保模型已训练
ls python/models/btcusdt_rf_real/model.pkl

# 2. 配置环境变量
cat > .env.test << EOF
DB_PASSWORD=your_secure_password
GRAFANA_PASSWORD=your_grafana_password
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_PASSPHRASE=your_okx_passphrase
EOF

# 3. 启动 Docker 服务
bash scripts/deploy_test.sh

# 4. 检查服务状态
docker-compose -f docker-compose.test.yml ps

# 5. 查看日志
docker-compose -f docker-compose.test.yml logs -f strategy-engine
```

### 访问服务（需要配置防火墙/安全组）

```bash
# 开放端口
sudo ufw allow 3000  # Grafana
sudo ufw allow 9090  # Prometheus
sudo ufw allow 8001  # Risk Monitor

# 或使用 SSH 隧道
ssh -L 3000:localhost:3000 \
    -L 9090:localhost:9090 \
    -L 8001:localhost:8001 \
    user@server
```

---

## Part 5: 监控和维护

### 查看日志

```bash
# 所有服务
docker-compose -f docker-compose.test.yml logs -f

# 特定服务
docker-compose -f docker-compose.test.yml logs -f strategy-engine
docker-compose -f docker-compose.test.yml logs -f risk-monitor

# 最近 100 行
docker-compose -f docker-compose.test.yml logs --tail=100 strategy-engine
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.test.yml restart

# 重启特定服务
docker-compose -f docker-compose.test.yml restart strategy-engine
```

### 停止服务

```bash
# 停止但保留数据
docker-compose -f docker-compose.test.yml stop

# 停止并删除容器（保留数据卷）
docker-compose -f docker-compose.test.yml down

# 完全清理（包括数据）
docker-compose -f docker-compose.test.yml down -v
```

### 备份数据

```bash
# 备份数据库
docker exec ttquant-timescaledb pg_dump -U ttquant ttquant_test > backup.sql

# 备份模型
tar -czf models_backup.tar.gz python/models/

# 备份配置
tar -czf config_backup.tar.gz config/ .env.test
```

---

## 故障排查

### 问题 1: 无法连接 OKX API

**症状**: 数据获取失败
**解决**:
```bash
# 检查网络
curl -I https://www.okx.com

# 使用代理
export https_proxy=http://proxy:port
python3 data/fetch_historical_data.py
```

### 问题 2: 容器启动失败

**症状**: docker-compose up 报错
**解决**:
```bash
# 查看详细日志
docker-compose -f docker-compose.test.yml logs

# 检查端口占用
netstat -tulpn | grep -E '3000|5432|9090|8001'

# 重新构建
docker-compose -f docker-compose.test.yml build --no-cache
```

### 问题 3: 数据库连接失败

**症状**: 策略引擎无法连接数据库
**解决**:
```bash
# 检查数据库状态
docker-compose -f docker-compose.test.yml ps timescaledb

# 测试连接
docker exec ttquant-timescaledb psql -U ttquant -d ttquant_test -c "SELECT 1"

# 查看数据库日志
docker-compose -f docker-compose.test.yml logs timescaledb
```

---

## 性能优化

### 数据库优化

```sql
-- 连接到数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_test

-- 创建索引
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp DESC);
CREATE INDEX idx_trades_timestamp ON trades(timestamp DESC);

-- 设置 TimescaleDB 参数
ALTER DATABASE ttquant_test SET timescaledb.max_background_workers = 4;
```

### 容器资源限制

```yaml
# 在 docker-compose.test.yml 中添加
services:
  strategy-engine:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

## 下一步

### 短期（1周内）
- [ ] 在服务器上获取真实数据
- [ ] 训练和评估模型
- [ ] 启动纸面交易测试
- [ ] 监控系统稳定性

### 中期（2-4周）
- [ ] 优化策略参数
- [ ] 添加更多策略
- [ ] 实现自动化测试
- [ ] 完善监控告警

### 长期（1-3月）
- [ ] 生产环境部署
- [ ] 高可用架构
- [ ] 多交易所支持
- [ ] 实盘交易

---

## 联系和支持

- **文档**: docs/
- **问题**: GitHub Issues
- **更新**: git pull

---

**最后更新**: 2026-02-12
**版本**: v1.0
**状态**: ✅ 就绪
