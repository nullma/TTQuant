use lazy_static::lazy_static;
use prometheus::{
    register_counter_vec, register_gauge_vec, register_histogram_vec, CounterVec, GaugeVec,
    HistogramVec, TextEncoder, Encoder,
};
use axum::{
    routing::get,
    Router,
    response::IntoResponse,
    http::StatusCode,
};
use tracing::info;

lazy_static! {
    // 订单总数
    pub static ref ORDERS_TOTAL: CounterVec = register_counter_vec!(
        "orders_total",
        "Total number of orders received",
        &["exchange", "symbol", "side"]
    ).unwrap();

    // 订单成功数
    pub static ref ORDERS_SUCCESS: CounterVec = register_counter_vec!(
        "orders_success_total",
        "Total number of successful orders",
        &["exchange", "symbol", "side"]
    ).unwrap();

    // 订单失败数
    pub static ref ORDERS_FAILED: CounterVec = register_counter_vec!(
        "orders_failed_total",
        "Total number of failed orders",
        &["exchange", "symbol", "side", "error_type"]
    ).unwrap();

    // 风控拒单数
    pub static ref ORDERS_RISK_REJECTED: CounterVec = register_counter_vec!(
        "orders_risk_rejected_total",
        "Total number of orders rejected by risk management",
        &["exchange", "reason"]
    ).unwrap();

    // 订单处理延迟（毫秒）
    pub static ref ORDER_PROCESSING_LATENCY: HistogramVec = register_histogram_vec!(
        "order_processing_latency_ms",
        "Order processing latency in milliseconds",
        &["exchange", "side"],
        vec![1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0, 2000.0, 5000.0]
    ).unwrap();

    // 成交统计
    pub static ref TRADES_TOTAL: CounterVec = register_counter_vec!(
        "trades_total",
        "Total number of trades executed",
        &["exchange", "symbol", "side"]
    ).unwrap();

    // 成交金额
    pub static ref TRADE_VOLUME: CounterVec = register_counter_vec!(
        "trade_volume_total",
        "Total trading volume in USD",
        &["exchange", "symbol"]
    ).unwrap();

    // 手续费
    pub static ref COMMISSION_PAID: CounterVec = register_counter_vec!(
        "commission_paid_total",
        "Total commission paid in USD",
        &["exchange", "symbol"]
    ).unwrap();

    // 当前持仓
    pub static ref CURRENT_POSITION: GaugeVec = register_gauge_vec!(
        "current_position",
        "Current position size",
        &["exchange", "symbol", "strategy_id"]
    ).unwrap();

    // API 限流计数
    pub static ref API_RATE_LIMIT_HIT: CounterVec = register_counter_vec!(
        "api_rate_limit_hit_total",
        "Total number of times API rate limit was hit",
        &["exchange", "endpoint"]
    ).unwrap();

    // 重试次数
    pub static ref ORDER_RETRIES: CounterVec = register_counter_vec!(
        "order_retries_total",
        "Total number of order retries",
        &["exchange", "reason"]
    ).unwrap();

    // 活跃订单数
    pub static ref ACTIVE_ORDERS: GaugeVec = register_gauge_vec!(
        "active_orders",
        "Number of active orders",
        &["exchange", "symbol"]
    ).unwrap();

    // 风控指标
    pub static ref RISK_EXPOSURE: GaugeVec = register_gauge_vec!(
        "risk_exposure_usd",
        "Current risk exposure in USD",
        &["exchange", "strategy_id"]
    ).unwrap();

    // 最大回撤
    pub static ref MAX_DRAWDOWN: GaugeVec = register_gauge_vec!(
        "max_drawdown_usd",
        "Maximum drawdown in USD",
        &["strategy_id"]
    ).unwrap();
}

pub struct GatewayMetrics {
    exchange: String,
}

impl GatewayMetrics {
    pub fn new(exchange: &str) -> Self {
        Self {
            exchange: exchange.to_string(),
        }
    }

    /// 记录订单接收
    pub fn record_order_received(&self, symbol: &str, side: &str) {
        ORDERS_TOTAL
            .with_label_values(&[&self.exchange, symbol, side])
            .inc();
    }

    /// 记录订单成功
    pub fn record_order_success(&self, symbol: &str, side: &str, latency_ms: f64) {
        ORDERS_SUCCESS
            .with_label_values(&[&self.exchange, symbol, side])
            .inc();

        ORDER_PROCESSING_LATENCY
            .with_label_values(&[&self.exchange, side])
            .observe(latency_ms);
    }

    /// 记录订单失败
    pub fn record_order_failed(&self, symbol: &str, side: &str, error_type: &str) {
        ORDERS_FAILED
            .with_label_values(&[&self.exchange, symbol, side, error_type])
            .inc();
    }

    /// 记录风控拒单
    pub fn record_risk_rejection(&self, reason: &str) {
        ORDERS_RISK_REJECTED
            .with_label_values(&[&self.exchange, reason])
            .inc();
    }

    /// 记录成交
    pub fn record_trade(&self, symbol: &str, side: &str, volume: f64, commission: f64) {
        TRADES_TOTAL
            .with_label_values(&[&self.exchange, symbol, side])
            .inc();

        TRADE_VOLUME
            .with_label_values(&[&self.exchange, symbol])
            .inc_by(volume);

        COMMISSION_PAID
            .with_label_values(&[&self.exchange, symbol])
            .inc_by(commission);
    }

    /// 更新持仓
    pub fn update_position(&self, symbol: &str, strategy_id: &str, position: f64) {
        CURRENT_POSITION
            .with_label_values(&[&self.exchange, symbol, strategy_id])
            .set(position);
    }

    /// 记录 API 限流
    pub fn record_rate_limit(&self, endpoint: &str) {
        API_RATE_LIMIT_HIT
            .with_label_values(&[&self.exchange, endpoint])
            .inc();
    }

    /// 记录重试
    pub fn record_retry(&self, reason: &str) {
        ORDER_RETRIES
            .with_label_values(&[&self.exchange, reason])
            .inc();
    }

    /// 更新活跃订单数
    pub fn update_active_orders(&self, symbol: &str, count: i64) {
        ACTIVE_ORDERS
            .with_label_values(&[&self.exchange, symbol])
            .set(count as f64);
    }

    /// 更新风险敞口
    pub fn update_risk_exposure(&self, strategy_id: &str, exposure: f64) {
        RISK_EXPOSURE
            .with_label_values(&[&self.exchange, strategy_id])
            .set(exposure);
    }

    /// 更新最大回撤
    pub fn update_max_drawdown(&self, strategy_id: &str, drawdown: f64) {
        MAX_DRAWDOWN
            .with_label_values(&[strategy_id])
            .set(drawdown);
    }
}

/// Metrics HTTP handler
async fn metrics_handler() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();

    match encoder.encode_to_string(&metric_families) {
        Ok(metrics) => (StatusCode::OK, metrics),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Failed to encode metrics: {}", e),
        ),
    }
}

/// Health check handler
async fn health_handler() -> impl IntoResponse {
    (StatusCode::OK, "OK")
}

/// Start metrics HTTP server
pub async fn start_metrics_server(port: u16) -> anyhow::Result<()> {
    let app = Router::new()
        .route("/metrics", get(metrics_handler))
        .route("/health", get(health_handler));

    let addr = format!("0.0.0.0:{}", port);
    info!("Starting gateway metrics server on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
