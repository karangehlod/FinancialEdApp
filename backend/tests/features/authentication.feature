Feature: User Authentication
  As a user of FinancialEdApp
  I want to register, log in, and manage my session securely
  So that my financial data is protected

  Background:
    Given the application is running
    And the rate limiter is configured with generous limits for testing

  # ---------------------------------------------------------------------------
  # Registration
  # ---------------------------------------------------------------------------

  Scenario: Successful user registration
    Given I have valid registration credentials
      | email              | password        |
      | alice@example.com  | SecurePass123!  |
    When I submit a registration request
    Then the response status should be 201
    And the response body should contain "access_token"
    And the response body should contain "token_type"

  Scenario: Registration with duplicate email is rejected
    Given a user already exists with email "bob@example.com"
    When I submit a registration request with email "bob@example.com" and password "AnotherPass456!"
    Then the response status should be 409
    And the response body should contain "already exists"

  Scenario: Registration with weak password is rejected
    When I submit a registration request with email "charlie@example.com" and password "weak"
    Then the response status should be 422

  Scenario: Registration with invalid email format is rejected
    When I submit a registration request with email "not-an-email" and password "SecurePass123!"
    Then the response status should be 422

  # ---------------------------------------------------------------------------
  # Login
  # ---------------------------------------------------------------------------

  Scenario: Successful login returns tokens
    Given a verified user exists with email "dave@example.com" and password "SecurePass123!"
    When I log in with email "dave@example.com" and password "SecurePass123!"
    Then the response status should be 200
    And the response body should contain "access_token"
    And the response body should contain "refresh_token"
    And the response body should contain "token_type"

  Scenario: Login with wrong password is rejected
    Given a verified user exists with email "eve@example.com" and password "CorrectPass123!"
    When I log in with email "eve@example.com" and password "WrongPassword!"
    Then the response status should be 401
    And the response body should contain "Invalid credentials"

  Scenario: Login with non-existent email is rejected
    When I log in with email "nobody@example.com" and password "AnyPassword123!"
    Then the response status should be 401

  # ---------------------------------------------------------------------------
  # Token Refresh
  # ---------------------------------------------------------------------------

  Scenario: Valid refresh token returns new access token
    Given a verified user exists with email "frank@example.com" and password "SecurePass123!"
    And the user is logged in
    When I submit a token refresh request with the refresh token
    Then the response status should be 200
    And the response body should contain "access_token"

  Scenario: Expired or invalid refresh token is rejected
    When I submit a token refresh request with token "invalid.refresh.token"
    Then the response status should be 401

  # ---------------------------------------------------------------------------
  # Rate Limiting on Auth Endpoints
  # ---------------------------------------------------------------------------

  Scenario: Brute-force login attempts are rate limited
    Given the rate limiter is configured with limit 3 per 60 seconds for login
    When I attempt to log in 4 times with incorrect credentials for "target@example.com"
    Then at least one response status should be 429
    And the response should contain "Retry-After" header

  Scenario: Registration spam is rate limited
    Given the rate limiter is configured with limit 3 per 60 seconds for register
    When I submit 4 registration requests in rapid succession
    Then at least one response status should be 429

  # ---------------------------------------------------------------------------
  # Security Headers
  # ---------------------------------------------------------------------------

  Scenario: All responses include security headers
    When I make a GET request to "/health"
    Then the response should contain header "X-Content-Type-Options" with value "nosniff"
    And the response should contain header "X-Frame-Options" with value "DENY"
    And the response should contain header "X-XSS-Protection"
