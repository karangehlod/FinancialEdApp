#!/bin/bash

################################################################################
# FinancialEdApp - API Endpoint Testing Script
# 
# This script provides comprehensive testing of all API endpoints
# Usage: ./test_endpoints.sh [OPTIONS]
# 
# Options:
#   -h, --help              Show this help message
#   -u, --url URL           Set API base URL (default: http://localhost:8000/api/v1)
#   -e, --email EMAIL       Set test email (default: test@example.com)
#   -p, --password PASSWORD Set test password (default: TestPassword123!)
#   -v, --verbose           Enable verbose output
#   -o, --output FILE       Save results to file
#   --skip-auth             Skip authentication tests
#   --health-check-only     Run health check only
#   --quick-test            Run quick test of key endpoints
#
################################################################################

set +e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api/v1}"
API_HEALTH_URL="${API_HEALTH_URL:-http://localhost:8000/health}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-TestPassword123!}"
VERBOSE=false
OUTPUT_FILE=""
SKIP_AUTH=false
HEALTH_CHECK_ONLY=false
QUICK_TEST=false

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Temporary files for storing test data
TEMP_DIR=$(mktemp -d)
TOKEN_FILE="$TEMP_DIR/token.txt"
USER_ID_FILE="$TEMP_DIR/user_id.txt"
EXPENSE_ID_FILE="$TEMP_DIR/expense_id.txt"
BUDGET_ID_FILE="$TEMP_DIR/budget_id.txt"
LOAN_ID_FILE="$TEMP_DIR/loan_id.txt"
GOAL_ID_FILE="$TEMP_DIR/goal_id.txt"
NOTIFICATION_ID_FILE="$TEMP_DIR/notification_id.txt"

################################################################################
# Helper Functions
################################################################################

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

print_test() {
    echo -ne "${YELLOW}[TEST]${NC} $1... "
}

print_pass() {
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED_TESTS++))
}

print_fail() {
    echo -e "${RED}✗ FAILED${NC}: $1"
    ((FAILED_TESTS++))
}

print_skip() {
    echo -e "${YELLOW}⊘ SKIPPED${NC}: $1"
    ((SKIPPED_TESTS++))
}

print_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Make HTTP request and return status code
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    local output_file=$5

    local url="$API_BASE_URL$endpoint"
    local args=(-s -w "\n%{http_code}" -X "$method" "$url")

    if [ -n "$data" ]; then
        args+=(-H "Content-Type: application/json" -d "$data")
    fi

    if [ -n "$token" ]; then
        args+=(-H "Authorization: Bearer $token")
    fi

    if [ -n "$output_file" ]; then
        args+=(-o "$output_file")
    fi

    curl "${args[@]}"
}

# Test an endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local expected_code=$4
    local data=${5:-}
    local token=${6:-}
    local save_response=${7:-}

    ((TOTAL_TESTS++))
    
    print_test "$description"

    local response_file=$(mktemp)
    local http_code=$(make_request "$method" "$endpoint" "$data" "$token" "$response_file" | tail -n1)
    local response=$(cat "$response_file")

    if [ "$http_code" == "$expected_code" ]; then
        print_pass
        
        if [ -n "$save_response" ]; then
            echo "$response" > "$save_response"
            print_info "Response saved to: $save_response"
        fi
        
        if [ "$VERBOSE" = true ]; then
            echo "Response: $response" | head -c 200
            echo ""
        fi
    else
        print_fail "Expected $expected_code, got $http_code"
        print_info "Response: $response"
    fi

    rm -f "$response_file"
}

# Extract value from JSON response
extract_json() {
    local json=$1
    local key=$2
    echo "$json" | jq -r "$key" 2>/dev/null || echo ""
}

