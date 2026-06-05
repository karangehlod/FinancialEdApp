# Backend Services

Complete reference for all backend services and their dependencies.

## 📋 Service Overview

All services follow a consistent architecture with dependency injection, error handling, and comprehensive test coverage.

```
┌─────────────────────────────────────────────────┐
│  Service Layer (Business Logic)                 │
├─────────────────────────────────────────────────┤
│  • AuthService          - JWT authentication    │
│  • ExpenseService       - Expense tracking      │
│  • BudgetService        - Budget management     │
│  • LoanService          - Loan calculations     │
│  • GoalService          - Financial goals       │
│  • NotificationService  - User alerts           │
│  • EmailService         - Email sending         │
│  • ExportService        - Data export (CSV/XL)  │
└─────────────────────────────────────────────────┘
```

---

## 1. AuthService

**Location:** `app/services/auth_service.py`  
**Tests:** `tests/services/test_auth_service.py`  
**Coverage:** 97%

Handles user authentication, JWT token generation, and password management.

### Key Methods

```python
# Login user
authenticate(email: str, password: str) -> TokenResponse

# Register new user
register(email: str, password: str, full_name: str) -> User

# Refresh expired token
refresh_token(refresh_token: str) -> TokenResponse

# Validate JWT token
validate_token(token: str) -> dict

# Reset password
reset_password(email: str) -> bool
```

### Dependencies
- **Database:** Auth DB (PostgreSQL)
- **Redis:** Token blacklist storage
- **External:** Email service for password reset

### Example Usage
```python
service = AuthService(db_session)

# Login
response = await service.authenticate("user@example.com", "password")
# Returns: TokenResponse with access_token, refresh_token, user info

# Register
user = await service.register("new@example.com", "SecurePass123!", "John Doe")

# Refresh token
new_token = await service.refresh_token(refresh_token)
```

### Features
- ✅ JWT token-based authentication (24hr expiration)
- ✅ Refresh token rotation
- ✅ Password hashing with bcrypt
- ✅ Account lockout after failed attempts
- ✅ Email verification support

---

## 2. ExpenseService

**Location:** `app/services/expense_service.py`  
**Tests:** `tests/services/test_expense_service.py`  
**Coverage:** 96%

Manages expense tracking with filtering, analytics, and categorization.

### Key Methods

```python
# Create new expense
create_expense(user_id: str, expense_data: ExpenseCreate) -> Expense

# List all expenses with filters
list_user_expenses(user_id: str, **filters) -> List[Expense]

# Get single expense
get_expense(expense_id: str, user_id: str) -> Expense

# Update expense
update_expense(expense_id: str, user_id: str, data: ExpenseUpdate) -> Expense

# Delete expense
delete_expense(expense_id: str, user_id: str) -> bool

# Get summary statistics
get_summary(user_id: str) -> ExpenseSummary
```

### Dependencies
- **Database:** Data DB (PostgreSQL)
- **Other Services:** BudgetService (for budget tracking)

### Example Usage
```python
service = ExpenseService(db_session)

# Create expense
expense = await service.create_expense(
    user_id="user123",
    expense_data=ExpenseCreate(
        amount=45.50,
        category="Food",
        description="Grocery shopping",
        date="2024-01-15"
    )
)

# Get expenses for month
expenses = await service.list_user_expenses(
    user_id="user123",
    month="2024-01",
    category="Food"
)
```

### Features
- ✅ Category-based expense tracking
- ✅ Advanced filtering (date range, category, amount)
- ✅ Monthly spending summaries
- ✅ Expense analytics

---

## 3. BudgetService

**Location:** `app/services/budget_service.py`  
**Tests:** `tests/services/test_budget_service.py`  
**Coverage:** 98%

Manages budget creation, tracking, and alert generation.

### Key Methods

```python
# Create monthly budget
create_budget(user_id: str, budget_data: BudgetCreate) -> Budget

# List budgets
list_budgets(user_id: str) -> List[Budget]

# Get budget with spending details
get_budget(budget_id: str, user_id: str) -> BudgetDetail

# Update budget
update_budget(budget_id: str, user_id: str, data: BudgetUpdate) -> Budget

# Delete budget
delete_budget(budget_id: str, user_id: str) -> bool

# Get budget status
get_budget_status(budget_id: str) -> BudgetStatus
```

### Dependencies
- **Database:** Data DB (PostgreSQL)
- **Other Services:** ExpenseService, BudgetAlertService

