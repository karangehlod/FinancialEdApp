# Backend Architecture

High-level system design and deployment overview.

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         Client Applications                         │
│              (Web Frontend, Mobile, Third-party APIs)              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  FastAPI Server │
                    │  (Port 8000)    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼────┐          ┌───▼────┐          ┌───▼──────┐
    │Auth DB  │          │Data DB │          │  Redis   │
    │(55432)  │          │(55433) │          │ (56379)  │
    └─────────┘          └────────┘          └──────────┘
```

---

## 🔄 Request Flow

```
1. Client Request
   │
   ├─► FastAPI Router (API Layer)
   │   - Route matching
   │   - Request validation
   │
   ├─► Authentication Middleware
   │   - JWT token validation
   │   - User identification
   │
   ├─► Service Layer
   │   - Business logic
   │   - Data manipulation
   │
   ├─► Repository Layer
   │   - Database queries
   │   - Data persistence
   │
   └─► Response
       - JSON serialization
       - HTTP status code
```

---

## 📦 Layered Architecture

### 1. **API Layer** (`app/api/v1/`)
Routes and endpoint definitions. Each module handles one domain:
- `auth.py` - Authentication endpoints
- `expenses.py` - Expense management
- `budgets.py` - Budget management
- `loans.py` - Loan management
- `goals.py` - Financial goals
- `notifications.py` - Notifications
- `exports.py` - Data exports

**Responsibilities:**
- HTTP request/response handling
- Input validation
- Route definition

### 2. **Service Layer** (`app/services/`)
Business logic and operations. Each service encapsulates domain logic:
- `auth_service.py` - User authentication
- `expense_service.py` - Expense tracking
- `budget_service.py` - Budget management
- `notification_service.py` - Notifications
- `email_service.py` - Email delivery
- `export_service.py` - Data export

**Responsibilities:**
- Business logic execution
- Data validation
- Service orchestration
- Error handling

### 3. **Repository Layer** (`app/repositories/`)
Data access abstraction. Each repository handles database operations:
- `user_repository.py` - User CRUD
- `expense_repository.py` - Expense CRUD
- `budget_repository.py` - Budget CRUD
- `loan_repository.py` - Loan CRUD
- `goal_repository.py` - Goal CRUD
- `notification_repository.py` - Notification CRUD

**Responsibilities:**
- SQL query execution
- Database transactions
- Data mapping to models

### 4. **Domain Layer** (`app/core/`, `app/models/`)
Pure business logic and data models:
- **Validators** - Input validation logic
- **Calculators** - EMI, interest calculations
- **Models** - SQLAlchemy ORM models
- **Schemas** - Pydantic request/response models

**Responsibilities:**
- Domain logic
- Data validation
- Type safety

---

## 💾 Database Design

### Two-Database Architecture

#### **Auth DB** (Port 55432)
Handles user authentication and credentials:
- User accounts
- Login credentials
- Password reset tokens
- JWT token blacklist

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255),
  full_name VARCHAR(255),
  created_at TIMESTAMP
);
```

#### **Data DB** (Port 55433)
Handles financial data and transactions:
- Expenses
- Budgets
- Loans
- Goals
- Notifications

```sql
CREATE TABLE expenses (
  id UUID PRIMARY KEY,
  user_id UUID,
  amount DECIMAL(10,2),
  category VARCHAR(50),
  description TEXT,
  date DATE,
  created_at TIMESTAMP
);
```

### Why Two Databases?
- ✅ Security isolation (credentials separate)
- ✅ Performance optimization
- ✅ Scalability (independent scaling)
- ✅ Easier access control
- ✅ Backup/recovery flexibility

---

## 🔐 Security Architecture

### Authentication Flow

```
1. User Registration
   └─► Password hashing (bcrypt)
   └─► Store in Auth DB

2. User Login
   ├─► Verify email exists
   ├─► Verify password matches hash
   └─► Generate JWT tokens

3. API Request
   ├─► Extract Bearer token from header
   ├─► Validate JWT signature
   ├─► Check token expiration
   └─► Extract user_id from claims

4. Token Refresh
   ├─► Validate refresh token
   ├─► Generate new access token
   └─► Return new token pair
```

### JWT Token Structure

```
Header: {
  "alg": "HS256",
  "typ": "JWT"
}

Payload: {
  "user_id": "user123",
  "email": "user@example.com",
  "iat": 1705574400,
  "exp": 1705660800
}

Signature: HMACSHA256(base64UrlEncode(header) + "." + base64UrlEncode(payload), SECRET_KEY)
```

### Security Features
- ✅ JWT token-based auth
- ✅ Refresh token rotation
- ✅ Password hashing (bcrypt)
- ✅ CORS protection
- ✅ Rate limiting
- ✅ Input validation
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ HTTPS support

---

## 📡 Redis Usage

Redis is used for:

1. **Token Blacklist** - Store revoked JWT tokens
2. **Caching** - Cache frequently accessed data
3. **Rate Limiting** - Track API request counts
4. **Sessions** - User session management (future)

