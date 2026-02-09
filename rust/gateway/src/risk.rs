use anyhow::{Result, anyhow};
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::sync::Arc;
use dashmap::DashMap;
use chrono::{DateTime, Utc, Duration};
use tracing::{info, warn};

use common::proto::Order;

#[derive(Debug, Deserialize)]
pub struct RiskConfig {
    pub position_limits: HashMap<String, i32>,
    pub rate_limits: RateLimits,
    pub order_validation: OrderValidation,
}

#[derive(Debug, Deserialize)]
pub struct RateLimits {
    pub max_orders_per_second: u32,
    pub max_orders_per_strategy_per_second: u32,
}

#[derive(Debug, Deserialize)]
pub struct OrderValidation {
    pub max_order_age_ms: i64,
    pub min_price: f64,
    pub max_price: f64,
}

pub struct RiskManager {
    config: Arc<RiskConfig>,
    positions: Arc<DashMap<String, i32>>,
    order_timestamps: Arc<DashMap<String, Vec<DateTime<Utc>>>>,
    strategy_order_timestamps: Arc<DashMap<String, Vec<DateTime<Utc>>>>,
}

impl RiskManager {
    pub fn new(config_path: &str) -> Result<Self> {
        let config_str = fs::read_to_string(config_path)?;
        let config: RiskConfig = toml::from_str(&config_str)?;

        info!("Risk manager initialized");
        info!("Position limits: {:?}", config.position_limits);
        info!("Rate limits: max {} orders/s", config.rate_limits.max_orders_per_second);

        Ok(Self {
            config: Arc::new(config),
            positions: Arc::new(DashMap::new()),
            order_timestamps: Arc::new(DashMap::new()),
            strategy_order_timestamps: Arc::new(DashMap::new()),
        })
    }

    pub fn check_order(&self, order: &Order) -> Result<()> {
        // 1. Check order age
        self.check_order_age(order)?;

        // 2. Check price validity
        self.check_price(order)?;

        // 3. Check position limits
        self.check_position_limit(order)?;

        // 4. Check rate limits
        self.check_rate_limits(order)?;

        Ok(())
    }

    fn check_order_age(&self, order: &Order) -> Result<()> {
        let now = Utc::now().timestamp_nanos_opt().unwrap_or(0);
        let age_ns = now - order.timestamp;
        let age_ms = age_ns / 1_000_000;

        if age_ms > self.config.order_validation.max_order_age_ms {
            return Err(anyhow!(
                "Order too old: {} ms (max: {} ms)",
                age_ms,
                self.config.order_validation.max_order_age_ms
            ));
        }

        Ok(())
    }

    fn check_price(&self, order: &Order) -> Result<()> {
        if order.price < self.config.order_validation.min_price {
            return Err(anyhow!(
                "Price too low: {} (min: {})",
                order.price,
                self.config.order_validation.min_price
            ));
        }

        if order.price > self.config.order_validation.max_price {
            return Err(anyhow!(
                "Price too high: {} (max: {})",
                order.price,
                self.config.order_validation.max_price
            ));
        }

        Ok(())
    }

    fn check_position_limit(&self, order: &Order) -> Result<()> {
        let limit = self.config.position_limits
            .get(&order.symbol)
            .copied()
            .unwrap_or(0);

        if limit == 0 {
            return Err(anyhow!("No position limit configured for {}", order.symbol));
        }

        let current_position = self.positions
            .get(&order.symbol)
            .map(|v| *v)
            .unwrap_or(0);

        let delta = if order.side == "BUY" {
            order.volume
        } else {
            -order.volume
        };

        let new_position = current_position + delta;

        if new_position.abs() > limit {
            return Err(anyhow!(
                "Position limit exceeded for {}: current={}, delta={}, limit={}",
                order.symbol,
                current_position,
                delta,
                limit
            ));
        }

        Ok(())
    }

    fn check_rate_limits(&self, order: &Order) -> Result<()> {
        let now = Utc::now();
        let one_second_ago = now - Duration::seconds(1);

        // Check global rate limit
        let mut global_timestamps = self.order_timestamps
            .entry("global".to_string())
            .or_insert_with(Vec::new);

        global_timestamps.retain(|ts| *ts > one_second_ago);

        if global_timestamps.len() >= self.config.rate_limits.max_orders_per_second as usize {
            return Err(anyhow!(
                "Global rate limit exceeded: {} orders/s",
                self.config.rate_limits.max_orders_per_second
            ));
        }

        global_timestamps.push(now);

        // Check per-strategy rate limit
        let mut strategy_timestamps = self.strategy_order_timestamps
            .entry(order.strategy_id.clone())
            .or_insert_with(Vec::new);

        strategy_timestamps.retain(|ts| *ts > one_second_ago);

        if strategy_timestamps.len() >= self.config.rate_limits.max_orders_per_strategy_per_second as usize {
            return Err(anyhow!(
                "Strategy rate limit exceeded for {}: {} orders/s",
                order.strategy_id,
                self.config.rate_limits.max_orders_per_strategy_per_second
            ));
        }

        strategy_timestamps.push(now);

        Ok(())
    }

    pub fn update_position(&self, symbol: &str, side: &str, volume: i32) {
        let delta = if side == "BUY" { volume } else { -volume };

        self.positions
            .entry(symbol.to_string())
            .and_modify(|pos| *pos += delta)
            .or_insert(delta);

        let new_position = self.positions.get(symbol).map(|v| *v).unwrap_or(0);
        info!("Position updated: {} = {}", symbol, new_position);
    }

    pub fn get_position(&self, symbol: &str) -> i32 {
        self.positions.get(symbol).map(|v| *v).unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_price_validation() {
        let config = RiskConfig {
            position_limits: HashMap::new(),
            rate_limits: RateLimits {
                max_orders_per_second: 100,
                max_orders_per_strategy_per_second: 10,
            },
            order_validation: OrderValidation {
                max_order_age_ms: 500,
                min_price: 0.01,
                max_price: 1000000.0,
            },
        };

        let manager = RiskManager {
            config: Arc::new(config),
            positions: Arc::new(DashMap::new()),
            order_timestamps: Arc::new(DashMap::new()),
            strategy_order_timestamps: Arc::new(DashMap::new()),
        };

        let mut order = Order {
            order_id: "test".to_string(),
            strategy_id: "test_strategy".to_string(),
            symbol: "BTCUSDT".to_string(),
            price: 0.005,
            volume: 1,
            side: "BUY".to_string(),
            timestamp: Utc::now().timestamp_nanos_opt().unwrap_or(0),
        };

        // Should fail: price too low
        assert!(manager.check_price(&order).is_err());

        // Should pass
        order.price = 50000.0;
        assert!(manager.check_price(&order).is_ok());
    }
}
