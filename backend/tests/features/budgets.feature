Feature: Budget Management
  As an authenticated user
  I want to manage monthly budgets per category
  So that I can stay within my spending limits

  Background:
    Given the application is running
    And I am authenticated as a user

  Scenario: User can create a budget for a category
    When I create a budget for category "food" month "2026-02-01" with allocated amount 5000.00
    Then the response status should be 201
    And the response body should contain "allocated_amount"

  Scenario: Duplicate budget for same user/month/category is rejected
    Given I have a budget for category "food" in month "2026-02-01"
    When I create another budget for category "food" in month "2026-02-01"
    Then the response status should be 409

  Scenario: Budget with negative allocated amount is rejected
    When I create a budget for category "food" month "2026-02-01" with allocated amount -100.00
    Then the response status should be 422

  Scenario: User can list their budgets for a month
    Given I have 2 budgets for month "2026-02-01"
    When I request GET "/api/v1/budgets?month=2026-02-01"
    Then the response status should be 200
    And the response body should be a list with at least 2 items

  Scenario: Budget alert fires when spending reaches threshold
    Given I have a budget for category "food" in month "2026-02-01" with allocated amount 1000.00
    And the budget alert threshold is set to 80 percent
    When expenses in category "food" total 850.00 for the month
    Then a budget alert should exist with alert_level "warning"

  Scenario: User cannot see another user's budgets
    Given another user has a budget for the same month
    When I request the budget list
    Then the response should not include the other user's budget