# Show usage
show_usage() {
    head -n 20 "$0" | grep "^#" | tail -n +2
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -u|--url)
                API_BASE_URL="$2"
                shift 2
                ;;
            -e|--email)
                TEST_EMAIL="$2"
                shift 2
                ;;
            -p|--password)
                TEST_PASSWORD="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --skip-auth)
                SKIP_AUTH=true
                shift
                ;;
            --health-check-only)
                HEALTH_CHECK_ONLY=true
                shift
                ;;
            --quick-test)
                QUICK_TEST=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

################################################################################
# Test Suites
################################################################################

# Health Check
test_health_check() {
    print_header "Health Check"
    
    ((TOTAL_TESTS++))
    print_test "Backend Health Check"
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$API_HEALTH_URL")
    
    if [ "$response" == "200" ]; then
        print_pass
    else
        print_fail "Health check failed with status $response"
        return 1
    fi
}

# Authentication Tests
test_authentication() {
    if [ "$SKIP_AUTH" = true ]; then
        print_header "Authentication Tests (SKIPPED)"
        print_skip "User requested to skip auth tests"
        return
    fi

    print_header "Authentication Tests"
    
    # Test 1: Register new user
    local reg_email="testuser_$(date +%s)@example.com"
    test_endpoint "POST" "/auth/register" \
        "Register new user" "201" \
        "{\"email\":\"$reg_email\",\"password\":\"SecurePass123!\",\"full_name\":\"Test User\"}"
    
    # Test 2: Login with correct credentials
    local login_response=$(curl -s -X POST "$API_BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$reg_email\",\"password\":\"SecurePass123!\"}")
    
    ((TOTAL_TESTS++))
    print_test "Login with correct credentials"
    
    local token=$(extract_json "$login_response" '.access_token')
    
    if [ -n "$token" ] && [ "$token" != "null" ]; then
        echo "$token" > "$TOKEN_FILE"
        print_pass
        local user_id=$(extract_json "$login_response" '.user.id')
        if [ -n "$user_id" ] && [ "$user_id" != "null" ]; then
            echo "$user_id" > "$USER_ID_FILE"
        fi
    else
        print_fail "No token in response"
        print_error "Cannot proceed with authenticated tests"
        return 1
    fi
    
    # Test 3: Get current user info
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    if [ -n "$token" ]; then
        test_endpoint "GET" "/auth/me" \
            "Get current authenticated user" "200" "" "$token"
    fi
    
    # Test 4: Login with invalid credentials
    test_endpoint "POST" "/auth/login" \
        "Login with invalid credentials (should fail)" "401" \
        "{\"email\":\"$TEST_EMAIL\",\"password\":\"WrongPassword\"}"
}

# User Profile Tests
test_user_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "User Profile Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "User Profile Tests"
    
    # Test 1: Get current authenticated user
    test_endpoint "GET" "/auth/me" \
        "Get current authenticated user" "200" "" "$token"
}

# Expense Tests
test_expense_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "Expense Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "Expense Tests"
    
    # Test 1: Create expense
    local create_response=$(curl -s -X POST "$API_BASE_URL/expenses/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"amount\":45.50,\"category\":\"Food\",\"description\":\"Grocery shopping\",\"date\":\"$(date +%Y-%m-%d)\"}")
    
    ((TOTAL_TESTS++))
    print_test "Create expense"
    
    local expense_id=$(extract_json "$create_response" '.id')
    if [ -n "$expense_id" ] && [ "$expense_id" != "null" ]; then
        echo "$expense_id" > "$EXPENSE_ID_FILE"
        print_pass
    else
        print_fail "No expense ID in response"
    fi
    
    # Test 2: List expenses
    test_endpoint "GET" "/expenses/" \
        "List all expenses" "200" "" "$token"
    
    # Test 3: Get single expense
    if [ -f "$EXPENSE_ID_FILE" ]; then
        local expense_id=$(cat "$EXPENSE_ID_FILE")
        test_endpoint "GET" "/expenses/$expense_id" \
            "Get single expense" "200" "" "$token"
        
        # Test 4: Update expense
        test_endpoint "PUT" "/expenses/$expense_id" \
            "Update expense" "200" \
            "{\"amount\":50.00,\"description\":\"Updated grocery shopping\"}" "$token"
        
        # Test 5: Delete expense
        test_endpoint "DELETE" "/expenses/$expense_id" \
            "Delete expense" "204" "" "$token"
    fi
    
    # Test 6: Get expense summary
    test_endpoint "GET" "/expenses/summary" \
        "Get expense summary" "200" "" "$token"
}

