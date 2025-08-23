# Alice AI Assistant - Development Makefile
# Professional-grade build automation for multi-component architecture

.PHONY: help dev test lint clean install up down logs build format check docker-build docker-push

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Project configuration
PYTHON := python3
PIP := pip3
NODE := node
NPM := npm
PROJECT_NAME := alice-ai
VENV_DIR := .venv
PYTHON_VERSION := $(shell python3 --version 2>/dev/null | cut -d' ' -f2)

help: ## Show this help message
	@echo "$(CYAN)Alice AI Assistant - Development Commands$(RESET)"
	@echo ""
	@echo "$(GREEN)Available commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Environment:$(RESET)"
	@echo "  Python: $(PYTHON_VERSION)"
	@echo "  Node: $(shell node --version 2>/dev/null || echo 'not found')"
	@echo "  Venv: $(VENV_DIR)"

install: ## Install all dependencies (Python backend + Node frontend + tools)
	@echo "$(CYAN)Installing Alice AI dependencies...$(RESET)"
	@echo "$(GREEN)1. Setting up Python virtual environment...$(RESET)"
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	@. $(VENV_DIR)/bin/activate && pip install --upgrade pip setuptools wheel
	@. $(VENV_DIR)/bin/activate && pip install -r server/requirements.txt
	@echo "$(GREEN)2. Installing development tools...$(RESET)"
	@. $(VENV_DIR)/bin/activate && pip install ruff black mypy pytest-cov pytest-xdist
	@echo "$(GREEN)3. Installing web frontend dependencies...$(RESET)"
	@cd web && npm install
	@echo "$(GREEN)4. Installing alice-tools dependencies...$(RESET)"
	@cd alice-tools && npm install
	@echo "$(GREEN)5. Installing nlu-agent dependencies...$(RESET)"
	@cd nlu-agent && npm install
	@echo "$(GREEN)All dependencies installed successfully!$(RESET)"

dev: ## Start development servers (backend + frontend)
	@echo "$(CYAN)Starting Alice development servers...$(RESET)"
	@echo "$(GREEN)Starting backend server (FastAPI)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && cd server && python app.py &
	@echo "$(GREEN)Starting frontend server (Next.js)...$(RESET)"
	@cd web && npm run dev &
	@echo "$(YELLOW)Both servers started. Backend: http://localhost:8000, Frontend: http://localhost:3000$(RESET)"
	@echo "$(YELLOW)Press Ctrl+C to stop all servers$(RESET)"
	@wait

dev-backend: ## Start only backend server
	@echo "$(CYAN)Starting Alice backend server...$(RESET)"
	@. $(VENV_DIR)/bin/activate && cd server && python app.py

dev-frontend: ## Start only frontend server
	@echo "$(CYAN)Starting Alice frontend server...$(RESET)"
	@cd web && npm run dev

test: ## Run all tests (backend + frontend + tools)
	@echo "$(CYAN)Running Alice AI test suite...$(RESET)"
	@echo "$(GREEN)1. Running backend tests (Python)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && cd server && python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)2. Running frontend unit tests...$(RESET)"
	@cd web && npm test -- --passWithNoTests
	@echo "$(GREEN)3. Running frontend E2E tests...$(RESET)"
	@cd web && npm run test:e2e
	@echo "$(GREEN)4. Running alice-tools tests...$(RESET)"
	@cd alice-tools && npm test -- --passWithNoTests
	@echo "$(GREEN)All tests completed!$(RESET)"

test-backend: ## Run only backend tests
	@echo "$(CYAN)Running backend tests...$(RESET)"
	@. $(VENV_DIR)/bin/activate && cd server && python -m pytest tests/ -v --cov=. --cov-report=term-missing

test-frontend: ## Run only frontend tests
	@echo "$(CYAN)Running frontend tests...$(RESET)"
	@cd web && npm test -- --passWithNoTests
	@cd web && npm run test:e2e

