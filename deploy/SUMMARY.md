# EC2 部署方案 - 完成总结

## ✅ 已创建的文件

### 📁 deploy/ 目录

| 文件 | 类型 | 用途 |
|------|------|------|
| `ec2-setup.sh` | Shell 脚本 | EC2 环境初始化（安装 Docker 等） |
| `ec2-deploy.sh` | Shell 脚本 | 部署/更新 TTQuant 系统 |
| `verify-okx.sh` | Shell 脚本 | 验证 OKX 连接状态 |
| `sync-to-ec2.sh` | Shell 脚本 | 从本地同步代码到 EC2 |
| `sync-to-ec2.bat` | Windows 批处理 | Windows 版本的同步脚本 |
| `README.md` | 文档 | 完整的部署指南 |
| `QUICKSTART.md` | 文档 | 5 分钟快速开始 |
| `INDEX.md` | 文档 | 文件索引和说明 |
| `SUMMARY.md` | 文档 | 本文件 |

---

## 🎯 使用场景

### 场景 1: 首次在 EC2 上部署

**在 EC2 上执行**:
```bash
# 1. 连接到 EC2
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 2. 下载初始化脚本
curl -O https://raw.githubusercontent.com/your-repo/TTQuant/main/deploy/ec2-setup.sh

# 3. 运行初始化
bash ec2-setup.sh

# 4. 重新登录
exit
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 5. 克隆代码
git clone <your-repo-url> TTQuant
cd TTQuant

# 6. 部署系统
bash deploy/ec2-deploy.sh

# 7. 验证
bash deploy/verify-okx.sh
```

**预计时间**: 10-15 分钟

---

### 场景 2: 本地开发 + EC2 部署（推荐工作流）

#### 在本地 Windows 开发
```bash
# 1. 修改代码
cd C:\Users\11915\Desktop\TTQuant
# ... 编辑代码 ...

# 2. 测试编译（可选）
cd docker
docker compose build md-okx

# 3. 提交代码
git add .
git commit -m "feat: 添加新功能"
git push origin main
```

#### 同步到 EC2 并部署

**方式 A: 使用自动同步脚本（推荐）**
```bash
# 在 Windows 上双击运行
deploy\sync-to-ec2.bat

# 或在 Git Bash 中运行
bash deploy/sync-to-ec2.sh
```

**方式 B: 手动在 EC2 上更新**
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

### 场景 3: 排查 OKX 连接问题

```bash
# 1. SSH 到 EC2
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 2. 运行验证脚本
cd TTQuant
bash deploy/verify-okx.sh

# 3. 如果失败，查看详细日志
cd docker
docker compose logs md-okx | grep -i "error\|tls"

# 4. 重新构建并启动
docker compose down
docker compose build --no-cache md-okx
docker compose up -d md-okx

# 5. 再次验证
cd ..
bash deploy/verify-okx.sh
```

---

## 📋 部署前检查清单

### EC2 实例要求
- [ ] 区域：香港 (ap-east-1) 或其他亚洲区域
- [ ] 实例类型：t3.medium 或更高 (2 vCPU, 4GB RAM)
- [ ] 操作系统：Ubuntu 22.04 LTS 或 24.04 LTS
- [ ] 存储：至少 20GB EBS 卷
- [ ] SSH 密钥：已下载并保存

### 安全组配置
- [ ] 端口 22 (SSH) - 仅您的 IP
- [ ] 端口 3000 (Grafana) - 仅您的 IP
- [ ] 端口 9090 (Prometheus) - 仅您的 IP
- [ ] 端口 5555-5560 (ZMQ) - 可选，内部使用
- [ ] 端口 8080-8083 (指标) - 可选，仅您的 IP

### 本地环境
- [ ] Git 已安装
- [ ] Git Bash 已安装（Windows）
- [ ] SSH 密钥可访问
- [ ] 代码已提交到 Git 仓库

---

## 🔧 配置同步脚本

如果您想使用 `sync-to-ec2.sh` 自动同步，需要先配置：

### 1. 编辑脚本
```bash
vim deploy/sync-to-ec2.sh
```

### 2. 修改配置
```bash
# 修改这些变量为您的实际值
EC2_IP="your-ec2-ip"              # 改为您的 EC2 IP
EC2_USER="ubuntu"                  # 通常是 ubuntu
EC2_KEY="path/to/your-key.pem"    # 改为您的密钥路径
EC2_PATH="/home/ubuntu/TTQuant"   # EC2 上的项目路径
```

### 3. 示例配置
```bash
EC2_IP="18.162.123.45"
EC2_USER="ubuntu"
EC2_KEY="/c/Users/11915/.ssh/my-ec2-key.pem"
EC2_PATH="/home/ubuntu/TTQuant"
```

### 4. 测试运行
```bash
bash deploy/sync-to-ec2.sh
```

---

## 📊 验证部署成功

### 1. 检查服务状态
```bash
cd TTQuant/docker
docker compose ps
```

**期望输出**: 所有服务状态为 "running"

### 2. 检查 OKX 连接
```bash
cd TTQuant
bash deploy/verify-okx.sh
```

