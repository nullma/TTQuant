# EC2 部署检查清单

使用此清单确保 EC2 部署的每个步骤都正确完成。

---

## 📋 部署前准备

### AWS EC2 实例
- [ ] 已创建 EC2 实例
  - [ ] 区域：香港 (ap-east-1) 或其他亚洲区域
  - [ ] 实例类型：t3.medium 或更高 (2 vCPU, 4GB RAM)
  - [ ] 操作系统：Ubuntu 22.04 LTS 或 24.04 LTS
  - [ ] 存储：至少 20GB EBS 卷

### 安全组配置
- [ ] 端口 22 (SSH) 已开放
  - [ ] 仅限您的 IP 地址访问
- [ ] 端口 3000 (Grafana) 已开放
  - [ ] 仅限您的 IP 地址访问
- [ ] 端口 9090 (Prometheus) 已开放
  - [ ] 仅限您的 IP 地址访问
- [ ] （可选）端口 5555-5560 (ZMQ) 已开放
  - [ ] 仅限内部网络访问
- [ ] （可选）端口 8080-8083 (指标端点) 已开放
  - [ ] 仅限您的 IP 地址访问

### SSH 访问
- [ ] SSH 密钥已下载并保存
- [ ] SSH 密钥权限正确 (`chmod 400 your-key.pem`)
- [ ] 可以成功连接到 EC2
  ```bash
  ssh -i your-key.pem ubuntu@<your-ec2-ip>
  ```

### 本地环境
- [ ] Git 已安装
- [ ] 代码已提交到 Git 仓库
- [ ] 可以访问 Git 仓库（GitHub/GitLab）

---

## 🚀 部署步骤

### 步骤 1: 初始化 EC2 环境
- [ ] 已连接到 EC2
  ```bash
  ssh -i your-key.pem ubuntu@<your-ec2-ip>
  ```
- [ ] 已运行初始化脚本
  ```bash
  bash deploy/ec2-setup.sh
  ```
- [ ] 脚本执行成功（无错误）
- [ ] 已重新登录 EC2
  ```bash
  exit
  ssh -i your-key.pem ubuntu@<your-ec2-ip>
  ```
- [ ] Docker 可以正常使用
  ```bash
  docker ps  # 应该不报错
  ```

### 步骤 2: 克隆代码
- [ ] 已克隆代码仓库
  ```bash
  git clone <your-repo-url> TTQuant
  cd TTQuant
  ```
- [ ] 代码完整（检查关键文件）
  ```bash
  ls -la deploy/
  ls -la docker/
  ls -la rust/
  ```

### 步骤 3: 部署系统
- [ ] 已运行部署脚本
  ```bash
  bash deploy/ec2-deploy.sh
  ```
- [ ] `.env` 文件已创建
  ```bash
  ls -la .env
  ```
- [ ] 已记录数据库密码和 Grafana 密码
  - 数据库密码: _______________
  - Grafana 密码: _______________
- [ ] Docker 镜像构建成功
- [ ] 所有服务已启动

### 步骤 4: 验证部署
- [ ] 已运行验证脚本
  ```bash
  bash deploy/verify-okx.sh
  ```
- [ ] 验证脚本通过（显示 "✅ 验证完成！OKX 连接正常"）

---

## ✅ 部署验证

### 服务状态检查
- [ ] 所有 Docker 容器运行正常
  ```bash
  cd docker
  docker compose ps
  ```
  期望输出：所有服务状态为 "running"

### OKX 连接检查
- [ ] WebSocket 连接成功
  ```bash
  docker compose logs md-okx | grep "Connected to OKX WebSocket"
  ```
  期望输出：看到连接成功的日志

- [ ] 无 TLS 错误
  ```bash
  docker compose logs md-okx | grep -i "tls error"
  ```
  期望输出：无输出（没有 TLS 错误）

### 数据接收检查
- [ ] 数据库中有最近的数据
  ```bash
  docker exec -it ttquant-timescaledb psql -U ttquant -d ttquant_trading -c \
    "SELECT exchange, symbol, COUNT(*), MAX(time) as last_update
     FROM market_data
     WHERE exchange='okx' AND time > NOW() - INTERVAL '5 minutes'
     GROUP BY exchange, symbol;"
  ```
  期望输出：显示最近 5 分钟的数据

### 监控面板检查
- [ ] Grafana 可以访问
  - URL: `http://<your-ec2-ip>:3000`
  - 用户名: `admin`
  - 密码: （查看 `.env` 文件）
  - [ ] 可以成功登录
  - [ ] 可以看到监控面板

