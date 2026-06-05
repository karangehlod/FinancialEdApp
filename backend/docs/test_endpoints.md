# API Endpoints & Testing Guide

Complete reference for all API endpoints and how to test them.

## 📡 Quick Reference

**Base URL:** `http://localhost:8000/api/v1`  
**Health Check:** `http://localhost:8000/health`  
**Interactive Docs:** `http://localhost:8000/docs`

---

## 🔐 Authentication

All endpoints except `register` and `login` require Bearer token authentication.

### Headers
```bash
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

---

## 🧪 Running Tests

### Automated Testing

```bash
# Run all tests (31 tests)
./test_endpoints.sh

# Quick test mode (16 tests - key endpoints only)
./test_endpoints.sh --quick-test

# Health check only
./test_endpoints.sh --health-check-only

# Custom test settings
./test_endpoints.sh --url http://localhost:8000/api/v1 \
                   --email test@example.com \
                   --password TestPassword123! \
                   --verbose
```

**Expected Output:**
```
Total Tests: 31
Passed: 31 ✅
Failed: 0
Skipped: 0
```

---

## 📚 API Endpoints

### 1. Authentication Endpoints

#### Register User
```bash
POST /auth/register
```

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "id": "user123",
  "email": "newuser@example.com",
  "full_name": "John Doe",
  "created_at": "2024-01-18T10:00:00Z"
}
```

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

---

#### Login
```bash
POST /auth/login
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "user123",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

**Test:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

---

#### Get Current User
```bash
GET /auth/me
```

**Response (200):**
```json
{
  "id": "user123",
  "email": "user@example.com",
  "full_name": "John Doe",
  "monthly_income": 6000.00,
  "created_at": "2024-01-15T08:30:00Z"
}
```

**Test:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

### 2. Expense Endpoints

#### Create Expense
```bash
POST /expenses/
```

**Request:**
```json
{
  "amount": 45.50,
  "category": "Food",
  "description": "Grocery shopping",
  "date": "2024-01-18"
}
```

**Response (201):**
```json
{
  "id": "expense123",
  "user_id": "user123",
  "amount": 45.50,
  "category": "Food",
  "description": "Grocery shopping",
  "date": "2024-01-18",
  "created_at": "2024-01-18T10:00:00Z"
}
```

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.50,
    "category": "Food",
    "description": "Grocery shopping",
    "date": "2024-01-18"
  }'
```

---

#### List Expenses
```bash
GET /expenses/
```

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Number of records to return (default: 100)
- `category`: Filter by category
- `month`: Filter by month (YYYY-MM format)

**Response (200):**
```json
[
  {
    "id": "expense123",
    "amount": 45.50,
    "category": "Food",
    "description": "Grocery shopping",
    "date": "2024-01-18"
  }
]
```

**Test:**
```bash
# List all expenses
curl -X GET http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN"

# Filter by category
curl -X GET "http://localhost:8000/api/v1/expenses/?category=Food" \
  -H "Authorization: Bearer $TOKEN"

# Filter by month
curl -X GET "http://localhost:8000/api/v1/expenses/?month=2024-01" \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Get Single Expense
```bash
GET /expenses/{expense_id}
```

**Response (200):**
```json
{
  "id": "expense123",
  "amount": 45.50,
  "category": "Food",
  "description": "Grocery shopping",
  "date": "2024-01-18"
}
```

**Test:**
```bash
curl -X GET http://localhost:8000/api/v1/expenses/expense123 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Update Expense
```bash
PUT /expenses/{expense_id}
```

**Request:**
```json
{
  "amount": 50.00,
  "description": "Updated grocery shopping"
}
```

**Response (200):**
```json
{
  "id": "expense123",
  "amount": 50.00,
  "category": "Food",
  "description": "Updated grocery shopping",
  "date": "2024-01-18"
}
```

**Test:**
```bash
curl -X PUT http://localhost:8000/api/v1/expenses/expense123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50.00,
    "description": "Updated grocery shopping"
  }'
```

---

#### Delete Expense
```bash
DELETE /expenses/{expense_id}
```

**Response (204):** No content

**Test:**
```bash
curl -X DELETE http://localhost:8000/api/v1/expenses/expense123 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Get Expense Summary
```bash
GET /expenses/summary
```

**Response (200):**
```json
{
  "total_expenses": 500.00,
  "average_expense": 25.00,
  "category_breakdown": {
    "Food": 200.00,
    "Transportation": 150.00,
    "Entertainment": 150.00
  },
  "monthly_trend": {
    "2024-01": 500.00
  }
}
```

**Test:**
```bash
curl -X GET http://localhost:8000/api/v1/expenses/summary \
  -H "Authorization: Bearer $TOKEN"
