# AWS EC2 安全组配置指南

## 📋 概述

当前 TTQuant 系统已在 EC2 上成功运行，但由于安全组未开放端口，无法从外部访问监控面板。本指南将帮助你在 5 分钟内完成配置。

**EC2 实例信息：**
- IP 地址: `43.198.18.252`
- 区域: 香港 (ap-east-1)

---

## 🎯 需要开放的端口

| 端口 | 服务 | 用途 | 优先级 |
|------|------|------|--------|
| **3000** | Grafana | 监控面板（主要界面） | ⭐⭐⭐ 必需 |
| **9090** | Prometheus | 指标查询和调试 | ⭐⭐ 重要 |
| **8082** | OKX Metrics | OKX 行情服务健康检查 | ⭐ 可选 |
| **8083** | OKX Gateway | OKX 交易网关健康检查 | ⭐ 可选 |

---

## 🚀 配置步骤

### 步骤 1: 登录 AWS 控制台

1. 打开浏览器，访问: https://console.aws.amazon.com/
2. 使用你的 AWS 账号登录
3. 确认右上角区域选择为 **香港 (ap-east-1)**

---

### 步骤 2: 找到 EC2 实例

1. 在顶部搜索框输入 `EC2`，点击进入 EC2 控制台
2. 左侧菜单点击 **实例（Instances）**
3. 在实例列表中找到 IP 为 `43.198.18.252` 的实例
   - 如果实例很多，可以在搜索框输入 `43.198.18.252` 过滤

---

### 步骤 3: 查看安全组

1. **点击该实例**，进入实例详情页
2. 点击 **安全（Security）** 选项卡
3. 在 **安全组（Security groups）** 部分，你会看到一个或多个安全组
   - 例如: `sg-0abc123def456` (launch-wizard-1)
4. **点击安全组名称**（蓝色链接），进入安全组配置页面

---

### 步骤 4: 编辑入站规则

1. 在安全组详情页，点击 **入站规则（Inbound rules）** 选项卡
2. 点击右上角的 **编辑入站规则（Edit inbound rules）** 按钮
3. 你会看到当前已有的规则（通常包含 SSH 22 端口）

---

### 步骤 5: 添加新规则

点击 **添加规则（Add rule）** 按钮，按以下信息添加 4 条规则：

#### 规则 1: Grafana 监控面板
```
类型 (Type):        自定义 TCP (Custom TCP)
端口范围 (Port):     3000
源 (Source):        0.0.0.0/0
描述 (Description): Grafana Dashboard
```

#### 规则 2: Prometheus 指标
```
类型 (Type):        自定义 TCP (Custom TCP)
端口范围 (Port):     9090
源 (Source):        0.0.0.0/0
描述 (Description): Prometheus Metrics
```

#### 规则 3: OKX 行情指标
```
类型 (Type):        自定义 TCP (Custom TCP)
端口范围 (Port):     8082
源 (Source):        0.0.0.0/0
描述 (Description): OKX Market Data Metrics
```

#### 规则 4: OKX 网关指标
```
类型 (Type):        自定义 TCP (Custom TCP)
端口范围 (Port):     8083
源 (Source):        0.0.0.0/0
描述 (Description): OKX Gateway Metrics
```

**安全提示：**
- `0.0.0.0/0` 表示允许所有 IP 访问
- 如果只想从你的 IP 访问，可以选择 **我的 IP (My IP)**
- 生产环境建议限制为特定 IP 范围

---

### 步骤 6: 保存规则

1. 检查所有规则是否正确
2. 点击右下角 **保存规则（Save rules）** 按钮
3. 等待几秒钟，规则会立即生效

---

## ✅ 验证配置

配置完成后，立即测试访问：

### 1. 访问 Grafana
在浏览器打开: http://43.198.18.252:3000

**预期结果：**
- 看到 Grafana 登录页面
- 默认账号: `admin`
- 默认密码: 查看 `.env` 文件中的 `GRAFANA_PASSWORD`

### 2. 访问 Prometheus
在浏览器打开: http://43.198.18.252:9090

**预期结果：**
- 看到 Prometheus 查询界面
- 可以查询指标数据

### 3. 检查 OKX 服务健康
在浏览器打开: http://43.198.18.252:8082/metrics

**预期结果：**
- 看到 Prometheus 格式的指标数据
- 包含 `market_data_` 开头的指标

---

## 🎨 Grafana 首次配置

成功登录 Grafana 后：

### 1. 添加数据源

1. 左侧菜单 → **Configuration** → **Data Sources**
2. 点击 **Add data source**
3. 选择 **Prometheus**
4. 配置：
   ```
   Name: Prometheus
   URL: http://prometheus:9090
   ```
5. 点击 **Save & Test**

### 2. 导入仪表板

1. 左侧菜单 → **Dashboards** → **Import**
2. 输入仪表板 ID: `1860` (Node Exporter Full)
3. 选择数据源: Prometheus
4. 点击 **Import**

---

## 🔒 安全建议

### 生产环境加固

1. **限制 IP 访问**
   ```
   将 0.0.0.0/0 改为你的办公室/家庭 IP
   例如: 123.45.67.89/32
   ```

2. **使用 VPN**
   - 配置 AWS VPN 或第三方 VPN
   - 只允许 VPN 网段访问

3. **启用 HTTPS**
   - 配置 Nginx 反向代理
   - 使用 Let's Encrypt 免费证书

4. **修改默认密码**
   ```bash
   # 在 EC2 上执行
   docker exec -it ttquant-grafana grafana-cli admin reset-admin-password <新密码>
   ```

---

## 🐛 故障排查

### 问题 1: 仍然无法访问

**检查清单：**
- [ ] 确认安全组规则已保存
- [ ] 确认选择了正确的区域
- [ ] 确认实例正在运行（状态为 Running）
- [ ] 尝试清除浏览器缓存或使用无痕模式

**测试命令：**
```bash
# 在本地 PowerShell 执行
curl http://43.198.18.252:3000
```

### 问题 2: 502 Bad Gateway

**原因：** Grafana 容器未正常启动

**解决：**
```bash
# SSH 到 EC2
ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252

# 重启 Grafana
cd TTQuant
docker restart ttquant-grafana

# 查看日志
docker logs ttquant-grafana -f
```

### 问题 3: 忘记 Grafana 密码

**解决：**
```bash
# SSH 到 EC2
ssh -i "C:\Users\11915\Desktop\蓝洞科技\mawentao.pem" ubuntu@43.198.18.252

# 重置密码为 admin123
docker exec -it ttquant-grafana grafana-cli admin reset-admin-password admin123
```

---

## 📞 需要帮助？

如果配置过程中遇到问题：

1. 检查 EC2 实例状态是否为 Running
2. 确认安全组规则已正确保存
3. 查看容器日志: `docker logs ttquant-grafana`
4. 联系 AWS 技术支持

---

## 📚 相关文档

- [AWS 安全组官方文档](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [Grafana 官方文档](https://grafana.com/docs/)
- [TTQuant 部署指南](../deploy/README.md)

---

**配置完成后，你将能够：**
- ✅ 实时查看系统监控数据
- ✅ 分析行情采集性能
- ✅ 监控数据库和服务健康状态
- ✅ 设置告警规则

祝配置顺利！🎉
