# TTQuant 快速开始指南

## 📦 环境准备

### 1. 安装依赖

**Rust**:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup update
```

**Python**:
```bash
python -m pip install --upgrade pip
cd python
pip install -r requirements.txt
```

**ZeroMQ** (如果系统没有):
```bash
# Ubuntu/Debian
sudo apt-get install libzmq3-dev

# macOS
brew install zeromq

# Windows
# 下载预编译的 ZeroMQ 库
```

## 🚀 运行 Market Data 模块

### 1. 编译 Rust 代码

```bash
cd rust
cargo build --release
```

### 2. 启动 Binance 行情服务

```bash
cd rust
MARKET=binance ZMQ_PUB_ENDPOINT=tcp://*:5555 ./target/release/market-data
```

你应该看到类似的输出：
```
INFO Starting market data service: binance
INFO ZMQ endpoint: tcp://*:5555
INFO Starting Binance market data service
INFO Connected to Binance WebSocket
INFO Sent subscription message
```

### 3. 测试行情接收（另一个终端）

```bash
cd python
python test_market_data.py
```

你应该看到实时行情：
```
Listening for market data on tcp://localhost:5555...
Press Ctrl+C to stop

Received: md.BTCUSDT.binance
Received: md.ETHUSDT.binance
Received: md.BTCUSDT.binance
...
```

## 🔧 开发模式

### 监听代码变化自动重新编译

```bash
cargo install cargo-watch
cd rust
cargo watch -x 'run --bin market-data'
```

### 查看详细日志

```bash
RUST_LOG=debug MARKET=binance ./target/release/market-data
```

## 📊 验证系统

### 检查 ZeroMQ 端口

```bash
# Linux/macOS
netstat -an | grep 5555

# Windows
netstat -an | findstr 5555
```

### 测试 ZeroMQ 连接

```python
import zmq
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5555")
socket.subscribe(b"")
print("Connected!")
```

## 🐛 常见问题

### 1. ZeroMQ 库找不到

**错误**: `error: linking with 'cc' failed`

**解决**:
```bash
# Ubuntu/Debian
sudo apt-get install libzmq3-dev pkg-config

# macOS
brew install zeromq pkg-config
```

### 2. Protobuf 编译失败

**错误**: `protoc not found`

**解决**:
```bash
# Ubuntu/Debian
sudo apt-get install protobuf-compiler

# macOS
brew install protobuf

# 或者使用 Rust 的 protoc
cargo install protobuf-codegen
```

### 3. WebSocket 连接失败

**错误**: `Failed to connect to WebSocket`

**解决**:
- 检查网络连接
- 检查防火墙设置
- 尝试使用代理

### 4. 端口被占用

**错误**: `Address already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :5555  # Linux/macOS
netstat -ano | findstr :5555  # Windows

# 杀死进程
kill -9 <PID>
```

## 📝 下一步

1. **实现 Gateway 模块** - 交易柜台
2. **实现 Python 策略引擎** - 策略开发
3. **配置 Docker** - 容器化部署

查看 [PROGRESS.md](../docs/PROGRESS.md) 了解完整的实现进度。

## 🆘 获取帮助

- 查看设计文档: `docs/plans/2026-02-10-ttquant-system-design.md`
- 查看进度: `docs/PROGRESS.md`
- 提交 Issue: GitHub Issues

---

**祝你开发顺利！** 🚀
