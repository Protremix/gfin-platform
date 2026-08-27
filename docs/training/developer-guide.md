# GFIN Developer Guide & Monorepo Architecture

**Document Version:** 1.0  
**Target Audience:** Software Engineers, Security Developers, Core Contributors  
**Scope:** Architecture, Extensibility Patterns, Testing, CI/CD, and Development Standards  

---

## 1. Monorepo Repository Structure

The GFIN monorepo is structured cleanly into top-level directories separating user interfaces, microservices, shared Python packages, infrastructure manifests, test suites, and documentation:

```
/gfin
├── apps/                        # Frontend applications and portals
│   ├── citizen-mobile/          # Flutter citizen reporting mobile application
│   ├── citizen-web/             # React/Next.js citizen web portal
│   └── police-console/          # Vue.js law enforcement intelligence workstation
├── services/                    # Independent microservice entry points
│   ├── ai-gateway/              # Model routing & provider fallback gateway
│   ├── ai-orchestrator/         # AI Investigation Orchestrator service
│   ├── api-gateway/             # FastAPI/Nginx unified ingress gateway
│   ├── campaign/                # Campaign Lifecycle Engine service
│   ├── entity/                  # Entity Resolution & deduplication service
│   ├── evidence/                # Cryptographic Evidence Vault service
│   ├── fraud/                   # Fraud Intake, Scoring & Detection service
│   ├── police-api/              # Restricted Police REST API service
│   └── search/                  # OpenSearch/Neo4j unified search service
├── packages/                    # Core Python packages & domain models
│   ├── api/                     # Shared REST & gRPC API schemas
│   ├── auth/                    # RBAC/ABAC authorization & rate limiting
│   ├── common/                  # Database adapters, repositories, utils
│   ├── events/                  # Event Bus, Kafka schemas & DLQ
│   ├── observability/           # Health checks, Prometheus metrics, tracing
│   ├── production/              # Go/No-Go Gate evaluator (Module 40)
│   ├── schemas/                 # Canonical Pydantic entities (26) & models
│   ├── security/                # Access control matrix & threat scanners
│   └── services/                # Domain logic implementations (Layer A/B)
├── infrastructure/              # Infrastructure-as-code & deployments
│   ├── kafka/                   # Kafka topic definitions & cluster config
│   ├── kubernetes/              # K8s NetworkPolicies, ingress & manifests
│   ├── monitoring/              # Prometheus rules & Grafana dashboards
│   ├── security/                # Vault policy files & TLS PKI setup
│   └── terraform/               # Cloud resource provisioning scripts
├── tests/                       # Automated test suite (1,776 passing tests)
│   ├── unit/                    # Unit tests for packages and services
│   ├── contract/                # Integration contract & API tests
│   ├── e2e/                     # End-to-end user workflow tests
│   ├── fault_injection/         # Resilience & network failure tests
│   ├── load/                    # Locust/K6 performance load tests
│   ├── observability/           # Metrics & tracing verifications
│   ├── production/              # Production readiness gate tests
│   └── security/                # SAST/DAST & penetration verification
└── docs/                        # Complete project documentation suite
```

---

## 2. Architecture: Layer A (In-Memory) vs Layer B (Production)

GFIN enforces a strict two-layer architecture paradigm across all modules to decouple core business logic from external infrastructure dependencies:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        GFIN Core Service Interface                     │
└────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│ Layer A: In-Memory Adapter      │           │ Layer B: Production Adapter     │
│  - Python dicts & sets          │           │  - PostgreSQL + Alembic        │
│  - In-process asyncio queues     │           │  - Apache Kafka Cluster         │
│  - HashiCorp Vault Mock         │           │  - HashiCorp Vault Live PKI     │
│  - In-memory Graph & Search     │           │  - Neo4j Graph + OpenSearch     │
│  - Direct execution (No infra)  │           │  - Distributed K8s Cluster      │
└─────────────────────────────────┘           └─────────────────────────────────┘
```

- **Layer A (In-Memory MVP):** Fully functional, zero-external-dependency execution environment used for rapid development, testing, local verification, and CI pipelines.
- **Layer B (Production):** Distributed infrastructure adapters replacing Layer A in-memory repositories with PostgreSQL, Apache Kafka, OpenSearch, Neo4j, HashiCorp Vault, and OPA.

---

## 3. Package Dependency Map

The shared Python packages enforce a strict, acyclic dependency hierarchy:

```
[ schemas ] ──▶ [ common ] ──▶ [ auth ] ──▶ [ events ] ──▶ [ services ] ──▶ [ observability ]
```

- `schemas`: Canonical data models (Pydantic). No internal dependencies.
- `common`: Repositories, database base interfaces, utilities.
- `auth`: RBAC/ABAC policy engine, audit logging, rate limiting.
- `events`: Event Bus contracts, Kafka topic schemas, DLQ adapters.
- `services`: High-level domain logic (Entity Resolution, Campaign Engine, AI Orchestrator).
- `observability`: Metrics, health checks, distributed tracing wrapping services.

---

## 4. How-To Developer Guides

### 4.1 How to Add a New Entity Type

1. **Define Schema in `packages/schemas/entities.py`:**
```python
from pydantic import Field
from packages.schemas.base import BaseEntity
from packages.schemas.enums import EntityType

