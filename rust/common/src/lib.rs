pub mod proto {
    include!(concat!(env!("OUT_DIR"), "/ttquant.rs"));
}

pub mod zmq_wrapper;
pub mod config;
pub mod time;

pub use proto::{MarketData, Order, Trade, Metrics};
