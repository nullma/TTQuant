# 环境配置说明

## 本地环境（Windows + v2rayN 代理）

本地需要通过 SOCKS5 代理连接 OKX。

**配置步骤：**
```bash
cd docker
cp .env.local .env
docker compose up -d
```

`.env` 文件内容：
```
SOCKS5_PROXY=proxy:1080
```

## 服务器环境（EC2 直连）

服务器可以直接连接 OKX，不需要代理。

**配置步骤：**
```bash
cd docker
cp .env.server .env
docker compose up -d
```

`.env` 文件内容：
```
SOCKS5_PROXY=
```

## 工作原理

- `docker-compose.yml` 使用 `${SOCKS5_PROXY:-}` 读取环境变量
- 本地：`SOCKS5_PROXY=proxy:1080` → md-okx 通过代理连接
- 服务器：`SOCKS5_PROXY=` (空) → md-okx 直连

## 代码逻辑

`rust/market-data/src/okx.rs`:
```rust
let socks5_proxy = std::env::var("SOCKS5_PROXY").ok();

if let Some(proxy_addr) = socks5_proxy {
    // 使用代理
    let tcp_stream = Socks5Stream::connect(proxy_addr, (host, port)).await?;
    // ...
} else {
    // 直连
    let (ws_stream, _) = connect_async(OKX_WS_URL).await?;
    // ...
}
```

## 注意事项

1. **本地开发**：必须配置 `SOCKS5_PROXY=proxy:1080`
2. **服务器部署**：必须配置 `SOCKS5_PROXY=` (空值)
3. **Git 提交**：不要提交 `.env` 文件（已在 .gitignore 中）
4. **部署流程**：
   - 本地：`git push` → GitHub
   - 服务器：`git pull` → 配置 `.env` → `docker compose up -d`