# Budget Tests
test_budget_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "Budget Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "Budget Tests"
    
    # Test 1: Create budget
    local today=$(date +%Y-%m-01)
    local create_response=$(curl -s -X POST "$API_BASE_URL/budgets/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"month\":\"$today\",\"category\":\"FOOD\",\"allocated_amount\":5000.00}")
    
    ((TOTAL_TESTS++))
    print_test "Create budget"
    
    local budget_id=$(extract_json "$create_response" '.id')
    if [ -n "$budget_id" ] && [ "$budget_id" != "null" ]; then
        echo "$budget_id" > "$BUDGET_ID_FILE"
        print_pass
    else
        print_fail "No budget ID in response"
    fi
    
    # Test 2: List budgets
    test_endpoint "GET" "/budgets/" \
        "List all budgets" "200" "" "$token"
    
    # Test 3: Get budget details
    if [ -f "$BUDGET_ID_FILE" ]; then
        local budget_id=$(cat "$BUDGET_ID_FILE")
        test_endpoint "GET" "/budgets/$budget_id" \
            "Get budget details" "200" "" "$token"
        
        # Test 4: Update budget
        test_endpoint "PUT" "/budgets/$budget_id" \
            "Update budget" "200" \
            "{\"allocated_amount\":6000.00}" "$token"
        
        # Test 5: Delete budget
        test_endpoint "DELETE" "/budgets/$budget_id" \
            "Delete budget" "204" "" "$token"
    fi
}

# Loan Tests
test_loan_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "Loan Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "Loan Tests"
    
    # Test 1: Create loan
    local today=$(date +%Y-%m-%d)
    local create_response=$(curl -s -X POST "$API_BASE_URL/loans/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"loan_type\":\"Personal\",\"lender_name\":\"Bank ABC\",\"principal_amount\":10000.00,\"interest_rate\":5.5,\"loan_term_months\":60,\"start_date\":\"$today\"}")
    
    ((TOTAL_TESTS++))
    print_test "Create loan"
    
    local loan_id=$(extract_json "$create_response" '.id')
    if [ -n "$loan_id" ] && [ "$loan_id" != "null" ]; then
        echo "$loan_id" > "$LOAN_ID_FILE"
        print_pass
    else
        print_fail "No loan ID in response"
    fi
    
    # Test 2: List loans
    test_endpoint "GET" "/loans/" \
        "List all loans" "200" "" "$token"
    
    # Test 3: Get loan details
    if [ -f "$LOAN_ID_FILE" ]; then
        local loan_id=$(cat "$LOAN_ID_FILE")
        test_endpoint "GET" "/loans/$loan_id" \
            "Get loan details" "200" "" "$token"
        
        # Test 4: Update loan
        test_endpoint "PUT" "/loans/$loan_id" \
            "Update loan" "200" \
            "{\"interest_rate\":5.75}" "$token"
        
        # Test 5: Delete loan
        test_endpoint "DELETE" "/loans/$loan_id" \
            "Delete loan" "204" "" "$token"
    fi
}

