# Error Handling Guide

Reference for error codes, troubleshooting, and resolution strategies.

## 🔴 HTTP Status Codes

| Code | Status | Usage | Recovery |
|------|--------|-------|----------|
| **200** | OK | Successful request | No action needed |
| **201** | Created | Resource created | No action needed |
| **204** | No Content | Deleted successfully | No action needed |
| **400** | Bad Request | Invalid request data | Fix request and retry |
| **401** | Unauthorized | Missing/invalid token | Re-authenticate |
| **403** | Forbidden | Not authorized for resource | Check permissions |
| **404** | Not Found | Resource doesn't exist | Verify resource ID |
| **409** | Conflict | Resource conflict | Handle duplicate/conflict |
| **422** | Unprocessable Entity | Validation error | Fix input data |
| **500** | Server Error | Internal server error | Check server logs |
| **503** | Service Unavailable | Service down | Wait and retry |

---

## 🔐 Authentication Errors (401)

### AUTH_001: Invalid Credentials
**Message:** `"Invalid email or password"`

**Causes:**
- Incorrect email address
- Incorrect password
- User account doesn't exist

**Solution:**
```bash
# Verify credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "correct@email.com",
    "password": "correct_password"
  }'

# If still failing:
# 1. Check email spelling
# 2. Reset password using forgot password endpoint
# 3. Verify user was registered
```

---

### AUTH_002: Token Expired
**Message:** `"Token has expired. Please login again"`

**Causes:**
- Access token issued more than 24 hours ago
- Session timeout
- System clock mismatch

**Solution:**
```bash
# Refresh token using refresh endpoint
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'

# Or re-authenticate
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }'

# Check system time: date
```

---

### AUTH_003: Invalid Token
**Message:** `"Invalid or malformed token"`

**Causes:**
- Token has been tampered with
- Token format is incorrect
- Token from different service

**Solution:**
```bash
# Clear stored token and re-authenticate
# 1. Remove token from localStorage/cookie
# 2. Re-login to get valid token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }'

# Verify token format: Authorization: Bearer <token>
```

---

### AUTH_004: Token Missing
**Message:** `"Authorization header missing"`

**Causes:**
- Authorization header not included
- Bearer prefix missing
- Token value is empty

**Solution:**
```bash
# Correct header format:
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

# Example request:
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer your_access_token"
```

---

## ❌ Validation Errors (400/422)

### VAL_001: Invalid Input Format
**Message:** `"Invalid input data"`

**Common Issues:**
- Wrong data type (string instead of number)
- Missing required fields
- Invalid email format
- Invalid date format

**Solution:**
```bash
# Expense creation - correct format:
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.50,          # Must be number
    "category": "Food",       # Must be string
    "description": "Groceries", # Required field
    "date": "2024-01-18"      # Format: YYYY-MM-DD
  }'

# Budget creation - correct format:
curl -X POST http://localhost:8000/api/v1/budgets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "month": "2024-01-01",        # Format: YYYY-MM-01
    "category": "FOOD",           # Must match enum
    "allocated_amount": 5000.00   # Must be number
  }'
```

---

### VAL_002: Amount Out of Range
**Message:** `"Amount must be between min and max"`

**Causes:**
- Negative amount
- Amount too large
- Decimal precision issue

**Solution:**
```bash
# Valid amount ranges:
# Expenses: 0.01 to 999,999.99
# Budgets: 1 to 999,999.99
# Loans: 1,000 to 10,000,000

# Correct request:
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.50,    # Valid: > 0
    "category": "Food",
    "description": "Groceries",
    "date": "2024-01-18"
  }'
```

---

### VAL_003: Invalid Category
**Message:** `"Category not found in allowed categories"`

**Causes:**
- Typo in category name
- Invalid category value
- Case sensitivity issue

**Solution:**
```bash
# Allowed categories:
# Food, Transportation, Entertainment, Utilities, Shopping, Healthcare, Education, etc.

# Correct request:
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.50,
    "category": "Food",      # Valid category
    "description": "Groceries",
    "date": "2024-01-18"
  }'
```

---

### VAL_004: Invalid Date Format
**Message:** `"Date must be in YYYY-MM-DD format"`

**Causes:**
- Wrong date format
- Invalid date (e.g., Feb 30)
- Future date for expense

**Solution:**
```bash
# Correct date format: YYYY-MM-DD
# Valid: "2024-01-18"
# Invalid: "18-01-2024", "2024/01/18", "01/18/2024"

# Correct request:
curl -X POST http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.50,
    "category": "Food",
    "description": "Groceries",
    "date": "2024-01-18"    # Format: YYYY-MM-DD
  }'
```

---

## 🔍 Resource Not Found (404)

### RES_001: Resource Not Found
**Message:** `"Resource not found"`

**Causes:**
- Invalid resource ID
- Resource was deleted
- Resource belongs to different user

**Solution:**
```bash
# 1. Verify resource ID is correct
# 2. List all resources to find valid ID
curl -X GET http://localhost:8000/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Use valid ID from response
curl -X GET http://localhost:8000/api/v1/expenses/expense123 \
  -H "Authorization: Bearer $TOKEN"

# 4. Check if resource was deleted
# If deleted, create new resource
```

---

## ⚠️ Permission Errors (403)

### PERM_001: Unauthorized Access
**Message:** `"You do not have permission to access this resource"`

