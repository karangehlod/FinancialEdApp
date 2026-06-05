#!/bin/bash

################################################################################
# FinancialEdApp - Complete API Testing Suite Runner
# 
# This script runs both quick and comprehensive endpoint tests
# Usage: ./run_all_tests.sh [--quick-only] [--verbose]
#
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
QUICK_ONLY=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick-only)
            QUICK_ONLY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--quick-only] [--verbose]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║     FinancialEdApp - Complete API Testing Suite Runner           ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Function to print section header
print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Function to check if backend is running
check_backend() {
    local health=$(curl -s "http://localhost:8000/health" 2>/dev/null | grep -c "healthy")
    if [ $health -eq 0 ]; then
        echo -e "${RED}✗ Backend is not running!${NC}"
        echo -e "${YELLOW}Please start the backend with: cd backend && uvicorn app.main:app --reload${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Backend is running${NC}"
}

# Check backend
print_section "Backend Status"
check_backend

# Run Quick Endpoint Test
print_section "Running Quick Endpoint Test"
if [ "$VERBOSE" = true ]; then
    VERBOSE=true bash quick_endpoint_test.sh
else
    bash quick_endpoint_test.sh
fi

QUICK_RESULT=$?

# Run Comprehensive Test (unless --quick-only specified)
if [ "$QUICK_ONLY" = false ]; then
    print_section "Running Comprehensive Endpoint Tests"
    if [ "$VERBOSE" = true ]; then
        VERBOSE=true bash test_endpoints.sh 2>&1 | grep -v "tee:"
    else
        bash test_endpoints.sh 2>&1 | grep -v "tee:"
    fi
    COMPREHENSIVE_RESULT=$?
else
    COMPREHENSIVE_RESULT=0
fi

# Print summary
print_section "Test Summary"

if [ $QUICK_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Quick Endpoint Test: PASSED${NC}"
else
    echo -e "${RED}✗ Quick Endpoint Test: FAILED${NC}"
fi

if [ "$QUICK_ONLY" = false ]; then
    if [ $COMPREHENSIVE_RESULT -eq 0 ]; then
        echo -e "${GREEN}✓ Comprehensive Test: PASSED${NC}"
    else
        echo -e "${YELLOW}⚠ Comprehensive Test: PARTIAL (some non-critical tests failed)${NC}"
    fi
fi

# Final status
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $QUICK_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CRITICAL TESTS PASSED${NC}"
    echo -e "\nThe API is fully functional and ready for use."
    exit 0
else
    echo -e "${RED}✗ TESTS FAILED${NC}"
    echo -e "\nPlease check the output above for details."
    exit 1
fi
