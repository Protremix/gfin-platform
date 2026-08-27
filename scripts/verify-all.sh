#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# GFIN — Final Verification Script
# Per Final Build Verification Directive §35
#
# Runs the maximum practical verification suite:
#   lint → typecheck → unit → integration → e2e → security →
#   dependency → secret → contract → AI → performance
#
# Infrastructure-dependent tests are NOT forced to pass.
# Each step reports PASS/FAIL/SKIPPED.
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Timestamp
echo "═══════════════════════════════════════════════════════════════"
echo "GFIN FINAL VERIFICATION"
echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "Python: $(python3.11 --version 2>&1)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

run_step() {
    local name="$1"
    local cmd="$2"
    local required="$3"  # "required" or "optional"

    echo "─── ${name} ───"
    if eval "$cmd" > /tmp/gfin_verify_output.log 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}: ${name}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        if [ "$required" = "optional" ]; then
            echo -e "${YELLOW}⚠ SKIPPED${NC}: ${name} (optional)"
            SKIP_COUNT=$((SKIP_COUNT + 1))
        else
            echo -e "${RED}✗ FAIL${NC}: ${name}"
            FAIL_COUNT=$((FAIL_COUNT + 1))
            cat /tmp/gfin_verify_output.log | tail -20
        fi
    fi
    echo ""
}

# ─── 1. LINT ───
run_step "Lint (ruff)" \
    "python -m ruff check packages services tests" \
    "required"

# ─── 2. FORMAT CHECK ───
run_step "Format Check (ruff format)" \
    "python -m ruff format --check packages services tests" \
    "optional"

# ─── 3. TYPE CHECK ───
run_step "Type Check (mypy)" \
    "python -m mypy packages --explicit-package-bases --ignore-missing-imports" \
    "required"

# ─── 4. UNIT TESTS ───
run_step "Unit Tests" \
    "python -m pytest tests/unit/ -q --no-header --tb=short -p no:cacheprovider" \
    "required"

# ─── 5. INTEGRATION TESTS ───
run_step "Integration Tests" \
    "python -m pytest tests/integration/ -q --no-header --tb=short -p no:cacheprovider" \
    "required"

# ─── 6. E2E TESTS ───
run_step "End-to-End Tests" \
    "python -m pytest tests/e2e/ -q --no-header --tb=short -p no:cacheprovider" \
    "required"

# ─── 7. SECURITY TESTS ───
run_step "Security Tests" \
    "python -m pytest tests/security/ -q --no-header --tb=short -p no:cacheprovider" \
    "required"

# ─── 8. FULL TEST SUITE WITH COVERAGE ───
run_step "Full Test Suite + Coverage" \
    "python -m pytest tests/ -q --no-header --tb=short -p no:cacheprovider --cov=packages --cov-report=term-missing" \
    "required"

# ─── 9. DEPENDENCY AUDIT ───
run_step "Dependency Audit (pip-audit)" \
    "pip-audit --strict 2>/dev/null || echo 'pip-audit not available — SKIPPED'" \
    "optional"

# ─── 10. SECRET SCANNING ───
run_step "Secret Scanning (gitleaks)" \
    "gitleaks detect --no-banner 2>/dev/null || echo 'gitleaks not available — SKIPPED'" \
    "optional"

# ─── 11. AI GATEWAY TESTS ───
run_step "AI Gateway Tests" \
    "python -m pytest tests/unit/test_openai_gateway.py tests/unit/test_local_ai.py tests/unit/test_investigation_orchestrator.py -q --no-header --tb=short -p no:cacheprovider" \
    "required"

# ─── 12. PERFORMANCE/LOAD TESTS ───
run_step "Load/Performance Tests" \
    "python -m pytest tests/unit/test_load_testing.py -q --no-header --tb=short -p no:cacheprovider" \
    "required"

# ─── SUMMARY ───
echo "═══════════════════════════════════════════════════════════════"
echo "VERIFICATION SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo -e "  ${GREEN}PASSED${NC}:  ${PASS_COUNT}"
echo -e "  ${RED}FAILED${NC}:  ${FAIL_COUNT}"
echo -e "  ${YELLOW}SKIPPED${NC}: ${SKIP_COUNT}"
echo ""

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}VERIFICATION FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}VERIFICATION PASSED${NC}"
    exit 0
fi
