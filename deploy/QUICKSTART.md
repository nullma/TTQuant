# TTQuant EC2 快速部署指南

## 🎯 5 分钟快速部署

### 前提条件
- ✅ 已有 AWS 账号
- ✅ 已创建香港区域的 Ubuntu EC2 实例
- ✅ 已配置安全组（开放端口 22, 3000, 9090）
- ✅ 已有 SSH 密钥

---

## 📝 部署步骤

### 1️⃣ 连接到 EC2
```bash
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 2️⃣ 一键初始化环境
```bash
# 下载并运行初始化脚本
curl -fsSL https://raw.githubusercontent.com/your-repo/TTQuant/main/deploy/ec2-setup.sh | bash

# 重新登录（使 Docker 权限生效）
exit
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 3️⃣ 克隆代码
```bash
git clone https://github.com/your-username/TTQuant.git
cd TTQuant
```

### 4️⃣ 一键部署
```bash
bash deploy/ec2-deploy.sh
```

### 5️⃣ 验证部署
```bash
bash deploy/verify-okx.sh
```

看到 "✅ 验证完成！OKX 连接正常" 即部署成功！

---

## 🌐 访问服务

### Grafana 监控面板
```
http://<your-ec2-ip>:3000
```
- 用户名: `admin`
- 密码: 查看 `.env` 文件中的 `GRAFANA_PASSWORD`

### Prometheus 指标
```
http://<your-ec2-ip>:9090
```

---

## 🔍 常用命令

### 查看服务状态
```bash
cd TTQuant/docker
docker compose ps
```

### 查看 OKX 日志
```bash
docker compose logs -f md-okx
```

### 查看数据库数据
```bash
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
  "SELECT exchange, symbol, COUNT(*), MAX(time) as last_update
   FROM market_data
   WHERE exchange='okx' AND time > NOW() - INTERVAL '5 minutes'
   GROUP BY exchange, symbol;"
```

### 重启服务
```bash
docker compose restart md-okx
```

---

## 🐛 遇到问题？

### OKX 连接失败
```bash
# 查看错误日志
docker compose logs md-okx | grep -i "error\|tls"

# 重新构建并启动
docker compose down
docker compose build --no-cache md-okx
docker compose up -d md-okx
```

### 服务无法启动
```bash
# 查看所有服务日志
docker compose logs

# 检查磁盘空间
df -h

# 清理 Docker 资源
docker system prune -a
```

---

## 📚 详细文档

查看完整文档: [deploy/README.md](README.md)

---

## ✅ 成功标准

- [ ] 所有 Docker 容器状态为 "running"
- [ ] 日志中看到 "Connected to OKX WebSocket"
- [ ] 数据库中有最近 5 分钟的数据
- [ ] Grafana 面板可以访问
- [ ] `verify-okx.sh` 脚本通过

---

**部署时间**: 约 5-10 分钟（取决于网络速度）

**预计成本**: t3.medium 实例约 $0.05/小时 (~$36/月)
