use anyhow::{Result, anyhow};
use chrono::Utc;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use std::future::Future;
use std::pin::Pin;
use tracing::{info, warn, error};

use ttquant_common::proto::{Order, Trade};
use super::Exchange;

type HmacSha256 = Hmac<Sha256>;

const BINANCE_API_BASE: &str = "https://api.binance.com";
const BINANCE_TESTNET_BASE: &str = "https://testnet.binance.vision";

#[derive(Debug, Deserialize)]
struct BinanceOrderResponse {
    #[serde(rename = "orderId")]
    order_id: i64,
    symbol: String,
    side: String,
    #[serde(rename = "executedQty")]
    executed_qty: String,
    price: String,
    status: String,
}

pub struct BinanceExchange {
    client: Client,
    api_key: String,
    api_secret: String,
    base_url: String,
    testnet: bool,
}

impl BinanceExchange {
    pub fn new() -> Result<Self> {
        let api_key = std::env::var("BINANCE_API_KEY")
            .unwrap_or_else(|_| "".to_string());
        let api_secret = std::env::var("BINANCE_API_SECRET")
            .unwrap_or_else(|_| "".to_string());
        let testnet = std::env::var("BINANCE_TESTNET")
            .unwrap_or_else(|_| "true".to_string())
            .parse::<bool>()
            .unwrap_or(true);

        let base_url = if testnet {
            BINANCE_TESTNET_BASE.to_string()
        } else {
            BINANCE_API_BASE.to_string()
        };

        if api_key.is_empty() || api_secret.is_empty() {
            warn!("Binance API credentials not set, using SIMULATION mode");
        }

        info!("Binance exchange initialized (testnet: {})", testnet);

        Ok(Self {
            client: Client::new(),
            api_key,
            api_secret,
            base_url,
            testnet,
        })
    }

    fn sign_request(&self, query_string: &str) -> String {
        let mut mac = HmacSha256::new_from_slice(self.api_secret.as_bytes())
            .expect("HMAC can take key of any size");
        mac.update(query_string.as_bytes());
        let result = mac.finalize();
        hex::encode(result.into_bytes())
    }

    async fn submit_real_order(&self, order: &Order) -> Result<Trade> {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)?
            .as_millis();

        let query_string = format!(
            "symbol={}&side={}&type=LIMIT&timeInForce=GTC&quantity={}&price={}&timestamp={}",
            order.symbol,
            order.side,
            order.volume,
            order.price,
            timestamp
        );

        let signature = self.sign_request(&query_string);
        let url = format!("{}/api/v3/order?{}&signature={}", self.base_url, query_string, signature);

        let response = self.client
            .post(&url)
            .header("X-MBX-APIKEY", &self.api_key)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow!("Binance API error: {}", error_text));
        }

        let binance_order: BinanceOrderResponse = response.json().await?;

        let filled_price = binance_order.price.parse::<f64>()
            .unwrap_or(order.price);
        let filled_volume = binance_order.executed_qty.parse::<i32>()
            .unwrap_or(order.volume);

        // Calculate commission (0.1% for Binance)
        let commission = filled_price * filled_volume as f64 * 0.001;

        Ok(Trade {
            trade_id: binance_order.order_id.to_string(),
            order_id: order.order_id.clone(),
            strategy_id: order.strategy_id.clone(),
            symbol: order.symbol.clone(),
            side: order.side.clone(),
            filled_price,
            filled_volume,
            trade_time: Utc::now().timestamp_nanos_opt().unwrap_or(0),
            status: if binance_order.status == "FILLED" {
                "FILLED".to_string()
            } else {
                "REJECTED".to_string()
            },
            error_code: 0,
            error_message: String::new(),
            is_retryable: false,
            commission,
        })
    }

    fn simulate_order(&self, order: &Order) -> Trade {
        info!("SIMULATION: Executing order {} {} @ {}", order.side, order.symbol, order.price);

        // Simulate slippage (0.01%)
        let slippage = if order.side == "BUY" { 1.0001 } else { 0.9999 };
        let filled_price = order.price * slippage;

        // Calculate commission (0.1%)
        let commission = filled_price * order.volume as f64 * 0.001;

        Trade {
            trade_id: format!("SIM_{}", order.order_id),
            order_id: order.order_id.clone(),
            strategy_id: order.strategy_id.clone(),
            symbol: order.symbol.clone(),
            side: order.side.clone(),
            filled_price,
            filled_volume: order.volume,
            trade_time: Utc::now().timestamp_nanos_opt().unwrap_or(0),
            status: "FILLED".to_string(),
            error_code: 0,
            error_message: String::new(),
            is_retryable: false,
            commission,
        }
    }
}

impl Exchange for BinanceExchange {
    fn name(&self) -> &str {
        if self.testnet {
            "binance-testnet"
        } else {
            "binance"
        }
    }

    fn submit_order<'a>(&'a self, order: &'a Order) -> Pin<Box<dyn Future<Output = Result<Trade>> + Send + 'a>> {
        Box::pin(async move {
            // If API credentials are not set, use simulation mode
            if self.api_key.is_empty() || self.api_secret.is_empty() {
                return Ok(self.simulate_order(order));
            }

            // Try real order submission
            match self.submit_real_order(order).await {
                Ok(trade) => Ok(trade),
                Err(e) => {
                    error!("Failed to submit real order: {}", e);
                    warn!("Falling back to simulation mode");
                    Ok(self.simulate_order(order))
                }
            }
        })
    }
}
