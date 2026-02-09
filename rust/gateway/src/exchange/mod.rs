use anyhow::{Result, anyhow};
use tracing::{info, error};
use std::future::Future;
use std::pin::Pin;

use common::proto::{Order, Trade};

mod binance;

use binance::BinanceExchange;

pub trait Exchange: Send + Sync {
    fn name(&self) -> &str;
    fn submit_order<'a>(&'a self, order: &'a Order) -> Pin<Box<dyn Future<Output = Result<Trade>> + Send + 'a>>;
}

pub struct ExchangeRouter {
    exchange: Box<dyn Exchange>,
}

impl ExchangeRouter {
    pub fn new(exchange_name: &str) -> Result<Self> {
        let exchange: Box<dyn Exchange> = match exchange_name.to_lowercase().as_str() {
            "binance" => Box::new(BinanceExchange::new()?),
            _ => return Err(anyhow!("Unsupported exchange: {}", exchange_name)),
        };

        info!("Exchange router initialized: {}", exchange.name());

        Ok(Self { exchange })
    }

    pub async fn submit_order(&self, order: &Order) -> Result<Trade> {
        info!(
            "Submitting order to {}: {} {} {} @ {}",
            self.exchange.name(),
            order.side,
            order.volume,
            order.symbol,
            order.price
        );

        let trade = self.exchange.submit_order(order).await?;

        info!(
            "Order executed: {} {} @ {} (commission: {})",
            trade.filled_volume,
            trade.symbol,
            trade.filled_price,
            trade.commission
        );

        Ok(trade)
    }

    pub fn exchange_name(&self) -> &str {
        self.exchange.name()
    }
}
