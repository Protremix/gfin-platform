#!/usr/bin/env bash
# GFIN Verification Script — Final Build Verification Directive §35
# Runs: lint → typecheck → tests → coverage → summary
set -euo pipefail

echo "═══════════════════════════════════════════════════════════════"
echo "  GFIN FINAL VERIFICATION SUITE"
echo "  Directive §35 — Automated Acceptance Verification"
echo "  Verifier: GPT Luna (GFIN-CEA)"
echo "  Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ─── 1. LINT ───
echo "▶ [1/4] Lint check (ruff)..."
if python -m ruff check packages/ tests/ --no-cache 2>&1 | tail -5; then
    echo "  ✅ LINT: PASS"
else
    echo "  ❌ LINT: FAIL"
fi
echo ""

# ─── 2. TYPE CHECK ───
echo "▶ [2/4] Type check (mypy)..."
if python -m mypy packages/ --ignore-missing-imports --namespace-packages --no-error-summary 2>&1 | grep -v "Source file found twice" | grep -q "^"; then
    TYPE_ERRORS=$(python -m mypy packages/ --ignore-missing-imports --namespace-packages --no-error-summary 2>&1 | grep -v "Source file found twice" | grep -c "error:" || true)
    if [ "$TYPE_ERRORS" -eq 0 ]; then
        echo "  ✅ TYPECHECK: PASS"
    else
        echo "  ❌ TYPECHECK: FAIL ($TYPE_ERRORS errors)"
    fi
else
    echo "  ✅ TYPECHECK: PASS"
fi
echo ""

# ─── 3. TESTS ───
echo "▶ [3/4] Running test suite..."
TEST_OUTPUT=$(python -m pytest tests/ -p no:cacheprovider --no-cov -q 2>&1)
echo "$TEST_OUTPUT" | tail -3
echo ""

# ─── 4. COVERAGE ───
echo "▶ [4/4] Coverage report..."
python -m pytest tests/ --cov=packages --cov-report=term --no-header -p no:cacheprovider -q 2>&1 | grep "TOTAL" || true
echo ""

# ─── SUMMARY ───
echo "═══════════════════════════════════════════════════════════════"
echo "  VERIFICATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
