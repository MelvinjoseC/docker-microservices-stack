.PHONY: up down build logs restart status test test-unit clean backup restore benchmark

# Default shell
SHELL := /bin/bash

# Docker compose command
DC = docker compose

up:
	@echo "Starting the microservices stack..."
	$(DC) up -d --build
	@echo "Stack is running. Execute 'make status' to check container status."

down:
	@echo "Stopping the microservices stack..."
	$(DC) down

build:
	@echo "Building all Docker images..."
	$(DC) build

logs:
	@echo "Following logs of all services..."
	$(DC) logs -f

restart:
	@echo "Restarting all services..."
	$(DC) restart

status:
	@echo "Checking status of stack services..."
	$(DC) ps

test:
	@echo "Running local service health checks..."
	./scripts/healthcheck.sh localhost

test-unit:
	@echo "Running unit test suites across all services..."
	cd services/user-service && npm test
	cd services/catalog-service && go test -v ./...
	pytest services/order-service/tests
	pytest services/notification-service/tests

backup:
	@echo "Creating database backup..."
	./scripts/backup-db.sh

restore:
	@echo "Restoring database from latest backup..."
	@latest_backup=$$(ls -t backups/db_backup_*.tar.gz 2>/dev/null | head -n 1); \
	if [ -n "$$latest_backup" ]; then \
		./scripts/restore-db.sh "$$latest_backup"; \
	else \
		echo "No backup tarball found in backups/"; \
	fi

benchmark:
	@echo "Executing benchmark load test..."
	./scripts/load-test.sh localhost

clean:
	@echo "Tearing down the stack and wiping persistent volumes..."
	$(DC) down -v
	@echo "Volumes cleaned."
