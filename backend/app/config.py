"""
Application settings — every runtime-tunable value is read from environment
variables so the application can be reconfigured without rebuilding the image.

Categories:
  - Application
  - CORS
  - JWT / Security
  - Auth Database (users, tokens)
  - Data Database (financial records)
  - Redis (pool, timeouts, TTLs)
  - Connection pool sizing
  - Rate limiting rules (all tunable without redeploy)
  - Email / SMTP
  - Notifications
  - Observability
  - OAuth / Social Login
  - GDPR / Compliance
  - Feature flags

All settings with a default value are optional; those without are required
and will raise a validation error at startup if missing.
"""

from typing import List
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # =========================================================================
    # Application
    # =========================================================================
    APP_NAME: str = "FinancialEdApp"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"       # "development" | "staging" | "production"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"               # DEBUG | INFO | WARNING | ERROR | CRITICAL

    # =========================================================================
    # CORS
    # =========================================================================
    # Comma-separated list e.g. "http://localhost:3000,https://app.example.com"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # =========================================================================
    # JWT / Security
    # =========================================================================
    JWT_SECRET_KEY: str                   # Required — no default (must be set in env)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Fernet key for encrypting TOTP secrets + OAuth tokens.
    # Derived from JWT_SECRET_KEY if not set (for convenience in dev).
    ENCRYPTION_KEY: str = ""

    # =========================================================================
    # Auth Database  (users, oauth_accounts, refresh_tokens)
    # =========================================================================
    AUTH_DB_HOST: str
    AUTH_DB_PORT: int = 5432
    AUTH_DB_NAME: str
    AUTH_DB_USER: str
    AUTH_DB_PASSWORD: str

    # =========================================================================
    # Data Database  (expenses, budgets, goals, loans, notifications …)
    # =========================================================================
    DATA_DB_HOST: str
    DATA_DB_PORT: int = 5432
    DATA_DB_NAME: str
    DATA_DB_USER: str
    DATA_DB_PASSWORD: str

    # =========================================================================
    # Database Connection Pool  (tunable without image rebuild)
    # =========================================================================
    # Number of persistent connections per worker process
    DB_POOL_SIZE: int = 20
    # Burst connections on top of pool_size
    DB_MAX_OVERFLOW: int = 40
    # Seconds to wait for a free connection before raising PoolTimeout
    DB_POOL_TIMEOUT: int = 30
    # Recycle connections after N seconds (prevents stale TCP links)
    DB_POOL_RECYCLE: int = 1800
    # Validate connection before checkout (handles DB restarts gracefully)
    DB_POOL_PRE_PING: bool = True
    # Set to true when using PgBouncer in transaction mode
    PGBOUNCER_MODE: bool = False

    # =========================================================================
    # Redis
    # =========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"

    # Connection pool
    REDIS_MAX_CONNECTIONS: int = 50
    # Seconds to wait for a new connection
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    # Seconds between keepalive probes
    REDIS_SOCKET_KEEPALIVE: bool = True
    # Retry on timeout (transient network errors)
    REDIS_RETRY_ON_TIMEOUT: bool = True

    # Cache TTLs (seconds) — all tunable per environment
    CACHE_TTL_USER_PROFILE: int = 300        # 5 min
    CACHE_TTL_EXPENSES: int = 300            # 5 min
    CACHE_TTL_BUDGETS: int = 300             # 5 min
    CACHE_TTL_GOALS: int = 300              # 5 min
    CACHE_TTL_ACCESS_TOKEN: int = 1800       # 30 min (match JWT expiry)
    CACHE_TTL_EXCHANGE_RATES: int = 3600     # 1 hour

    # =========================================================================
    # Rate Limiting  (all tunable — no redeploy needed)
    # Limits are "requests per WINDOW seconds"
    # =========================================================================
    # Auth endpoints — tight to prevent brute-force / enumeration
    RATE_LIMIT_LOGIN_LIMIT: int = 5
    RATE_LIMIT_LOGIN_WINDOW: int = 60        # 5 req / 60 s

    RATE_LIMIT_REGISTER_LIMIT: int = 3
    RATE_LIMIT_REGISTER_WINDOW: int = 60     # 3 req / 60 s

    RATE_LIMIT_FORGOT_PASSWORD_LIMIT: int = 3
    RATE_LIMIT_FORGOT_PASSWORD_WINDOW: int = 3600   # 3 req / hour

    RATE_LIMIT_REFRESH_LIMIT: int = 10
    RATE_LIMIT_REFRESH_WINDOW: int = 60      # 10 req / 60 s

    RATE_LIMIT_OAUTH_LIMIT: int = 10
    RATE_LIMIT_OAUTH_WINDOW: int = 60        # 10 req / 60 s

    # Expensive endpoints
    RATE_LIMIT_EXPORTS_LIMIT: int = 10
    RATE_LIMIT_EXPORTS_WINDOW: int = 60

    RATE_LIMIT_ANALYTICS_LIMIT: int = 30
    RATE_LIMIT_ANALYTICS_WINDOW: int = 60

    # Default limits for authenticated / unauthenticated traffic
    RATE_LIMIT_DEFAULT_AUTH_LIMIT: int = 300
    RATE_LIMIT_DEFAULT_AUTH_WINDOW: int = 60

    RATE_LIMIT_DEFAULT_UNAUTH_LIMIT: int = 60
    RATE_LIMIT_DEFAULT_UNAUTH_WINDOW: int = 60

    # Account lockout after N consecutive failed logins (reset on success)
    RATE_LIMIT_LOCKOUT_MAX_FAILURES: int = 5
    RATE_LIMIT_LOCKOUT_WINDOW: int = 900     # 15 min sliding window

    # =========================================================================
    # Email / SMTP
    # =========================================================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@financialedu.com"
    SMTP_FROM_NAME: str = "Financial Education App"
    EMAIL_ENABLED: bool = False
    FRONTEND_URL: str = "http://localhost:5173"

    # =========================================================================
    # Notifications
    # =========================================================================
    NOTIFICATION_RETENTION_DAYS: int = 30
    SEND_BUDGET_ALERTS: bool = True
    SEND_LOAN_REMINDERS: bool = True
    SEND_GOAL_NOTIFICATIONS: bool = True
    BUDGET_ALERT_THRESHOLD: float = 80.0     # % of budget at which alert fires

    # =========================================================================
    # Observability / Metrics
    # =========================================================================
    METRICS_USERNAME: str = ""              # Optional HTTP Basic auth on /metrics
    METRICS_PASSWORD: str = ""
    OTEL_EXPORTER_ENDPOINT: str = ""        # e.g. "http://otel-collector:4317"

    # =========================================================================
    # OAuth / Social Login (P2-6)
    # =========================================================================
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_PRIVATE_KEY: str = ""

    # =========================================================================
    # Multi-Currency (P2-7)
    # =========================================================================
    OPEN_EXCHANGE_RATES_API_KEY: str = ""   # https://openexchangerates.org
    BASE_CURRENCY: str = "USD"

    # =========================================================================
    # GDPR / Compliance (P2-5)
    # =========================================================================
    # Inactive accounts auto-deleted after N days (0 = disabled)
    GDPR_ACCOUNT_RETENTION_DAYS: int = 730  # 2 years
    GDPR_DATA_EXPORT_TTL: int = 86400       # Export file available for 24 h

    # =========================================================================
    # AI / Chat — Azure OpenAI + LangChain
    # =========================================================================
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""          # e.g. "https://my-resource.openai.azure.com/"
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"  # Azure deployment name
    AZURE_OPENAI_MODEL: str = "gpt-4o"       # Fallback model name for direct OpenAI
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    OPENAI_API_KEY: str = ""                 # Fallback to direct OpenAI if Azure not set
    CHAT_TEMPERATURE: float = 0.4
    CHAT_MAX_TOKENS: int = 1024
    CHAT_MAX_HISTORY: int = 20               # Max turns per conversation

    # =========================================================================
    # Feature Flags
    # =========================================================================
    FEATURE_2FA_ENABLED: bool = True
    FEATURE_OAUTH_ENABLED: bool = True
    FEATURE_WEBSOCKET_ENABLED: bool = True
    FEATURE_GDPR_ENABLED: bool = True
    FEATURE_ADMIN_ENABLED: bool = True
    FEATURE_CURRENCY_CONVERSION_ENABLED: bool = True
    FEATURE_CHAT_ENABLED: bool = True

    # =========================================================================
    # Admin
    # =========================================================================
    ADMIN_EMAILS: str = ""                   # Comma-separated admin emails for bootstrapping

    # =========================================================================
    # Computed properties (derived — not read from env)
    # =========================================================================

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return upper

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @computed_field
    @property
    def PROJECT_NAME(self) -> str:
        return self.APP_NAME

    @computed_field
    @property
    def VERSION(self) -> str:
        return self.APP_VERSION

    @computed_field
    @property
    def API_V1_STR(self) -> str:
        return self.API_V1_PREFIX

    @computed_field
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @computed_field
    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET_KEY

    @computed_field
    @property
    def ALGORITHM(self) -> str:
        return self.JWT_ALGORITHM

    @computed_field
    @property
    def AUTH_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.AUTH_DB_USER}:{self.AUTH_DB_PASSWORD}"
            f"@{self.AUTH_DB_HOST}:{self.AUTH_DB_PORT}/{self.AUTH_DB_NAME}"
        )

    @computed_field
    @property
    def DATA_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DATA_DB_USER}:{self.DATA_DB_PASSWORD}"
            f"@{self.DATA_DB_HOST}:{self.DATA_DB_PORT}/{self.DATA_DB_NAME}"
        )

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Legacy alias — points to auth DB."""
        return self.AUTH_DATABASE_URL

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()
