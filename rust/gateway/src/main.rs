use anyhow::Result;
use tracing::{info, error, warn};
use tracing_subscriber;

mod risk;
mod exchange;
mod order_manager;
mod metrics;

use risk::RiskManager;
use exchange::ExchangeRouter;
use order_manager::OrderManager;
use ttquant_common::Database;

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
    let metrics_port: u16 = std::env::var("METRICS_PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse()
        .unwrap_or(8080);
    let db_uri = std::env::var("DB_URI").ok();

    info!("Exchange: {}", exchange);
    info!("ZMQ PULL endpoint: {}", zmq_pull_endpoint);
    info!("ZMQ PUB endpoint: {}", zmq_pub_endpoint);
    info!("Metrics port: {}", metrics_port);

    // Start metrics HTTP server (in background)
    let metrics_handle = tokio::spawn(async move {
        if let Err(e) = metrics::start_metrics_server(metrics_port).await {
            error!("Metrics server error: {}", e);
        }
    });

    // Initialize components
    let risk_manager = RiskManager::new("config/risk.toml")?;
    let exchange_router = ExchangeRouter::new(&exchange)?;
    let mut order_manager = OrderManager::new(
        &zmq_pull_endpoint,
        &zmq_pub_endpoint,
        risk_manager,
        exchange_router,
    )?;

    // Initialize database connection if URI is provided
    if let Some(uri) = db_uri {
        match Database::new(&uri).await {
            Ok(db) => {
                info!("Database connection established");
                order_manager = order_manager.with_database(db);
            }
            Err(e) => {
                warn!("Failed to connect to database: {}, continuing without persistence", e);
            }
        }
    } else {
        info!("No database URI provided, running without persistence");
    }

    // Start order processing loop (in main thread to avoid Send issues)
    info!("Gateway ready, waiting for orders...");
    if let Err(e) = order_manager.run().await {
        error!("Order manager error: {}", e);
    }

    // Wait for metrics server
    let _ = metrics_handle.await;

    Ok(())
}
