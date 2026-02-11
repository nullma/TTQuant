use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use tokio::time::{Duration, interval};
use tokio::net::TcpStream;
use tokio_tungstenite::{connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream};
use tokio_socks::tcp::Socks5Stream;
use tracing::{info, warn, error};
use ttquant_common::{MarketData, zmq_wrapper::ZmqPublisher, time::now_nanos, Database, MarketDataBatchWriter};
use bumpalo::Bump;
use url::Url;

const OKX_WS_URL: &str = "wss://ws.okx.com:8443/ws/v5/public";

pub async fn run(zmq_endpoint: &str, db_uri: Option<&str>) -> Result<()> {
    info!("Starting OKX market data service");

    // 创建 ZMQ Publisher
    let publisher = ZmqPublisher::new(zmq_endpoint)?;

    // 创建数据库连接（如果提供了 URI）
    let db_writer = if let Some(uri) = db_uri {
        match Database::new(uri).await {
            Ok(db) => {
                info!("Database connection established");
                // 批量写入器：每100条或每1秒刷新一次
                Some(MarketDataBatchWriter::new(db, 100, 1))
            }
            Err(e) => {
                warn!("Failed to connect to database: {}, continuing without persistence", e);
                None
            }
        }
    } else {
        info!("No database URI provided, running without persistence");
        None
    };

    // 订阅的交易对（OKX 格式：BTC-USDT）
    // 只订阅主流交易对，避免 WebSocket 连接过载
    let symbols = vec![
        "BTC-USDT",
        "ETH-USDT",
        "SOL-USDT",
        "BNB-USDT",
    ];

    // 构建订阅消息
    let subscribe_msg = build_subscribe_message(&symbols);

    loop {
        match connect_and_stream(&publisher, &subscribe_msg, db_writer.as_ref()).await {
            Ok(_) => {
                warn!("WebSocket connection closed, reconnecting...");
            }
            Err(e) => {
                error!("WebSocket error: {}, reconnecting in 5s...", e);
                tokio::time::sleep(Duration::from_secs(5)).await;
            }
        }
    }
}

async fn connect_and_stream(
    publisher: &ZmqPublisher,
    subscribe_msg: &str,
    db_writer: Option<&MarketDataBatchWriter>,
) -> Result<()> {
    // 检查是否配置了 SOCKS5 代理
    let socks5_proxy = std::env::var("SOCKS5_PROXY").ok();

    let ws_stream = if let Some(proxy_addr) = socks5_proxy {
        info!("Using SOCKS5 proxy: {}", proxy_addr);

        // 解析 OKX WebSocket URL
        let url = Url::parse(OKX_WS_URL)?;
        let host = url.host_str().ok_or_else(|| anyhow::anyhow!("Invalid host"))?;
        let port = url.port().unwrap_or(8443);

        // 通过 SOCKS5 代理连接
        let tcp_stream = Socks5Stream::connect(proxy_addr.as_str(), (host, port)).await?;

        // 升级到 WebSocket
        let (ws_stream, _) = tokio_tungstenite::client_async_tls(url, tcp_stream.into_inner()).await?;
        ws_stream
    } else {
        // 直接连接
        let (ws_stream, _) = connect_async(OKX_WS_URL).await?;
        ws_stream
    };

    info!("Connected to OKX WebSocket");

    let (mut write, mut read) = ws_stream.split();

    // 发送订阅消息
    write.send(Message::Text(subscribe_msg.to_string())).await?;
    info!("Sent subscription message");

    // 心跳定时器（OKX 需要每 15 秒发送 ping）
    let mut heartbeat = interval(Duration::from_secs(15));

    // 数据库刷新定时器（每秒检查一次）
    let mut db_flush_timer = interval(Duration::from_secs(1));

    // 内存池
    let mut arena = Bump::new();

    // Clone the writer for use in the loop
    let db_writer_clone = db_writer.cloned();

    loop {
        tokio::select! {
            // 接收消息
            msg = read.next() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        if let Err(e) = handle_message(&text, publisher, db_writer_clone.as_ref(), &arena).await {
                            warn!("Failed to handle message: {}", e);
                        }
                        arena.reset();
                    }
                    Some(Ok(Message::Ping(_))) => {
                        // WebSocket ping/pong 自动处理
                    }
                    Some(Ok(Message::Close(_))) => {
                        info!("WebSocket closed by server");
                        break;
                    }
                    Some(Err(e)) => {
                        error!("WebSocket error: {}", e);
                        break;
                    }
                    None => {
                        info!("WebSocket stream ended");
                        break;
                    }
                    _ => {}
                }
            }

            // 心跳（OKX 需要发送 ping 消息）
            _ = heartbeat.tick() => {
                let ping_msg = serde_json::json!({"op": "ping"}).to_string();
                if let Err(e) = write.send(Message::Text(ping_msg)).await {
                    error!("Failed to send ping: {}", e);
                    break;
                }
            }

            // 定期刷新数据库缓冲区
            _ = db_flush_timer.tick() => {
                if let Some(ref writer) = db_writer_clone {
                    if let Err(e) = writer.flush().await {
                        warn!("Failed to flush database buffer: {}", e);
                    }
                }
            }
        }
    }

    // 连接关闭前，刷新剩余数据
    if let Some(ref writer) = db_writer_clone {
        if let Err(e) = writer.flush().await {
            error!("Failed to flush database buffer on shutdown: {}", e);
        }
    }

    Ok(())
}

