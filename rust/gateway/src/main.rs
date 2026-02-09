use anyhow::Result;
use tracing::{info, error};
use tracing_subscriber;

mod risk;
mod exchange;
mod order_manager;

use risk::RiskManager;
use exchange::ExchangeRouter;
use order_manager::OrderManager;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    info!("Starting Gateway service");

    // Load configuration
    let exchange = std::env::var("EXCHANGE").unwrap_or_else(|_| "binance".to_string());
    let zmq_pull_endpoint = std::env::var("ZMQ_PULL_ENDPOINT")
        .unwrap_or_else(|_| "tcp://*:5556".to_string());
    let zmq_pub_endpoint = std::env::var("ZMQ_PUB_ENDPOINT")
        .unwrap_or_else(|_| "tcp://*:5557".to_string());

    info!("Exchange: {}", exchange);
    info!("ZMQ PULL endpoint: {}", zmq_pull_endpoint);
    info!("ZMQ PUB endpoint: {}", zmq_pub_endpoint);

    // Initialize components
    let risk_manager = RiskManager::new("config/risk.toml")?;
    let exchange_router = ExchangeRouter::new(&exchange)?;
    let mut order_manager = OrderManager::new(
        &zmq_pull_endpoint,
        &zmq_pub_endpoint,
        risk_manager,
        exchange_router,
    )?;

    // Start order processing loop
    info!("Gateway ready, waiting for orders...");
    order_manager.run().await?;

    Ok(())
}