test-coverage: ## Generate test coverage reports
	@echo "$(CYAN)Generating coverage reports...$(RESET)"
	@. $(VENV_DIR)/bin/activate && cd server && python -m pytest tests/ --cov=. --cov-report=html --cov-report=term

lint: ## Run linting and formatting checks
	@echo "$(CYAN)Running Alice AI linting and formatting...$(RESET)"
	@echo "$(GREEN)1. Python linting (ruff)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && ruff check server/ --fix
	@echo "$(GREEN)2. Python formatting (black)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && black server/ --check --diff
	@echo "$(GREEN)3. Python type checking (mypy)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && mypy server/ --ignore-missing-imports
	@echo "$(GREEN)4. Frontend linting (ESLint)...$(RESET)"
	@cd web && npm run lint
	@echo "$(GREEN)5. TypeScript compilation check...$(RESET)"
	@cd web && npx tsc --noEmit
	@cd alice-tools && npx tsc --noEmit
	@cd nlu-agent && npx tsc --noEmit
	@echo "$(GREEN)All linting checks passed!$(RESET)"

format: ## Auto-format all code
	@echo "$(CYAN)Auto-formatting all code...$(RESET)"
	@echo "$(GREEN)1. Formatting Python code (black)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && black server/
	@echo "$(GREEN)2. Formatting Python imports (ruff)...$(RESET)"
	@. $(VENV_DIR)/bin/activate && ruff check server/ --fix
	@echo "$(GREEN)3. Formatting TypeScript/JavaScript (prettier)...$(RESET)"
	@cd web && npx prettier --write .
	@cd alice-tools && npx prettier --write src/
	@cd nlu-agent && npx prettier --write src/
	@echo "$(GREEN)All code formatted!$(RESET)"

check: ## Run comprehensive quality checks (lint + test + type check)
	@echo "$(CYAN)Running comprehensive quality checks...$(RESET)"
	@$(MAKE) lint
	@$(MAKE) test
	@echo "$(GREEN)All quality checks passed!$(RESET)"

clean: ## Clean build artifacts and caches
	@echo "$(CYAN)Cleaning Alice AI build artifacts...$(RESET)"
	@echo "$(GREEN)Removing Python cache and build files...$(RESET)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf server/htmlcov/
	@rm -rf server/.coverage
	@echo "$(GREEN)Removing Node.js build files...$(RESET)"
	@rm -rf web/.next/
	@rm -rf web/out/
	@rm -rf alice-tools/dist/
	@rm -rf nlu-agent/dist/
	@echo "$(GREEN)Removing test artifacts...$(RESET)"
	@rm -rf web/test-results/
	@rm -rf web/playwright-report/
	@echo "$(GREEN)Clean completed!$(RESET)"

up: ## Start all services using Docker Compose
	@echo "$(CYAN)Starting Alice AI services with Docker Compose...$(RESET)"
	@docker-compose up -d
	@echo "$(GREEN)Services started! Frontend: http://localhost:3000, Backend: http://localhost:8000$(RESET)"
	@echo "$(YELLOW)Run 'make logs' to view logs$(RESET)"

up-monitoring: ## Start all services including monitoring
	@echo "$(CYAN)Starting Alice AI services with monitoring...$(RESET)"
	@docker-compose --profile monitoring up -d
	@echo "$(GREEN)Services started with monitoring! Prometheus: http://localhost:9090$(RESET)"

down: ## Stop all Docker services
	@echo "$(CYAN)Stopping Alice AI Docker services...$(RESET)"
	@docker-compose down
	@echo "$(GREEN)All services stopped$(RESET)"

logs: ## Show logs from all services
	@echo "$(CYAN)Showing Alice AI service logs...$(RESET)"
	@docker-compose logs -f

build: ## Build all components for production
	@echo "$(CYAN)Building Alice AI for production...$(RESET)"
	@echo "$(GREEN)1. Building frontend...$(RESET)"
	@cd web && npm run build
	@echo "$(GREEN)2. Building alice-tools...$(RESET)"
	@cd alice-tools && npm run build 2>/dev/null || echo "No build script in alice-tools"
	@echo "$(GREEN)3. Building nlu-agent...$(RESET)"
	@cd nlu-agent && npm run build 2>/dev/null || echo "No build script in nlu-agent"
	@echo "$(GREEN)Production build completed!$(RESET)"

