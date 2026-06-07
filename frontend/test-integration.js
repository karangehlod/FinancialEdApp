#!/usr/bin/env node

/**
 * Frontend-Backend Integration Test Suite
 * 
 * This script tests the integration between the React frontend and FastAPI backend.
 * It verifies that:
 * 1. API endpoints are correctly configured
 * 2. Authentication flow works (register, login, token refresh)
 * 3. Protected routes work correctly
 * 4. CRUD operations work for all resources
 */

const axios = require('axios');

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  blue: '\x1b[34m',
  gray: '\x1b[90m',
  bold: '\x1b[1m',
};

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';
const TEST_USER = {
  email: `test-${Date.now()}@example.com`,
  password: 'TestPassword123',
  name: 'Test User',
};

let testResults = {
  passed: 0,
  failed: 0,
  errors: [],
};

let accessToken = null;
let userId = null;

/**
 * Log test results with colors
 */
function logTest(name, passed, error = null) {
  if (passed) {
    console.log(`${colors.green}✓${colors.reset} ${name}`);
    testResults.passed++;
  } else {
    console.log(`${colors.red}✗${colors.reset} ${name}`);
    if (error) {
      console.log(`${colors.red}  Error: ${error}${colors.reset}`);
    }
    testResults.failed++;
    testResults.errors.push({ test: name, error });
  }
}

/**
 * Test helper to make API requests
 */
async function apiRequest(method, endpoint, data = null, token = null) {
  try {
    const config = {
      method,
      url: `${API_URL}${endpoint}`,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (data) {
      config.data = data;
    }

    const response = await axios(config);
    return { success: true, data: response.data, status: response.status };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.detail || error.message,
      status: error.response?.status,
    };
  }
}

/**
 * Main test suite
 */
