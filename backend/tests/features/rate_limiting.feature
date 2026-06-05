Feature: Rate Limiting and API Abuse Prevention
  As a platform operator
  I want API rate limiting enforced at every endpoint
  So that the service remains stable under abuse, bots, and DDoS attacks

  Background:
    Given the application is running

  # ---------------------------------------------------------------------------
  # Per-endpoint limits (verified via middleware headers)
  # ---------------------------------------------------------------------------

  Scenario: Rate limit headers are present on every authenticated API response
    Given I am authenticated as a user
    When I make a GET request to "/api/v1/health"
    Then the response should contain header "X-RateLimit-Limit"
    And the response should contain header "X-RateLimit-Remaining"
    And the response should contain header "X-RateLimit-Reset"

  Scenario: Unauthenticated requests have lower rate limits than authenticated ones
    Given I am not authenticated
    When I record the "X-RateLimit-Limit" header from a GET request to "/health"
    And I authenticate as a user
    And I record the "X-RateLimit-Limit" header from a GET request to "/api/v1/health"
    Then the authenticated limit should be greater than or equal to the unauthenticated limit

  # ---------------------------------------------------------------------------
  # Login endpoint — 5 req / 60 s per IP (unauthenticated)
  # ---------------------------------------------------------------------------

  Scenario Outline: Login endpoint blocks requests beyond the configured limit
    Given the login rate limit is set to <limit> per <window> seconds
    When I send <count> POST requests to "/api/v1/auth/login" with invalid credentials
    Then at least one response should have status 429
    And the 429 response body should contain error code "SRV_003"
    And the 429 response headers should contain "Retry-After"

    Examples:
      | limit | window | count |
      | 5     | 60     | 6     |

  # ---------------------------------------------------------------------------
  # Register endpoint — 3 req / 60 s per IP
  # ---------------------------------------------------------------------------

  Scenario: Register endpoint blocks requests beyond the configured limit
    Given the register rate limit is set to 3 per 60 seconds
    When I send 4 POST requests to "/api/v1/auth/register" with different emails
    Then at least one response should have status 429

  # ---------------------------------------------------------------------------
  # Forgot-password endpoint — 3 req / 3600 s per IP (prevent enumeration)
  # ---------------------------------------------------------------------------

  Scenario: Forgot-password endpoint has hourly rate limiting
    Given the forgot-password rate limit is set to 3 per 3600 seconds
    When I send 4 POST requests to "/api/v1/auth/forgot-password" with an email
    Then at least one response should have status 429

  # ---------------------------------------------------------------------------
  # Sliding window — requests at window boundary
  # ---------------------------------------------------------------------------

  Scenario: Rate limit counter resets after the window expires
    Given the rate limiter uses a sliding window algorithm
    And the current window has expired
    When I send a request that was previously rate-limited
    Then the response status should be 200

  # ---------------------------------------------------------------------------
  # Fail-open behaviour — Redis unavailable
  # ---------------------------------------------------------------------------

  Scenario: When Redis is unavailable, API requests still succeed (fail-open)
    Given the Redis connection is simulated as unavailable
    When I make a GET request to "/health"
    Then the response status should be 200

  # ---------------------------------------------------------------------------
  # X-Forwarded-For spoofing prevention
  # ---------------------------------------------------------------------------

  Scenario: Spoofed X-Forwarded-For header uses only the first IP for rate limiting
    Given two clients share a spoofed X-Forwarded-For header "1.2.3.4, 5.6.7.8"
    When both clients send requests
    Then the rate-limit key is derived from "1.2.3.4" only

  # ---------------------------------------------------------------------------
  # Account lockout after consecutive failed logins
  # ---------------------------------------------------------------------------

  Scenario: Account lockout fires after 5 consecutive failed logins
    Given the lockout threshold is 5 failures within 900 seconds
    When I submit 5 consecutive failed login attempts for "victim@example.com"
    Then the 6th login attempt should return status 429
    And the response should indicate the account is temporarily locked
