mod binance;
mod okx;
mod metrics;

use anyhow::Result;
use std::env;
use tracing::{info, error};
use tracing_subscriber;

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

    info!("Starting market data service: {}", market);
    info!("ZMQ endpoint: {}", zmq_endpoint);

    // 根据市场类型启动对应的服务
    match market.as_str() {
        "binance" => {
            binance::run(&zmq_endpoint, db_uri.as_deref()).await?;
        }
        "okx" => {
            okx::run(&zmq_endpoint, db_uri.as_deref()).await?;
        }
        _ => {
            error!("Unknown market: {}", market);
            return Err(anyhow::anyhow!("Unknown market"));
        }
    }

    Ok(())
}