```

---

### 3. Budget Endpoints

#### Create Budget
```bash
POST /budgets/
```

**Request:**
```json
{
  "month": "2024-01-01",
  "category": "FOOD",
  "allocated_amount": 5000.00
}
```

**Response (201):**
```json
{
  "id": "budget123",
  "month": "2024-01-01",
  "category": "FOOD",
  "allocated_amount": 5000.00,
  "spent_amount": 0.00,
  "remaining_amount": 5000.00,
  "created_at": "2024-01-18T10:00:00Z"
}
```

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/budgets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "month": "2024-01-01",
    "category": "FOOD",
    "allocated_amount": 5000.00
  }'
```

---

#### List Budgets
```bash
GET /budgets/
```

**Response (200):**
```json
[
  {
    "id": "budget123",
    "month": "2024-01-01",
    "category": "FOOD",
    "allocated_amount": 5000.00,
    "spent_amount": 2500.00,
    "remaining_amount": 2500.00
  }
]
```

**Test:**
```bash
curl -X GET http://localhost:8000/api/v1/budgets/ \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Get Budget Details
```bash
GET /budgets/{budget_id}
```

**Response (200):**
```json
{
  "id": "budget123",
  "month": "2024-01-01",
  "category": "FOOD",
  "allocated_amount": 5000.00,
  "spent_amount": 2500.00,
  "remaining_amount": 2500.00,
  "utilization_percentage": 50.0,
  "status": "on_track"
}
```

**Test:**
```bash
curl -X GET http://localhost:8000/api/v1/budgets/budget123 \
  -H "Authorization: Bearer $TOKEN"
```

---

#### Update Budget
```bash
PUT /budgets/{budget_id}
```

**Request:**
```json
{
  "allocated_amount": 6000.00
}
```

**Response (200):**
```json
{
  "id": "budget123",
  "allocated_amount": 6000.00,
  "spent_amount": 2500.00,
  "remaining_amount": 3500.00
}
```

**Test:**
```bash
curl -X PUT http://localhost:8000/api/v1/budgets/budget123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "allocated_amount": 6000.00
  }'
```

---

#### Delete Budget
```bash
DELETE /budgets/{budget_id}
```

**Response (204):** No content

**Test:**
```bash
curl -X DELETE http://localhost:8000/api/v1/budgets/budget123 \
  -H "Authorization: Bearer $TOKEN"
```

---

### 4. Loan Endpoints

#### Create Loan
```bash
POST /loans/
```

**Request:**
```json
{
  "loan_type": "Home Loan",
  "lender_name": "HDFC Bank",
  "principal_amount": 5000000.00,
  "interest_rate": 7.5,
  "loan_term_months": 240,
  "start_date": "2024-01-18"
}
```

**Response (201):**
```json
{
  "id": "loan123",
  "loan_type": "Home Loan",
  "lender_name": "HDFC Bank",
  "principal_amount": 5000000.00,
  "interest_rate": 7.5,
  "loan_term_months": 240,
  "emi_amount": 41769.49,
  "created_at": "2024-01-18T10:00:00Z"
}
```

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/loans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "loan_type": "Home Loan",
    "lender_name": "HDFC Bank",
    "principal_amount": 5000000.00,
    "interest_rate": 7.5,
    "loan_term_months": 240,
    "start_date": "2024-01-18"
  }'
```

---

#### List Loans
```bash
GET /loans/
```

**Response (200):**
```json
[
  {
    "id": "loan123",
    "loan_type": "Home Loan",
    "lender_name": "HDFC Bank",
    "principal_amount": 5000000.00,
    "interest_rate": 7.5,
    "emi_amount": 41769.49,
    "outstanding_balance": 4900000.00
  }
]
```

---

#### Get Loan Details
```bash
GET /loans/{loan_id}
```

**Response (200):**
```json
{
  "id": "loan123",
  "loan_type": "Home Loan",
  "lender_name": "HDFC Bank",
  "principal_amount": 5000000.00,
  "interest_rate": 7.5,
  "loan_term_months": 240,
  "emi_amount": 41769.49,
  "paid_amount": 100000.00,
  "outstanding_balance": 4900000.00
}
```

---

#### Update Loan
```bash
PUT /loans/{loan_id}
```

**Request:**
```json
{
  "interest_rate": 7.75
}
```

