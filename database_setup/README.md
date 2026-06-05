# Database Setup

This directory contains **only** database and Redis initialization assets.

## Purpose
- Database schema creation and initialization
- Redis cache setup
- No backend application logic
- No Python code

## Contents

### `docker-compose.yml`
Orchestrates PostgreSQL + Redis services for local development.

**Services:**
- **postgres**: PostgreSQL 16 with pgvector extension
- **redis**: Redis 7 cache with persistence

### `Dockerfile`
Custom database image (optional). By default, uses `pgvector/pgvector:pg16`.

### `db/init/`
Database initialization scripts executed in alphabetical order:
- `01-init-databases.sql` - Creates databases
- `02-create-tables.sql` - Creates schema and tables
- `03-seed-data.sql` - Seeds initial data
- Additional scripts for auth and data sync

## Usage

### Start Database & Redis Only
```bash
cd database_setup
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Remove Data Volumes
```bash
docker-compose down -v
```

### View Logs
```bash
docker-compose logs -f
```

## Connection Details

### PostgreSQL
- **Host**: localhost
- **Port**: 55432
- **User**: finedu_admin
- **Password**: finedu_admin_password
- **Databases**: 
  - `postgres` (default)
  - `financial_auth_db` (created by init scripts)
  - `financial_data_db` (created by init scripts)

### Redis
- **Host**: localhost
- **Port**: 56379
- **Password**: finedu_redis_password

## Important Rules

### ✅ What Belongs Here
- Database Dockerfile
- docker-compose.yml for DB + Redis
- SQL initialization scripts
- Database configuration files

### ❌ What Does NOT Belong Here
- Python code
- Backend application logic
- API endpoints
- Business logic
- Test files
- Alembic migrations (those belong in `backend/`)

## Architecture Notes

1. **Database First**: Always start database services before backend
2. **Schema Creation**: Handled by SQL scripts in `db/init/`
3. **No Backend Dependency**: This directory is independent of backend code
4. **Idempotent Scripts**: Init scripts should be safe to run multiple times
5. **Data Persistence**: Data persists in Docker volumes

## Testing Database Connection

```bash
# PostgreSQL
psql -h localhost -p 55432 -U finedu_admin -d postgres

# Redis
redis-cli -h localhost -p 56379 -a finedu_redis_password
```

## Quick Setup Commands

```bash
# 1. Start database and Redis
cd database_setup
docker-compose up -d

# 2. Wait for init scripts to complete (30 seconds)
sleep 30

# 3. Verify databases are created
docker exec -it finedu_postgres psql -U finedu_admin -d postgres -c "\l"

# 4. Test seeded data (if available)
./scripts/test_seed.sh
```

## Health Checks

Both services include health checks:
- **PostgreSQL**: `pg_isready` command (interval: 10s, retries: 10)
- **Redis**: `redis-cli ping` command (interval: 5s, retries: 10)

## Troubleshooting

### Database won't start
```bash
# Check logs
docker-compose logs db

# Reset volumes and restart
docker-compose down -v
docker-compose up -d
```

### Redis connection refused
```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 56379 -a finedu_redis_password ping
```

### Init scripts not running
- Scripts must have `.sql` extension
- Scripts run in alphabetical order
- Check logs: `docker-compose logs db`
- Volume must be mounted: `./db/init:/docker-entrypoint-initdb.d`

### Complete reset
```bash
# Stop services and remove volumes
docker-compose down -v

# Remove Docker volumes explicitly
docker volume rm finedu_pg_data finedu_redis_data 2>/dev/null || true

# Start fresh
docker-compose up -d
```

## Production Deployment

For production, use managed database services:
- AWS RDS for PostgreSQL
- AWS ElastiCache for Redis
- Azure Database for PostgreSQL + Azure Cache for Redis
- Or equivalent services on other cloud providers

This local setup is for **development only**.

## Idempotent index creation (ops)

For production you may wish to create additional CONCURRENT indexes as a one-off ops task.
Run the included script which issues idempotent CREATE INDEX CONCURRENTLY IF NOT EXISTS statements.

Usage (zsh):

  DATABASE_URL="postgresql://user:pass@host:5432/financial_data_db" ./ops/create_indexes_postgres.sh

Notes:
- `CREATE INDEX CONCURRENTLY` must be executed outside a transaction and is safe to run on a primary.
- The script is idempotent: re-running it is a no-op for already-existing indexes.
- Run against each target database (auth DB vs data DB) as appropriate.
- Ensure the `pg_trgm` extension is available before creating trigram/Gin indexes.

If you cannot run the script, you can execute the same commands via `psql -c "<SQL>"` as documented in the PRODUCTION_FIX_PLAN.

## Network Architecture

```
┌─────────────────────────────────────┐
│     database_setup/ services        │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  PostgreSQL  │  │    Redis    │ │
│  │  Port: 55432 │  │ Port: 56379 │ │
│  └──────────────┘  └─────────────┘ │
│         ▲                 ▲         │
└─────────┼─────────────────┼─────────┘
          │                 │
          │                 │
┌─────────┼─────────────────┼─────────┐
│         │    Backend      │         │
│         └─────────────────┘         │
│    (Must check connectivity         │
│     before starting)                │
└─────────────────────────────────────┘
```
