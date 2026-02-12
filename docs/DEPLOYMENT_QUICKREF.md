# TTQuant 混合部署快速参考

## 📋 部署方案 C - 已完成

### ✅ Part 1: 本地 Docker 配置（已完成）

**文件清单**:
```
docker-compose.test.yml       # 服务编排
python/Dockerfile             # Python 镜像
python/.dockerignore          # 构建忽略
config/test.yaml              # 测试配置
config/prometheus.yml         # 监控配置
scripts/deploy_test.sh        # 本地部署脚本
```

**本地测试**:
```bash
cd TTQuant
bash scripts/deploy_test.sh
```

**访问地址**:
- Grafana: http://localhost:3000 (admin/admin123)
- Prometheus: http://localhost:9090
- 风险监控: http://localhost:8001/metrics

---

### 🚀 Part 2: 服务器部署（待执行）

**前置条件**:
- Ubuntu 20.04+ / CentOS 7+
- 内存 ≥ 4GB（推荐 8GB）
- Docker + Docker Compose
- Python 3.11+
- 可访问 OKX API

**部署步骤**:
```bash
# 1. 上传代码到服务器
git clone https://github.com/nullma/TTQuant.git
cd TTQuant

# 2. 运行服务器部署脚本
chmod +x scripts/server_deploy.sh
bash scripts/server_deploy.sh
```

**脚本会自动**:
1. ✓ 检查环境
2. ✓ 安装依赖
3. ✓ 从 OKX 获取真实数据（BTC/USDT, 1h, 365天）
4. ✓ 训练 ML 模型（Random Forest + Gradient Boosting）
5. ✓ 保存模型文件

**验证**:
```bash
# 检查数据
ls -lh python/data/historical/BTCUSDT_1h_365d_okx.csv

# 检查模型
ls -lh python/models/btcusdt_rf_real/model.pkl

# 查看性能
cat python/models/btcusdt_rf_real/metadata.json
```

---

### 🔄 Part 3: 数据同步（服务器 → 本地）

**方法 A: SCP**
```bash
# 下载数据
scp user@server:/path/to/TTQuant/python/data/historical/*.csv \
    ./python/data/historical/

# 下载模型
scp -r user@server:/path/to/TTQuant/python/models/btcusdt_*_real \
    ./python/models/
```

**方法 B: Git**
```bash
# 服务器上提交
git add python/models/ python/data/
git commit -m "Add trained models and data"
git push

# 本地拉取
git pull
```

---

### 🎯 Part 4: 完整系统启动

**在服务器上**:
```bash
# 1. 配置环境变量
cat > .env.test << EOF
DB_PASSWORD=your_password
GRAFANA_PASSWORD=your_password
OKX_API_KEY=your_key
OKX_API_SECRET=your_secret
OKX_PASSPHRASE=your_passphrase
EOF

# 2. 启动服务
bash scripts/deploy_test.sh

# 3. 检查状态
docker-compose -f docker-compose.test.yml ps

# 4. 查看日志
docker-compose -f docker-compose.test.yml logs -f
```

**开放端口**（如需远程访问）:
```bash
sudo ufw allow 3000  # Grafana
sudo ufw allow 9090  # Prometheus
sudo ufw allow 8001  # Risk Monitor
```

**或使用 SSH 隧道**:
```bash
ssh -L 3000:localhost:3000 \
    -L 9090:localhost:9090 \
    -L 8001:localhost:8001 \
    user@server
```

---

## 🛠️ 常用命令

### Docker 管理
```bash
# 查看日志
docker-compose -f docker-compose.test.yml logs -f [service]

# 重启服务
docker-compose -f docker-compose.test.yml restart [service]

# 停止服务
docker-compose -f docker-compose.test.yml down

# 重新构建
docker-compose -f docker-compose.test.yml build --no-cache
```

### 数据库操作
```bash
# 连接数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_test

# 备份数据库
docker exec ttquant-timescaledb pg_dump -U ttquant ttquant_test > backup.sql

# 恢复数据库
docker exec -i ttquant-timescaledb psql -U ttquant -d ttquant_test < backup.sql
```

### 监控检查
```bash
# Prometheus 指标
curl http://localhost:8001/metrics

# 服务健康检查
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    TTQuant 系统                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Grafana    │  │  Prometheus  │  │ TimescaleDB  │ │
│  │   :3000      │  │    :9090     │  │    :5432     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                            │                            │
│  ┌──────────────┐  ┌──────────────┐                   │
│  │Strategy Engine│  │Risk Monitor │                   │
│  │              │  │    :8001     │                   │
│  └──────────────┘  └──────────────┘                   │
│         │                  │                            │
│         └──────────────────┘                            │
│                    │                                    │
│              ┌─────┴─────┐                             │
│              │  OKX API  │                             │
│              └───────────┘                             │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 当前状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| 本地 Docker 配置 | ✅ 完成 | 所有配置文件已创建 |
| 服务器部署脚本 | ✅ 完成 | 自动化脚本已就绪 |
| 真实数据获取 | ⏳ 待执行 | 需在服务器上运行 |
| ML 模型训练 | ⏳ 待执行 | 需在服务器上运行 |
| 完整系统部署 | ⏳ 待执行 | 模型训练后启动 |

---

## 📚 详细文档

完整指南: `docs/HYBRID_DEPLOYMENT_GUIDE.md`

包含:
- 详细部署步骤
- 故障排查指南
- 性能优化建议
- 监控和维护方法

---

## 🚦 下一步行动

### 立即执行（服务器上）
```bash
# 1. 克隆代码
git clone https://github.com/nullma/TTQuant.git
cd TTQuant

# 2. 运行部署脚本
bash scripts/server_deploy.sh

# 3. 验证结果
ls python/models/btcusdt_rf_real/
cat python/models/btcusdt_rf_real/metadata.json
```

### 后续步骤
1. 启动完整系统
2. 运行纸面交易测试
3. 监控系统稳定性
4. 优化策略参数

---

**最后更新**: 2026-02-12
**版本**: v1.0
**状态**: ✅ 就绪部署
