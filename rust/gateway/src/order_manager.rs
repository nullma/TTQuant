use anyhow::Result;
use prost::Message;
use tracing::{info, warn, error};
use chrono::Utc;

use ttquant_common::proto::{Order, Trade};
use ttquant_common::zmq_wrapper::{ZmqPuller, ZmqPublisher};
use ttquant_common::Database;

use super::risk::RiskManager;
use super::exchange::ExchangeRouter;

pub struct OrderManager {
    puller: ZmqPuller,
    publisher: ZmqPublisher,
    risk_manager: RiskManager,
    exchange_router: ExchangeRouter,
    order_count: u64,
    db: Option<Database>,
}

impl OrderManager {
    pub fn new(
        pull_endpoint: &str,
        pub_endpoint: &str,
        risk_manager: RiskManager,
        exchange_router: ExchangeRouter,
    ) -> Result<Self> {
        let puller = ZmqPuller::new(pull_endpoint)?;
        let publisher = ZmqPublisher::new(pub_endpoint)?;

        info!("Order manager initialized");
        info!("Listening for orders on: {}", pull_endpoint);
        info!("Publishing trades on: {}", pub_endpoint);

        Ok(Self {
            puller,
            publisher,
            risk_manager,
            exchange_router,
            order_count: 0,
            db: None,
        })
    }

    /// 设置数据库连接
    pub fn with_database(mut self, db: Database) -> Self {
        info!("Database persistence enabled for order manager");
        self.db = Some(db);
        self
    }

    pub async fn run(&mut self) -> Result<()> {
        loop {
            // Receive order from strategy
            match self.puller.recv::<Order>() {
                Ok(order) => {
                    self.order_count += 1;

                    info!(
                        "[Order #{}] Received: {} {} {} @ {} (strategy: {})",
                        self.order_count,
                        order.side,
                        order.volume,
                        order.symbol,
                        order.price,
                        order.strategy_id
                    );

                    // 写入订单到数据库
                    if let Some(ref db) = self.db {
                        if let Err(e) = db.insert_order(&order).await {
                            warn!("Failed to insert order to database: {}", e);
                        }
                    }

                    // Process order
                    let trade = self.process_order(&order).await;

                    // 写入成交记录到数据库
                    if let Some(ref db) = self.db {
                        if let Err(e) = db.insert_trade(&trade).await {
                            warn!("Failed to insert trade to database: {}", e);
                        }
                    }

                    // Publish trade result
                    let topic = format!("trade.{}.{}", order.symbol, self.exchange_router.exchange_name());
                    if let Err(e) = self.publisher.send(&topic, &trade) {
                        error!("Failed to publish trade: {}", e);
                    }

                    // Update position if filled
                    if trade.status == "FILLED" {
                        self.risk_manager.update_position(
                            &trade.symbol,
                            &trade.side,
                            trade.filled_volume,
                        );

                        // 写入持仓快照到数据库
                        if let Some(ref db) = self.db {
                            if let Some(position) = self.risk_manager.get_position_details(&trade.symbol) {
                                if let Err(e) = db.insert_position_snapshot(
                                    &trade.strategy_id,
                                    &trade.symbol,
                                    position.quantity,
                                    position.avg_price,
                                    0.0, // unrealized_pnl 需要根据当前价格计算
                                ).await {
                                    warn!("Failed to insert position snapshot: {}", e);
                                }
                            }
                        }
                    }

                    // Log result
                    if trade.status == "FILLED" {
                        info!(
                            "[Order #{}] FILLED: {} {} @ {} (commission: ${})",
                            self.order_count,
                            trade.filled_volume,
                            trade.symbol,
                            trade.filled_price,
                            trade.commission
                        );
                    } else {
                        warn!(
                            "[Order #{}] REJECTED: {} (code: {})",
                            self.order_count,
                            trade.error_message,
                            trade.error_code
                        );
                    }
                }
                Err(e) => {
                    error!("Failed to receive order: {}", e);
                    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                }
            }
        }
    }

    async fn process_order(&self, order: &Order) -> Trade {
        // Step 1: Risk check
        if let Err(e) = self.risk_manager.check_order(order) {
            warn!("Risk check failed: {}", e);
            return self.create_rejected_trade(order, 1001, &e.to_string(), false);
        }

        // Step 2: Submit to exchange
        match self.exchange_router.submit_order(order).await {
            Ok(trade) => trade,
            Err(e) => {
                error!("Exchange submission failed: {}", e);
                let is_retryable = self.is_retryable_error(&e);
                self.create_rejected_trade(order, 2001, &e.to_string(), is_retryable)
            }
        }
    }

    fn create_rejected_trade(&self, order: &Order, error_code: i32, error_message: &str, is_retryable: bool) -> Trade {
        Trade {
            trade_id: format!("REJECTED_{}", order.order_id),
            order_id: order.order_id.clone(),
            strategy_id: order.strategy_id.clone(),
            symbol: order.symbol.clone(),
            side: order.side.clone(),
            filled_price: 0.0,
            filled_volume: 0,
            trade_time: Utc::now().timestamp_nanos_opt().unwrap_or(0),
            status: "REJECTED".to_string(),
            error_code,
            error_message: error_message.to_string(),
            is_retryable,
            commission: 0.0,
        }
    }

    fn is_retryable_error(&self, error: &anyhow::Error) -> bool {
        let error_str = error.to_string().to_lowercase();

        // Network errors are retryable
        if error_str.contains("timeout") || error_str.contains("connection") {
            return true;
        }

        // Rate limit errors are retryable
        if error_str.contains("rate limit") || error_str.contains("429") {
            return true;
        }

        // Other errors are not retryable
        false
    }

    pub fn get_order_count(&self) -> u64 {
        self.order_count
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retryable_error() {
        let manager = OrderManager {
            puller: ZmqPuller::new("tcp://localhost:9999").unwrap(),
            publisher: ZmqPublisher::new("tcp://*:9998").unwrap(),
            risk_manager: RiskManager::new("config/risk.toml").unwrap(),
            exchange_router: ExchangeRouter::new("binance").unwrap(),
            order_count: 0,
        };

        let timeout_error = anyhow::anyhow!("Connection timeout");
        assert!(manager.is_retryable_error(&timeout_error));

        let rate_limit_error = anyhow::anyhow!("Rate limit exceeded");
        assert!(manager.is_retryable_error(&rate_limit_error));

        let invalid_order_error = anyhow::anyhow!("Invalid order");
        assert!(!manager.is_retryable_error(&invalid_order_error));
    }
}
