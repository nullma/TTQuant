# VPS 部署说明（香港/新加坡等海外服务器）

## 🌏 适用地区

此配置适用于以下地区的 VPS，**无需代理**直接连接币安：
- 🇭🇰 香港
- 🇸🇬 新加坡  
- 🇯🇵 日本
- 🇰🇷 韩国
- 🇹🇼 台湾
- 🇪🇺 欧洲大部分国家

---

## 📋 与本地部署的区别

| 项目 | 本地（国内） | VPS（香港等） |
|------|-------------|--------------|
| 网络访问 | ❌ 无法直连币安 | ✅ 直接访问 |
| 代理需求 | ✅ 必须使用 Clash | ❌ 不需要代理 |
| 稳定性 | ⚠️ 依赖代理 | ✅ 原生连接 |
| 配置复杂度 | 较高 | 简单 |
| 延迟 | 取决于代理 | 极低 |

---

## 🚀 快速部署步骤

### 步骤 1: 上传代码

```bash
# 方法 A: 使用 SCP（在本地执行）
scp -r C:\Users\11915\Desktop\TTQuant root@YOUR_VPS_IP:/root/

# 方法 B: 使用 Git（在 VPS 上执行）
git clone <你的仓库地址> /root/TTQuant
cd /root/TTQuant
```

### 步骤 2: 配置环境变量

```bash
# 在 VPS 上执行
cd /root/TTQuant

# 复制生产环境配置模板
cp .env.production .env

# 编辑配置文件
nano .env
```

填入以下信息：
```bash
# 数据库密码
DB_PASSWORD=your_secure_password_here

# Binance API（如果有）
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=false  # 生产环境改为 false

# OKX API（如果有）
OKX_API_KEY=your_okx_key
OKX_SECRET_KEY=your_okx_secret
OKX_PASSPHRASE=your_okx_passphrase

# Grafana 密码
GRAFANA_PASSWORD=admin123
```

### 步骤 3: 移除代理配置

VPS 上**不需要代理配置**，需要删除或注释掉代理环境变量：

```bash
# 编辑 docker-compose.prod.yml
nano docker/docker-compose.prod.yml

# 找到并删除或注释掉以下行（在所有服务中）：
# HTTP_PROXY: http://xxx
# HTTPS_PROXY: http://xxx
# NO_PROXY: xxx
```

或者运行清理脚本：

```bash
# 创建清理脚本
cat > remove-proxy.sh << 'EOF'
#!/bin/bash
# 移除 docker-compose 中的代理配置

sed -i '/HTTP_PROXY:/d' docker/docker-compose.prod.yml
sed -i '/HTTPS_PROXY:/d' docker/docker-compose.prod.yml
sed -i '/NO_PROXY:/d' docker/docker-compose.prod.yml
sed -i '/# Clash 代理/d' docker/docker-compose.prod.yml

echo "✅ 代理配置已移除"
EOF

chmod +x remove-proxy.sh
./remove-proxy.sh
```

### 步骤 4: 一键部署

```bash
# 执行部署脚本（会自动安装 Docker 等依赖）
bash deploy-vps.sh
```

脚本会自动：
1. ✅ 安装 Docker 和 Docker Compose
2. ✅ 构建所有镜像
3. ✅ 启动所有服务
4. ✅ 配置自动备份
5. ✅ 设置开机自启

### 步骤 5: 验证部署

```bash
# 查看服务状态
docker compose -f docker/docker-compose.prod.yml ps

# 查看 Binance 行情服务日志
docker logs ttquant-md-binance -f --tail 30

# 期待看到
# ✅ INFO WebSocket connected to wss://stream.binance.com:9443/ws
# ✅ INFO Subscribed to btcusdt@trade
# ✅ INFO Received tick data
```

---

## 🔍 监控访问

### 配置防火墙端口

```bash
# 允许 Grafana 端口（仅从你的 IP 访问）
ufw allow from YOUR_LOCAL_IP to any port 3000

# 或允许所有 IP（不推荐）
ufw allow 3000
```

