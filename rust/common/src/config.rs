use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketConfig {
    pub ws_url: String,
    pub symbols: Vec<String>,
    pub heartbeat_interval_secs: u64,
    pub reconnect_backoff_ms: Vec<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketsConfig {
    pub binance: Option<MarketConfig>,
    pub okx: Option<MarketConfig>,
    pub tushare: Option<MarketConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskConfig {
    pub position_limits: HashMap<String, i32>,
    pub rate_limits: RateLimits,
    pub order_validation: OrderValidation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimits {
    pub max_orders_per_second: u32,
    pub max_orders_per_strategy_per_second: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderValidation {
    pub max_order_age_ms: i64,
    pub min_price: f64,
    pub max_price: f64,
}

impl MarketsConfig {
    pub fn from_file(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        Ok(toml::from_str(&content)?)
    }
}

impl RiskConfig {
    pub fn from_file(path: &str) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        Ok(toml::from_str(&content)?)
    }
}
