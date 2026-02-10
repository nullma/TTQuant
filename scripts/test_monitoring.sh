#!/bin/bash
# TTQuant 监控系统测试脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# 测试计数器
TESTS_PASSED=0
TESTS_FAILED=0

# 测试函数
test_service() {
    local name=$1
    local url=$2
    local expected=$3

    if curl -s "$url" | grep -q "$expected"; then
        print_success "$name is accessible"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$name is not accessible"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 主测试流程
main() {
    print_header "TTQuant Monitoring System Tests"

    # 1. 测试 Prometheus
    print_header "Testing Prometheus"
    test_service "Prometheus Health" "http://localhost:9090/-/healthy" "Prometheus"
    test_service "Prometheus Targets" "http://localhost:9090/api/v1/targets" "activeTargets"
    test_service "Prometheus Rules" "http://localhost:9090/api/v1/rules" "groups"

    # 检查 Prometheus targets 状态
    print_info "Checking Prometheus targets status..."
    targets=$(curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"')
    echo "$targets"

    # 2. 测试 Grafana
    print_header "Testing Grafana"
    test_service "Grafana Health" "http://localhost:3000/api/health" "ok"
    test_service "Grafana Datasources" "http://localhost:3000/api/datasources" "Prometheus"

    # 3. 测试 AlertManager
    print_header "Testing AlertManager"
    test_service "AlertManager Health" "http://localhost:9093/-/healthy" "Healthy"
    test_service "AlertManager Status" "http://localhost:9093/api/v2/status" "cluster"

    # 4. 测试 Node Exporter
    print_header "Testing Node Exporter"
    test_service "Node Exporter Metrics" "http://localhost:9100/metrics" "node_cpu"

    # 5. 测试 Postgres Exporter
    print_header "Testing Postgres Exporter"
    test_service "Postgres Exporter Metrics" "http://localhost:9187/metrics" "pg_up"

    # 6. 测试应用指标端点
    print_header "Testing Application Metrics"

    # Market Data
    if curl -s http://localhost:8080/metrics > /dev/null 2>&1; then
        test_service "Market Data Metrics" "http://localhost:8080/metrics" "market_data"
    else
        print_info "Market Data service not running (optional)"
    fi

    # Gateway
    if curl -s http://localhost:8081/metrics > /dev/null 2>&1; then
        test_service "Gateway Metrics" "http://localhost:8081/metrics" "orders"
    else
        print_info "Gateway service not running (optional)"
    fi

    # Strategy Engine
    if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
        test_service "Strategy Engine Metrics" "http://localhost:8000/metrics" "strategy"
    else
        print_info "Strategy Engine not running (optional)"
    fi

    # 7. 测试指标查询
    print_header "Testing Metric Queries"

    # 查询 up 指标
    print_info "Querying 'up' metric..."
    up_result=$(curl -s 'http://localhost:9090/api/v1/query?query=up' | jq -r '.data.result[] | "\(.metric.job): \(.value[1])"')
    if [ -n "$up_result" ]; then
        print_success "Metric query successful"
        echo "$up_result"
        ((TESTS_PASSED++))
    else
        print_error "Metric query failed"
        ((TESTS_FAILED++))
    fi

    # 8. 测试告警规则
    print_header "Testing Alert Rules"

    print_info "Checking alert rules..."
    rules=$(curl -s http://localhost:9090/api/v1/rules | jq -r '.data.groups[] | .name')
    if [ -n "$rules" ]; then
        print_success "Alert rules loaded"
        echo "$rules"
        ((TESTS_PASSED++))
    else
        print_error "No alert rules found"
        ((TESTS_FAILED++))
    fi

    # 9. 测试 Grafana Dashboard
    print_header "Testing Grafana Dashboards"

    print_info "Checking dashboards..."
    # 注意：需要 Grafana API token 才能查询，这里只做基本检查
    if curl -s http://localhost:3000/api/search | grep -q "TTQuant"; then
        print_success "TTQuant dashboard found"
        ((TESTS_PASSED++))
    else
        print_info "Dashboard check skipped (requires authentication)"
    fi

    # 10. 性能测试
    print_header "Performance Tests"

    print_info "Testing Prometheus query performance..."
    start_time=$(date +%s%N)
    curl -s 'http://localhost:9090/api/v1/query?query=up' > /dev/null
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))

    if [ $duration -lt 1000 ]; then
        print_success "Query latency: ${duration}ms (good)"
        ((TESTS_PASSED++))
    else
        print_error "Query latency: ${duration}ms (slow)"
        ((TESTS_FAILED++))
    fi

    # 11. 数据完整性测试
    print_header "Data Integrity Tests"

    print_info "Checking metric data availability..."

    # 检查是否有最近的数据点
    recent_data=$(curl -s 'http://localhost:9090/api/v1/query?query=up' | jq -r '.data.result | length')
    if [ "$recent_data" -gt 0 ]; then
        print_success "Recent metric data available ($recent_data series)"
        ((TESTS_PASSED++))
    else
        print_error "No recent metric data found"
        ((TESTS_FAILED++))
    fi

    # 12. 配置验证
    print_header "Configuration Validation"

    print_info "Validating Prometheus configuration..."
    if docker run --rm -v "$(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml" \
        prom/prometheus:latest \
        promtool check config /etc/prometheus/prometheus.yml > /dev/null 2>&1; then
        print_success "Prometheus configuration is valid"
        ((TESTS_PASSED++))
    else
        print_error "Prometheus configuration is invalid"
        ((TESTS_FAILED++))
    fi

    print_info "Validating alert rules..."
    if docker run --rm -v "$(pwd)/monitoring/alerts.yml:/etc/prometheus/alerts.yml" \
        prom/prometheus:latest \
        promtool check rules /etc/prometheus/alerts.yml > /dev/null 2>&1; then
        print_success "Alert rules are valid"
        ((TESTS_PASSED++))
    else
        print_error "Alert rules are invalid"
        ((TESTS_FAILED++))
    fi

    # 测试总结
    print_header "Test Summary"

    TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed!${NC}\n"
        exit 0
    else
        echo -e "\n${RED}Some tests failed!${NC}\n"
        exit 1
    fi
}

# 运行测试
main
