# GFIN — Development Environment

**Module:** 01
**Last Updated:** 2026-08-25

---

## Prerequisites

- Python 3.11+
- Go 1.22+ (for high-performance services)
- Docker (for containerized services)
- Git
- pre-commit (`pip install pre-commit`)

## Setup

```bash
# Clone the repository
git clone <repo-url> gfin
cd gfin

# Create virtual environment and install dependencies
make install

# Install pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env with real values (NEVER commit .env)
```

## Running

```bash
# Start development server
make dev

# Run tests
make test

# Run tests fast (no coverage)
make test-fast

# Lint
make lint

# Format
make format

# Type check
make typecheck

# Security scan
make security
```

## Project Structure

```
/gfin
  /apps          — User-facing applications (citizen-web, citizen-mobile, police-console)
  /services      — Backend microservices
  /packages      — Shared libraries (schemas, interfaces, events, auth, observability)
  /infrastructure — Infrastructure-as-Code (Kubernetes, Terraform)
  /tests         — Test suites (unit, integration, e2e, load, security)
  /docs          — Documentation
```

## Two-Layer Architecture

The project is built in two layers:

### Layer A — Application / MVP (current)
Implemented and tested in the current environment. Uses development adapters:
- Database: InMemoryEntityRepository (→ Base44 entities in later modules)
- Event Bus: InMemoryEventBus (→ Kafka in production)
- Search: EntitySearchService (→ OpenSearch in production)
- Storage: LocalObjectStorage (→ S3 in production)
- Graph: AdjacencyListGraph (→ Neo4j in production)
- Cache: MemoryCache (→ Redis in production)
- Identity: Base44IdentityProvider (→ OIDC/OAuth2 in production)
- Model Gateway: BaseModelGateway (→ OpenAI/local via gateway)

### Layer B — Production Infrastructure (not deployed from sandbox)
Infrastructure-as-Code and deployment manifests created for future deployment:
- Kubernetes manifests (`/infrastructure/kubernetes/`)
- Terraform configurations (`/infrastructure/terraform/`)
- Docker images (`Dockerfile` per service)
- CI/CD pipelines (`.github/workflows/`)

All Layer B components are marked **REQUIRES EXTERNAL INFRASTRUCTURE**.

## Dependency Management

Core dependencies are in `pyproject.toml`. Development dependencies are in the `[dev]` extras.

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Audit dependencies for vulnerabilities
pip-audit --strict
```

## Linting and Formatting

- **Linter:** Ruff (replaces flake8, isort, pyupgrade)
- **Formatter:** Ruff format (replaces black)
- **Type checker:** MyPy (strict mode)
- **Pre-commit:** Runs ruff, mypy, gitleaks, and general checks

Configuration in:
- `pyproject.toml` — ruff, mypy, pytest settings
- `.pre-commit-config.yaml` — pre-commit hooks

## Secret Scanning

- **Pre-commit:** Gitleaks runs on every commit
- **CI:** Gitleaks runs on every push/PR
- **Config:** `.gitleaks.toml` — includes GFIN-specific patterns
- **Gitignore:** `.env`, `*.pem`, `*.key`, `secrets/`, `credentials/` are ignored

## Dependency Scanning

- **pip-audit:** Scans installed packages for known vulnerabilities
- **safety:** Additional vulnerability check
- **CI:** Runs on every push/PR

## CI/CD

- **CI pipeline** (`.github/workflows/ci.yml`): lint, type check, test, secret scan, dependency scan
- **CD pipeline** (`.github/workflows/cd.yml`): build Docker images, deploy to Kubernetes
  - CD pipeline is **REQUIRES EXTERNAL INFRASTRUCTURE** — will not succeed until cloud environment is provisioned
