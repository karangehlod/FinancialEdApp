#!/bin/bash

################################################################################
# FinancialEdApp - Quick Endpoint Test Script
# 
# Quick and simple endpoint testing for rapid verification
# Usage: ./quick_endpoint_test.sh [BASE_URL]
#
################################################################################

# Don't exit on error - we want to report test failures
set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BASE_URL="${1:-http://localhost:8000}"
API_URL="${BASE_URL}/api/v1"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-TestPassword123!}"
VERBOSE="${VERBOSE:-false}"

# Counters
PASS=0
FAIL=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASS++))
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAIL++))
}

test_request() {
    local method=$1
    local endpoint=$2
    local description=$3
    local expected_code=$4
    local data=$5
    local token=$6
    
    local url="$API_URL$endpoint"
    local cmd="curl -s -w '\n%{http_code}' -X $method $url"
    
    if [ -n "$data" ]; then
        cmd="$cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    if [ -n "$token" ]; then
        cmd="$cmd -H 'Authorization: Bearer $token'"
    fi
    
    local response=$(eval $cmd)
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_code" ]; then
        success "$description (HTTP $http_code)"
        echo "$body"
    else
        fail "$description (Expected $expected_code, got $http_code)"
    fi
    
    echo "$body"
}

################################################################################
# Main Tests
################################################################################

echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║         FinancialEdApp - Quick Endpoint Test                     ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo "API URL: $API_URL"
echo "Test Email: $TEST_EMAIL"

# 1. Health Check
print_header "Health Check"
HEALTH_CHECK=$(curl -s "$BASE_URL/health" 2>/dev/null)
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    success "Backend is healthy"
else
    fail "Backend is not responding"
    exit 1
fi

# 2. Authentication
print_header "Authentication"

# Try to login first (user should exist)
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" 2>/dev/null)

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4 2>/dev/null || echo "")

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    success "Login successful"
else
    # If login fails, try to register
    REG_EMAIL="test_user_$(date +%s)@test.com"
    REG_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$REG_EMAIL\",\"password\":\"SecurePass123!\",\"full_name\":\"Test User\"}" 2>/dev/null)
    
    if echo "$REG_RESPONSE" | grep -q "\"id\""; then
        success "User registration works"
        
        # Now login with the new user
        LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
          -H "Content-Type: application/json" \
          -d "{\"email\":\"$REG_EMAIL\",\"password\":\"SecurePass123!\"}" 2>/dev/null)
        
        TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4 2>/dev/null || echo "")
        
        if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
            success "Login with new user successful"
        else
            fail "Login with new user failed"
            exit 1
        fi
    else
        fail "User registration failed"
        fail "Login failed - could not extract token"
        exit 1
    fi
fi

