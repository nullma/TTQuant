#!/bin/bash
# TTQuant 监控系统管理脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/docker"
MONITORING_DIR="$SCRIPT_DIR/monitoring"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi

    print_info "Docker and Docker Compose are installed"
}

# 启动监控系统
start_monitoring() {
    print_info "Starting monitoring stack..."
    cd "$DOCKER_DIR"

    # 启动监控服务
    docker-compose up -d prometheus grafana alertmanager node-exporter postgres-exporter

    print_info "Waiting for services to be ready..."
    sleep 5

    # 检查服务状态
    check_status
}

# 停止监控系统
stop_monitoring() {
    print_info "Stopping monitoring stack..."
    cd "$DOCKER_DIR"

    docker-compose stop prometheus grafana alertmanager node-exporter postgres-exporter

    print_info "Monitoring stack stopped"
}

# 重启监控系统
restart_monitoring() {
    print_info "Restarting monitoring stack..."
    stop_monitoring
    sleep 2
    start_monitoring
}

# 检查服务状态
check_status() {
    print_info "Checking service status..."
    cd "$DOCKER_DIR"

    echo ""
    echo "=== Container Status ==="
    docker-compose ps prometheus grafana alertmanager node-exporter postgres-exporter

    echo ""
    echo "=== Service Health ==="

    # Prometheus
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        print_info "Prometheus: ${GREEN}UP${NC}"
    else
        print_error "Prometheus: ${RED}DOWN${NC}"
    fi

    # Grafana
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        print_info "Grafana: ${GREEN}UP${NC}"
    else
        print_error "Grafana: ${RED}DOWN${NC}"
    fi

    # AlertManager
    if curl -s http://localhost:9093/-/healthy > /dev/null 2>&1; then
        print_info "AlertManager: ${GREEN}UP${NC}"
    else
        print_error "AlertManager: ${RED}DOWN${NC}"
    fi

    # Node Exporter
    if curl -s http://localhost:9100/metrics > /dev/null 2>&1; then
        print_info "Node Exporter: ${GREEN}UP${NC}"
    else
        print_error "Node Exporter: ${RED}DOWN${NC}"
    fi

    echo ""
    echo "=== Access URLs ==="
    echo "Grafana:       http://localhost:3000 (admin/admin)"
    echo "Prometheus:    http://localhost:9090"
    echo "AlertManager:  http://localhost:9093"
    echo ""
}

# 查看日志
view_logs() {
    local service=$1
    cd "$DOCKER_DIR"

    if [ -z "$service" ]; then
        print_error "Please specify a service: prometheus, grafana, alertmanager"
        exit 1
    fi

    case $service in
        prometheus)
            docker-compose logs -f prometheus
            ;;
        grafana)
            docker-compose logs -f grafana
            ;;
        alertmanager)
            docker-compose logs -f alertmanager
            ;;
        *)
            print_error "Unknown service: $service"
            exit 1
            ;;
    esac
}

# 重新加载配置
reload_config() {
    print_info "Reloading Prometheus configuration..."
    if curl -X POST http://localhost:9090/-/reload > /dev/null 2>&1; then
        print_info "Prometheus configuration reloaded"
    else
        print_error "Failed to reload Prometheus configuration"
        print_warn "Trying to restart Prometheus..."
        cd "$DOCKER_DIR"
        docker-compose restart prometheus
    fi

    print_info "Reloading AlertManager configuration..."
    if curl -X POST http://localhost:9093/-/reload > /dev/null 2>&1; then
        print_info "AlertManager configuration reloaded"
    else
        print_error "Failed to reload AlertManager configuration"
        print_warn "Trying to restart AlertManager..."
        cd "$DOCKER_DIR"
        docker-compose restart alertmanager
    fi
}

# 验证配置
validate_config() {
    print_info "Validating Prometheus configuration..."

    if docker run --rm -v "$MONITORING_DIR/prometheus.yml:/etc/prometheus/prometheus.yml" \
        prom/prometheus:latest \
        promtool check config /etc/prometheus/prometheus.yml; then
        print_info "Prometheus configuration is valid"
    else
        print_error "Prometheus configuration is invalid"
        exit 1
    fi

    print_info "Validating alert rules..."

    if docker run --rm -v "$MONITORING_DIR/alerts.yml:/etc/prometheus/alerts.yml" \
        prom/prometheus:latest \
        promtool check rules /etc/prometheus/alerts.yml; then
        print_info "Alert rules are valid"
    else
        print_error "Alert rules are invalid"
        exit 1
    fi

    print_info "All configurations are valid"
}

# 备份数据
backup_data() {
    local backup_dir="$SCRIPT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    print_info "Backing up monitoring data to $backup_dir..."

    # 备份 Prometheus 数据
    cd "$DOCKER_DIR"
    docker-compose exec -T prometheus tar czf - /prometheus > "$backup_dir/prometheus-data.tar.gz"

    # 备份 Grafana 数据
    docker-compose exec -T grafana tar czf - /var/lib/grafana > "$backup_dir/grafana-data.tar.gz"

    # 备份配置文件
    tar czf "$backup_dir/configs.tar.gz" -C "$SCRIPT_DIR" monitoring

    print_info "Backup completed: $backup_dir"
}

# 清理数据
clean_data() {
    print_warn "This will delete all monitoring data!"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_info "Cancelled"
        exit 0
    fi

    print_info "Stopping monitoring stack..."
    cd "$DOCKER_DIR"
    docker-compose down

    print_info "Removing data volumes..."
    docker volume rm ttquant_prometheus-data ttquant_grafana-data ttquant_alertmanager-data 2>/dev/null || true

    print_info "Data cleaned"
}

# 显示帮助
show_help() {
    cat << EOF
TTQuant Monitoring System Management Script

Usage: $0 [command]

Commands:
    start       Start monitoring stack
    stop        Stop monitoring stack
    restart     Restart monitoring stack
    status      Check service status
    logs        View service logs (usage: $0 logs [service])
    reload      Reload configurations
    validate    Validate configurations
    backup      Backup monitoring data
    clean       Clean all monitoring data
    help        Show this help message

Examples:
    $0 start
    $0 status
    $0 logs prometheus
    $0 reload
    $0 validate

EOF
}

# 主函数
main() {
    check_docker

    case "${1:-}" in
        start)
            start_monitoring
            ;;
        stop)
            stop_monitoring
            ;;
        restart)
            restart_monitoring
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs "$2"
            ;;
        reload)
            reload_config
            ;;
        validate)
            validate_config
            ;;
        backup)
            backup_data
            ;;
        clean)
            clean_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: ${1:-}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
