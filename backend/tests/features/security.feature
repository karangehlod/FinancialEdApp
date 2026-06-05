Feature: Security Hardening
  As a platform security officer
  I want all API endpoints to be hardened against common attacks
  So that user financial data is protected

  Background:
    Given the application is running

  # ---------------------------------------------------------------------------
  # Security Headers
  # ---------------------------------------------------------------------------

  Scenario Outline: Security headers are present on all responses
    When I make a GET request to "<path>"
    Then the response should contain header "<header>" with value "<value>"

    Examples:
      | path    | header                  | value          |
      | /health | X-Content-Type-Options  | nosniff        |
      | /health | X-Frame-Options         | DENY           |
      | /health | X-XSS-Protection        | 1; mode=block  |
      | /health | Referrer-Policy         | strict-origin-when-cross-origin |

  # ---------------------------------------------------------------------------
  # Input Validation / SQL Injection Prevention
  # ---------------------------------------------------------------------------

  Scenario: SQL injection in email field is rejected
    When I submit a login request with email "' OR '1'='1" and password "anything"
    Then the response status should be 422

  Scenario: XSS payload in description field is sanitised
    Given I am authenticated as a user
    When I create an expense with description "<script>alert('xss')</script>" in category "food"
    Then the response status should be 201 or 422
    And if accepted, the stored description should not contain "<script>"

  Scenario: Oversized payload is rejected
    When I send a POST request to "/api/v1/auth/login" with a body larger than 1MB
    Then the response status should be 413 or 422

  # ---------------------------------------------------------------------------
  # Authentication & Authorisation
  # ---------------------------------------------------------------------------

  Scenario: Unauthenticated access to protected endpoint is rejected
    When I make a GET request to "/api/v1/expenses" without an Authorization header
    Then the response status should be 401

  Scenario: Expired access token is rejected
    Given I have an expired JWT access token
    When I make a GET request to "/api/v1/expenses" with the expired token
    Then the response status should be 401

  Scenario: Tampered JWT token is rejected
    Given I have a tampered JWT access token
    When I make a GET request to "/api/v1/expenses" with the tampered token
    Then the response status should be 401

  Scenario: Token without required claims is rejected
    Given I have a JWT without the "sub" claim
    When I make a GET request to "/api/v1/expenses" with the malformed token
    Then the response status should be 401

  # ---------------------------------------------------------------------------
  # Sensitive Data Exposure
  # ---------------------------------------------------------------------------

  Scenario: Password hash is never returned in any API response
    Given a verified user exists with email "secure@example.com" and password "Pass123!"
    When I log in with email "secure@example.com" and password "Pass123!"
    Then the response body should not contain "password_hash"
    And the response body should not contain "bcrypt"

  Scenario: TOTP secret is never returned in any API response
    Given I am authenticated as a user
    When I call any user profile endpoint
    Then the response body should not contain "totp_secret"

  # ---------------------------------------------------------------------------
  # CORS
  # ---------------------------------------------------------------------------

  Scenario: Request from disallowed origin is rejected
    When I make a GET request to "/health" with Origin header "https://malicious.example.com"
    Then the response should not contain header "Access-Control-Allow-Origin" with value "https://malicious.example.com"

  Scenario: Request from allowed origin receives CORS headers
    When I make an OPTIONS request to "/api/v1/auth/login" with Origin "http://localhost:3000"
    Then the response should contain header "Access-Control-Allow-Origin"

  # ---------------------------------------------------------------------------
  # Refresh Token Security
  # ---------------------------------------------------------------------------

  Scenario: Refresh token reuse is detected and all sessions revoked
    Given a user is logged in with a refresh token
    When the refresh token is used for the first time to get a new access token
    And the original refresh token is used again
    Then the second use should return status 401
    And all sessions for the user should be revoked

  Scenario: Logout invalidates the refresh token
    Given a user is logged in with a refresh token
    When the user logs out
    And the refresh token is used to attempt a refresh
    Then the response status should be 401