### Example Usage
```python
service = BudgetService(db_session)

# Create monthly budget
budget = await service.create_budget(
    user_id="user123",
    budget_data=BudgetCreate(
        month="2024-01-01",
        category="Food",
        allocated_amount=5000.00
    )
)

# Get budget status
status = await service.get_budget_status(budget_id)
# Returns: {"allocated": 5000, "spent": 2500, "remaining": 2500, "utilization": "50%"}
```

### Features
- ✅ Monthly budget allocation by category
- ✅ Real-time spending tracking
- ✅ Budget status (on-track, warning, exceeded)
- ✅ Alert generation for budget thresholds

---

## 4. LoanService

**Location:** `app/services/loan_service.py`  
**Tests:** `tests/services/test_loan_service.py`  
**Coverage:** 95%

Manages loan tracking with EMI calculations and interest computations.

### Key Methods

```python
# Create new loan
create_loan(user_id: str, loan_data: LoanCreate) -> Loan

# List all loans
list_loans(user_id: str) -> List[Loan]

# Get loan details with calculations
get_loan(loan_id: str, user_id: str) -> LoanDetail

# Update loan information
update_loan(loan_id: str, user_id: str, data: LoanUpdate) -> Loan

# Delete loan
delete_loan(loan_id: str, user_id: str) -> bool

# Get EMI schedule
get_emi_schedule(loan_id: str) -> List[EMIPayment]

# Calculate prepayment impact
calculate_prepayment(loan_id: str, amount: float) -> PrepaymentResult
```

### Dependencies
- **Database:** Data DB (PostgreSQL)
- **Domain:** LoanCalculator (EMI, interest calculations)

### Example Usage
```python
service = LoanService(db_session)

# Create loan
loan = await service.create_loan(
    user_id="user123",
    loan_data=LoanCreate(
        loan_type="Home Loan",
        lender_name="HDFC Bank",
        principal_amount=5000000.00,
        interest_rate=7.5,
        loan_term_months=240,
        start_date="2024-01-01"
    )
)

# Get EMI calculations
schedule = await service.get_emi_schedule(loan_id)
# Returns list of monthly EMI payments with principal/interest breakdown
```

### Features
- ✅ Multiple loan types (Home, Auto, Personal, etc.)
- ✅ Accurate EMI calculations (monthly installments)
- ✅ Interest calculation with precision
- ✅ Prepayment impact analysis
- ✅ Complete EMI schedule generation

---

## 5. GoalService

**Location:** `app/services/goal_service.py`  
**Tests:** `tests/services/test_goal_service.py`  
**Coverage:** 94%

Tracks financial goals with progress monitoring and target calculations.

### Key Methods

```python
# Create financial goal
create_goal(user_id: str, goal_data: GoalCreate) -> Goal

# List all goals
list_goals(user_id: str) -> List[Goal]

# Get goal details with progress
get_goal(goal_id: str, user_id: str) -> GoalDetail

# Update goal
update_goal(goal_id: str, user_id: str, data: GoalUpdate) -> Goal

# Delete goal
delete_goal(goal_id: str, user_id: str) -> bool

# Add progress to goal
add_progress(goal_id: str, user_id: str, amount: float) -> GoalProgress

# Get progress analytics
get_progress_analytics(goal_id: str) -> ProgressAnalytics
```

### Dependencies
- **Database:** Data DB (PostgreSQL)

### Example Usage
```python
service = GoalService(db_session)

# Create goal
goal = await service.create_goal(
    user_id="user123",
    goal_data=GoalCreate(
        goal_name="Emergency Fund",
        goal_type="emergency_fund",
        target_amount=500000.00,
        target_date="2025-12-31",
        priority="high"
    )
)

# Add progress
progress = await service.add_progress(
    goal_id=goal.id,
    user_id="user123",
    amount=50000.00
)

# Get analytics
analytics = await service.get_progress_analytics(goal_id)
# Returns: {"target": 500000, "current": 50000, "progress": "10%", "months_remaining": 12}
```

### Features
- ✅ Multiple goal types (emergency fund, retirement, vacation, etc.)
- ✅ Progress tracking with milestones
- ✅ Target date calculations
- ✅ Priority-based goal management
- ✅ Progress analytics

---

## 6. NotificationService

**Location:** `app/services/notification_service.py`  
**Tests:** `tests/services/test_notification_service.py`  
**Coverage:** 92%

Manages user notifications for budget alerts, goal milestones, and system events.

### Key Methods

