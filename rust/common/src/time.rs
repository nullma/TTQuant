use std::time::{SystemTime, UNIX_EPOCH};

/// 获取当前时间戳（纳秒）
#[inline]
pub fn now_nanos() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos() as i64
}

/// 获取当前时间戳（微秒）
#[inline]
pub fn now_micros() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_micros() as i64
}

/// 获取当前时间戳（毫秒）
#[inline]
pub fn now_millis() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis() as i64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_time() {
        let nanos = now_nanos();
        let micros = now_micros();
        let millis = now_millis();

        assert!(nanos > 0);
        assert!(micros > 0);
        assert!(millis > 0);

        assert!(nanos / 1000 >= micros - 1);
        assert!(micros / 1000 >= millis - 1);
    }
}
