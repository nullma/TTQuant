use anyhow::Result;
use chrono::{DateTime, Utc};
use sqlx::{PgPool, postgres::PgPoolOptions};
use tracing::{info, error, warn};
use std::time::Duration;

use crate::proto::{MarketData, Order, Trade};

/// 数据库连接池管理器
pub struct Database {
    pool: PgPool,
}

impl Database {
    /// 创建新的数据库连接
    pub async fn new(database_url: &str) -> Result<Self> {
        info!("Connecting to database: {}", database_url);

        let pool = PgPoolOptions::new()
            .max_connections(10)
            .min_connections(2)
            .acquire_timeout(Duration::from_secs(5))
            .connect(database_url)
            .await?;

        info!("Database connection pool created");

        Ok(Self { pool })
    }

    /// 批量写入行情数据
    pub async fn insert_market_data_batch(&self, data: &[MarketData]) -> Result<()> {
        if data.is_empty() {
            return Ok(());
        }

        let mut tx = self.pool.begin().await?;

        for md in data {
            let time = DateTime::from_timestamp_nanos(md.local_time);
            let exchange_time = DateTime::from_timestamp_nanos(md.exchange_time);

            sqlx::query(
                r#"
                INSERT INTO market_data (time, symbol, exchange, last_price, volume, exchange_time, local_time)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                "#
            )
            .bind(time)
            .bind(&md.symbol)
            .bind(&md.exchange)
            .bind(md.last_price)
            .bind(md.volume)
            .bind(exchange_time)
            .bind(time)
            .execute(&mut *tx)
            .await?;
        }

        tx.commit().await?;
        Ok(())
    }

    /// 写入单条行情数据
    pub async fn insert_market_data(&self, md: &MarketData) -> Result<()> {
        let time = DateTime::from_timestamp_nanos(md.local_time);
        let exchange_time = DateTime::from_timestamp_nanos(md.exchange_time);

        sqlx::query(
            r#"
            INSERT INTO market_data (time, symbol, exchange, last_price, volume, exchange_time, local_time)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            "#
        )
        .bind(time)
        .bind(&md.symbol)
        .bind(&md.exchange)
        .bind(md.last_price)
        .bind(md.volume)
        .bind(exchange_time)
        .bind(time)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    /// 写入订单记录
    pub async fn insert_order(&self, order: &Order) -> Result<()> {
        let time = DateTime::from_timestamp_nanos(order.timestamp);

        sqlx::query(
            r#"
            INSERT INTO orders (time, order_id, strategy_id, symbol, side, price, volume, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            "#
        )
        .bind(time)
        .bind(&order.order_id)
        .bind(&order.strategy_id)
        .bind(&order.symbol)
        .bind(&order.side)
        .bind(order.price)
        .bind(order.volume)
        .bind(order.timestamp)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    /// 写入成交记录
    pub async fn insert_trade(&self, trade: &Trade) -> Result<()> {
        let time = DateTime::from_timestamp_nanos(trade.trade_time);

        sqlx::query(
            r#"
            INSERT INTO trades (time, trade_id, order_id, strategy_id, symbol, side,
                              filled_price, filled_volume, trade_time, status,
                              error_code, error_message)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            "#
        )
        .bind(time)
        .bind(&trade.trade_id)
        .bind(&trade.order_id)
        .bind(&trade.strategy_id)
        .bind(&trade.symbol)
        .bind(&trade.side)
        .bind(trade.filled_price)
        .bind(trade.filled_volume)
        .bind(trade.trade_time)
        .bind(&trade.status)
        .bind(trade.error_code)
        .bind(&trade.error_message)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    /// 写入持仓快照
    pub async fn insert_position_snapshot(
        &self,
        strategy_id: &str,
        symbol: &str,
        position: i32,
        avg_price: f64,
        unrealized_pnl: f64,
    ) -> Result<()> {
        let time = Utc::now();

        sqlx::query(
            r#"
            INSERT INTO positions (time, strategy_id, symbol, position, avg_price, unrealized_pnl)
            VALUES ($1, $2, $3, $4, $5, $6)
            "#
        )
        .bind(time)
        .bind(strategy_id)
        .bind(symbol)
        .bind(position)
        .bind(avg_price)
        .bind(unrealized_pnl)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    /// 写入账户余额快照
    pub async fn insert_account_balance(
        &self,
        strategy_id: &str,
        balance: f64,
        frozen: f64,
        available: f64,
    ) -> Result<()> {
        let time = Utc::now();

        sqlx::query(
            r#"
            INSERT INTO account_balance (time, strategy_id, balance, frozen, available)
            VALUES ($1, $2, $3, $4, $5)
            "#
        )
        .bind(time)
        .bind(strategy_id)
        .bind(balance)
        .bind(frozen)
        .bind(available)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    /// 写入性能指标
    pub async fn insert_metrics(
        &self,
        component: &str,
        metric_name: &str,
        value: f64,
    ) -> Result<()> {
        let time = Utc::now();

        sqlx::query(
            r#"
            INSERT INTO metrics (time, component, metric_name, value)
            VALUES ($1, $2, $3, $4)
            "#
        )
        .bind(time)
        .bind(component)
        .bind(metric_name)
        .bind(value)
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    /// 健康检查
    pub async fn health_check(&self) -> Result<()> {
        sqlx::query("SELECT 1")
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    /// 获取连接池
    pub fn pool(&self) -> &PgPool {
        &self.pool
    }
}

/// 批量写入器 - 用于缓冲和批量写入行情数据
pub struct MarketDataBatchWriter {
    db: Database,
    buffer: Vec<MarketData>,
    batch_size: usize,
    flush_interval: Duration,
    last_flush: std::time::Instant,
}

impl MarketDataBatchWriter {
    pub fn new(db: Database, batch_size: usize, flush_interval_secs: u64) -> Self {
        Self {
            db,
            buffer: Vec::with_capacity(batch_size),
            batch_size,
            flush_interval: Duration::from_secs(flush_interval_secs),
            last_flush: std::time::Instant::now(),
        }
    }

    /// 添加行情数据到缓冲区
    pub async fn add(&mut self, md: MarketData) -> Result<()> {
        self.buffer.push(md);

        // 检查是否需要刷新
        if self.buffer.len() >= self.batch_size
            || self.last_flush.elapsed() >= self.flush_interval {
            self.flush().await?;
        }

        Ok(())
    }

    /// 强制刷新缓冲区
    pub async fn flush(&mut self) -> Result<()> {
        if self.buffer.is_empty() {
            return Ok(());
        }

        match self.db.insert_market_data_batch(&self.buffer).await {
            Ok(_) => {
                info!("Flushed {} market data records to database", self.buffer.len());
                self.buffer.clear();
                self.last_flush = std::time::Instant::now();
                Ok(())
            }
            Err(e) => {
                error!("Failed to flush market data: {}", e);
                // 保留缓冲区数据，下次重试
                Err(e)
            }
        }
    }

    /// 获取缓冲区大小
    pub fn buffer_size(&self) -> usize {
        self.buffer.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // 需要数据库连接
    async fn test_database_connection() {
        let db_url = "postgresql://ttquant:changeme@localhost:5432/ttquant_trading";
        let db = Database::new(db_url).await.unwrap();
        db.health_check().await.unwrap();
    }
}