async function runTests() {
  console.log(`${colors.blue}${colors.bold}\n🧪 Frontend-Backend Integration Test Suite\n${colors.reset}`);
  console.log(`API URL: ${API_URL}`);
  console.log(`Test User Email: ${TEST_USER.email}\n`);

  // Test 1: Health Check
  console.log(`${colors.cyan}Test Group: Health Check${colors.reset}`);
  const healthResult = await apiRequest('GET', '/health');
  logTest('Health endpoint accessible', healthResult.success, healthResult.error);

  // Test 2: User Registration
  console.log(`${colors.cyan}\nTest Group: Authentication - Registration${colors.reset}`);
  const registerResult = await apiRequest('POST', '/auth/register', TEST_USER);
  logTest(
    'User registration successful',
    registerResult.success && registerResult.status === 201,
    registerResult.error
  );

  if (registerResult.success) {
    userId = registerResult.data.id;
    console.log(`${colors.gray}  Created user ID: ${userId}${colors.reset}`);
  }

  // Test 3: User Login
  console.log(`${colors.cyan}\nTest Group: Authentication - Login${colors.reset}`);
  const loginResult = await apiRequest('POST', '/auth/login', {
    email: TEST_USER.email,
    password: TEST_USER.password,
  });

  logTest(
    'User login successful',
    loginResult.success && loginResult.status === 200,
    loginResult.error
  );

  if (loginResult.success && loginResult.data.access_token) {
    accessToken = loginResult.data.access_token;
    console.log(`${colors.gray}  Received access token: ${accessToken.substring(0, 20)}...${colors.reset}`);
  }

  // Test 4: Get Current User
  console.log(`${colors.cyan}\nTest Group: Authentication - Get Current User${colors.reset}`);
  const userResult = await apiRequest('GET', '/auth/me', null, accessToken);
  logTest('Get current user successful', userResult.success && userResult.status === 200, userResult.error);

  if (userResult.success) {
    console.log(`${colors.gray}  User email: ${userResult.data.email}${colors.reset}`);
  }

  // Test 5: Create Expense
  console.log(`${colors.cyan}\nTest Group: Expenses${colors.reset}`);
  const expenseData = {
    amount: 50.00,
    category: 'Food',
    description: 'Test expense',
    date: new Date().toISOString().split('T')[0],
  };
  const createExpenseResult = await apiRequest('POST', '/expenses', expenseData, accessToken);
  logTest('Create expense successful', createExpenseResult.success, createExpenseResult.error);

  if (createExpenseResult.success && createExpenseResult.data.id) {
    console.log(`${colors.gray}  Created expense ID: ${createExpenseResult.data.id}${colors.reset}`);
  }

  // Test 6: Get All Expenses
  const getExpensesResult = await apiRequest('GET', '/expenses', null, accessToken);
  logTest('Get all expenses successful', getExpensesResult.success, getExpensesResult.error);

  if (getExpensesResult.success && Array.isArray(getExpensesResult.data)) {
    console.log(`${colors.gray}  Retrieved ${getExpensesResult.data.length} expenses${colors.reset}`);
  }

  // Test 7: Create Budget
  console.log(`${colors.cyan}\nTest Group: Budgets${colors.reset}`);
  const budgetData = {
    name: 'Test Budget',
    amount: 1000.00,
    category: 'Food',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  };
  const createBudgetResult = await apiRequest('POST', '/budgets', budgetData, accessToken);
  logTest('Create budget successful', createBudgetResult.success, createBudgetResult.error);

  // Test 8: Get All Budgets
  const getBudgetsResult = await apiRequest('GET', '/budgets', null, accessToken);
  logTest('Get all budgets successful', getBudgetsResult.success, getBudgetsResult.error);

  if (getBudgetsResult.success && Array.isArray(getBudgetsResult.data)) {
    console.log(`${colors.gray}  Retrieved ${getBudgetsResult.data.length} budgets${colors.reset}`);
  }

  // Test 9: Create Loan
  console.log(`${colors.cyan}\nTest Group: Loans${colors.reset}`);
  const loanData = {
    lender_name: 'Test Lender',
    amount: 5000.00,
    interest_rate: 5.5,
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  };
  const createLoanResult = await apiRequest('POST', '/loans', loanData, accessToken);
  logTest('Create loan successful', createLoanResult.success, createLoanResult.error);

  // Test 10: Get All Loans
  const getLoansResult = await apiRequest('GET', '/loans', null, accessToken);
  logTest('Get all loans successful', getLoansResult.success, getLoansResult.error);

  if (getLoansResult.success && Array.isArray(getLoansResult.data)) {
    console.log(`${colors.gray}  Retrieved ${getLoansResult.data.length} loans${colors.reset}`);
  }

  // Test 11: Create Goal
  console.log(`${colors.cyan}\nTest Group: Goals${colors.reset}`);
  const goalData = {
    name: 'Test Goal',
    description: 'A test financial goal',
    target_amount: 10000.00,
    current_amount: 0.00,
    target_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  };
  const createGoalResult = await apiRequest('POST', '/goals', goalData, accessToken);
  logTest('Create goal successful', createGoalResult.success, createGoalResult.error);

  // Test 12: Get All Goals
  const getGoalsResult = await apiRequest('GET', '/goals', null, accessToken);
  logTest('Get all goals successful', getGoalsResult.success, getGoalsResult.error);

  if (getGoalsResult.success && Array.isArray(getGoalsResult.data)) {
    console.log(`${colors.gray}  Retrieved ${getGoalsResult.data.length} goals${colors.reset}`);
  }

  // Test 13: Get Notifications
  console.log(`${colors.cyan}\nTest Group: Notifications${colors.reset}`);
  const getNotificationsResult = await apiRequest('GET', '/notifications', null, accessToken);
  logTest('Get notifications successful', getNotificationsResult.success, getNotificationsResult.error);

  // Test 14: Get Enums
  console.log(`${colors.cyan}\nTest Group: Enums${colors.reset}`);
  const getEnumsResult = await apiRequest('GET', '/enums');
  logTest('Get enums successful', getEnumsResult.success, getEnumsResult.error);

  if (getEnumsResult.success && getEnumsResult.data) {
    console.log(`${colors.gray}  Retrieved enums: ${Object.keys(getEnumsResult.data).join(', ')}${colors.reset}`);
  }

  // Test 15: Unauthorized Access
  console.log(`${colors.cyan}\nTest Group: Security${colors.reset}`);
  const unauthorizedResult = await apiRequest('GET', '/budgets');
  logTest(
    'Unauthorized access blocked',
    !unauthorizedResult.success && unauthorizedResult.status === 401,
    unauthorizedResult.error
  );

  // Print Summary
  console.log(`${colors.blue}${colors.bold}\n📊 Test Summary\n${colors.reset}`);
  console.log(`${colors.green}✓ Passed: ${testResults.passed}${colors.reset}`);
  console.log(`${colors.red}✗ Failed: ${testResults.failed}${colors.reset}`);
  console.log(`${colors.blue}Total: ${testResults.passed + testResults.failed}${colors.reset}`);

  if (testResults.errors.length > 0) {
    console.log(`${colors.red}${colors.bold}\n❌ Failed Tests:\n${colors.reset}`);
    testResults.errors.forEach((error) => {
      console.log(`${colors.red}  • ${error.test}${colors.reset}`);
      console.log(`${colors.gray}    Error: ${error.error}${colors.reset}`);
    });
  } else {
    console.log(`${colors.green}${colors.bold}\n✅ All tests passed!\n${colors.reset}`);
  }

  // Exit with appropriate code
  process.exit(testResults.failed > 0 ? 1 : 0);
}

// Run tests
runTests().catch((error) => {
  console.error(`${colors.red}Fatal error:${colors.reset}`, error.message);
  process.exit(1);
});

