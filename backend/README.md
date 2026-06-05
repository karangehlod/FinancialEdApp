# FinancialEdApp — Backend

This document describes the backend service for FinancialEdApp. It covers features, architecture, how things work, how to run locally and in Docker/Kubernetes, testing, scaling guidance for high traffic (1M users), security, and contribution / interview notes.

Table of contents
- Project summary
- Key features
- Tech stack
- Repo layout
- How it works (high level architecture)
- Running locally
- Running with Docker / docker-compose
- Running in Kubernetes (overview)
- Testing
- Observability, logging and monitoring
- Scaling to 1M users — design & operational guidance
- Security and privacy
- Contribution guide
- Interview guide / talking points


Project summary
---------------
The backend is a Python-based service that provides core APIs for FinancialEdApp: user management, financial data retrieval, goals, budgets, transactions ingestion, analytics and the conversational advisor agent. It is implemented as a modular web application designed to be stateless at the HTTP layer and backed by persistent services (Postgres, Redis, etc.).

Key features
------------
- User authentication and authorization (cookie/session or token based)
- CRUD for users, goals, budgets, loans and transactions
- Financial analytics and recommendations engine
- LangGraph-based conversational agent that can call domain tools for personalized advice
- Database migrations and seeding utilities
- Test suite with unit and integration tests
- Docker and k8s deployment scripts

Tech stack
----------
- Python 3.11+ (pyproject-managed)
- FastAPI (or the chosen ASGI framework in the codebase)
- SQLAlchemy / alembic for DB models & migrations
- PostgreSQL as primary relational store
- Redis for caching and session storage
- LangChain / LangGraph for the agent orchestration
- Pytest for tests
- Docker / docker-compose for local containerized development
- Kubernetes manifests and helper scripts for cluster deployment

Repo layout
----------
(Top-level directories and their purpose)
- app/: main backend application code
  - api/: request handlers / router definitions
  - core/: domain logic
  - db/: database helpers (sessions, init), migrations
  - models/: ORM models
  - repositories/: data access layer
  - schemas/: pydantic request/response models
  - services/: business services (chat agent, analytics)
  - utils/: helpers and common utilities
- alembic/ or migrations/: DB migration tooling
- tests/: unit and integration tests
- docker-compose.yml and docker-compose.dev.yml: local compose setups
- Dockerfile: image definition for the service
- k8s/: Kubernetes manifests for production-like deployment
- scripts/ and top-level helper bash scripts for tasks and deploys

How it works (high level architecture)
-------------------------------------
- HTTP/API Layer: Accepts requests from the frontend or third-party clients. Endpoints are stateless and validate input using pydantic schemas.
- Services Layer: Encapsulates business logic; depends on repositories for persistence.
- Repositories: Single responsibility for DB access and queries (SQLAlchemy/ORM). Keep these mockable for tests.
- Agent (LangGraph + LLM): Coordinates conversational flows. The agent is configured to call internal tools to fetch user data (via service/repository functions) only when consented.
- Background Jobs: Long-running or asynchronous work (e.g., transaction ingestion, reports, analytics) should be queued to workers (Celery/RQ/Custom) and executed out-of-band.
- Persistence: PostgreSQL (primary), Redis (cache & sessions), optionally object storage for large artifacts.

Design principles
- Keep HTTP services stateless; store session/state in Redis when needed.
- Follow SOLID and single-responsibility: routers → services → repositories.
- Make services and repositories easily testable and injectable via dependency overrides.

Running locally
---------------
Prerequisites
- Python 3.11+
- PostgreSQL (local or via Docker)
- Redis (local or via Docker)
- Node.js (for frontend if running together)
- Recommended: poetry or pip + virtualenv

Steps
1. Create and activate a virtual environment
   - zsh example: python -m venv .venv && source .venv/bin/activate
2. Install dependencies
   - pip install -r requirements.txt
   or if using poetry: poetry install
3. Configure environment variables
   - Copy sample env file if present (e.g. .env.example -> .env)
   - Required values: DATABASE_URL (postgres), REDIS_URL, SECRET_KEY, etc.
4. Prepare the database
   - Run migrations: alembic upgrade head (or the provided migration script)
   - Optionally seed test/demo data: python -m app.seed_users (or provided script)
5. Run the app
   - uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
6. Access API docs
   - Open http://localhost:8000/docs or /redoc depending on implementation

Running with Docker (local)
---------------------------
A docker-compose.dev.yml is provided for local development. It typically includes PostgreSQL, Redis and the backend service.

1. Start using docker-compose
   - docker-compose -f docker-compose.dev.yml up --build
2. The first run should apply DB migrations; check logs for successful migration/seed messages.
3. Visit http://localhost:8000

Production image build
- docker build -t financialed-backend:latest -f backend/Dockerfile .
- Push to registry and deploy with your chosen orchestration

Running in Kubernetes (overview)
-------------------------------
The repo contains helper scripts and k8s manifests under k8s/.
General flow:
1. Build container & push to registry
2. Update k8s manifests (image tags, secrets)
3. Apply manifests (kubectl apply -f k8s/)
4. Ensure DB and Redis are provisioned (managed services recommended)