### 访问监控面板

- **Grafana**: `http://YOUR_VPS_IP:3000` (admin/admin123)
- **Prometheus**: `http://YOUR_VPS_IP:9090` (内部访问)

---

## 🛡️ 安全建议

### 1. 更改默认密码

```bash
# 进入 Grafana 后立即更改默认密码
# 访问 http://YOUR_VPS_IP:3000
# 登录后在 Profile → Change Password
```

### 2. 限制端口访问

```bash
# 只允许特定 IP 访问 Grafana
ufw delete allow 3000
ufw allow from YOUR_HOME_IP to any port 3000
```

### 3. 设置 HTTPS（可选）

使用 Let's Encrypt 配置 SSL：
```bash
# 安装 Certbot
apt install certbot

# 获取证书（需要域名）
certbot certonly --standalone -d your-domain.com
```

---

## 📊 性能优化

### 调整资源限制

根据 VPS 配置调整 `docker-compose.prod.yml` 中的资源限制：

```yaml
# 例如：2核4G VPS 可以这样分配
timescaledb:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 2G
```

### 监控资源使用

```bash
# 查看容器资源占用
docker stats

# 查看系统资源
htop
```

---

## 🔄 日常维护

### 查看日志

```bash
# 所有服务
docker compose -f docker/docker-compose.prod.yml logs -f

# 特定服务
docker logs ttquant-md-binance -f
docker logs ttquant-md-okx -f
```

### 备份数据库

```bash
# 手动备份
bash scripts/backup.sh

# 查看备份文件
ls -lh backups/
```

### 更新代码

```bash
cd /root/TTQuant
git pull
docker compose -f docker/docker-compose.prod.yml restart
```

---

## ❓ 常见问题

### Q: VPS 最低配置要求？

**A**: 
- **最低**: 1核2G（仅监控 1-2 个交易对）
- **推荐**: 2核4G（监控 5-10 个交易对 + 策略运行）
- **最佳**: 4核8G（多交易对 + 复杂策略）

### Q: 香港 VPS 推荐服务商？

**A**: 
- 腾讯云香港（国内访问快）
- 阿里云香港
- Vultr 香港
- DigitalOcean 新加坡

### Q: 需要域名吗？

**A**: 
- **不需要** - 可以直接用 IP 访问
- **推荐有** - 方便配置 HTTPS 和记忆

### Q: 币安 API 需要 VPN 吗？

**A**: 
- **香港 VPS**: ❌ 不需要任何代理
- **国内服务器**: ✅ 必须使用代理（不推荐）

---

## 📚 相关文档

- **完整部署指南**: [`docs/PRODUCTION_DEPLOY.md`](PRODUCTION_DEPLOY.md)
- **系统架构说明**: [`PROJECT_SUMMARY.md`](../PROJECT_SUMMARY.md)
- **快速启动**: [`QUICKSTART_OKX.md`](../QUICKSTART_OKX.md)

---

## 🎉 成功标志

部署成功后，你会看到：

```bash
$ docker compose -f docker/docker-compose.prod.yml ps

NAME                    STATUS          PORTS
ttquant-md-binance      Up 5 minutes    0.0.0.0:5555->5555/tcp
ttquant-md-okx          Up 5 minutes    0.0.0.0:5558->5558/tcp
ttquant-gateway-binance Up 5 minutes    0.0.0.0:5556->5556/tcp
ttquant-grafana         Up 5 minutes    0.0.0.0:3000->3000/tcp
...

$ docker logs ttquant-md-binance --tail 5
✅ INFO WebSocket connected
✅ INFO Subscribed to BTC-USDT@ticker
✅ INFO Received tick: 92341.50
```

访问 Grafana 面板，实时行情数据涌入！🚀

---

**最后更新**: 2026-02-10 18:56  
**适用场景**: 香港/新加坡/日本等海外 VPS  
**优势**: 无需代理，原生连接，稳定性最佳
