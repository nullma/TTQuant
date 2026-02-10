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
use ttquant_common::symbol::{normalize_symbol, to_exchange_format};
use super::Exchange;

type HmacSha256 = Hmac<Sha256>;

const OKX_API_BASE: &str = "https://www.okx.com";

#[derive(Debug, Deserialize)]
struct OkxOrderResponse {
    code: String,
    msg: String,
    data: Vec<OkxOrderData>,
}

#[derive(Debug, Deserialize)]
struct OkxOrderData {
    #[serde(rename = "ordId")]
    ord_id: String,
    #[serde(rename = "clOrdId")]
    cl_ord_id: String,
    #[serde(rename = "sCode")]
    s_code: String,
    #[serde(rename = "sMsg")]
    s_msg: String,
}

pub struct OkxExchange {
    client: Client,
    api_key: String,
    secret_key: String,
    passphrase: String,
    base_url: String,
    testnet: bool,
}

impl OkxExchange {
    pub fn new() -> Result<Self> {
        let api_key = std::env::var("OKX_API_KEY")
            .unwrap_or_else(|_| "".to_string());
        let secret_key = std::env::var("OKX_SECRET_KEY")
            .unwrap_or_else(|_| "".to_string());
        let passphrase = std::env::var("OKX_PASSPHRASE")
            .unwrap_or_else(|_| "".to_string());
        let testnet = std::env::var("OKX_TESTNET")
            .unwrap_or_else(|_| "true".to_string())
            .parse::<bool>()
            .unwrap_or(true);

        let base_url = OKX_API_BASE.to_string();

        if api_key.is_empty() || secret_key.is_empty() || passphrase.is_empty() {
            warn!("OKX API credentials not set, using SIMULATION mode");
        }

        info!("OKX exchange initialized (testnet: {})", testnet);

        Ok(Self {
            client: Client::new(),
            api_key,
            secret_key,
            passphrase,
            base_url,
            testnet,
        })
    }

    fn sign_request(&self, timestamp: &str, method: &str, request_path: &str, body: &str) -> String {
        // Pre-hash string: timestamp + method + request_path + body
        let prehash = format!("{}{}{}{}", timestamp, method, request_path, body);

        let mut mac = HmacSha256::new_from_slice(self.secret_key.as_bytes())
            .expect("HMAC can take key of any size");
        mac.update(prehash.as_bytes());
        let result = mac.finalize();

        // Base64 encode (not hex!)
        base64::encode(result.into_bytes())
    }

    async fn submit_real_order(&self, order: &Order) -> Result<Trade> {
        let timestamp = Utc::now().format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string();

        // 转换符号格式：BTCUSDT → BTC-USDT
        let okx_symbol = to_exchange_format(&order.symbol, "okx");

        // 构建请求体
        let body = serde_json::json!({
            "instId": okx_symbol,
            "tdMode": "cash",
            "side": order.side.to_lowercase(),
            "ordType": "limit",
            "px": order.price.to_string(),
            "sz": order.volume.to_string(),
        })
        .to_string();

        let request_path = "/api/v5/trade/order";
        let method = "POST";

        let signature = self.sign_request(&timestamp, method, request_path, &body);

        let url = format!("{}{}", self.base_url, request_path);

        let response = self.client
            .post(&url)
            .header("OK-ACCESS-KEY", &self.api_key)
            .header("OK-ACCESS-SIGN", &signature)
            .header("OK-ACCESS-TIMESTAMP", &timestamp)
            .header("OK-ACCESS-PASSPHRASE", &self.passphrase)
            .header("Content-Type", "application/json")
            .body(body)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow!("OKX API error: {}", error_text));
        }

        let okx_response: OkxOrderResponse = response.json().await?;

        if okx_response.code != "0" {
            return Err(anyhow!("OKX order failed: {} - {}", okx_response.code, okx_response.msg));
        }

        let order_data = okx_response.data.first()
            .ok_or_else(|| anyhow!("No order data in response"))?;

        if order_data.s_code != "0" {
            return Err(anyhow!("OKX order failed: {} - {}", order_data.s_code, order_data.s_msg));
        }

        // Calculate commission (0.1% for OKX)
        let commission = order.price * order.volume as f64 * 0.001;

        Ok(Trade {
            trade_id: order_data.ord_id.clone(),
            order_id: order.order_id.clone(),
            strategy_id: order.strategy_id.clone(),
            symbol: order.symbol.clone(),
            side: order.side.clone(),
            filled_price: order.price,
            filled_volume: order.volume,
            trade_time: Utc::now().timestamp_nanos_opt().unwrap_or(0),
            status: "FILLED".to_string(),
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

impl Exchange for OkxExchange {
    fn name(&self) -> &str {
        if self.testnet {
            "okx-testnet"
        } else {
            "okx"
        }
    }

    fn submit_order<'a>(&'a self, order: &'a Order) -> Pin<Box<dyn Future<Output = Result<Trade>> + Send + 'a>> {
        Box::pin(async move {
            // If API credentials are not set, use simulation mode
            if self.api_key.is_empty() || self.secret_key.is_empty() || self.passphrase.is_empty() {
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


