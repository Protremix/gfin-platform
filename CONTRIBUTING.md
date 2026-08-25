# Contributing to GFIN

Thank you for contributing to the Global Fraud Intelligence Network (GFIN). As an internationally federated, evidence-based fraud intelligence platform, GFIN maintains rigorous standards for code quality, security, and governance under the **GFIN-CEA Constitution v1.0**.

Please read this guide before submitting any pull requests or issue reports.

---

## 🌿 Branching Strategy

The `main` branch is protected and contains production-ready or accepted module code. Direct commits to `main` are restricted.

All development must occur on dedicated branches matching the following conventions:

- `feature/module-XX-short-description` — New features or module components
- `fix/module-XX-short-description` — Bug fixes
- `security/short-description` — Security fixes and hardening
- `docs/short-description` — Documentation updates and additions

Example branch names:
- `feature/module-03-audit-logger`
- `fix/module-01-token-parsing`
- `security/sanitize-gateway-inputs`

---

## 📝 Commit Conventions

Commit messages must follow structured prefix formats referencing the affected module or sub-system:

```
<type>(module-XX): <short summary>

[optional body]
```

### Allowed Commit Types:
- `feat`: A new feature or capability
- `fix`: A bug fix
- `test`: Adding or refactoring test suites
- `docs`: Documentation updates only
- `refactor`: Code changes that neither fix bugs nor add features
- `sec`: Security improvements or secret handling fixes
- `chore`: Maintenance tasks, dependency updates, build configurations

### Examples:
- `feat(module-02): implement model gateway fallback handling`
- `fix(module-05): address null pointer in entity resolution engine`
- `test(module-08): add unit tests for cryptographic signature verifier`

---

## 🔀 Pull Request (PR) Process

1. **Prerequisites:**
   - Ensure your code adheres to all requirements in this document.
   - All existing and new tests must pass (`pytest tests/ -v`).
   - Linting, formatting, and type checks must pass without warnings (`make lint`, `make typecheck`).

2. **PR Submission:**
   - Create a PR from your feature branch against `main`.
   - Complete the standard PR template, detailing the changes, context, module affected, and test coverage provided.

3. **CI Pipeline Checks:**
   - Automated CI checks will run on all PRs (linting, type checks, unit tests, secret scanning with `gitleaks`, dependency audits).
   - PRs cannot be merged until all CI checks pass.

4. **Code Review:**
   - At least one code review and approval from a designated maintainer is required before merging.
   - Code reviews enforce compliance with the 53-article GFIN-CEA Constitution v1.0.

---

## 🧪 Testing Requirements

Testing is mandatory for all code contributions.

- **100% Mandatory Test Coverage for New Features:** Every new function, endpoint, or package must include corresponding tests in `tests/`.
- **Run Tests Locally:**
  ```bash
  pytest tests/ -v
  ```
- **Layer A Compatibility:** Tests must pass in Layer A (in-memory execution) without requiring external Layer B infrastructure services (PostgreSQL, Kafka, OpenSearch, etc.). Use mocks, synthetic test fixtures, and in-memory implementations for Layer A testing.

---

## 🎨 Code Style & Quality Standards

GFIN uses **Ruff** for linting/formatting and **MyPy** for static type checking.

1. **Python Version:** Python 3.11+
2. **Formatting & Linting:**
   ```bash
   ruff check packages services tests
   ruff format packages services tests
   ```
3. **Type Annotations & Checking:**
   - All python code must use explicit type annotations (`strict = true` mode in MyPy).
   ```bash
   mypy packages services --strict
   ```
4. **Error Handling & Logging:**
   - Use structured logging with `structlog`.
   - Never suppress exceptions silently without logging context.

---

## 📚 Documentation Requirements

Documentation is treated with equal importance as code.

- **Code Changes Require Doc Updates:** If a PR modifies existing APIs, configurations, architecture, or workflows, update the relevant documentation in `docs/` or module READMEs.
- **Inline Documentation:** All public functions, classes, and modules must include Google-style or NumPy-style docstrings.

---

## 🛡️ Security & Privacy Requirements

Given GFIN's mission in fraud intelligence, strictly observe the following security constraints:

1. **No Credentials or Secrets:**
   - NEVER commit API keys, passwords, private keys, authorization tokens, or environment credentials.
   - `gitleaks` is run on every commit; commits containing detected secrets will be rejected.

2. **Synthetic Test Data Only:**
   - NEVER use real citizen data, police case information, real financial accounts, or live evidence in code, tests, or documentation.
   - Always use synthetic identifiers formatted as:
     - Phone: `TEST-PHONE-001`, `TEST-PHONE-002`
     - Email: `TEST-EMAIL-001@example.com`
     - Account: `TEST-ACCT-001`
     - Entity ID: `TEST-ENTITY-001`

3. **Input Sanitization:**
   - Validate and sanitize all inputs at entry boundaries (API Gateway, Model Gateway).

Thank you for helping build a secure and federated fraud intelligence platform!
