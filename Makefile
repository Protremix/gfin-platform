# GFIN Makefile — Development Environment
# Usage: make help

.PHONY: help install dev lint format typecheck test test-fast security clean

PYTHON := python3.11
PIP := pip

help:
	@echo "GFIN Development Commands"
	@echo "  make install      — Install dependencies"
	@echo "  make dev          — Start development server"
	@echo "  make lint         — Run linter (ruff)"
	@echo "  make format       — Format code (ruff format)"
	@echo "  make typecheck     — Type check (mypy)"
	@echo "  make test         — Run all tests"
	@echo "  make test-fast    — Run tests (no coverage)"
	@echo "  make security     — Run security scans"
	@echo "  make clean        — Clean build artifacts"

install:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && $(PIP) install -e ".[dev]"
	pre-commit install
	@echo "✓ Development environment installed"
	@echo "  Activate: source .venv/bin/activate"

dev:
	uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check packages services tests

format:
	ruff format packages services tests
	ruff check --fix packages services tests

typecheck:
	mypy packages services --strict --ignore-missing-imports

test:
	pytest tests/ -v --tb=short --cov=packages --cov=services --cov-report=term-missing

test-fast:
	pytest tests/ -v --tb=short --no-cov

security:
	@echo "Running secret scan..."
	gitleaks detect --config .gitleaks.toml --no-banner
	@echo "Running dependency audit..."
	pip-audit --strict
	@echo "Running safety check..."
	safety check --short-report || true

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -f coverage.xml .coverage