- [ ] Prometheus 可以访问
  - URL: `http://<your-ec2-ip>:9090`
  - [ ] 可以打开页面
  - [ ] 可以查询指标

### 日志检查
- [ ] 无严重错误
  ```bash
  cd docker
  docker compose logs | grep -i "error\|fatal\|panic" | tail -20
  ```
  期望输出：无严重错误（或只有预期的错误）

---

## 🔧 配置检查（可选）

### OKX API 配置（如需真实交易）
- [ ] 已在 OKX 创建 API Key
- [ ] 已更新 `.env` 文件
  ```bash
  vim .env
  ```
  - [ ] `OKX_API_KEY` 已填写
  - [ ] `OKX_SECRET_KEY` 已填写
  - [ ] `OKX_PASSPHRASE` 已填写
  - [ ] `OKX_TESTNET` 设置正确（true/false）
- [ ] 已重启 Gateway 服务
  ```bash
  cd docker
  docker compose restart gateway-okx
  ```

### 同步脚本配置（如需自动同步）
- [ ] 已编辑 `deploy/sync-to-ec2.sh`
  - [ ] `EC2_IP` 已设置
  - [ ] `EC2_KEY` 已设置
  - [ ] `EC2_USER` 已设置
  - [ ] `EC2_PATH` 已设置
- [ ] 已测试同步脚本
  ```bash
  bash deploy/sync-to-ec2.sh
  ```

---

## 📊 性能检查

### 系统资源
- [ ] CPU 使用率正常（< 80%）
  ```bash
  htop
  ```
- [ ] 内存使用正常（< 80%）
  ```bash
  free -h
  ```
- [ ] 磁盘空间充足（> 5GB 可用）
  ```bash
  df -h
  ```

### 网络连接
- [ ] 可以访问 OKX
  ```bash
  curl -I https://www.okx.com
  ```
  期望输出：HTTP 200 或 301

- [ ] DNS 解析正常
  ```bash
  nslookup ws.okx.com
  ```
  期望输出：返回 IP 地址

---

## 🐛 故障排查

如果遇到问题，按以下顺序检查：

### 问题 1: OKX 连接失败
- [ ] 查看详细日志
  ```bash
  cd docker
  docker compose logs md-okx | grep -i "error\|tls"
  ```
- [ ] 重新构建镜像
  ```bash
  docker compose down
  docker compose build --no-cache md-okx
  docker compose up -d md-okx
  ```
- [ ] 再次验证
  ```bash
  cd ..
  bash deploy/verify-okx.sh
  ```

### 问题 2: 服务无法启动
- [ ] 查看所有服务日志
  ```bash
  cd docker
  docker compose logs
  ```
- [ ] 检查端口占用
  ```bash
  sudo netstat -tulpn | grep -E "5555|5556|5557|5558|5559|5560|3000|9090"
  ```
- [ ] 检查磁盘空间
  ```bash
  df -h
  ```

### 问题 3: 数据库连接失败
- [ ] 检查数据库状态
  ```bash
  cd docker
  docker compose ps timescaledb
  docker compose logs timescaledb
  ```
- [ ] 重启数据库
  ```bash
  docker compose restart timescaledb
  ```

---

## 📝 部署后任务

### 立即执行
- [ ] 保存 `.env` 文件中的密码（安全存储）
- [ ] 配置 Grafana 监控面板
- [ ] 设置 Prometheus 告警规则
- [ ] 测试数据接收和存储

### 定期执行
- [ ] 每周备份数据库
  ```bash
  docker exec ttquant-timescaledb pg_dump -U ttquant ttquant_trading > backup_$(date +%Y%m%d).sql
  ```
- [ ] 每月更新系统
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
- [ ] 监控磁盘使用
  ```bash
  df -h
  ```
- [ ] 清理 Docker 资源
  ```bash
  docker system prune -a
  ```

---

## 🎯 成功标准

部署成功的标志：

✅ **所有检查项都已完成**
✅ **`verify-okx.sh` 脚本通过**
✅ **Grafana 和 Prometheus 可以访问**
✅ **数据持续写入数据库**
✅ **日志中无严重错误**
✅ **系统资源使用正常**

---

## 📞 获取帮助

如果遇到问题：

1. 查看 [deploy/README.md](README.md) 的故障排查部分
2. 查看 [deploy/QUICKSTART.md](QUICKSTART.md) 的常见问题
3. 导出日志并分析
   ```bash
   cd docker
   docker compose logs > logs_$(date +%Y%m%d_%H%M%S).txt
   ```

---

**部署日期**: _______________

**部署人员**: _______________

**EC2 IP**: _______________

**备注**: _______________

---

祝部署顺利！🚀
