# TTQuant - 多市场量化交易系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**TTQuant** (TurboTrade Quantitative Trading System) 是一个高性能、多市场量化交易系统，采用 Python + Rust 混合架构，支持 A股、加密货币、期货等多个市场。

## ✨ 核心特性

- 🚀 **超低延迟**：信号到订单 < 1ms
- 🔄 **多市场支持**：A股、加密货币、期货统一接入
- 🛡️ **生产级风控**：持仓限制、频率限制、订单校验
- 📊 **回测即实盘**：策略代码无需修改，直接切换
- 🔍 **全栈可观测**：Prometheus + Grafana + Loki 监控
- 🐳 **容器化部署**：Docker Compose 一键启动

## 🏗️ 系统架构

```
┌─────────────┐ PUB/SUB ┌──────────────┐ PUSH/PULL ┌─────────────┐
│ 行情模块(MD) │────────>│ 策略引擎(Py)  │─────────>│ 交易柜台(GW) │
│   (Rust)    │         │  (Python)    │          │   (Rust)    │
└──────┬──────┘         └──────┬───────┘          └──────┬──────┘
       │                       │                         │
       │                       │<──── PUB/SUB ───────────┘
       │                       │    (成交回报)
       │                       │
       └───────────────────────┴─────────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │  TimescaleDB    │
                        └─────────────────┘
```

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 方法 1: 使用 Makefile（推荐）

```bash
# 构建镜像
make build

# 启动服务
make up

# 查看行情日志
make logs-md

# 查看测试客户端
make logs-test

# 停止服务
make down
```

### 方法 2: 使用部署脚本

```bash
chmod +x deploy.sh
./deploy.sh
```

### 方法 3: 手动 Docker Compose

```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f
```

### 验证部署

```bash
# 查看服务状态
docker compose -f docker/docker-compose.yml ps

# 查看实时行情
docker compose -f docker/docker-compose.yml logs -f test-client
```

你应该看到：
```
[    10] md.BTCUSDT.binance          | Rate: 5.2 msg/s
[    20] md.ETHUSDT.binance          | Rate: 6.1 msg/s
```

## 📖 文档

- [系统设计文档](docs/plans/2026-02-10-ttquant-system-design.md) - 完整的架构设计
- [Docker 部署指南](docs/DOCKER.md) - Docker 使用和故障排查
- [快速开始指南](docs/QUICKSTART.md) - 本地开发环境搭建
- [Gateway 模块文档](docs/GATEWAY.md) - 交易网关使用指南 🆕
- [测试指南](docs/TESTING.md) - 测试清单和性能基准
- [开发进度](docs/PROGRESS.md) - 实现进度跟踪

## 🛠️ 技术栈

### 核心技术

- **Rust**: 行情采集、交易执行（高性能、内存安全）
- **Python**: 策略开发、因子计算（生态丰富）
- **ZeroMQ**: 进程间通信（低延迟）
- **TimescaleDB**: 时序数据存储
- **Protocol Buffers**: 数据序列化

### 监控与运维

- **Prometheus**: 指标采集（待实现）
- **Grafana**: 可视化（待实现）
- **Loki**: 日志聚合（待实现）
- **Docker Compose**: 容器编排

## 📊 性能指标

- **延迟**: < 1ms（信号到订单，目标）
- **吞吐量**: > 100 msg/s（行情处理，已验证）
- **可用性**: 99.9%（目标）
- **恢复时间**: < 3s（服务自愈）

## 🎯 当前状态

**项目进度**: 60% 完成

### ✅ 已完成
- 行情模块（Binance WebSocket）
- 交易网关（订单提交、风控、成交回报）
- Docker 部署（一键启动）
- TimescaleDB 数据库
- 完整文档体系

### 🚧 进行中
- Python 策略引擎
- 回测框架
- 监控系统

### 📋 待实现
- 更多交易所支持（OKX, Tushare）
- 机器学习因子
- 生产环境优化

## 🔧 开发

### 测试 Gateway 模块

```bash
# 启动所有服务
make up

# 测试网关
make test-gateway

# 查看网关日志
make logs-gateway
```

### 构建 Rust 模块

```bash
cd rust
cargo build --release
```

### 运行 Python 测试

```bash
cd python
pip install -r requirements.txt
python test_market_data.py  # 测试行情接收
python test_gateway.py      # 测试网关（需要 Docker）
python simulate_system.py   # 系统模拟（无需 Docker）
```

## 📝 策略示例（待实现）

```python
class EMACrossStrategy(BaseStrategy):
    def on_market_data(self, md: MarketData) -> Optional[Signal]:
        # 计算均线
        fast_ema = self.calculate_ema(md.symbol, 5)
        slow_ema = self.calculate_ema(md.symbol, 20)

        # 生成信号
        if fast_ema > slow_ema:
            self.send_order(md.symbol, "BUY", md.last_price, 100)
        elif fast_ema < slow_ema:
            self.send_order(md.symbol, "SELL", md.last_price, 100)
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## ⚠️ 免责声明

本系统仅供学习和研究使用。量化交易存在风险，请谨慎使用真实资金。作者不对任何交易损失负责。

## 📧 联系方式

- 项目主页: https://github.com/yourusername/TTQuant
- 问题反馈: https://github.com/yourusername/TTQuant/issues

---

**Built with ❤️ by the TTQuant Team**
