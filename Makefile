.PHONY: help build up down logs clean test

help:
	@echo "TTQuant 开发命令"
	@echo ""
	@echo "  make build    - 构建 Docker 镜像"
	@echo "  make up       - 启动所有服务"
	@echo "  make down     - 停止所有服务"
	@echo "  make logs     - 查看日志"
	@echo "  make clean    - 清理所有数据（危险！）"
	@echo "  make test     - 运行测试"
	@echo "  make restart  - 重启服务"
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

ps:
	docker compose -f docker/docker-compose.yml ps