**Response (200):**
```json
{
  "id": "loan123",
  "interest_rate": 7.75,
  "emi_amount": 42000.00
}
```

---

#### Delete Loan
```bash
DELETE /loans/{loan_id}
```

**Response (204):** No content

---

### 5. Goal Endpoints

#### Create Goal
```bash
POST /goals/
```

**Request:**
```json
{
  "goal_name": "Emergency Fund",
  "goal_type": "emergency_fund",
  "target_amount": 500000.00,
  "target_date": "2025-12-31",
  "priority": "high"
}
```

**Response (201):**
```json
{
  "id": "goal123",
  "goal_name": "Emergency Fund",
  "goal_type": "emergency_fund",
  "target_amount": 500000.00,
  "current_amount": 0.00,
  "target_date": "2025-12-31",
  "priority": "high",
  "progress_percentage": 0.0
}
```

---

#### List Goals
```bash
GET /goals/
```

**Response (200):**
```json
[
  {
    "id": "goal123",
    "goal_name": "Emergency Fund",
    "target_amount": 500000.00,
    "current_amount": 50000.00,
    "progress_percentage": 10.0,
    "priority": "high"
  }
]
```

---

#### Get Goal Details
```bash
GET /goals/{goal_id}
```

**Response (200):**
```json
{
  "id": "goal123",
  "goal_name": "Emergency Fund",
  "goal_type": "emergency_fund",
  "target_amount": 500000.00,
  "current_amount": 50000.00,
  "progress_percentage": 10.0,
  "target_date": "2025-12-31",
  "months_remaining": 12,
  "monthly_required": 37500.00
}
```

---

#### Update Goal
```bash
PUT /goals/{goal_id}
```

**Request:**
```json
{
  "target_amount": 600000.00
}
```

**Response (200):**
```json
{
  "id": "goal123",
  "target_amount": 600000.00,
  "progress_percentage": 8.33
}
```

---

#### Delete Goal
```bash
DELETE /goals/{goal_id}
```

**Response (204):** No content

---

### 6. Notification Endpoints

#### Get All Notifications
```bash
GET /notifications
```

**Query Parameters:**
- `unread`: Filter unread only (true/false)

**Response (200):**
```json
[
  {
    "id": "notif123",
    "user_id": "user123",
    "title": "Budget Alert",
    "message": "Your Food budget is 80% utilized",
    "type": "budget_alert",
    "read": false,
    "created_at": "2024-01-18T10:00:00Z"
  }
]
```

**Test:**
```bash
# All notifications
curl -X GET http://localhost:8000/api/v1/notifications \
  -H "Authorization: Bearer $TOKEN"

# Unread only
curl -X GET "http://localhost:8000/api/v1/notifications?unread=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 7. Export Endpoints

#### Export Expenses as CSV
```bash
POST /exports/expenses/csv
```

**Query Parameters:**
- `start_date`: Optional - Filter start date (YYYY-MM-DD)
- `end_date`: Optional - Filter end date (YYYY-MM-DD)

**Response (200):** CSV file

**Test:**
```bash
curl -X POST "http://localhost:8000/api/v1/exports/expenses/csv" \
  -H "Authorization: Bearer $TOKEN" \
  --output expenses.csv
```

---

#### Export Complete Financial Data
```bash
POST /exports/complete/excel
```

**Response (200):** Excel file with sheets: Expenses, Budgets, Loans, Goals

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/exports/complete/excel \
  -H "Authorization: Bearer $TOKEN" \
  --output financial_data.xlsx
```

---

## 🔍 Common Patterns

### Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_001",
  "timestamp": "2024-01-18T10:00:00Z"
}
```

Common HTTP Status Codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Deleted successfully
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing/invalid token
- `404 Not Found` - Resource not found
- `500 Server Error` - Internal error

---

### Pagination

List endpoints support pagination:

```bash
curl -X GET "http://localhost:8000/api/v1/expenses/?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Test Results Summary

| Test Category | Count | Status |
|---------------|-------|--------|
| Authentication | 4 | ✅ Passing |
| Expenses | 6 | ✅ Passing |
| Budgets | 5 | ✅ Passing |
| Loans | 5 | ✅ Passing |
| Goals | 5 | ✅ Passing |
| Notifications | 2 | ✅ Passing |
| Exports | 2 | ✅ Passing |
| **Total** | **31** | **✅ All Passing** |

---

**Last Updated:** January 2026  
**Interactive Docs:** http://localhost:8000/docs
