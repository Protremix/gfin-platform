# GFIN — GitHub Environments & Branch Protection

**Status:** REQUIRES MANUAL GITHUB CONFIGURATION

These settings must be configured by the repository owner after the repository is created on GitHub. They cannot be configured from the current development environment.

---

## Branch Protection Rules

Configure on GitHub under Settings → Branches → Branch protection rules.

### `main` branch protection:
- ✅ Require a pull request before merging
  - Required approving reviews: 1 (minimum)
  - Dismiss stale pull request approvals when new commits are pushed
  - Require review from Code Owners
- ✅ Require status checks to pass before merging
  - Required checks: `Lint & Format`, `Type Check (MyPy)`, `Tests`, `Secret Scanning`, `Dependency Scanning`
  - Require branches to be up to date before merging
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings
- ❌ Do not allow force pushes
- ❌ Do not allow deletions

### `develop` branch protection (when created):
- Same as `main` but allow force pushes for rebasing if needed

---

## Environments

Configure on GitHub under Settings → Environments.

### `development`
- No protection rules
- No secrets (uses local/dev secrets only)
- Auto-deploy from `develop` branch

### `staging`
- Required reviewers: 1
- No production secrets
- Deploy from `main` branch or release tags

### `production`
- Required reviewers: 2
- Wait timer: 5 minutes
- Restricted to `main` branch
- Separate production secrets (stored in GitHub Secrets or external secret manager)
- DEPLOYMENT TO PRODUCTION IS NOT YET AUTHORIZED

---

## GitHub Secrets

Configure under Settings → Secrets and variables → Actions.

**Never commit secrets to the repository.** Use GitHub Secrets for CI/CD.

Required secrets (add when production infrastructure is ready):
- `OPENAI_PROJECT_KEY` — OpenAI API key for gpt-5.6-luna
- `PRODUCTION_DATABASE_URL` — PostgreSQL connection string
- `KAFKA_BOOTSTRAP_SERVERS` — Kafka broker addresses
- `REDIS_URL` — Redis connection string
- `S3_BUCKET_NAME` — Evidence storage bucket
- `KUBE_CONFIG` — Kubernetes configuration (production deploy)
- `NEO4J_URI` — Graph database connection
- `OPENSEARCH_URL` — Search index URL

**Current status:** No GitHub secrets are configured. Development uses local environment variables only.

---

## Dependency Management

### Lock Files
- `requirements.txt` — Python dependencies (currently using `pyproject.toml` with `pip install -e ".[test]"`)
- No `package-lock.json` or `go.sum` yet (JavaScript/Go dependencies not yet added)

### Vulnerability Alerts
- Enable GitHub Dependabot alerts (Settings → Code security)
- Enable Dependabot security updates
- CI workflow runs `pip-audit` and `safety check` on every PR

### Dependency Review
- Enable GitHub Dependency Review API for PRs
- The `dependency.yml` workflow runs dependency review on pull requests

### Automated Updates
- Configure Dependabot for Python ecosystem
- Do NOT auto-merge critical dependency updates — require manual review
- Weekly schedule for minor/patch updates
- Monthly schedule for major updates

---

## Status Summary

| Setting | Status |
|---------|--------|
| Repository created | REQUIRES MANUAL GITHUB CONFIGURATION |
| Repository private | REQUIRES MANUAL GITHUB CONFIGURATION |
| Branch protection (main) | REQUIRES MANUAL GITHUB CONFIGURATION |
| Environments (dev/staging/prod) | REQUIRES MANUAL GITHUB CONFIGURATION |
| GitHub Secrets | REQUIRES MANUAL GITHUB CONFIGURATION |
| Dependabot alerts | REQUIRES MANUAL GITHUB CONFIGURATION |
| Dependency review | REQUIRES MANUAL GITHUB CONFIGURATION |
| CODEOWNERS enforcement | REQUIRES MANUAL GITHUB CONFIGURATION |
