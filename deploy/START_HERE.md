# 🚀 TTQuant EC2 部署 - 立即开始

## 📦 已为您准备的文件

```
TTQuant/
└── deploy/
    ├── ec2-setup.sh       # EC2 环境初始化脚本
    ├── ec2-deploy.sh      # 部署/更新脚本
    ├── verify-okx.sh      # OKX 连接验证脚本
    ├── sync-to-ec2.sh     # 本地到 EC2 同步脚本
    ├── sync-to-ec2.bat    # Windows 版同步脚本
    ├── README.md          # 完整部署指南
    ├── QUICKSTART.md      # 5 分钟快速开始
    ├── INDEX.md           # 文件索引
    └── SUMMARY.md         # 完成总结
```

---

## ⚡ 3 步快速部署

### 步骤 1: 连接到您的香港 EC2
```bash
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 步骤 2: 初始化环境（首次部署）
```bash
# 如果代码已在 EC2 上
cd TTQuant
bash deploy/ec2-setup.sh

# 重新登录
exit
ssh -i your-key.pem ubuntu@<your-ec2-ip>
```

### 步骤 3: 部署系统
```bash
cd TTQuant
bash deploy/ec2-deploy.sh
bash deploy/verify-okx.sh
```

**完成！** 🎉

---

## 🔄 日常开发工作流

### 在本地 Windows 开发
```bash
# 1. 修改代码
cd C:\Users\11915\Desktop\TTQuant
# ... 编辑代码 ...

# 2. 提交到 Git
git add .
git commit -m "feat: 新功能"
git push
```

### 同步到 EC2（两种方式）

**方式 A: 自动同步（推荐）**
```bash
# 先配置 deploy/sync-to-ec2.sh 中的 EC2_IP 和 EC2_KEY
# 然后双击运行
deploy\sync-to-ec2.bat
```

**方式 B: 手动同步**
```bash
# SSH 到 EC2
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 更新并部署
cd TTQuant
git pull
bash deploy/ec2-deploy.sh
bash deploy/verify-okx.sh
```

---

## 📊 访问监控面板

### Grafana
```
http://<your-ec2-ip>:3000
```
- 用户名: `admin`
- 密码: 查看 `.env` 文件

### Prometheus
```
http://<your-ec2-ip>:9090
```

---

## 🔍 常用命令速查

```bash
# 查看服务状态
cd TTQuant/docker && docker compose ps

# 查看 OKX 日志
docker compose logs -f md-okx

# 验证 OKX 连接
cd .. && bash deploy/verify-okx.sh

# 重启服务
cd docker && docker compose restart md-okx

# 查看数据库数据
docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
  "SELECT * FROM market_data WHERE exchange='okx' ORDER BY time DESC LIMIT 10;"
```

---

## 📚 详细文档

- **快速开始**: `deploy/QUICKSTART.md`
- **完整指南**: `deploy/README.md`
- **文件说明**: `deploy/INDEX.md`
- **完成总结**: `deploy/SUMMARY.md`

---

## ✅ 成功标准

部署成功后，您应该看到：

1. ✅ `verify-okx.sh` 显示 "验证完成！OKX 连接正常"
2. ✅ 日志中有 "Connected to OKX WebSocket"
3. ✅ 数据库中有最近 5 分钟的数据
4. ✅ Grafana 面板可以访问

---

## 🆘 遇到问题？

### TLS 连接失败
```bash
docker compose down
docker compose build --no-cache md-okx
docker compose up -d md-okx
```

### 查看详细日志
```bash
cd TTQuant/docker
docker compose logs md-okx | grep -i "error\|tls"
```

### 查看完整故障排查指南
```bash
cat deploy/README.md  # 查看 "故障排查" 部分
```

---

## 🎯 下一步

1. **首次部署**: 按照上面的 "3 步快速部署" 操作
2. **配置同步**: 编辑 `deploy/sync-to-ec2.sh` 配置您的 EC2 信息
3. **开始开发**: 在本地开发，使用同步脚本部署到 EC2
4. **配置 API**: 如需真实交易，在 `.env` 中配置 OKX API 凭证

---

**预计部署时间**: 10-15 分钟

**预计成本**: t3.medium 约 $0.05/小时 (~$36/月)

**问题反馈**: 查看 `deploy/README.md` 获取详细帮助

---

祝您部署顺利！🚀
