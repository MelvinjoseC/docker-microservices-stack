.PHONY: up down build logs restart status test clean

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

clean:
	@echo "Tearing down the stack and wiping persistent volumes..."
	$(DC) down -v
	@echo "Volumes cleaned."
