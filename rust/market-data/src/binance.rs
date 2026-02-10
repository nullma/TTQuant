use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use tokio::time::{Duration, interval};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{info, warn, error};
use ttquant_common::{MarketData, zmq_wrapper::ZmqPublisher, time::now_nanos, Database, MarketDataBatchWriter};
use bumpalo::Bump;

const BINANCE_WS_URL: &str = "wss://stream.binance.com:9443/ws";

pub async fn run(zmq_endpoint: &str, db_uri: Option<&str>) -> Result<()> {
    info!("Starting Binance market data service");

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

    // 订阅的交易对
    let symbols = vec!["btcusdt", "ethusdt"];

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
    // 连接 WebSocket
    let url = format!("{}/stream", BINANCE_WS_URL);
    let (ws_stream, _) = connect_async(&url).await?;
    info!("Connected to Binance WebSocket");

    let (mut write, mut read) = ws_stream.split();

    // 发送订阅消息
    write.send(Message::Text(subscribe_msg.to_string())).await?;
    info!("Sent subscription message");

    // 心跳定时器
    let mut heartbeat = interval(Duration::from_secs(20));

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

            // 心跳
            _ = heartbeat.tick() => {
                if let Err(e) = write.send(Message::Pong(vec![])).await {
                    error!("Failed to send pong: {}", e);
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

    // 解析 Binance 行情数据
    if let Some(stream) = json.get("stream").and_then(|v| v.as_str()) {
        if stream.contains("@trade") {
            let data = json.get("data").ok_or_else(|| anyhow::anyhow!("No data field"))?;

            let symbol = data.get("s")
                .and_then(|v| v.as_str())
                .ok_or_else(|| anyhow::anyhow!("No symbol"))?;

            let price = data.get("p")
                .and_then(|v| v.as_str())
                .and_then(|s| s.parse::<f64>().ok())
                .ok_or_else(|| anyhow::anyhow!("No price"))?;

            let volume = data.get("q")
                .and_then(|v| v.as_str())
                .and_then(|s| s.parse::<f64>().ok())
                .unwrap_or(0.0);

            let exchange_time = data.get("T")
                .and_then(|v| v.as_i64())
                .map(|t| t * 1_000_000)  // 毫秒转纳秒
                .unwrap_or(0);

            let local_time = now_nanos();

            // 构建 MarketData
            let md = MarketData {
                symbol: symbol.to_string(),
                last_price: price,
                volume,
                exchange_time,
                local_time,
                exchange: "binance".to_string(),
            };

            // 发布到 ZMQ
            let topic = format!("md.{}.binance", symbol);
            publisher.send(&topic, &md)?;

            // 异步写入数据库（不阻塞行情发布）
            if let Some(writer) = db_writer {
                if let Err(e) = writer.add(md).await {
                    warn!("Failed to add market data to database buffer: {}", e);
                }
            }
        }
    }

    Ok(())
}

fn build_subscribe_message(symbols: &[&str]) -> String {
    let streams: Vec<String> = symbols
        .iter()
        .map(|s| format!("{}@trade", s))
        .collect();

    serde_json::json!({
        "method": "SUBSCRIBE",
        "params": streams,
        "id": 1
    })
    .to_string()
}
