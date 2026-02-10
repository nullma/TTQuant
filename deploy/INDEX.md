# EC2 部署文件说明

本目录包含在 AWS EC2 上部署 TTQuant 系统的所有脚本和文档。

## 📁 文件列表

### 脚本文件

| 文件 | 用途 | 何时使用 |
|------|------|----------|
| `ec2-setup.sh` | 初始化 EC2 环境 | 首次部署时运行一次 |
| `ec2-deploy.sh` | 部署/更新系统 | 每次更新代码后运行 |
| `verify-okx.sh` | 验证 OKX 连接 | 部署后验证，或排查问题时 |

### 文档文件

| 文件 | 内容 | 适合人群 |
|------|------|----------|
| `QUICKSTART.md` | 5 分钟快速部署 | 想快速开始的用户 |
| `README.md` | 完整部署指南 | 需要详细说明的用户 |
| `INDEX.md` | 本文件 | 了解文件结构 |

---

## 🚀 使用流程

### 首次部署
```bash
# 1. 连接到 EC2
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 2. 初始化环境（只需运行一次）
bash ec2-setup.sh

# 3. 重新登录
exit
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# 4. 克隆代码
git clone <your-repo-url> TTQuant
cd TTQuant

# 5. 部署系统
bash deploy/ec2-deploy.sh

# 6. 验证部署
bash deploy/verify-okx.sh
```

### 更新代码
```bash
# 1. 拉取最新代码
cd TTQuant
git pull

# 2. 重新部署
bash deploy/ec2-deploy.sh

# 3. 验证
bash deploy/verify-okx.sh
```

---

## 📖 推荐阅读顺序

1. **新手**: 先看 `QUICKSTART.md`，快速部署
2. **进阶**: 再看 `README.md`，了解详细配置
3. **问题**: 查看 `README.md` 的故障排查部分

---

## 🔧 脚本详解

### ec2-setup.sh
**功能**:
- 更新系统包
- 安装 Docker 和 Docker Compose
- 安装 Git 和其他工具
- 配置 Docker 权限

**运行时间**: 约 3-5 分钟

**注意**: 运行后需要重新登录以使 Docker 权限生效

### ec2-deploy.sh
**功能**:
- 创建/更新 `.env` 文件
- 停止旧服务
- 拉取最新代码
- 构建 Docker 镜像
- 启动所有服务
- 验证服务状态

**运行时间**: 约 5-10 分钟（首次构建较慢）

**幂等性**: 可以重复运行，不会破坏现有数据

### verify-okx.sh
**功能**:
- 检查服务状态
- 验证 WebSocket 连接
- 检查数据接收
- 显示数据详情
- 检查健康指标

**运行时间**: 约 10 秒

**输出**: 详细的验证报告

---

## 🎯 常见场景

### 场景 1: 全新部署
```bash
bash ec2-setup.sh      # 初始化环境
# 重新登录
git clone <repo> TTQuant
cd TTQuant
bash deploy/ec2-deploy.sh  # 部署系统
bash deploy/verify-okx.sh  # 验证
```

### 场景 2: 更新代码
```bash
cd TTQuant
git pull
bash deploy/ec2-deploy.sh
bash deploy/verify-okx.sh
```

### 场景 3: 排查问题
```bash
bash deploy/verify-okx.sh  # 查看详细状态
cd docker
docker compose logs md-okx  # 查看日志
```

### 场景 4: 重新部署
```bash
cd TTQuant/docker
docker compose down  # 停止服务
cd ..
bash deploy/ec2-deploy.sh  # 重新部署
```

---

## ⚠️ 注意事项

1. **首次部署**: 必须先运行 `ec2-setup.sh`
2. **重新登录**: 安装 Docker 后必须重新登录
3. **网络要求**: 需要稳定的网络连接
4. **磁盘空间**: 确保至少有 10GB 可用空间
5. **权限问题**: 不要使用 root 用户运行脚本

---

## 🆘 获取帮助

### 查看脚本帮助
```bash
# 查看脚本内容
cat deploy/ec2-setup.sh
cat deploy/ec2-deploy.sh
cat deploy/verify-okx.sh
```

### 查看详细文档
```bash
# 在 EC2 上查看
cd TTQuant/deploy
cat README.md
cat QUICKSTART.md
```

### 常见问题
参考 `README.md` 的 "🐛 故障排查" 部分

---

## 📊 部署检查清单

部署前:
- [ ] EC2 实例已创建（Ubuntu 22.04/24.04）
- [ ] 安全组已配置（端口 22, 3000, 9090）
- [ ] SSH 密钥可用
- [ ] 磁盘空间充足（>20GB）

部署中:
- [ ] `ec2-setup.sh` 运行成功
- [ ] 已重新登录
- [ ] 代码已克隆
- [ ] `ec2-deploy.sh` 运行成功

部署后:
- [ ] `verify-okx.sh` 通过
- [ ] Grafana 可访问
- [ ] 数据库有数据
- [ ] 日志无错误

---

**最后更新**: 2024-01-01
