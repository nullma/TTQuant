use lazy_static::lazy_static;
use prometheus::{
    register_counter_vec, register_gauge_vec, register_histogram_vec, CounterVec, GaugeVec,
    HistogramVec, TextEncoder, Encoder,
};
use std::sync::Arc;
use axum::{
    routing::get,
    Router,
    response::IntoResponse,
    http::StatusCode,
};
use tracing::info;

lazy_static! {
    // 行情接收计数器
    pub static ref MARKET_DATA_RECEIVED: CounterVec = register_counter_vec!(
        "market_data_received_total",
        "Total number of market data messages received",
        &["exchange", "symbol"]
    ).unwrap();

    // 行情延迟直方图（毫秒）
    pub static ref MARKET_DATA_LATENCY: HistogramVec = register_histogram_vec!(
        "market_data_latency_ms",
        "Market data latency in milliseconds (exchange time to local time)",
        &["exchange", "symbol"],
        vec![1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0, 5000.0]
    ).unwrap();

    // WebSocket 连接状态
    pub static ref WS_CONNECTION_STATUS: GaugeVec = register_gauge_vec!(
        "ws_connection_status",
        "WebSocket connection status (1=connected, 0=disconnected)",
        &["exchange"]
    ).unwrap();

    // WebSocket 重连次数
    pub static ref WS_RECONNECT_COUNT: CounterVec = register_counter_vec!(
        "ws_reconnect_total",
        "Total number of WebSocket reconnections",
        &["exchange"]
    ).unwrap();

    // 消息解析错误
    pub static ref MESSAGE_PARSE_ERRORS: CounterVec = register_counter_vec!(
        "message_parse_errors_total",
        "Total number of message parsing errors",
        &["exchange", "error_type"]
    ).unwrap();

    // 数据库写入计数
    pub static ref DB_WRITES: CounterVec = register_counter_vec!(
        "db_writes_total",
        "Total number of database writes",
        &["table"]
    ).unwrap();

    // 数据库写入错误
    pub static ref DB_WRITE_ERRORS: CounterVec = register_counter_vec!(
        "db_write_errors_total",
        "Total number of database write errors",
        &["table", "error_type"]
    ).unwrap();

    // ZMQ 发布计数
    pub static ref ZMQ_PUBLISHED: CounterVec = register_counter_vec!(
        "zmq_published_total",
        "Total number of messages published via ZMQ",
        &["topic"]
    ).unwrap();

    // 最新价格（用于监控）
    pub static ref LAST_PRICE: GaugeVec = register_gauge_vec!(
        "market_last_price",
        "Last traded price for symbol",
        &["exchange", "symbol"]
    ).unwrap();

    // 24小时成交量
    pub static ref VOLUME_24H: GaugeVec = register_gauge_vec!(
        "market_volume_24h",
        "24-hour trading volume",
        &["exchange", "symbol"]
    ).unwrap();
}

pub struct MetricsCollector {
    exchange: String,
}

impl MetricsCollector {
    pub fn new(exchange: &str) -> Self {
        Self {
            exchange: exchange.to_string(),
        }
    }

    /// 记录行情接收
    pub fn record_market_data(&self, symbol: &str, latency_ms: f64, price: f64, volume: f64) {
        MARKET_DATA_RECEIVED
            .with_label_values(&[&self.exchange, symbol])
            .inc();

        MARKET_DATA_LATENCY
            .with_label_values(&[&self.exchange, symbol])
            .observe(latency_ms);

        LAST_PRICE
            .with_label_values(&[&self.exchange, symbol])
            .set(price);

        VOLUME_24H
            .with_label_values(&[&self.exchange, symbol])
            .set(volume);
    }

    /// 记录 WebSocket 连接状态
    pub fn set_connection_status(&self, connected: bool) {
        WS_CONNECTION_STATUS
            .with_label_values(&[&self.exchange])
            .set(if connected { 1.0 } else { 0.0 });
    }

    /// 记录重连
    pub fn record_reconnect(&self) {
        WS_RECONNECT_COUNT
            .with_label_values(&[&self.exchange])
            .inc();
    }

    /// 记录解析错误
    pub fn record_parse_error(&self, error_type: &str) {
        MESSAGE_PARSE_ERRORS
            .with_label_values(&[&self.exchange, error_type])
            .inc();
    }

    /// 记录数据库写入
    pub fn record_db_write(&self, table: &str) {
        DB_WRITES
            .with_label_values(&[table])
            .inc();
    }

    /// 记录数据库错误
    pub fn record_db_error(&self, table: &str, error_type: &str) {
        DB_WRITE_ERRORS
            .with_label_values(&[table, error_type])
            .inc();
    }

    /// 记录 ZMQ 发布
    pub fn record_zmq_publish(&self, topic: &str) {
        ZMQ_PUBLISHED
            .with_label_values(&[topic])
            .inc();
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
    info!("Starting metrics server on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
