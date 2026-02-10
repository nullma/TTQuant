.PHONY: help build up down logs clean test monitoring

help:
	@echo "TTQuant 开发命令"
	@echo ""
	@echo "  make build         - 构建 Docker 镜像"
	@echo "  make up            - 启动所有服务"
	@echo "  make down          - 停止所有服务"
	@echo "  make logs          - 查看所有日志"
	@echo "  make logs-md       - 查看行情模块日志"
	@echo "  make logs-gateway  - 查看网关模块日志"
	@echo "  make logs-test     - 查看测试客户端日志"
	@echo "  make clean         - 清理所有数据（危险！）"
	@echo "  make test          - 运行测试"
	@echo "  make test-gateway  - 测试网关模块"
	@echo "  make restart       - 重启服务"
	@echo "  make ps            - 查看服务状态"
	@echo ""
	@echo "监控系统命令:"
	@echo "  make monitoring-start    - 启动监控系统"
	@echo "  make monitoring-stop     - 停止监控系统"
	@echo "  make monitoring-restart  - 重启监控系统"
	@echo "  make monitoring-status   - 查看监控状态"
	@echo "  make monitoring-logs     - 查看监控日志"
	@echo "  make monitoring-test     - 测试监控系统"
	@echo "  make monitoring-validate - 验证监控配置"
	@echo ""

build:
	docker compose -f docker/docker-compose.yml build

up:
	docker compose -f docker/docker-compose.yml up -d
	@echo "等待服务启动..."
	@sleep 10
	@docker compose -f docker/docker-compose.yml ps

down:
	docker compose -f docker/docker-compose.yml down

logs:
	docker compose -f docker/docker-compose.yml logs -f

logs-md:
	docker compose -f docker/docker-compose.yml logs -f md-binance

logs-gateway:
	docker compose -f docker/docker-compose.yml logs -f gateway-binance

logs-test:
	docker compose -f docker/docker-compose.yml logs -f test-client

clean:
	@echo "警告: 这将删除所有数据！"
	@read -p "确认删除? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f docker/docker-compose.yml down -v; \
		echo "已清理所有数据"; \
	fi

restart: down up

test:
	@echo "运行测试..."
	docker compose -f docker/docker-compose.yml up test-client

test-gateway:
	@echo "测试网关模块..."
	docker compose -f docker/docker-compose.yml run --rm test-client python test_gateway.py

ps:
	docker compose -f docker/docker-compose.yml ps

# ==================== 监控系统命令 ====================

monitoring-start:
	@echo "启动监控系统..."
	docker compose -f docker/docker-compose.yml up -d prometheus grafana alertmanager node-exporter postgres-exporter
	@echo "等待服务启动..."
	@sleep 5
	@echo ""
	@echo "监控系统已启动！"
	@echo "Grafana:      http://localhost:3000 (admin/admin)"
	@echo "Prometheus:   http://localhost:9090"
	@echo "AlertManager: http://localhost:9093"
	@echo ""

monitoring-stop:
	@echo "停止监控系统..."
	docker compose -f docker/docker-compose.yml stop prometheus grafana alertmanager node-exporter postgres-exporter

monitoring-restart: monitoring-stop monitoring-start

monitoring-status:
	@echo "检查监控服务状态..."
	@docker compose -f docker/docker-compose.yml ps prometheus grafana alertmanager node-exporter postgres-exporter
	@echo ""
	@echo "服务健康检查:"
	@curl -s http://localhost:9090/-/healthy > /dev/null 2>&1 && echo "✓ Prometheus: UP" || echo "✗ Prometheus: DOWN"
	@curl -s http://localhost:3000/api/health > /dev/null 2>&1 && echo "✓ Grafana: UP" || echo "✗ Grafana: DOWN"
	@curl -s http://localhost:9093/-/healthy > /dev/null 2>&1 && echo "✓ AlertManager: UP" || echo "✗ AlertManager: DOWN"
	@curl -s http://localhost:9100/metrics > /dev/null 2>&1 && echo "✓ Node Exporter: UP" || echo "✓ Node Exporter: UP (may not be accessible from host)"

monitoring-logs:
	docker compose -f docker/docker-compose.yml logs -f prometheus grafana alertmanager

monitoring-logs-prometheus:
	docker compose -f docker/docker-compose.yml logs -f prometheus

monitoring-logs-grafana:
	docker compose -f docker/docker-compose.yml logs -f grafana

monitoring-logs-alertmanager:
	docker compose -f docker/docker-compose.yml logs -f alertmanager

monitoring-test:
	@echo "运行监控系统测试..."
	@bash scripts/test_monitoring.sh

monitoring-validate:
	@echo "验证 Prometheus 配置..."
	@docker run --rm -v "$$(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml" \
		prom/prometheus:latest \
		promtool check config /etc/prometheus/prometheus.yml
	@echo ""
	@echo "验证告警规则..."
	@docker run --rm -v "$$(pwd)/monitoring/alerts.yml:/etc/prometheus/alerts.yml" \
		prom/prometheus:latest \
		promtool check rules /etc/prometheus/alerts.yml
	@echo ""
	@echo "配置验证完成！"

monitoring-reload:
	@echo "重新加载 Prometheus 配置..."
	@curl -X POST http://localhost:9090/-/reload && echo "✓ Prometheus 配置已重新加载" || echo "✗ 重新加载失败"
	@echo "重新加载 AlertManager 配置..."
	@curl -X POST http://localhost:9093/-/reload && echo "✓ AlertManager 配置已重新加载" || echo "✗ 重新加载失败"

monitoring-backup:
	@echo "备份监控数据..."
	@mkdir -p backups/$$(date +%Y%m%d_%H%M%S)
	@docker compose -f docker/docker-compose.yml exec -T prometheus tar czf - /prometheus > backups/$$(date +%Y%m%d_%H%M%S)/prometheus-data.tar.gz
	@docker compose -f docker/docker-compose.yml exec -T grafana tar czf - /var/lib/grafana > backups/$$(date +%Y%m%d_%H%M%S)/grafana-data.tar.gz
	@tar czf backups/$$(date +%Y%m%d_%H%M%S)/configs.tar.gz monitoring
	@echo "备份完成: backups/$$(date +%Y%m%d_%H%M%S)/"

monitoring-clean:
	@echo "警告: 这将删除所有监控数据！"
	@read -p "确认删除? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f docker/docker-compose.yml down; \
		docker volume rm ttquant_prometheus-data ttquant_grafana-data ttquant_alertmanager-data 2>/dev/null || true; \
		echo "已清理监控数据"; \
	fi