async fn handle_message(
    text: &str,
    publisher: &ZmqPublisher,
    db_writer: Option<&MarketDataBatchWriter>,
    _arena: &Bump,
) -> Result<()> {
    let json: Value = serde_json::from_str(text)?;

    // 处理 pong 响应
    if let Some(op) = json.get("op").and_then(|v| v.as_str()) {
        if op == "pong" {
            return Ok(());
        }
    }

    // 解析 OKX 行情数据
    if let Some(arg) = json.get("arg") {
        if let Some(channel) = arg.get("channel").and_then(|v| v.as_str()) {
            if channel == "trades" {
                if let Some(data_array) = json.get("data").and_then(|v| v.as_array()) {
                    for data in data_array {
                        if let Err(e) = process_trade_data(data, publisher, db_writer).await {
                            warn!("Failed to process trade data: {}", e);
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

async fn process_trade_data(
    data: &Value,
    publisher: &ZmqPublisher,
    db_writer: Option<&MarketDataBatchWriter>,
) -> Result<()> {
    let symbol = data.get("instId")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("No instId"))?;

    let price = data.get("px")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<f64>().ok())
        .ok_or_else(|| anyhow::anyhow!("No price"))?;

    let volume = data.get("sz")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<f64>().ok())
        .unwrap_or(0.0);

    let exchange_time = data.get("ts")
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<i64>().ok())
        .map(|t| t * 1_000_000)  // 毫秒转纳秒
        .unwrap_or(0);

    let local_time = now_nanos();

    // 转换符号格式：BTC-USDT → BTCUSDT（统一格式）
    let normalized_symbol = symbol.replace("-", "");

    // 构建 MarketData
    let md = MarketData {
        symbol: normalized_symbol.clone(),
        last_price: price,
        volume,
        exchange_time,
        local_time,
        exchange: "okx".to_string(),
    };

    // 发布到 ZMQ
    let topic = format!("md.{}.okx", normalized_symbol);
    publisher.send(&topic, &md)?;

    // 异步写入数据库（不阻塞行情发布）
    if let Some(writer) = db_writer {
        if let Err(e) = writer.add(md).await {
            warn!("Failed to add market data to database buffer: {}", e);
        }
    }

    Ok(())
}

fn build_subscribe_message(symbols: &[&str]) -> String {
    let args: Vec<Value> = symbols
        .iter()
        .map(|s| serde_json::json!({
            "channel": "trades",
            "instId": s
        }))
        .collect();

    serde_json::json!({
        "op": "subscribe",
        "args": args
    })
    .to_string()
}
