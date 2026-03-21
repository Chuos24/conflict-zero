.PHONY: help build up down logs migrate test lint clean

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Conflict Zero - Docker Compose Commands$(NC)"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Development Commands
build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	cd infrastructure && docker-compose build

build-no-cache: ## Build all Docker images without cache
	@echo "$(BLUE)Building Docker images (no cache)...$(NC)"
	cd infrastructure && docker-compose build --no-cache

up: ## Start all services in detached mode
	@echo "$(GREEN)Starting services...$(NC)"
	cd infrastructure && docker-compose up -d

up-nginx: ## Start all services with Nginx reverse proxy
	@echo "$(GREEN)Starting services with Nginx...$(NC)"
	cd infrastructure && docker-compose --profile nginx up -d

up-prod: ## Start services in production mode
	@echo "$(GREEN)Starting services in production mode...$(NC)"
	cd infrastructure && BACKEND_BUILD_TARGET=production FRONTEND_BUILD_TARGET=production docker-compose --profile nginx up -d

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	cd infrastructure && docker-compose down

down-volumes: ## Stop all services and remove volumes (⚠️ data loss)
	@echo "$(RED)Stopping services and removing volumes...$(NC)"
	cd infrastructure && docker-compose down -v

restart: down up ## Restart all services

restart-backend: ## Restart only the backend service
	@echo "$(YELLOW)Restarting backend...$(NC)"
	cd infrastructure && docker-compose restart backend

restart-frontend: ## Restart only the frontend service
	@echo "$(YELLOW)Restarting frontend...$(NC)"
	cd infrastructure && docker-compose restart frontend

# Database Commands
migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	cd infrastructure && docker-compose --profile migrate run --rm migrate

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	@echo "$(BLUE)Creating new migration: $(msg)...$(NC)"
	cd infrastructure && docker-compose exec backend poetry run alembic revision --autogenerate -m "$(msg)"

psql: ## Open PostgreSQL console
	@echo "$(BLUE)Opening PostgreSQL console...$(NC)"
	cd infrastructure && docker-compose exec postgres psql -U conflictzero -d conflictzero

redis-cli: ## Open Redis CLI
	@echo "$(BLUE)Opening Redis CLI...$(NC)"
	cd infrastructure && docker-compose exec redis redis-cli

# Logs
logs: ## View logs from all services
	cd infrastructure && docker-compose logs -f

logs-backend: ## View backend logs
	cd infrastructure && docker-compose logs -f backend

logs-frontend: ## View frontend logs
	cd infrastructure && docker-compose logs -f frontend

logs-db: ## View database logs
	cd infrastructure && docker-compose logs -f postgres

# Testing
test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd infrastructure && docker-compose exec backend poetry run pytest

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd infrastructure && docker-compose exec frontend npm test

# Code Quality
lint-backend: ## Run backend linters
	@echo "$(BLUE)Running backend linters...$(NC)"
	cd infrastructure && docker-compose exec backend poetry run black --check .
	cd infrastructure && docker-compose exec backend poetry run isort --check-only .
	cd infrastructure && docker-compose exec backend poetry run flake8 .
	cd infrastructure && docker-compose exec backend poetry run mypy .

lint-frontend: ## Run frontend linters
	@echo "$(BLUE)Running frontend linters...$(NC)"
	cd infrastructure && docker-compose exec frontend npm run lint

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend code...$(NC)"
	cd infrastructure && docker-compose exec backend poetry run black .
	cd infrastructure && docker-compose exec backend poetry run isort .

format-frontend: ## Format frontend code
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd infrastructure && docker-compose exec frontend npm run lint:fix

# Shell Access
shell-backend: ## Open shell in backend container
	cd infrastructure && docker-compose exec backend /bin/sh

shell-frontend: ## Open shell in frontend container
	cd infrastructure && docker-compose exec frontend /bin/sh

shell-db: ## Open shell in database container
	cd infrastructure && docker-compose exec postgres /bin/sh

# Status and Info
status: ## Show container status
	@echo "$(BLUE)Container Status:$(NC)"
	cd infrastructure && docker-compose ps

stats: ## Show resource usage statistics
	@echo "$(BLUE)Resource Usage:$(NC)"
	docker stats --no-stream

# Cleanup
clean: ## Remove stopped containers and unused images
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	docker system prune -f

clean-all: ## Remove all containers, images, and volumes (⚠️ complete cleanup)
	@echo "$(RED)WARNING: This will remove all Docker resources for this project!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	cd infrastructure && docker-compose down -v --rmi all --remove-orphans
	@echo "$(GREEN)Cleanup complete!$(NC)"

# Development Setup
setup: ## Initial setup - copy env file and build
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env file from .env.example$(NC)"; \
		echo "$(YELLOW)Please edit .env with your settings before starting services$(NC)"; \
	fi
	$(MAKE) build

# Health Check
health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@cd infrastructure && docker-compose ps | grep -q "healthy" && echo "$(GREEN)All services are healthy!$(NC)" || echo "$(YELLOW)Some services are not healthy. Check logs with: make logs$(NC)"