docker-build: ## Build Docker images
	@echo "$(CYAN)Building Alice AI Docker images...$(RESET)"
	@echo "$(GREEN)Building backend image...$(RESET)"
	@docker build -f Dockerfile.backend -t alice-backend:latest .
	@echo "$(GREEN)Building frontend image...$(RESET)"
	@docker build -f Dockerfile.frontend -t alice-frontend:latest .
	@echo "$(GREEN)Docker images built successfully!$(RESET)"

docker-push: ## Push Docker images to registry
	@echo "$(CYAN)Pushing Alice AI Docker images...$(RESET)"
	@echo "$(YELLOW)Configure DOCKER_REGISTRY environment variable first$(RESET)"
	@docker tag alice-backend:latest $(DOCKER_REGISTRY)/alice-backend:latest
	@docker tag alice-frontend:latest $(DOCKER_REGISTRY)/alice-frontend:latest
	@docker push $(DOCKER_REGISTRY)/alice-backend:latest
	@docker push $(DOCKER_REGISTRY)/alice-frontend:latest

# Environment check targets
check-python: ## Check Python environment
	@echo "$(CYAN)Python Environment Check:$(RESET)"
	@python3 --version || (echo "$(RED)Python 3 not found$(RESET)" && exit 1)
	@test -d $(VENV_DIR) || (echo "$(YELLOW)Virtual environment not found. Run 'make install'$(RESET)" && exit 1)
	@echo "$(GREEN)Python environment OK$(RESET)"

check-node: ## Check Node.js environment  
	@echo "$(CYAN)Node.js Environment Check:$(RESET)"
	@node --version || (echo "$(RED)Node.js not found$(RESET)" && exit 1)
	@npm --version || (echo "$(RED)npm not found$(RESET)" && exit 1)
	@echo "$(GREEN)Node.js environment OK$(RESET)"

check-env: check-python check-node ## Check all environment requirements
	@echo "$(GREEN)All environment checks passed!$(RESET)"

# Quick development workflow
quick-start: install dev ## Install dependencies and start development servers

# CI/CD friendly targets
ci-install: ## Install dependencies for CI environment
	@echo "$(CYAN)Installing dependencies for CI...$(RESET)"
	@python3 -m venv $(VENV_DIR)
	@. $(VENV_DIR)/bin/activate && pip install --upgrade pip
	@. $(VENV_DIR)/bin/activate && pip install -r server/requirements.txt
	@. $(VENV_DIR)/bin/activate && pip install ruff black mypy pytest-cov pytest-xdist
	@cd web && npm ci
	@cd alice-tools && npm ci
	@cd nlu-agent && npm ci

ci-test: ## Run tests in CI environment
	@$(MAKE) lint
	@$(MAKE) test-coverage
	@cd web && npm run test:e2e

# Development utilities
reset: clean install ## Clean everything and reinstall
	@echo "$(GREEN)Reset completed! Run 'make dev' to start development$(RESET)"

status: ## Show project status
	@echo "$(CYAN)Alice AI Project Status:$(RESET)"
	@echo "$(GREEN)Backend:$(RESET) FastAPI server in server/"
	@echo "$(GREEN)Frontend:$(RESET) Next.js application in web/"  
	@echo "$(GREEN)Tools:$(RESET) TypeScript utilities in alice-tools/"
	@echo "$(GREEN)NLU:$(RESET) NLU agent in nlu-agent/"
	@echo ""
	@echo "$(CYAN)Quick Start:$(RESET) make quick-start"
	@echo "$(CYAN)Development:$(RESET) make dev"
	@echo "$(CYAN)Testing:$(RESET) make test"
	@echo "$(CYAN)Linting:$(RESET) make lint"