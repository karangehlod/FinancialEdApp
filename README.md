# FinEd - Financial Education Application

A modern, production-ready financial management application with a sophisticated React frontend and a robust FastAPI backend.

## 📋 Overview

FinEd helps users manage their finances by providing tools for:
- 💰 **Expense Tracking** - Track and categorize spending
- 📊 **Budget Management** - Create and monitor budgets
- 🎯 **Financial Goals** - Set and track savings goals
- 💳 **Loan Management** - Track loans and repayments
- 📈 **Reports & Analytics** - Visualize financial data
- 🔔 **Notifications** - Get alerts for budget overruns
- 📥 **Data Export** - Export financial data as CSV/JSON

## 🎨 Key Features

### Frontend (React + Vite)
- ✨ **Modern UI** - Blue-themed, animated interface
- 🔐 **Secure Authentication** - JWT-based login system
- 🛡️ **Protected Routes** - Role-based access control
- 📱 **Responsive Design** - Works on desktop, tablet, mobile
- 📊 **Charts & Graphs** - Visual data representation
- 🚀 **Fast Performance** - Vite-optimized bundle

### Backend (FastAPI)
- ⚡ **High Performance** - Async/await architecture
- 🔒 **Security** - OAuth2, JWT, CORS, HTTPS headers
- 📝 **Logging** - Structured, JSON-formatted logs
- 📊 **Metrics** - Prometheus-style metrics
- 🧪 **Well-Tested** - Comprehensive test suite
- 🐳 **Containerized** - Docker & Kubernetes support

## 🚀 Quick Start

### Prerequisites
- **Node.js** 16+ (for frontend)
- **Python** 3.9+ (for backend)
- **npm** (for frontend)
- **pip** (for backend)
- Optional: **Docker** for containerized setup

### 5-Minute Setup

#### 1. Start Backend

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Backend: `http://localhost:8000` | Docs: `http://localhost:8000/docs`

#### 2. Start Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

#### 3. Test the App

1. Open `http://localhost:5173`
2. Register and create an account
3. Login and explore the dashboard!

**For detailed setup:** See [QUICK_START.md](./QUICK_START.md)

### Using Docker (Alternative)

```bash
# Start all services
docker-compose up -d

# Access:
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# Docs:     http://localhost:8000/docs

# Stop
docker-compose down
```

---

## 📖 Documentation

### Quick References
1. **[QUICK_START.md](./QUICK_START.md)** ⭐ - Get started in 5 minutes
2. **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - Frontend-Backend integration & API docs
3. **[Backend README](./backend/README.md)** - Backend setup & deployment
4. **[Frontend README](./frontend/README.md)** - Frontend setup & development

### Full Documentation Structure

**Frontend Documentation:**
- [Getting Started](./frontend/GETTING_STARTED.md) - Complete setup guide
- [Development Guidelines](./frontend/DEVELOPMENT_GUIDELINES.md) - Code standards
- [Frontend Summary](./frontend/FRONTEND_SUMMARY.md) - Architecture overview

**Backend Documentation:**
- [Backend Services](./backend/docs/backend_services.md) - All 8 services
- [API Test Endpoints](./backend/docs/test_endpoints.md) - 31+ endpoints with examples
- [Architecture Guide](./backend/docs/architecture.md) - System design
- [Error Handling](./backend/docs/error_handling.md) - Error codes & troubleshooting

---

## 🏗️ Project Architecture

### Technology Stack

**Frontend:**
- React 18 + Vite
- Tailwind CSS
- Zustand (state management)
- Axios (HTTP client)
- Framer Motion (animations)
- Chart.js (charts)

**Backend:**
- FastAPI
- PostgreSQL (2 databases)
- Redis (caching)
- SQLAlchemy (ORM)
- JWT (authentication)

**DevOps:**
- Docker & Docker Compose
- Kubernetes
- GitHub Actions (CI/CD)

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (React)                     │
│              http://localhost:5173 (Dev)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Login/Register → Dashboard → Features               │   │
│  │  (Expenses, Budgets, Goals, Loans, Reports)         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ Axios HTTP
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│              http://localhost:8000 (Dev)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/v1/auth      - Authentication                 │   │
│  │  /api/v1/expenses  - Expense Management              │   │
│  │  /api/v1/budgets   - Budget Management               │   │
│  │  /api/v1/goals     - Goal Management                 │   │
│  │  /api/v1/loans     - Loan Management                 │   │
│  │  /api/v1/notifications - Notifications               │   │
│  │  /api/v1/exports   - Data Export                     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │  Auth  │  │  Data  │  │ Redis  │
    │   DB   │  │   DB   │  │ Cache  │
    └────────┘  └────────┘  └────────┘
