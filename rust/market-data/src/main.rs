use anyhow::Result;
use std::env;
use tracing::{info, error};
use tracing_subscriber;

mod binance;
mod okx;
mod metrics;

#[tokio::main]
async fn main() -> Result<()> {
    // 初始化日志
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    // 读取环境变量
    let market = env::var("MARKET").unwrap_or_else(|_| "binance".to_string());
    let zmq_endpoint = env::var("ZMQ_PUB_ENDPOINT").unwrap_or_else(|_| "tcp://*:5555".to_string());
    let db_uri = env::var("DB_URI").ok();
    let metrics_port: u16 = env::var("METRICS_PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse()
        .unwrap_or(8080);

    info!("Starting market data service: {}", market);
    info!("ZMQ endpoint: {}", zmq_endpoint);
    info!("Metrics port: {}", metrics_port);

    // 启动 Metrics HTTP 服务器（在后台运行）
    let metrics_handle = tokio::spawn(async move {
        if let Err(e) = metrics::start_metrics_server(metrics_port).await {
            error!("Metrics server error: {}", e);
        }
    });

    // 根据市场类型启动对应的服务（在主线程运行，避免 Send 问题）
    let result = match market.as_str() {
        "binance" => {
            binance::run(&zmq_endpoint, db_uri.as_deref()).await
        }
        "okx" => {
            okx::run(&zmq_endpoint, db_uri.as_deref()).await
        }
        _ => {
            error!("Unknown market: {}", market);
            Err(anyhow::anyhow!("Unknown market"))
        }
    };

    if let Err(e) = result {
        error!("Market data service error: {}", e);
    }

    // 等待 metrics 服务器
    let _ = metrics_handle.await;

    Ok(())
}
