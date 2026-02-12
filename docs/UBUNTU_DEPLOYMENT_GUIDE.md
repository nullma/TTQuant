# TTQuant Ubuntu 服务器部署指南

## 系统要求

- **操作系统**: Ubuntu 20.04+ / 22.04+ (推荐)
- **内存**: 最少 4GB，推荐 8GB
- **磁盘**: 最少 20GB 可用空间
- **网络**: 可访问 OKX API
- **权限**: sudo 权限（用于安装系统包）

---

## 快速部署（一键脚本）

### 步骤 1: 克隆代码

```bash
# 使用 HTTPS
git clone https://github.com/nullma/TTQuant.git
cd TTQuant

# 或使用 SSH（如果配置了 SSH key）
git clone git@github.com:nullma/TTQuant.git
cd TTQuant
```

### 步骤 2: 运行部署脚本

```bash
# 添加执行权限
chmod +x scripts/server_deploy.sh

# 运行脚本
bash scripts/server_deploy.sh
```

**脚本会自动**:
1. ✅ 检查系统环境（Ubuntu 版本）
2. ✅ 检查 Python 环境
3. ✅ 安装系统依赖（python3-dev, build-essential, libpq-dev）
4. ✅ 安装 Python 依赖（numpy, pandas, scikit-learn, ccxt 等）
5. ✅ 从 OKX 获取真实历史数据（BTC/USDT, 1h, 365天）
6. ✅ 训练 ML 模型（Random Forest + Gradient Boosting）

### 预期输出

```
========================================================================
TTQuant 服务器部署 - 真实数据获取和模型训练
========================================================================

[1/6] 检查系统环境...
✓ 操作系统: Ubuntu 22.04.3 LTS

[2/6] 检查 Python 环境...
✓ Python 3.11.0

[3/6] 检查系统依赖...
✓ 系统依赖已安装

[4/6] 安装 Python 依赖...
✓ 依赖安装完成

[5/6] 从 OKX 获取真实历史数据...
交易对: BTC/USDT
周期: 1小时
天数: 365天

✓ 数据获取成功

[6/6] 训练 ML 模型...
✓ 模型训练完成

========================================================================
部署完成！
========================================================================
```

---

## 手动部署（分步骤）

如果自动脚本遇到问题，可以手动执行：

### 1. 安装系统依赖

```bash
# 更新包列表
sudo apt-get update

# 安装 Python 和编译工具
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    libpq-dev \
    git

# 验证安装
python3 --version
pip3 --version
```

### 2. 安装 Python 依赖

```bash
cd TTQuant/python

# 升级 pip
pip3 install --upgrade pip

# 安装依赖
pip3 install -r requirements.txt

# 验证关键包
python3 -c "import numpy, pandas, sklearn, ccxt; print('All packages OK')"
```

### 3. 获取历史数据

```bash
cd TTQuant/python

# 从 OKX 获取数据
python3 data/fetch_historical_data.py

# 检查数据文件
ls -lh data/historical/
# 应该看到: BTCUSDT_1h_365d_okx.csv
```

**如果 OKX API 访问失败**，使用模拟数据：
```bash
python3 data/generate_simulated_data.py
```

### 4. 训练 ML 模型

```bash
cd TTQuant/python

# 训练模型
python3 train_ml_with_real_data.py

# 检查模型文件
ls -lh models/btcusdt_rf_real/
# 应该看到: model.pkl, metadata.json

# 查看模型性能
cat models/btcusdt_rf_real/metadata.json
```

---

## Docker 部署（推荐用于生产）

### 1. 安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt-get install -y docker-compose-plugin

# 验证安装
docker --version
docker compose version

# 添加当前用户到 docker 组（避免每次 sudo）
sudo usermod -aG docker $USER
newgrp docker
```

### 2. 配置环境变量

```bash
cd TTQuant

# 创建环境变量文件
cat > .env.test << EOF
# 数据库
DB_PASSWORD=your_secure_password

# Grafana
GRAFANA_PASSWORD=your_grafana_password

# OKX API（可选，纸面交易不需要）
OKX_API_KEY=your_api_key
OKX_API_SECRET=your_api_secret
OKX_PASSPHRASE=your_passphrase
EOF

# 设置权限
chmod 600 .env.test
```

### 3. 启动服务

```bash
# 构建镜像
docker compose -f docker-compose.test.yml build

# 启动所有服务
docker compose -f docker-compose.test.yml up -d

# 查看服务状态
docker compose -f docker-compose.test.yml ps

