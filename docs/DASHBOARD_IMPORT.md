# 📊 导入 OKX 实时行情仪表板

## 🎯 仪表板内容

这个仪表板包含以下监控面板：

1. **OKX WebSocket 状态** - 实时连接状态（绿色=已连接，红色=断开）
2. **WebSocket 消息接收速率** - 每秒接收的消息数曲线图
3. **消息总数** - 累计接收的消息总数
4. **行情数据速率（按交易对）** - 每个交易对的数据更新速率
5. **行情数据分布（饼图）** - 各交易对数据量占比
6. **Top 10 活跃交易对** - 数据最活跃的前10个交易对

**自动刷新**: 每 5 秒  
**时间范围**: 最近 15 分钟

---

## 📥 方法 1: 自动导入（推荐）

仪表板文件已保存到：
```
monitoring/dashboards/okx-realtime-dashboard.json
```

Grafana 会自动加载这个目录下的仪表板！

### 步骤：

1. **重启 Grafana 容器**（让它加载新仪表板）：
```powershell
docker compose -f docker/docker-compose.prod.yml restart grafana
```

2. **等待 10 秒**让 Grafana 启动完成

3. **访问 Grafana**：http://localhost:3000

4. **登录**：admin / admin123

5. **查看仪表板**：
   - 点击左侧 **☰** → **Dashboards**
   - 点击 **Browse**
   - 应该能看到 **OKX 实时行情监控** 仪表板
   - 点击打开即可！

---

## 📥 方法 2: 手动导入JSON

如果自动导入不生效，可以手动导入：

### 步骤：

1. **登录 Grafana**：http://localhost:3000

2. **导入仪表板**：
   - 点击左侧 **☰** → **Dashboards** → **Import**

3. **上传 JSON 文件**：
   - 点击 **Upload JSON file**
   - 选择文件：
     ```
     C:\Users\11915\Desktop\TTQuant\monitoring\dashboards\okx-realtime-dashboard.json
     ```

4. **配置选项**（通常保持默认）：
   - Dashboard name: `OKX 实时行情监控`
   - Folder: `General` (或创建新文件夹)
   - Unique identifier (UID): `okx-realtime-v1`

5. **选择数据源**：
   - Prometheus: 选择 `Prometheus`

6. **点击 Import**

7. **完成！** 🎉 仪表板应该立即显示数据

---

## 📥 方法 3: 复制粘贴JSON

1. **打开 JSON 文件**：
   ```
   C:\Users\11915\Desktop\TTQuant\monitoring\dashboards\okx-realtime-dashboard.json
   ```

2. **复制全部内容** (Ctrl+A, Ctrl+C)

3. **在 Grafana 中导入**：
   - **☰** → **Dashboards** → **Import**
   - 点击 **Import via panel json**
   - **粘贴** JSON 内容 (Ctrl+V)
   - 点击 **Load**

4. **配置并导入**（同方法 2 步骤 4-6）

---

## ✅ 验证仪表板

### 导入成功后，你应该看到：

1. **左上角** - `OKX 实时行情监控` 标题

2. **第一行**：
   - WebSocket 状态卡片（应显示绿色 "已连接"）
   - 消息接收速率曲线图（实时波动）

3. **第二行**：
   - 消息总数统计
   - （空白区域预留扩展）

4. **第三行**：
   - 各交易对数据速率曲线图
   - 交易对数据分布饼图

5. **第四行**：
   - Top 10 活跃交易对柱状图

### 数据应该实时更新：

- **刷新频率**: 右上角显示 `5s` (每5秒刷新)
- **时间范围**: 显示 `Last 15 minutes`
- **数据流动**: 曲线图应该在移动

---

## 🎨 自定义仪表板

### 调整刷新频率

1. 点击右上角 **⏱️** (时钟图标)
2. 在下拉菜单中选择：
   - `5s` - 每 5 秒（默认）
   - `10s` - 每 10 秒
   - `30s` - 每 30 秒
   - `Off` - 关闭自动刷新

### 调整时间范围

1. 点击右上角时间范围（如 `Last 15 minutes`）
2. 选择：
   - `Last 5 minutes` - 最近 5 分钟
   - `Last 15 minutes` - 最近 15 分钟（默认）
   - `Last 30 minutes` - 最近 30 分钟
   - `Last 1 hour` - 最近 1 小时

### 编辑面板

1. 将鼠标悬停在任意面板上
2. 点击面板标题旁的 **⋯** (三个点)
3. 选择 **Edit** 编辑
4. 修改查询、样式、标题等
5. 点击 **Apply** 保存

### 添加新面板

1. 点击右上角 **Add panel** (+)
2. 选择 **Add a new panel**
3. 配置数据源和查询
4. 点击 **Apply**

### 保存修改

1. 点击右上角 **💾 Save dashboard**
2. 输入保存原因（可选）
3. 点击 **Save**

---

## 🔧 故障排查

### 问题 1: 看不到 "OKX 实时行情监控" 仪表板

**解决方案**:
```powershell
# 重启 Grafana
docker compose -f docker/docker-compose.prod.yml restart grafana

# 等待 10 秒
Start-Sleep -Seconds 10

# 刷新浏览器页面
```

### 问题 2: 仪表板显示 "No Data"

**检查清单**:
1. ✅ OKX 服务是否运行:
   ```powershell
   docker ps --filter "name=okx"
   ```

2. ✅ Prometheus 是否可访问:
   ```
   http://localhost:8082/metrics
   ```

3. ✅ 数据源是否正确:
   - 在仪表板中，点击面板 → Edit
   - 检查 Data source 是否为 `Prometheus`

### 问题 3: 导入时提示错误

**可能原因**: JSON 格式问题或 Grafana 版本不兼容

**解决方案**: 使用方法 2 或 3 手动导入，并检查错误提示

---

## 📚 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `d` + `k` | 打开搜索 |
| `f` | 全屏显示当前面板 |
| `Ctrl + S` | 保存仪表板 |
| `Ctrl + H` | 隐藏/显示菜单 |
| `t` + `z` | 放大时间范围 |
| `t` + `←` | 时间范围后退 |
| `t` + `→` | 时间范围前进 |

---

## 🎉 完成！

现在你应该有一个功能完整的 OKX 实时行情监控仪表板了！

**访问**: http://localhost:3000  
**账号**: admin / admin123  
**仪表板**: OKX 实时行情监控

享受实时数据可视化的乐趣！📈

---

**创建时间**: 2026-02-10 20:13  
**文件位置**: `monitoring/dashboards/okx-realtime-dashboard.json`  
**支持**: 如有问题查看 `docs/GRAFANA_GUIDE.md`