**Causes:**
- Accessing another user's data
- Insufficient permissions
- Deleted user account

**Solution:**
```bash
# Verify you're accessing own data
# Endpoints return data only for authenticated user

# Get current user info:
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# User can only access own resources (filtered by user_id)
# Cannot access other users' expenses, budgets, etc.

# If needed, request access from resource owner
```

---

## 💥 Server Errors (500)

### ERR_001: Internal Server Error
**Message:** `"Internal server error"`

**Causes:**
- Database connection failed
- Unhandled exception
- Service dependency error

**Solution:**
```bash
# 1. Check server logs
docker-compose logs app

# 2. Verify database is running
docker-compose ps

# 3. Check Redis connection
docker-compose logs redis

# 4. Restart services
docker-compose restart

# 5. Check .env configuration
# Verify all required variables are set

# 6. Check database migrations
alembic upgrade head
```

---

## 🔗 Service Unavailable (503)

### SVC_001: Service Temporarily Unavailable
**Message:** `"Service is temporarily unavailable"`

**Causes:**
- Server is down
- Database maintenance
- Redis unavailable
- High load

**Solution:**
```bash
# Check service status
curl http://localhost:8000/health

# Check individual services
docker-compose ps

# Restart if needed
docker-compose restart

# Wait and retry (exponential backoff recommended)
```

---

## 🛠️ Troubleshooting Guide

### Problem: Cannot Login

**Steps:**
1. Verify user exists: Check email in Auth DB
2. Verify password: Reset password if forgotten
3. Check token generation: Verify JWT_SECRET_KEY in .env
4. Check Auth DB connection: `docker-compose logs postgres_auth`

```bash
# Reset password
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

---

### Problem: API Returns 404 for Valid Endpoint

**Steps:**
1. Verify endpoint path is correct
2. Check HTTP method (GET/POST/PUT/DELETE)
3. Verify API is running: `docker-compose ps`
4. Check backend logs: `docker-compose logs app`

```bash
# List all available endpoints
curl http://localhost:8000/docs

# Test health endpoint
curl http://localhost:8000/health
```

---

### Problem: Database Connection Error

**Steps:**
1. Check containers are running: `docker-compose ps`
2. Verify database credentials in .env
3. Check port conflicts (55432, 55433)
4. Check container logs: `docker-compose logs postgres_auth`

```bash
# Restart databases
docker-compose restart postgres_auth postgres_data

# Check logs
docker-compose logs postgres_auth postgres_data

# Verify connection
psql postgresql://user:password@localhost:55432/auth_db
```

---

### Problem: Redis Connection Error

**Steps:**
1. Check Redis container: `docker-compose ps redis`
2. Verify REDIS_URL in .env
3. Check port 56379 is available
4. Check Redis logs: `docker-compose logs redis`

```bash
# Restart Redis
docker-compose restart redis

# Test connection
redis-cli -h localhost -p 56379 PING
# Expected: PONG
```

---

### Problem: Token Always Expired

**Steps:**
1. Check system time: `date`
2. Verify JWT_EXPIRATION_HOURS in .env (default: 24)
3. Check token generation: Verify JWT_SECRET_KEY
4. Use refresh token endpoint

```bash
# Check system time matches server time
date

# Refresh expired token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'
```

---

## 📋 Error Response Format

All errors follow consistent format:

```json
{
  "detail": "Detailed error message",
  "error_code": "ERROR_001",
  "timestamp": "2024-01-18T10:00:00Z",
  "path": "/api/v1/expenses/",
  "method": "POST"
}
```

---

## 🔄 Retry Strategy

**Recommended retry approach (Exponential Backoff):**

```
Attempt 1: Immediate
Attempt 2: Wait 1 second
Attempt 3: Wait 2 seconds
Attempt 4: Wait 4 seconds
Attempt 5: Wait 8 seconds
Max: 5 attempts
```

**Retryable errors:**
- 408 Request Timeout
- 429 Too Many Requests
- 500 Internal Server Error
- 503 Service Unavailable

**Non-retryable errors:**
- 400 Bad Request (invalid data)
- 401 Unauthorized (invalid token)
- 403 Forbidden (no permission)
- 404 Not Found (resource doesn't exist)

---

## 🚨 Critical Errors

| Scenario | Status | Action |
|----------|--------|--------|
| **Database Down** | 500 | Restart database, check logs |
| **Redis Down** | 500 | Restart Redis, check connection |
| **All Services Down** | 503 | Run `docker-compose up -d` |
| **Migration Failed** | 500 | Run `alembic upgrade head` |
| **Disk Full** | 500 | Free up disk space |

---

## 📞 Support & Debugging

**Generate Debug Info:**
```bash
# Collect system information
echo "=== System Info ===" && uname -a
echo "=== Docker Status ===" && docker-compose ps
echo "=== App Logs ===" && docker-compose logs app | tail -50
echo "=== Database Status ===" && docker-compose logs postgres_auth | tail -20
echo "=== Redis Status ===" && docker-compose logs redis | tail -20
```

**Check .env Configuration:**
```bash
# Verify required variables
grep -E "^(AUTH_DB|DATA_DB|JWT|REDIS|API)" .env
```

---

**Last Updated:** January 2026  
**Support:** Check logs with `docker-compose logs [service_name]`
