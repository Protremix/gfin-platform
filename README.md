# GFIN — Global Fraud Intelligence Network

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Modules_00--09_Accepted-success.svg)](#current-project-status)
[![Tests](https://img.shields.io/badge/Tests-766_Passing-brightgreen.svg)](#running-tests)

**GFIN (Global Fraud Intelligence Network)** is a secure, evidence-based, internationally federated digital fraud intelligence platform designed to enable cross-jurisdictional intelligence sharing, threat analysis, and automated fraud mitigation.

---

## 🏛️ Mission & Core Principles

GFIN provides an internationally federated architecture for digital fraud intelligence sharing, governed strictly by ethical, legal, and cryptographic standards.

- **Evidence-Based:** Every intelligence unit is cryptographically verifiable, traceable, and backed by structured evidence chains.
- **Federated Architecture:** Enables cross-jurisdictional collaboration without centralizing sensitive operational data.
- **Constitutional Governance:** Fully governed by the **53-article GFIN-CEA Constitution v1.0**, enforcing strict compliance, privacy, auditability, and data ownership rules across all modules.

---

## 🏗️ Architecture Overview

GFIN is designed around a dual-layer architectural model and vendor-neutral AI provider integration:

```
                  +-----------------------------------+
                  |      GFIN-CEA Constitution v1.0   |
                  +-----------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                                                   |
  +---------------+                                   +---------------+
  |    Layer A    |                                   |    Layer B    |
  | (MVP / Local) |                                   | (Production)  |
  +---------------+                                   +---------------+
  | - In-Memory   |                                   | - PostgreSQL  |
  | - Lightweight |                                   | - OpenSearch  |
  | - Fast Tests  |                                   | - Neo4j / S3  |
  | - Zero Infra  |                                   | - Kafka / K8s |
  +---------------+                                   +---------------+
          |                                                   |
          +-------------------------+-------------------------+
                                    |
                        +-----------------------+
                        |     Model Gateway     |
                        | (OpenAI gpt-5.6-luna) |
                        +-----------------------+
```

### Two-Layer Architecture
1. **Layer A (MVP / In-Memory):**
   - In-memory execution layer designed for rapid local development, continuous integration, and lightweight unit/module verification.
   - Zero external infrastructure dependencies required.
2. **Layer B (Production):**
   - Production-grade federated distributed infrastructure.
   - **REQUIRES EXTERNAL INFRASTRUCTURE:** PostgreSQL, OpenSearch, Neo4j, Redis, Apache Kafka, AWS S3 / MinIO, Docker, and Kubernetes.

### AI Model Gateway
- **Provider Independence:** Decouples AI application logic from specific model vendors via a unified Model Gateway interface.
- **Primary Model:** OpenAI `gpt-5.6-luna` serves as the primary intelligence model for automated analysis, natural language querying, and threat classification.

### Core Technology Stack
- **Languages:** Python 3.11+ (FastAPI, Pydantic v2, Structlog), Go (high-performance processing services).
- **Data Stores:** PostgreSQL (relational), OpenSearch (log & threat search), Redis (caching & pub/sub), Neo4j (graph analysis), S3 (blob storage).
- **Messaging & Eventing:** Apache Kafka.
- **Orchestration & Containers:** Docker, Kubernetes.

---

## 📁 Repository Structure

```
gfin/
├── apps/             # End-user applications and frontend entrypoints
├── services/         # Microservices (API Gateway, Core Services, Go processing engines)
├── packages/         # Shared python modules (domain logic, gateways, intelligence components)
├── infrastructure/   # Terraform, Kubernetes manifests, Helm charts, Docker compose
├── tests/            # Test suites across all modules
├── docs/             # Technical specifications, architecture docs, and constitutional specs
├── tools/            # Developer tools, linting, and operational scripts
└── .github/          # GitHub Actions CI/CD workflows and issue/PR templates
```

---

## ⚙️ Development Environment Setup

### Prerequisites
- Python 3.11 or higher
- `pip` and `virtualenv`
- Git

### Quickstart Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/GFIN-Network/gfin.git
   cd gfin
   ```

2. **Set up Python Virtual Environment:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   make install
   # Or manually:
   pip install -e ".[dev]"
   pre-commit install
   ```

4. **Environment Configuration:**
   ```bash
   cp .env.example .env
   # Edit .env for local configuration options
   ```

---

## 🧪 Running Tests

GFIN maintains strict test coverage and verification standards across all modules.

Run the test suite:
```bash
pytest tests/ -v
```

Using `make` targets:
```bash
make test         # Run pytest with full coverage report
make test-fast    # Run pytest without coverage
```

Code quality and security checks:
```bash
make lint         # Run ruff check
make format       # Run ruff format & fix
make typecheck    # Run mypy strict type check
make security     # Run gitleaks, pip-audit, and safety checks
```

---

## 🧩 Module System (00–40)

GFIN is built using a modular system consisting of 41 planned modules (00 through 40), covering governance, ingestion, analysis, graph correlation, and federated exchange.

- **Modules 00–09:** Core Governance, Security, Infrastructure Intelligence, Model Gateway, and Foundation layer.
- **Modules 10–19:** Intelligence Ingestion, Entity Resolution, and Threat Telemetry.
- **Modules 20–29:** Graph Analytics, Pattern Detection, and Evidence Management.
- **Modules 30–40:** Federated Exchange, Multi-Jurisdictional Clearing, and Autonomous Defense.

### Current Project Status
- ✅ **Modules 00–09 Accepted** (Governance through Infrastructure Intelligence - Layer A).
- ✅ **766 tests passing** with high code coverage.

---

## 🤝 Contribution Workflow

We welcome contributions! All contributions must adhere to the GFIN-CEA Constitution v1.0 and follow our standard development workflow:

1. Create a feature branch off `main` following our naming standards (`feature/*`, `fix/*`, `security/*`, `docs/*`).
2. Implement your changes with corresponding tests.
3. Ensure all tests pass (`pytest tests/ -v`) and code quality checks pass (`make lint`, `make typecheck`).
4. Submit a Pull Request with the required PR template.

For detailed guidelines, code style, commit standards, and PR requirements, please see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🔒 Security & Privacy

Security is paramount to the GFIN platform:
- **Never commit credentials, API keys, or operational secrets.**
- **Never use real citizen data, law enforcement case data, or live evidence in tests or docs.** Use synthetic test data only (e.g., `TEST-PHONE-001`, `TEST-EMAIL-001`).
- To report a security vulnerability, follow our disclosure process in [SECURITY.md](SECURITY.md).

---

## 📄 License

This repository is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
