# 🚀 快速导入指南 - 3步完成

## 📋 当前状态
- ❌ 自动加载失败
- ✅ JSON 文件已准备好
- ✅ JSON 已在记事本中打开

---

## ⚡ 最简单方法（推荐）

### 1️⃣ 在 Grafana 中点击

在浏览器的 Grafana 页面中：

```
左侧菜单 ☰  →  Dashboards  →  New  →  Import
```

或直接访问：**http://localhost:3000/dashboard/import**

---

### 2️⃣ 上传文件

1. 点击 **"Upload JSON file"** 按钮

2. 在弹出的文件选择框中粘贴路径（或手动导航）：
   ```
   C:\Users\11915\Desktop\TTQuant\monitoring\dashboards\okx-realtime-dashboard.json
   ```

3. 选择该文件，点击 **"打开"**

---

### 3️⃣ 完成导入

1. 在配置页面：
   - **Prometheus 数据源**: 选择 `Prometheus`（下拉列表中）
   
2. 点击底部的 **"Import"** 按钮（绿色）

3. **完成！** 🎉

---

## 🎯 成功标志

导入成功后，你会立即看到：

- ✅ 仪表板标题：**OKX 实时行情监控**
- ✅ 绿色状态卡：**已连接**
- ✅ 波动的曲线图
- ✅ 右上角自动刷新倒计时：5秒

---

## 🆘 如果遇到问题

### 问题：找不到 "Upload JSON file" 按钮

**访问这个 URL**：
```
http://localhost:3000/dashboard/import
```

---

### 问题：没有 Prometheus 数据源选项

**快速添加**：

1. 左侧 ☰ → **Connections** → **Data sources**
2. 点击 **Add data source**
3. 选择 **Prometheus**
4. URL 填入：`http://prometheus:9090`
5. 点击 **Save & test**
6. 返回导入仪表板

---

### 问题：导入后显示 "No data"

**检查服务状态**：

```powershell
# 在 PowerShell 中运行
docker ps --filter "name=okx"
docker ps --filter "name=prometheus"
```

都应该显示 "Up" 状态。

---

## 📞 需要帮助？

查看详细文档：
```
docs/MANUAL_IMPORT_DASHBOARD.md
```

---

**预计时间**: 1-2 分钟  
**难度**: ⭐☆☆☆☆ 非常简单  
**成功率**: 99%

现在就试试吧！🚀
