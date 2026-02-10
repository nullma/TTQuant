# Clash Verge 配置指南 - 允许 Docker 使用代理

## 问题
Docker 容器无法使用 Clash 代理，因为 Clash 只监听 127.0.0.1（本地），不允许局域网连接。

## 解决方案

### 步骤 1：在 Clash Verge GUI 中开启"允许局域网连接"

**重要：必须在 GUI 中设置，修改配置文件会被覆盖！**

1. **打开 Clash Verge**

2. **点击左侧 "设置" 图标** ⚙️

3. **找到 "Clash 内核" 或 "Clash Core" 部分**

4. **找到 "允许局域网连接" (Allow LAN) 选项**
   - 可能在 "网络设置" 或 "Network Settings" 下
   - 或者在 "高级设置" 或 "Advanced" 下

5. **开启此选项** ✅

6. **点击 "保存" 或 "应用"**

7. **重启 Clash Verge**
   - 右键托盘图标 → 退出
   - 重新启动

### 步骤 2：验证配置

重启后，运行以下命令验证：

```bash
# 检查端口是否监听所有接口
netstat -ano | findstr "7897"

# 应该看到：
# TCP    0.0.0.0:7897           0.0.0.0:0              LISTENING
# 或
# TCP    [::]:7897              [::]:0                 LISTENING
```

### 步骤 3：测试代理

```bash
# 测试 IP 位置
curl -x http://127.0.0.1:7897 https://ipapi.co/json/

# 应该看到美国 IP
```

## 如果找不到"允许局域网连接"选项

### 方法 A：使用配置文件覆盖

1. 在 Clash Verge 中找到 "配置文件" 或 "Profiles"
2. 点击当前配置的 "编辑" 或 "Edit"
3. 在配置文件顶部添加：
   ```yaml
   allow-lan: true
   bind-address: "*"
   ```
4. 保存并重启

### 方法 B：使用 Clash Verge 的配置覆盖功能

1. 设置 → Clash 字段 → 配置文件补充
2. 添加：
   ```yaml
   allow-lan: true
   ```
3. 保存并重启

## 当前状态

- ✅ Clash 运行正常
- ✅ 代理端口 7897 监听中
- ❌ 只监听 127.0.0.1（需要改为 0.0.0.0）
- ❌ allow-lan: false（需要改为 true）

## 下一步

完成上述配置后：
1. 重启 Docker 的 md-binance 服务
2. 查看日志验证 Binance 连接

---

**配置完成后请告知，我会继续测试。**
