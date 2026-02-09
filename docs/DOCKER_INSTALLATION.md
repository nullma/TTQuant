# Docker Desktop 安装指南（Windows）

## 📋 安装前检查

### 1. 检查 Windows 版本

```powershell
# 在 PowerShell 中运行
winver
```

**要求**：
- Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041+)
- 或 Windows 11 64-bit

### 2. 检查虚拟化是否启用

```powershell
# 在 PowerShell 中运行
systeminfo
```

查找 "Hyper-V Requirements" 部分，确保显示：
```
Hyper-V Requirements:     A hypervisor has been detected.
```

如果未启用，需要在 BIOS 中启用 VT-x/AMD-V。

## 📥 下载和安装

### 方法 1: 官网下载（推荐）

1. 访问：https://www.docker.com/products/docker-desktop/
2. 点击 "Download for Windows"
3. 下载 `Docker Desktop Installer.exe`

### 方法 2: 直接下载链接

```
https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe
```

### 安装步骤

1. **运行安装程序**
   - 双击 `Docker Desktop Installer.exe`
   - 如果提示 UAC，点击"是"

2. **配置选项**
   - ✅ 勾选 "Use WSL 2 instead of Hyper-V"（推荐）
   - ✅ 勾选 "Add shortcut to desktop"

3. **等待安装**
   - 安装过程需要 5-10 分钟
   - 可能需要重启电脑

4. **重启电脑**
   - 安装完成后，重启 Windows

## 🚀 首次启动

### 1. 启动 Docker Desktop

- 从桌面或开始菜单启动 "Docker Desktop"
- 首次启动需要 2-3 分钟初始化

### 2. 接受服务条款

- 阅读并接受 Docker 服务条款

### 3. 可选：跳过登录

- 可以点击 "Skip" 跳过 Docker Hub 登录
- 本地使用不需要登录

## ✅ 验证安装

### 1. 检查 Docker 版本

打开 Git Bash 或 PowerShell：

```bash
docker --version
```

**预期输出**：
```
Docker version 24.0.x, build xxxxx
```

### 2. 检查 Docker Compose

```bash
docker compose version
```

**预期输出**：
```
Docker Compose version v2.x.x
```

### 3. 运行测试容器

```bash
docker run hello-world
```

**预期输出**：
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

## 🔧 常见问题

### 问题 1: WSL 2 未安装

**错误信息**：
```
WSL 2 installation is incomplete
```

**解决方案**：

1. 以管理员身份打开 PowerShell：

```powershell
# 启用 WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 启用虚拟机平台
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

2. 重启电脑

3. 下载并安装 WSL 2 内核更新：
   ```
   https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
   ```

4. 设置 WSL 2 为默认版本：
   ```powershell
   wsl --set-default-version 2
   ```

### 问题 2: 虚拟化未启用

**错误信息**：
```
Hardware assisted virtualization and data execution protection must be enabled in the BIOS
```

**解决方案**：

1. 重启电脑，进入 BIOS（通常按 F2, F10, Del 键）
2. 找到虚拟化选项：
   - Intel: "Intel VT-x" 或 "Virtualization Technology"
   - AMD: "AMD-V" 或 "SVM Mode"
3. 启用虚拟化
4. 保存并退出 BIOS

### 问题 3: Docker Desktop 无法启动

**解决方案**：

1. 完全退出 Docker Desktop（右键托盘图标 → Quit）
2. 以管理员身份运行 Docker Desktop
3. 如果仍然失败，重置 Docker Desktop：
   - 设置 → Troubleshoot → Reset to factory defaults

### 问题 4: 端口冲突

**错误信息**：
```
Port 5432 is already in use
```

**解决方案**：

1. 检查占用端口的进程：
   ```powershell
   netstat -ano | findstr :5432
   ```

2. 停止占用端口的服务，或修改 docker-compose.yml 中的端口映射

## ⚙️ Docker Desktop 配置

### 推荐设置

1. **Resources → Advanced**
   - CPUs: 4（或更多）
   - Memory: 8 GB（或更多）
   - Swap: 2 GB
   - Disk image size: 60 GB

2. **General**
   - ✅ Start Docker Desktop when you log in
   - ✅ Use Docker Compose V2

3. **Docker Engine**（保持默认即可）

## 🎯 安装完成后

### 测试 TTQuant 系统

```bash
# 进入项目目录
cd /c/Users/11915/Desktop/TTQuant

# 构建镜像
make build

# 启动服务
make up

# 查看服务状态
make ps

# 查看行情日志
make logs-md

# 测试网关
make test-gateway
```

## 📚 参考资源

- Docker Desktop 官方文档：https://docs.docker.com/desktop/install/windows-install/
- WSL 2 安装指南：https://docs.microsoft.com/en-us/windows/wsl/install
- Docker 入门教程：https://docs.docker.com/get-started/

## 💡 提示

1. **首次构建会比较慢**
   - Rust 编译需要 10-15 分钟
   - 下载依赖需要时间
   - 后续构建会使用缓存，速度会快很多

2. **磁盘空间**
   - Docker 镜像会占用 5-10 GB 空间
   - 确保 C 盘有足够空间

3. **网络问题**
   - 如果下载慢，可以配置 Docker 镜像加速器
   - 阿里云、腾讯云都提供免费的镜像加速服务

---

**安装完成后，请运行验证命令确认 Docker 正常工作！**
