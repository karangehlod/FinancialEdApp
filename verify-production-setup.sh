#!/usr/bin/env bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASSED=0
FAILED=0
WARNINGS=0

pass() { echo -e "${GREEN}✓${NC} $*"; ((PASSED++)); }
fail() { echo -e "${RED}✗${NC} $*"; ((FAILED++)); }
warn() { echo -e "${YELLOW}⚠${NC} $*"; ((WARNINGS++)); }
section() { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n${BLUE}$*${NC}\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗"
echo "║  Production Setup Verification - FinancialEdApp               ║"
echo "╚════════════════════════════════════════════════════════════════╝${NC}\n"

section "BACKEND VERIFICATION"
[ -d "$PROJECT_ROOT/backend" ] && pass "Backend directory exists" || fail "Backend not found"
[ -f "$PROJECT_ROOT/backend/app/main.py" ] && pass "main.py exists" || fail "main.py not found"
[ -f "$PROJECT_ROOT/backend/requirements.txt" ] && pass "requirements.txt exists" || fail "requirements.txt not found"
[ -f "$PROJECT_ROOT/backend/Dockerfile" ] && pass "Dockerfile exists" || fail "Dockerfile not found"
[ -f "$PROJECT_ROOT/backend/pyproject.toml" ] && pass "pyproject.toml exists" || fail "pyproject.toml not found"

section "DATABASE SETUP VERIFICATION"
[ -d "$PROJECT_ROOT/database_setup" ] && pass "database_setup exists" || fail "database_setup not found"
[ -d "$PROJECT_ROOT/database_setup/db/init" ] && pass "Init scripts exist" || warn "Init scripts not found"
[ -f "$PROJECT_ROOT/database_setup/Dockerfile" ] && pass "Database Dockerfile exists" || warn "Database Dockerfile not found"

section "DOCKER DEPLOYMENT VERIFICATION"
if command -v docker &> /dev/null; then
    pass "Docker installed"
    docker info &> /dev/null && pass "Docker daemon running" || fail "Docker daemon not running"
else
    fail "Docker not installed"
fi
if command -v docker-compose &> /dev/null; then
    pass "Docker Compose installed"
else
    fail "Docker Compose not installed"
fi
[ -f "$PROJECT_ROOT/docker-compose.yml" ] && pass "docker-compose.yml exists" || fail "docker-compose.yml not found"

section "KUBERNETES DEPLOYMENT VERIFICATION"
[ -d "$PROJECT_ROOT/backend/k8s" ] && pass "K8s directory exists" || fail "K8s not found"
[ -f "$PROJECT_ROOT/backend/k8s/00-namespace-config-secrets.yaml" ] && pass "Namespace config exists" || warn "Namespace config missing"
[ -f "$PROJECT_ROOT/backend/k8s/01-postgres.yaml" ] && pass "PostgreSQL manifest exists" || warn "PostgreSQL manifest missing"
[ -f "$PROJECT_ROOT/backend/k8s/02-redis.yaml" ] && pass "Redis manifest exists" || warn "Redis manifest missing"
[ -f "$PROJECT_ROOT/backend/k8s/03-backend.yaml" ] && pass "Backend manifest exists" || warn "Backend manifest missing"

section "SECURITY CHECKS"
[ -f "$PROJECT_ROOT/.gitignore" ] && pass ".gitignore exists" || fail ".gitignore not found"
SECRETS="$PROJECT_ROOT/backend/k8s/00-namespace-config-secrets.yaml"
if [ -f "$SECRETS" ]; then
    grep -q "SecurePassword123" "$SECRETS" && warn "Default database password found - CHANGE for production!"
    grep -q "RedisPassword123" "$SECRETS" && warn "Default Redis password found - CHANGE for production!"
    grep -q "your-super-secret-key" "$SECRETS" && warn "Default JWT secret found - CHANGE for production!"
fi

section "DEPENDENCIES CHECK"
command -v python3 &> /dev/null && pass "Python3 installed" || fail "Python3 not found"
command -v git &> /dev/null && pass "Git installed" || warn "Git not found"
command -v curl &> /dev/null && pass "Curl installed" || warn "Curl not found"

section "FILE STRUCTURE VERIFICATION"
[ -f "$PROJECT_ROOT/README.md" ] && pass "README.md exists" || warn "README.md not found"
[ -f "$PROJECT_ROOT/PRODUCTION_READINESS_CHECK.md" ] && pass "Production guide exists" || warn "Production guide not found"
[ -d "$PROJECT_ROOT/backend/tests" ] && pass "Tests directory exists" || warn "Tests not found"
[ -f "$PROJECT_ROOT/test-docker-deployment.sh" ] && pass "Docker test script exists" || warn "Docker test script not found"
[ -f "$PROJECT_ROOT/deploy-to-k8s-local.sh" ] && pass "K8s deployment script exists" || warn "K8s deployment script not found"

section "VERIFICATION SUMMARY"
TOTAL=$((PASSED + FAILED + WARNINGS))
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${RED}Failed:${NC}   $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "Total:    $TOTAL\n"

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}\n"
else
    echo -e "${RED}✗ Some critical checks failed.${NC}\n"
fi