**Connection:** `redis://localhost:56379/0`

---

## 🧪 Testing Architecture

```
tests/
├── conftest.py              # Shared fixtures
├── services/                # Service layer tests
│   ├── test_auth_service.py
│   ├── test_expense_service.py
│   └── ... (96%+ coverage)
├── repositories/            # Repository tests
│   ├── test_user_repository.py
│   └── ... (100% coverage)
├── api/                     # API endpoint tests
│   ├── test_auth_endpoints.py
│   └── ...
└── integration/             # End-to-end tests
    └── test_full_workflow.py
```

**Test Statistics:**
- **Total Tests:** 1,361+
- **Pass Rate:** 100%
- **Coverage:** 95%+ branch coverage
- **Services:** 96%+ average coverage

---

## 🚀 Deployment Architectures

### Development (Docker Compose)

```bash
docker-compose up -d
```

Services:
- FastAPI (port 8000)
- PostgreSQL Auth DB (port 55432)
- PostgreSQL Data DB (port 55433)
- Redis (port 56379)

### Production (Kubernetes)

```bash
kubectl apply -f k8s/
```

**K8s Resources:**
- Deployments (app, postgres, redis)
- Services (ClusterIP, LoadBalancer)
- ConfigMaps (configuration)
- Secrets (credentials)
- PersistentVolumeClaims (data storage)

**HA Setup:**
- Multiple app replicas
- Load balancing
- Database replication
- Redis persistence
- Auto-scaling based on CPU/memory

---

## 🔄 Data Flow Example: Create Expense

```
1. Frontend sends POST /api/v1/expenses/
   {
     "amount": 45.50,
     "category": "Food",
     "description": "Groceries",
     "date": "2024-01-18"
   }

2. FastAPI Router receives request
   ├─► Validates JSON schema
   └─► Extracts Authorization header

3. Authentication Middleware
   ├─► Decodes JWT token
   ├─► Validates signature
   └─► Loads current_user from claims

4. ExpenseService.create_expense()
   ├─► Validates input data
   ├─► Creates Expense object
   └─► Calls repository.create()

5. ExpenseRepository.create()
   ├─► Constructs SQL INSERT
   ├─► Executes transaction
   ├─► Commits to Data DB
   └─► Returns saved Expense

6. Service returns to Router

7. Router returns JSON response
   {
     "id": "expense123",
     "amount": 45.50,
     "category": "Food",
     ...
   }

8. Frontend receives 201 Created response
```

---

## 🔧 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.104+ |
| **Web Server** | Uvicorn | 0.24+ |
| **Database** | PostgreSQL | 14+ |
| **Cache** | Redis | 7+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Validation** | Pydantic | 2.0+ |
| **Auth** | PyJWT | 2.8+ |
| **Password** | bcrypt | 4.1+ |
| **Testing** | pytest | 7.4+ |
| **Logging** | Python logging | Built-in |

---

## 📈 Performance Considerations

### Database Optimization
- ✅ Indexed foreign keys
- ✅ Query optimization
- ✅ Connection pooling
- ✅ Transaction management

### API Performance
- ✅ Rate limiting (10 req/sec)
- ✅ Response compression
- ✅ Caching strategy
- ✅ Pagination (limit 100)

### Scalability
- ✅ Stateless app servers
- ✅ Horizontal scaling (K8s)
- ✅ Database replication
- ✅ Redis clustering

---

## 🔄 Environment Variables

**Database:**
```env
AUTH_DB_URL=postgresql://user:password@localhost:55432/auth_db
DATA_DB_URL=postgresql://user:password@localhost:55433/data_db
```

**JWT:**
```env
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

**Redis:**
```env
REDIS_URL=redis://localhost:56379/0
```

**API:**
```env
API_PORT=8000
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 📊 Monitoring & Logging

### Logging Levels
- `DEBUG` - Detailed debug information
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical system issues

### Logs Location
```
logs/
├── app.log      # General application logs
├── error.log    # Error-specific logs
└── access.log   # HTTP access logs
```

### Health Endpoints
- `GET /health` - Basic health check
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe

---

## 🔒 Data Privacy

- ✅ User passwords hashed with bcrypt
- ✅ No sensitive data in logs
- ✅ CORS protection
- ✅ Input sanitization
- ✅ SQL injection prevention
- ✅ Rate limiting to prevent abuse

---

## 📝 Deployment Checklist

- [ ] Update `.env` with production values
- [ ] Generate strong `JWT_SECRET_KEY`
- [ ] Configure database backups
- [ ] Set up Redis persistence
- [ ] Configure CORS origins
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable HTTPS
- [ ] Set up monitoring/logging
- [ ] Run database migrations
- [ ] Test all endpoints
- [ ] Setup CI/CD pipeline
- [ ] Configure auto-scaling

---

**Last Updated:** January 2026  
**Status:** Production Ready ✅