**期望输出**: "✅ 验证完成！OKX 连接正常"

### 3. 检查数据库
```bash
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
  "SELECT exchange, symbol, COUNT(*), MAX(time) as last_update
   FROM market_data
   WHERE exchange='okx' AND time > NOW() - INTERVAL '5 minutes'
   GROUP BY exchange, symbol;"
```

**期望输出**: 显示最近 5 分钟的数据

### 4. 访问 Grafana
```
http://<your-ec2-ip>:3000
```

**期望结果**: 可以登录并看到监控面板

---

## 🎉 成功标准

部署成功后，您应该看到：

✅ **服务运行正常**
```bash
$ docker compose ps
NAME                    STATUS
ttquant-timescaledb     Up (healthy)
ttquant-md-okx          Up
ttquant-gateway-okx     Up
ttquant-prometheus      Up
ttquant-grafana         Up
```

✅ **OKX 连接成功**
```bash
$ docker compose logs md-okx | grep "Connected"
Connected to OKX WebSocket
```

✅ **数据持续接收**
```bash
$ bash deploy/verify-okx.sh
✅ 验证完成！OKX 连接正常
```

✅ **监控面板可访问**
- Grafana: http://<your-ec2-ip>:3000 ✅
- Prometheus: http://<your-ec2-ip>:9090 ✅

---

## 🐛 常见问题

### Q1: OKX 连接失败，显示 TLS 错误
**A**: 这正是我们部署到 EC2 要解决的问题。在 EC2 上应该不会出现此问题。如果仍然失败：
```bash
# 更新 CA 证书
docker compose down
docker compose build --no-cache md-okx
docker compose up -d md-okx
```

### Q2: 服务无法启动，提示端口被占用
**A**: 检查端口占用并停止冲突的服务：
```bash
sudo netstat -tulpn | grep <port>
sudo kill <pid>
```

### Q3: 数据库连接失败
**A**: 检查数据库状态：
```bash
docker compose ps timescaledb
docker compose logs timescaledb
docker compose restart timescaledb
```

### Q4: 磁盘空间不足
**A**: 清理 Docker 资源：
```bash
docker system prune -a
df -h  # 检查磁盘使用
```

### Q5: 无法访问 Grafana
**A**: 检查安全组配置：
- 确保端口 3000 对您的 IP 开放
- 检查防火墙设置
- 确认服务正在运行：`docker compose ps grafana`

---

## 📞 获取更多帮助

### 查看详细文档
```bash
cd TTQuant/deploy
cat README.md        # 完整指南
cat QUICKSTART.md    # 快速开始
cat INDEX.md         # 文件索引
```

### 查看日志
```bash
cd TTQuant/docker

# 所有服务日志
docker compose logs

# 特定服务日志
docker compose logs -f md-okx
docker compose logs -f gateway-okx
docker compose logs -f timescaledb
```

### 导出日志
```bash
cd TTQuant/docker
docker compose logs > logs_$(date +%Y%m%d_%H%M%S).txt
```

---

## 💡 最佳实践

### 1. 定期备份数据库
```bash
# 创建备份
docker exec ttquant-timescaledb pg_dump -U ttquant ttquant_trading > backup_$(date +%Y%m%d).sql

# 恢复备份
cat backup_20240101.sql | docker exec -i ttquant-timescaledb psql -U ttquant -d ttquant_trading
```

### 2. 监控系统资源
```bash
# 查看系统资源
htop

# 查看磁盘使用
df -h

# 查看 Docker 资源
docker stats
```

### 3. 定期更新系统
```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新 Docker 镜像
cd TTQuant/docker
docker compose pull
docker compose up -d
```

### 4. 配置告警
编辑 `monitoring/alertmanager.yml` 配置 Slack/Email 告警

---

## 🔗 相关资源

- **OKX API 文档**: https://www.okx.com/docs-v5/en/
- **Docker 文档**: https://docs.docker.com/
- **TimescaleDB 文档**: https://docs.timescale.com/
- **Grafana 文档**: https://grafana.com/docs/

---

## 📈 下一步

部署成功后，您可以：

1. **配置 OKX API 凭证**（如果要真实交易）
   - 编辑 `.env` 文件
   - 添加 `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_PASSPHRASE`
   - 重启服务：`docker compose restart gateway-okx`

2. **开发和测试策略**
   - 在本地开发策略
   - 使用 `sync-to-ec2.sh` 同步到 EC2
   - 在 EC2 上运行实盘测试

3. **配置监控告警**
   - 设置 Prometheus 告警规则
   - 配置 Slack/Email 通知
   - 监控系统健康状态

4. **优化性能**
   - 调整数据库参数
   - 配置数据保留策略
   - 优化日志级别

---

**部署完成时间**: 2024-01-01

**预计成本**: t3.medium 实例约 $0.05/小时 (~$36/月)

**维护建议**: 每周检查一次系统状态，每月备份一次数据库

---

🎉 **恭喜！您已经完成了 TTQuant 系统的 EC2 部署方案准备工作！**

现在您可以开始在 EC2 上部署系统，彻底解决本地 Windows 环境的 TLS 连接问题。