# 查看日志
docker compose -f docker-compose.test.yml logs -f
```

### 4. 访问服务

**如果在本地服务器**:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- 风险监控: http://localhost:8001/metrics

**如果在远程服务器**，使用 SSH 隧道:
```bash
# 在本地机器上执行
ssh -L 3000:localhost:3000 \
    -L 9090:localhost:9090 \
    -L 8001:localhost:8001 \
    user@your-server-ip

# 然后在本地浏览器访问
# http://localhost:3000
```

**或配置防火墙**:
```bash
# 开放端口（谨慎使用，建议配合安全组）
sudo ufw allow 3000/tcp  # Grafana
sudo ufw allow 9090/tcp  # Prometheus
sudo ufw allow 8001/tcp  # Risk Monitor
sudo ufw enable
```

---

## 验证部署

### 检查数据

```bash
# 查看数据文件
ls -lh python/data/historical/

# 查看数据摘要
head -20 python/data/historical/BTCUSDT_1h_365d_okx.csv
```

### 检查模型

```bash
# 查看模型文件
ls -lh python/models/btcusdt_rf_real/

# 查看模型元数据
cat python/models/btcusdt_rf_real/metadata.json | python3 -m json.tool
```

### 测试模型

```bash
cd python

# 运行快速演示
python3 example_quick_demo.py

# 预期输出：组合优化、归因分析、ML 因子演示
```

---

## 常见问题

### Q1: pip install 很慢

**解决**: 使用国内镜像源
```bash
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: OKX API 连接失败

**原因**: 网络限制或 API 配额

**解决**:
1. 检查网络: `curl -I https://www.okx.com`
2. 使用代理（如果需要）
3. 或使用模拟数据: `python3 data/generate_simulated_data.py`

### Q3: 内存不足

**症状**: 训练时 Killed 或 OOM

**解决**:
```bash
# 检查内存
free -h

# 减少训练数据量（修改 train_ml_with_real_data.py）
# 或增加 swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q4: Docker 构建失败

**症状**: apt-get 报错

**解决**:
```bash
# 清理 Docker 缓存
docker system prune -a

# 重新构建
docker compose -f docker-compose.test.yml build --no-cache
```

### Q5: 端口被占用

**症状**: Address already in use

**解决**:
```bash
# 查看占用端口的进程
sudo netstat -tulpn | grep -E '3000|5432|9090|8001'

# 停止冲突的服务
sudo systemctl stop <service-name>

# 或修改 docker-compose.test.yml 中的端口映射
```

---

## 性能优化

### 1. 数据库优化

```bash
# 连接数据库
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_test

# 创建索引
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp DESC);
CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp DESC);

# 设置 TimescaleDB 参数
ALTER DATABASE ttquant_test SET timescaledb.max_background_workers = 4;
```

### 2. Python 优化

```bash
# 使用 PyPy（可选，某些场景更快）
sudo apt-get install pypy3

# 或使用 Numba 加速
pip3 install numba
```

### 3. 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化网络参数
sudo sysctl -w net.core.somaxconn=1024
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=2048
```

---

## 监控和维护

### 查看日志

```bash
# Docker 服务日志
docker compose -f docker-compose.test.yml logs -f [service]

# 系统日志
journalctl -u docker -f

# Python 应用日志
tail -f python/logs/*.log
```

### 备份

```bash
# 备份数据库
docker exec ttquant-timescaledb pg_dump -U ttquant ttquant_test > backup_$(date +%Y%m%d).sql

# 备份模型
tar -czf models_backup_$(date +%Y%m%d).tar.gz python/models/

# 备份配置
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/ .env.test
```

### 更新代码

```bash
# 拉取最新代码
git pull

# 重启服务
docker compose -f docker-compose.test.yml restart

# 或重新构建
docker compose -f docker-compose.test.yml up -d --build
```

---

## 安全建议

1. **修改默认密码**
   ```bash
   # 修改 .env.test 中的密码
   vim .env.test
   ```

2. **配置防火墙**
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 3000/tcp  # 仅在需要时开放
   ```

3. **使用 HTTPS**
   - 配置 Nginx 反向代理
   - 使用 Let's Encrypt 证书

4. **限制 API 访问**
   - 使用只读 API key
   - 设置 IP 白名单

5. **定期更新**
   ```bash
   sudo apt-get update && sudo apt-get upgrade
   docker compose -f docker-compose.test.yml pull
   ```

---

## 下一步

部署成功后：

1. ✅ 访问 Grafana 配置仪表板
2. ✅ 运行回测验证策略
3. ✅ 启动纸面交易测试
4. ✅ 监控系统稳定性
5. ✅ 优化策略参数

---

**文档版本**: v1.0
**最后更新**: 2026-02-12
**适用系统**: Ubuntu 20.04+
**状态**: ✅ 生产就绪