# Goal Tests
test_goal_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "Goal Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "Goal Tests"
    
    # Test 1: Create goal
    local target_date=$(date -d "+1 year" +%Y-%m-%d 2>/dev/null || date -v+1y +%Y-%m-%d)
    local create_response=$(curl -s -X POST "$API_BASE_URL/goals/" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"goal_name\":\"Emergency Fund\",\"goal_type\":\"emergency_fund\",\"target_amount\":15000.00,\"target_date\":\"$target_date\",\"priority\":\"high\"}")
    
    ((TOTAL_TESTS++))
    print_test "Create goal"
    
    local goal_id=$(extract_json "$create_response" '.id')
    if [ -n "$goal_id" ] && [ "$goal_id" != "null" ]; then
        echo "$goal_id" > "$GOAL_ID_FILE"
        print_pass
    else
        print_fail "No goal ID in response"
    fi
    
    # Test 2: List goals
    test_endpoint "GET" "/goals/" \
        "List all goals" "200" "" "$token"
    
    # Test 3: Get goal details
    if [ -f "$GOAL_ID_FILE" ]; then
        local goal_id=$(cat "$GOAL_ID_FILE")
        test_endpoint "GET" "/goals/$goal_id" \
            "Get goal details" "200" "" "$token"
        
        # Test 4: Update goal
        test_endpoint "PUT" "/goals/$goal_id" \
            "Update goal" "200" \
            "{\"target_amount\":20000.00}" "$token"
        
        # Test 5: Delete goal
        test_endpoint "DELETE" "/goals/$goal_id" \
            "Delete goal" "204" "" "$token"
    fi
}

# Notification Tests
test_notification_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "Notification Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "Notification Tests"
    
    # Test 1: Get notifications
    test_endpoint "GET" "/notifications" \
        "Get all notifications" "200" "" "$token"
    
    # Test 2: Get unread notifications
    test_endpoint "GET" "/notifications?unread=true" \
        "Get unread notifications" "200" "" "$token"
}

# Export Tests
test_export_endpoints() {
    local token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    if [ -z "$token" ]; then
        print_header "Export Tests (SKIPPED)"
        print_skip "No valid token available"
        return
    fi

    print_header "Export Tests"
    
    # Test 1: Export expenses as CSV
    test_endpoint "POST" "/exports/expenses/csv" \
        "Export expenses as CSV" "200" "" "$token"
    
    # Test 2: Export complete financial data as Excel
    test_endpoint "POST" "/exports/complete/excel" \
        "Export complete financial data as Excel" "200" "" "$token"
}

# Run all tests
run_all_tests() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FinancialEdApp API Testing Suite                          ║
║                                                                              ║
║  This script comprehensively tests all API endpoints                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    echo -e "API URL: ${BLUE}$API_BASE_URL${NC}"
    echo -e "Health URL: ${BLUE}$API_HEALTH_URL${NC}"
    echo -e "Test Email: ${BLUE}$TEST_EMAIL${NC}\n"
    
    # Health check
    test_health_check
    
    if [ "$HEALTH_CHECK_ONLY" = true ]; then
        return
    fi
    
    # Run test suites based on quick test flag
    if [ "$QUICK_TEST" = true ]; then
        print_header "Quick Test Mode - Testing Key Endpoints"
        test_authentication
        test_expense_endpoints
        test_budget_endpoints
    else
        test_authentication
        test_user_endpoints
        test_expense_endpoints
        test_budget_endpoints
        test_loan_endpoints
        test_goal_endpoints
        test_notification_endpoints
        test_export_endpoints
    fi
}

# Print test summary
print_summary() {
    print_header "Test Summary"
    
    echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
    echo -e "Skipped: ${YELLOW}$SKIPPED_TESTS${NC}\n"
    
    if [ "$FAILED_TESTS" -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC} ✓"
        return 0
    else
        echo -e "${RED}Some tests failed.${NC} ✗"
        return 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    parse_args "$@"
    
    {
        run_all_tests
        print_summary
    } | tee -a "${OUTPUT_FILE:-.}"
    
    if [ -n "$OUTPUT_FILE" ]; then
        echo ""
        echo -e "${BLUE}Results saved to: $OUTPUT_FILE${NC}"
    fi
}

main "$@"