class SatelliteTerminalEntity(BaseEntity):
    """Satellite terminal infrastructure entity."""
    entity_type: EntityType = EntityType.SATELLITE_TERMINAL
    terminal_id: str = Field(..., description="Hardware IMEI/MAC or Terminal ID")
    provider: str = Field(..., description="Satellite network provider")
    associated_ip: str | None = None

    def calculate_normalized_value(self) -> str:
        return self.terminal_id.strip().upper()
```

2. **Register in `packages/schemas/__init__.py` and Enum:**
   Add `SATELLITE_TERMINAL = "satellite_terminal"` to `EntityType` enum and register in `ENTITY_TYPE_TO_CLASS`.

3. **Add Unit Test in `tests/unit/test_data_model.py`:**
```python
def test_satellite_terminal_entity_creation():
    entity = SatelliteTerminalEntity(terminal_id="SAT-9921-X", provider="Starlink")
    assert entity.normalized_value == "SAT-9921-X"
    assert entity.id.startswith("ENT-")
```

---

### 4.2 How to Add a New Fraud Detection Rule

1. **Implement Rule in `packages/services/fraud_detection.py`:**
```python
from packages.services.fraud_detection import FraudRule, Signal, Pattern

class RapidDomainRegistrationRule(FraudRule):
    """Detects rapid creation of multiple domains under the same registrant."""
    
    def evaluate(self, signals: list[Signal]) -> float:
        domain_signals = [s for s in signals if s.type == "DOMAIN_REGISTERED"]
        if len(domain_signals) >= 5:
            return 85.0  # Composite risk score boost
        return 0.0
```

2. **Register Rule in `FraudDetectionEngine`:**
```python
engine.register_rule(RapidDomainRegistrationRule(name="RAPID_DOMAIN_REG"))
```

---

### 4.3 How to Extend the Event Bus (New Topics & Subscribers)

1. **Define Topic in `packages/events/event_bus.py`:**
```python
# Add new topic constant
TOPIC_CRYPTO_MIXER_DETECTED = "crypto.mixer_detected"
```

2. **Register Subscriber:**
```python
def mixer_alert_handler(event: Event):
    print(f"Mixer detected for address: {event.payload['address']}")

event_bus.subscribe(TOPIC_CRYPTO_MIXER_DETECTED, mixer_alert_handler)
```

---

### 4.4 How to Add a New AI Model to the Gateway

1. **Extend Provider Adapter in `packages/services/model_gateway.py`:**
```python
class AnthropicModelAdapter(BaseModelAdapter):
    """Adapter for Claude model integration."""
    
    def generate(self, prompt: str, **kwargs) -> str:
        # Layer A mock or Layer B API call
        return f"[Claude-Response] Analyzed: {prompt[:30]}"
```

2. **Register Model Route in Gateway:**
```python
gateway.register_model("claude-3-5-sonnet", AnthropicModelAdapter())
```

---

## 5. Testing Strategy & Test Execution

GFIN mandates a multi-tiered testing strategy with 100% pass enforcement across all suites:

| Test Suite | Directory | Description | Execution Command |
|------------|-----------|-------------|-------------------|
| **Unit** | `tests/unit/` | Isolated logic & schema tests | `pytest tests/unit/` |
| **Contract** | `tests/contract/` | API schema & inter-service contracts | `pytest tests/contract/` |
| **Fault Injection** | `tests/fault_injection/` | Network delay, queue overflow, retry logic | `pytest tests/fault_injection/` |
| **Security** | `tests/security/` | Authz bypass, SQLi, XSS, classification leakage | `pytest tests/security/` |
| **Load** | `tests/load/` | Throughput, latency SLOs (5,000 req/s) | `pytest tests/load/` |

### Running Full Test Suite
```bash
pytest -v --cov=packages --cov=services
```

---

## 6. CI/CD Pipeline Overview

The CI/CD pipeline runs on every push and pull request via GitHub Actions (`.github/workflows/ci.yml`):

1. **Linting & Formatting:** Code style check via `ruff check .` and `ruff format --check .`.
2. **Type Checking:** Static typing check via `mypy packages/`.
3. **Unit & Integration Testing:** Pytest execution across Python 3.11/3.12 matrices.
4. **Security Scanning:** Bandit SAST scan + Trivy container vulnerability scan.
5. **Go/No-Go Evaluation:** `python -m packages.production.go_no_go_gates` sanity check.

---

## 7. Code Style and Formatting (Ruff)

GFIN follows Python PEP 8 standards enforced strictly via **Ruff**:

- **Line Length:** 100 characters maximum.
- **Import Ordering:** Sorted automatically (`isort` rules).
- **Docstrings:** Required for all public modules, classes, and functions (`Google` format).

```bash
# Run Ruff Auto-Fix
ruff check --fix .
ruff format .
```