Recommended production setup
- Use managed Postgres (e.g., Azure Database for PostgreSQL, RDS) with read replicas
- Use managed Redis (Azure Cache/Elasticache)
- Use Horizontal Pod Autoscaler for the backend deployment
- Use Kubernetes Secrets / ExternalSecret for secret management

Testing
-------
- Unit tests: run pytest tests/unit
- Integration tests: pytest tests/integration (these may require a running DB/Redis or use test containers)
- Coverage: run run_all_tests.sh or run_coverage_report.py as provided

CI
- Add CI steps to run linting, unit tests, and integration tests (with test DB). Ensure migrations are validated.

Observability, logging and monitoring
------------------------------------
- Structured logging (JSON) with request IDs
- Integrate tracing (OpenTelemetry) to trace requests across services
- Metrics: expose Prometheus metrics and monitor response times, error rates
- Centralized logs: ship to ELK/Datadog/Logz

Scaling to 1M users — design & operational guidance
--------------------------------------------------
This section gives a pragmatic plan for scaling the backend to support ~1,000,000 monthly active users (MAU) or more. Exact needs depend on workload patterns (read-heavy vs write-heavy), concurrency, and per-user data.

Principles
- Make services stateless and horizontally scalable.
- Use caching and read replicas to offload read traffic.
- Employ async/background processing for heavy work.
- Adopt autoscaling with sensible thresholds and limits.

Data layer
- Primary DB: migrate to a managed Postgres with vertical scale; add read replicas for high read throughput.
- Connection pooling: use pgbouncer to limit DB connections from application pods.
- Partitioning / Sharding: for very large datasets, implement logical partitioning by user_id ranges or customer tenant.
- Indexing & query optimization: profile slow queries, add proper indexes, use materialized views for heavy aggregations.

Caching
- Short-lived responses: use Redis as a cache layer (application-level cache) and set TTLs.
- CDN: serve static assets and heavy read-only resources via CDN.

Asynchronous processing
- Offload ingestion, enrichment, heavy analytics to background workers (Celery/RQ) using a message broker (Redis or RabbitMQ).
- Design idempotent background tasks and retry policies.

API & compute
- Make API pods stateless. Increase pod replicas behind a load balancer.
- Use autoscaling (HPA) based on CPU / request latency / custom metrics (queue lengths, error rates).
- Use multi-availability-zone deployments for resilience.

Search & analytics
- For high-volume analytical workloads, use specialized stores (ClickHouse, BigQuery) or pre-aggregate data into OLAP stores.

Rate limiting and throttling
- Protect the backend using per-user and per-IP rate limiting. Implement graceful degradation for non-critical endpoints.

Security & privacy
- Encrypt data in transit (TLS) and at rest (managed DB encryption)
- Rotate secrets and limit access via least privilege IAM
- Pseudonymize or redact sensitive data in logs and traces
- Comply with applicable regulations (GDPR, CCPA) for user data handling

Operational runbook
- Prepare runbooks for common failures: DB replication lag, high error rates, cache failures, worker backlog
- Setup alerts for SLO breaches (latency, errors, traffic anomalies)

Cost control
- Use autoscaling and scheduled scaling for off-peak periods
- Prefer managed services (DB, Redis) for operational ease and negotiated SLAs

Security and privacy
--------------------
- Never log raw PII. Use hashed IDs where needed.
- Use parameterized queries / ORM to avoid SQL injection.
- Validate user inputs and rate-limit endpoints that accept bulk input.
- Require consent for fetching personal financial data in the conversational agent (already enforced in agent code).

Contribution guide
------------------
- Follow the repo coding standards: SOLID, clear separation of concerns, and OOP where applicable.
- Run tests locally before opening a PR. Ensure new code is covered by unit tests.
- Write small, focused PRs with descriptive titles and linked issue(s).
- Use the branch naming convention: feature/<short-desc>, fix/<issue-number>
- Include migration files for DB schema changes and a downgrade path where feasible.

Developer setup checklist
- Clone repo
- Create .env from .env.example
- Start local dependencies (Postgres, Redis) or use docker-compose.dev.yml
- Run migrations and seeders
- Start the app in reload mode for iterative development

Interview guide / talking points
-------------------------------
When explaining the backend in an interview or to a new contributor, cover:
- Overall architecture (API, services, repos, DB, cache, workers)
- Key design decisions: stateless services, dependency injection for testability, background worker separation
- Where LLM/agent integration lives and how it calls internal tools (consent-first pattern)
- How to add a new API endpoint: schema → router → service → repository → migration (if needed) → tests
- Scaling story: how to scale each tier (web, DB, cache, workers) and tradeoffs
- Security and privacy considerations, and how personal data is protected

Appendix
--------
- Useful scripts: run_all_tests.sh, run_coverage_report.py, quick_endpoint_test.sh
- Deployment helpers: docker-deploy.sh, k8s-deploy.sh, deploy-to-k8s-local.sh


Maintainers
- Primary: project maintainers (see CODEOWNERS or repository settings)


License
- See top-level LICENSE file (if present)


Contact
- For questions and contribution coordination, open an issue or contact the maintainers via repository channels.
