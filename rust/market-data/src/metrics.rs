// TODO: 实现性能指标收集和上报
pub struct MetricsCollector {
    // 延迟统计
    // 消息计数
    // 连接状态
}

impl MetricsCollector {
    pub fn new() -> Self {
        Self {}
    }

    pub fn record_latency(&mut self, _latency_ns: i64) {
        // TODO: 记录延迟
    }

    pub fn record_message(&mut self) {
        // TODO: 记录消息数
    }
}