```python
# Get all notifications
get_notifications(user_id: str, unread_only: bool = False) -> List[Notification]

# Mark notification as read
mark_as_read(notification_id: str, user_id: str) -> bool

# Delete notification
delete_notification(notification_id: str, user_id: str) -> bool

# Create notification (internal)
create_notification(user_id: str, notification_data: NotificationCreate) -> Notification

# Clear all notifications
clear_all(user_id: str) -> bool
```

### Dependencies
- **Database:** Data DB (PostgreSQL)
- **Other Services:** EmailService (for email notifications)

### Example Usage
```python
service = NotificationService(db_session)

# Get unread notifications
notifications = await service.get_notifications(
    user_id="user123",
    unread_only=True
)

# Mark as read
await service.mark_as_read(
    notification_id="notif123",
    user_id="user123"
)
```

### Features
- ✅ Budget threshold alerts
- ✅ Goal milestone notifications
- ✅ System event notifications
- ✅ Read/unread status tracking
- ✅ Optional email delivery

---

## 7. EmailService

**Location:** `app/services/email_service.py`  
**Tests:** `tests/services/test_email_service.py`  
**Coverage:** 92%

Handles email sending for notifications, password resets, and confirmations.

### Key Methods

```python
# Send simple email
send_email(to: str, subject: str, body: str) -> bool

# Send password reset email
send_password_reset(to: str, reset_token: str) -> bool

# Send welcome email
send_welcome_email(to: str, user_name: str) -> bool

# Send notification email
send_notification_email(to: str, notification: dict) -> bool
```

### Dependencies
- **External:** SMTP server (Gmail, SendGrid, etc.)
- **Configuration:** EMAIL_FROM, SMTP_HOST, SMTP_PORT in .env

### Example Usage
```python
service = EmailService()

# Send password reset
await service.send_password_reset(
    to="user@example.com",
    reset_token="abc123xyz"
)

# Send custom email
await service.send_email(
    to="user@example.com",
    subject="Budget Alert",
    body="Your Food budget is 80% utilized"
)
```

### Features
- ✅ HTML and plain text email support
- ✅ Email templates
- ✅ Password reset emails
- ✅ Welcome and confirmation emails
- ✅ Error handling and retry logic

---

## 8. ExportService

**Location:** `app/services/export_service.py`  
**Tests:** `tests/services/test_export_service.py`  
**Coverage:** 93%

Generates CSV and Excel exports of financial data.

### Key Methods

```python
# Export expenses to CSV
export_expenses_csv(user_id: str, start_date: Optional[date], end_date: Optional[date]) -> BytesIO

# Export budgets to CSV
export_budgets_csv(user_id: str, month: Optional[date]) -> BytesIO

# Export loans to CSV
export_loans_csv(user_id: str) -> BytesIO

# Export goals to CSV
export_goals_csv(user_id: str) -> BytesIO

# Export complete data to Excel
export_complete_financial_data_excel(user_id: str) -> BytesIO
```

### Dependencies
- **Database:** Data DB (PostgreSQL)
- **Libraries:** openpyxl (Excel), csv (CSV)

### Example Usage
```python
service = ExportService(db_session)

# Export expenses as CSV
csv_data = await service.export_expenses_csv(
    user_id="user123",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
# Returns BytesIO object that can be streamed as file

# Export all data as Excel
excel_data = await service.export_complete_financial_data_excel(
    user_id="user123"
)
# Returns Excel file with multiple sheets (Expenses, Budgets, Loans, Goals)
```

### Features
- ✅ CSV export for individual data types
- ✅ Excel export with multiple sheets
- ✅ Formatted headers and columns
- ✅ Date range filtering
- ✅ Streaming response for large files

---

## Service Dependencies Summary

| Service | DB | Redis | External |
|---------|----|----|----------|
| AuthService | Auth DB | ✅ (tokens) | Email |
| ExpenseService | Data DB | ❌ | ❌ |
| BudgetService | Data DB | ❌ | ❌ |
| LoanService | Data DB | ❌ | ❌ |
| GoalService | Data DB | ❌ | ❌ |
| NotificationService | Data DB | ❌ | Email |
| EmailService | ❌ | ❌ | SMTP |
| ExportService | Data DB | ❌ | ❌ |

---

## Service Usage in API

All services are injected via FastAPI dependencies:

```python
from app.dependencies import get_expense_service

@router.get("/expenses")
async def list_expenses(
    service: ExpenseService = Depends(get_expense_service),
    current_user: User = Depends(get_current_user)
):
    return await service.list_user_expenses(current_user.id)
```

See [test_endpoints.md](test_endpoints.md) for API endpoint details.

---

**Last Updated:** January 2026
