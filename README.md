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

- Docker & Docker Compose
- Rust 1.75+
- Python 3.11+

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/TTQuant.git
cd TTQuant
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 3. 启动系统

```bash
chmod +x deploy.sh
./deploy.sh
```

### 4. 访问监控面板

- **Grafana**: http://localhost:3000 (admin / 你的密码)
- **Prometheus**: http://localhost:9090

## 📖 文档

- [系统设计文档](docs/plans/2026-02-10-ttquant-system-design.md)
- [API 文档](docs/api/)
- [策略开发指南](docs/strategy-guide.md)

## 🛠️ 技术栈

### 核心技术

- **Rust**: 行情采集、交易执行（高性能、内存安全）
- **Python**: 策略开发、因子计算（生态丰富）
- **ZeroMQ**: 进程间通信（低延迟）
- **TimescaleDB**: 时序数据存储
- **Protocol Buffers**: 数据序列化

### 监控与运维

- **Prometheus**: 指标采集
- **Grafana**: 可视化
- **Loki**: 日志聚合
- **Docker Compose**: 容器编排

## 📊 性能指标

- **延迟**: < 1ms（信号到订单）
- **吞吐量**: > 10,000 msg/s（行情处理）
- **可用性**: 99.9%
- **恢复时间**: < 3s（服务自愈）

## 🔧 开发

### 构建 Rust 模块

```bash
cd rust
cargo build --release
```

### 运行 Python 策略

```bash
cd python
pip install -r requirements.txt
python strategy/engine.py
```

### 运行回测

```bash
python backtest/run_backtest.py --strategy EMA_Cross --start 2025-01-01 --end 2025-12-31
```

## 📝 策略示例

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
