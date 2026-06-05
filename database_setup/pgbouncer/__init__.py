"""
PgBouncer configuration for FinancialEdApp.

Connection pooling architecture:
  FastAPI pods (4 workers × 60 conns = 240 conns/pod)
       ↓
  PgBouncer (transaction-mode pooling, 1 pod)
       ↓
  PostgreSQL primary (max_connections = 500)

PgBouncer in transaction mode:
  - Each transaction gets a DB connection from the pool.
  - Connection is returned to pool when transaction ends.
  - Enables many more application connections than DB connections.
  - max_client_conn: 5000 (app-side connections)
  - default_pool_size: 100 (PostgreSQL connections PgBouncer holds)

IMPORTANT: Transaction mode incompatibilities:
  - SET/RESET session variables
  - LISTEN/NOTIFY (use direct connections for this)
  - Advisory locks spanning transactions
  - Prepared statements (disable in asyncpg: statement_cache_size=0)
"""