# 3. User Endpoints
print_header "User Endpoints"
ME_RESPONSE=$(curl -s -X GET "$API_URL/auth/me" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$ME_RESPONSE" | grep -q "\"id\""; then
    success "Get current user"
else
    fail "Get current user failed"
fi

# 4. Expenses
print_header "Expense Endpoints"

# Create
EXPENSE_RESPONSE=$(curl -s -X POST "$API_URL/expenses/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"amount\":50.00,\"category\":\"Food\",\"description\":\"Test expense\",\"date\":\"$(date +%Y-%m-%d)\"}" 2>/dev/null)

EXPENSE_ID=$(echo "$EXPENSE_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4 2>/dev/null || echo "")

if [ -n "$EXPENSE_ID" ] && [ "$EXPENSE_ID" != "null" ]; then
    success "Create expense"
else
    fail "Create expense failed"
    if [ "$VERBOSE" = "true" ]; then
        echo "Response: $EXPENSE_RESPONSE" | head -c 200
    fi
fi

# List
LIST_RESPONSE=$(curl -s -X GET "$API_URL/expenses/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$LIST_RESPONSE" | grep -q "expense\|data\|amount"; then
    success "List expenses"
else
    fail "List expenses failed"
    if [ "$VERBOSE" = "true" ]; then
        echo "Response: $LIST_RESPONSE" | head -c 200
    fi
fi

# Get single
if [ -n "$EXPENSE_ID" ] && [ "$EXPENSE_ID" != "null" ]; then
    GET_RESPONSE=$(curl -s -X GET "$API_URL/expenses/$EXPENSE_ID" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
    if echo "$GET_RESPONSE" | grep -q "$EXPENSE_ID"; then
        success "Get single expense"
    else
        fail "Get single expense failed"
    fi
fi

# 5. Budgets
print_header "Budget Endpoints"

# Create
BUDGET_RESPONSE=$(curl -s -X POST "$API_URL/budgets/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"month\":\"$(date +%Y-%m-01)\",\"category\":\"Food\",\"allocated_amount\":500.00}" 2>/dev/null)

BUDGET_ID=$(echo "$BUDGET_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4 2>/dev/null || echo "")

if [ -n "$BUDGET_ID" ] && [ "$BUDGET_ID" != "null" ]; then
    success "Create budget"
else
    fail "Create budget failed"
fi

# List
LIST_BUDGET=$(curl -s -X GET "$API_URL/budgets/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$LIST_BUDGET" | grep -q "allocated_amount\|data"; then
    success "List budgets"
else
    fail "List budgets failed"
fi

# 6. Loans
print_header "Loan Endpoints"

# Create
LOAN_RESPONSE=$(curl -s -X POST "$API_URL/loans/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"loan_type\":\"Personal\",\"lender_name\":\"Bank ABC\",\"principal_amount\":10000.00,\"interest_rate\":5.5,\"loan_term_months\":60,\"start_date\":\"$(date +%Y-%m-%d)\"}" 2>/dev/null)

LOAN_ID=$(echo "$LOAN_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4 2>/dev/null || echo "")

if [ -n "$LOAN_ID" ] && [ "$LOAN_ID" != "null" ]; then
    success "Create loan"
else
    fail "Create loan failed"
    echo "Response: $LOAN_RESPONSE"
fi

# List
LIST_LOAN=$(curl -s -X GET "$API_URL/loans/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$LIST_LOAN" | grep -q "principal_amount\|data"; then
    success "List loans"
else
    fail "List loans failed"
fi

# 7. Goals
print_header "Goal Endpoints"

# Create
GOAL_RESPONSE=$(curl -s -X POST "$API_URL/goals/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"goal_name\":\"Emergency Fund\",\"goal_type\":\"savings\",\"target_amount\":15000.00,\"target_date\":\"2026-12-31\",\"priority\":\"high\"}" 2>/dev/null)

GOAL_ID=$(echo "$GOAL_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4 2>/dev/null || echo "")

if [ -n "$GOAL_ID" ] && [ "$GOAL_ID" != "null" ]; then
    success "Create goal"
else
    fail "Create goal failed"
fi

# List
LIST_GOAL=$(curl -s -X GET "$API_URL/goals/" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$LIST_GOAL" | grep -q "target_amount\|data"; then
    success "List goals"
else
    fail "List goals failed"
fi

# 8. Notifications
print_header "Notification Endpoints"
NOTIF_RESPONSE=$(curl -s -X GET "$API_URL/notifications" -H "Authorization: Bearer $TOKEN" 2>/dev/null)
if echo "$NOTIF_RESPONSE" | grep -q "total\|skip\|limit\|notifications"; then
    success "Get notifications"
else
    fail "Get notifications failed"
    if [ "$VERBOSE" = "true" ]; then
        echo "Response: $NOTIF_RESPONSE" | head -c 200
    fi
fi

# Summary
print_header "Test Summary"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed! ✓${NC}\n"
    exit 0
else
    echo -e "\n${RED}Some tests failed.${NC}\n"
    exit 1
fi