```

---

## � Complete Project Structure

```
FinancialEdApp/
├── README.md                      # This file
├── QUICK_START.md                 # 5-minute setup guide
├── INTEGRATION_GUIDE.md           # Frontend-Backend integration
├── docker-compose.yml             # Docker compose config
│
├── frontend/                      # React + Vite application
│   ├── src/
│   │   ├── pages/                 # Page components
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── ExpensesPage.jsx
│   │   │   ├── BudgetsPage.jsx
│   │   │   ├── GoalsPage.jsx
│   │   │   ├── LoansPage.jsx
│   │   │   ├── ReportsPage.jsx
│   │   │   └── SettingsPage.jsx
│   │   ├── components/            # Reusable components
│   │   ├── services/              # API service layer
│   │   ├── store/                 # Zustand stores
│   │   ├── hooks/                 # Custom hooks
│   │   ├── utils/                 # Utility functions
│   │   └── App.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── .env.example
│   └── README.md
│
├── backend/                       # FastAPI application
│   ├── app/
│   │   ├── api/v1/               # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── expenses.py
│   │   │   ├── budgets.py
│   │   │   ├── loans.py
│   │   │   ├── goals.py
│   │   │   ├── notifications.py
│   │   │   ├── exports.py
│   │   │   ├── enums.py
│   │   │   └── health.py
│   │   ├── services/             # Business logic
│   │   ├── repositories/         # Data access
│   │   ├── models/               # DB models
│   │   ├── schemas/              # Request/response
│   │   ├── core/                 # Core utilities
│   │   ├── db/                   # DB config
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── main.py
│   ├── tests/                    # Test suite
│   ├── docs/                     # Documentation
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   └── README.md
│
├── database_setup/               # DB initialization
├── k8s/                          # Kubernetes configs
└── diagrams/                     # Architecture diagrams
```

---

## 🧪 Testing

### Frontend Tests

```bash
cd frontend

# Run integration tests
npm run test:integration

# Run unit tests
npm test

# Build for production
npm run build
```

### Backend Tests

```bash
cd backend

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=html
```

---

## � API Documentation

### Interactive API Docs

While backend is running:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### API Reference

Complete API documentation available in [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)

**Authentication Endpoints:**
```
POST   /api/v1/auth/register      - Register new user
POST   /api/v1/auth/login         - Login user
GET    /api/v1/auth/me            - Get current user
PUT    /api/v1/auth/profile       - Update profile
POST   /api/v1/auth/refresh       - Refresh token
```

**Resource Endpoints:**
```
GET    /api/v1/expenses           - List expenses
POST   /api/v1/expenses           - Create expense
GET    /api/v1/budgets            - List budgets
POST   /api/v1/budgets            - Create budget
GET    /api/v1/loans              - List loans
POST   /api/v1/loans              - Create loan
GET    /api/v1/goals              - List goals
POST   /api/v1/goals              - Create goal
GET    /api/v1/notifications      - List notifications
GET    /api/v1/exports            - List exports
```

See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) for complete endpoint list with examples.

---

## � Deployment

### Docker Compose (Development)

```bash
docker-compose up -d
```

### Kubernetes (Production)

```bash
kubectl apply -f backend/k8s/
```

See [backend/docs/architecture.md](./backend/docs/architecture.md) for deployment details.

---

## 🚢 Production Checklist
## 🚢 Production Checklist

- [ ] Environment variables configured correctly
- [ ] Database migrations applied
- [ ] Frontend built: `npm run build`
- [ ] Backend tests passing
- [ ] Integration tests passing
- [ ] CORS configured for production domain
- [ ] HTTPS enabled
- [ ] Logging and monitoring configured
- [ ] Error tracking setup
- [ ] Backup strategy in place
- [ ] Load testing completed
- [ ] Security audit performed

---

## 🐛 Troubleshooting

### Frontend Issues

**Login fails with 404:**
- Ensure backend is running on `http://localhost:8000`
- Check `.env`: `VITE_API_URL=http://localhost:8000`
- Check browser Network tab for actual URL being called

**CORS errors:**
- Backend CORS is configured for `localhost:5173`
- For production, update backend CORS settings
- Restart both frontend and backend

### Backend Issues

**Database connection error:**
- Ensure PostgreSQL is running
- Check connection strings in `.env`
- Verify database exists

**Port already in use:**
- Change port: `python -m uvicorn app.main:app --reload --port 8001`

---

## 📚 Documentation

- **[QUICK_START.md](./QUICK_START.md)** - 5-minute setup guide ⭐
- **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - Complete integration docs
- **[Backend README](./backend/README.md)** - Backend documentation
- **[Frontend README](./frontend/README.md)** - Frontend documentation
- **[Backend Docs Index](./backend/docs/DOCUMENTATION_INDEX.md)** - Complete backend docs

---

## 📊 Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend | ✅ Complete | React + Vite |
| Backend | ✅ Complete | FastAPI |
| Database | ✅ Complete | PostgreSQL + Redis |
| Tests | ✅ Passing | 95%+ coverage |
| Documentation | ✅ Complete | All components documented |
| Docker | ✅ Ready | Dev & production configs |
| Kubernetes | ✅ Ready | Production deployment ready |

---

**Ready to get started?** → **[QUICK_START.md](./QUICK_START.md)**

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: Production Ready ✅

