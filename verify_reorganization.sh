#!/bin/bash

# Verification script for project reorganization
# This script verifies the new project structure and startup flow

set -e  # Exit on error

echo "=================================="
echo "Project Reorganization Verification"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Missing: $1"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Found directory: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Missing directory: $1"
        return 1
    fi
}

echo "1. Checking Root Directory Structure..."
echo "----------------------------------------"
check_file "README.md"
check_file "PROJECT_GUIDELINES.md"
check_file "REORGANIZATION_SUMMARY.md"
check_file "docker-compose.yml"
check_dir "database_setup"
check_dir "backend"
echo ""

echo "2. Checking database_setup/ Structure..."
echo "----------------------------------------"
check_file "database_setup/README.md"
check_file "database_setup/Dockerfile"
check_file "database_setup/docker-compose.yml"
check_dir "database_setup/db/init"
echo ""

echo "3. Checking backend/ Structure..."
echo "----------------------------------------"
check_file "backend/README_NEW.md"
check_file "backend/Dockerfile"
check_file "backend/requirements.txt"
check_file "backend/app/startup_checks.py"
check_file "backend/app/main.py"
check_dir "backend/k8s"
check_dir "backend/tests"
echo ""

echo "4. Checking Kubernetes Manifests..."
echo "----------------------------------------"
check_file "backend/k8s/00-namespace-config-secrets.yaml"
check_file "backend/k8s/01-postgres.yaml"
check_file "backend/k8s/02-redis.yaml"
check_file "backend/k8s/03-backend.yaml"
check_file "backend/k8s/K8S_DEPLOYMENT_GUIDE.md"
echo ""

echo "5. Verifying startup_checks.py content..."
echo "----------------------------------------"
if grep -q "check_database_connectivity" backend/app/startup_checks.py; then
    echo -e "${GREEN}✓${NC} Contains check_database_connectivity()"
else
    echo -e "${RED}✗${NC} Missing check_database_connectivity()"
fi

if grep -q "check_redis_connectivity" backend/app/startup_checks.py; then
    echo -e "${GREEN}✓${NC} Contains check_redis_connectivity()"
else
    echo -e "${RED}✗${NC} Missing check_redis_connectivity()"
fi

if grep -q "perform_startup_checks" backend/app/startup_checks.py; then
    echo -e "${GREEN}✓${NC} Contains perform_startup_checks()"
else
    echo -e "${RED}✗${NC} Missing perform_startup_checks()"
fi
echo ""

echo "6. Verifying main.py changes..."
echo "----------------------------------------"
if grep -q "startup_checks import" backend/app/main.py; then
    echo -e "${GREEN}✓${NC} Imports startup_checks module"
else
    echo -e "${RED}✗${NC} Missing startup_checks import"
fi

if grep -q "perform_startup_checks" backend/app/main.py; then
    echo -e "${GREEN}✓${NC} Calls perform_startup_checks()"
else
    echo -e "${RED}✗${NC} Missing perform_startup_checks() call"
fi

if ! grep -q "create_all" backend/app/main.py || grep -q "# No longer creates tables" backend/app/main.py; then
    echo -e "${GREEN}✓${NC} Does not call create_all()"
else
    echo -e "${YELLOW}⚠${NC}  Warning: Still contains create_all() call"
fi
echo ""

echo "7. Checking docker-compose.yml updates..."
echo "----------------------------------------"
if grep -q "database_setup/db/init" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} Mounts database init scripts"
else
    echo -e "${RED}✗${NC} Missing init scripts mount"
fi

if grep -q "55432" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} Uses port 55432 for PostgreSQL"
else
    echo -e "${YELLOW}⚠${NC}  Warning: Not using port 55432"
fi

if grep -q "56379" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} Uses port 56379 for Redis"
else
    echo -e "${YELLOW}⚠${NC}  Warning: Not using port 56379"
fi
echo ""

echo "8. Checking database_setup isolation..."
echo "----------------------------------------"
PYTHON_FILES=$(find database_setup -name "*.py" 2>/dev/null | grep -v __pycache__ || true)
if [ -z "$PYTHON_FILES" ]; then
    echo -e "${GREEN}✓${NC} No Python files in database_setup/"
else
    echo -e "${YELLOW}⚠${NC}  Warning: Found Python files in database_setup/:"
    echo "$PYTHON_FILES"
fi
echo ""

echo "=================================="
echo "Verification Complete!"
echo "=================================="
echo ""
echo "Next Steps:"
echo "1. Test database startup: cd database_setup && docker-compose up -d"
echo "2. Test backend startup checks: cd backend && python -m app.startup_checks"
echo "3. Test full stack: docker-compose up -d"
echo "4. Read PROJECT_GUIDELINES.md for detailed information"
echo ""
