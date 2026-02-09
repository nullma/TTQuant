use anyhow::Result;
use prost::Message;
use std::time::Duration;

/// ZeroMQ Publisher 封装
pub struct ZmqPublisher {
    socket: zmq::Socket,
}

impl ZmqPublisher {
    pub fn new(endpoint: &str) -> Result<Self> {
        let context = zmq::Context::new();
        let socket = context.socket(zmq::PUB)?;
        socket.bind(endpoint)?;

        // 性能优化配置
        socket.set_sndhwm(1000)?;

        Ok(Self { socket })
    }

    /// 发送消息（Topic + Protobuf Data）
    pub fn send<T: Message>(&self, topic: &str, msg: &T) -> Result<()> {
        let mut buf = Vec::new();
        msg.encode(&mut buf)?;

        self.socket.send_multipart(&[topic.as_bytes(), &buf], 0)?;
        Ok(())
    }
}

/// ZeroMQ Subscriber 封装
pub struct ZmqSubscriber {
    socket: zmq::Socket,
}

impl ZmqSubscriber {
    pub fn new(endpoint: &str, topics: &[&str]) -> Result<Self> {
        let context = zmq::Context::new();
        let socket = context.socket(zmq::SUB)?;
        socket.connect(endpoint)?;

        // 订阅 topics
        for topic in topics {
            socket.set_subscribe(topic.as_bytes())?;
        }

        // 性能优化配置
        socket.set_rcvhwm(1000)?;

        Ok(Self { socket })
    }

    /// 非阻塞接收消息
    pub fn recv_nonblock<T: Message + Default>(&self) -> Result<Option<(String, T)>> {
        match self.socket.recv_multipart(zmq::DONTWAIT) {
            Ok(parts) if parts.len() == 2 => {
                let topic = String::from_utf8(parts[0].clone())?;
                let msg = T::decode(&parts[1][..])?;
                Ok(Some((topic, msg)))
            }
            Err(zmq::Error::EAGAIN) => Ok(None),
            Err(e) => Err(e.into()),
            _ => Ok(None),
        }
    }

    /// 阻塞接收消息（带超时）
    pub fn recv_timeout<T: Message + Default>(&self, timeout: Duration) -> Result<Option<(String, T)>> {
        self.socket.set_rcvtimeo(timeout.as_millis() as i32)?;

        match self.socket.recv_multipart(0) {
            Ok(parts) if parts.len() == 2 => {
                let topic = String::from_utf8(parts[0].clone())?;
                let msg = T::decode(&parts[1][..])?;
                Ok(Some((topic, msg)))
            }
            Err(zmq::Error::EAGAIN) => Ok(None),
            Err(e) => Err(e.into()),
            _ => Ok(None),
        }
    }
}

/// ZeroMQ Push 封装
pub struct ZmqPusher {
    socket: zmq::Socket,
}

impl ZmqPusher {
    pub fn new(endpoint: &str) -> Result<Self> {
        let context = zmq::Context::new();
        let socket = context.socket(zmq::PUSH)?;
        socket.connect(endpoint)?;
        socket.set_sndhwm(1000)?;

        Ok(Self { socket })
    }

    pub fn send<T: Message>(&self, msg: &T) -> Result<()> {
        let mut buf = Vec::new();
        msg.encode(&mut buf)?;
        self.socket.send(&buf, 0)?;
        Ok(())
    }
}

/// ZeroMQ Pull 封装
pub struct ZmqPuller {
    socket: zmq::Socket,
}

impl ZmqPuller {
    pub fn new(endpoint: &str) -> Result<Self> {
        let context = zmq::Context::new();
        let socket = context.socket(zmq::PULL)?;
        socket.bind(endpoint)?;
        socket.set_rcvhwm(1000)?;

        Ok(Self { socket })
    }

    pub fn recv<T: Message + Default>(&self) -> Result<T> {
        let msg = self.socket.recv_bytes(0)?;
        Ok(T::decode(&msg[..])?)
    }

    pub fn recv_nonblock<T: Message + Default>(&self) -> Result<Option<T>> {
        match self.socket.recv_bytes(zmq::DONTWAIT) {
            Ok(msg) => Ok(Some(T::decode(&msg[..])?)),
            Err(zmq::Error::EAGAIN) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::MarketData;

    #[test]
    fn test_pub_sub() {
        let pub_socket = ZmqPublisher::new("tcp://127.0.0.1:15555").unwrap();
        let sub_socket = ZmqSubscriber::new("tcp://127.0.0.1:15555", &["md."]).unwrap();

        std::thread::sleep(Duration::from_millis(100));

        let md = MarketData {
            symbol: "BTCUSDT".to_string(),
            last_price: 50000.0,
            volume: 1.5,
            exchange_time: 0,
            local_time: 0,
            exchange: "binance".to_string(),
        };

        pub_socket.send("md.BTCUSDT.binance", &md).unwrap();

        std::thread::sleep(Duration::from_millis(100));

        let result: Option<(String, MarketData)> = sub_socket.recv_nonblock().unwrap();
        assert!(result.is_some());
    }
}
