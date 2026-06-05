Feature: Expense Management
  As an authenticated user
  I want to manage my expenses
  So that I can track my spending and stay within my budget

  Background:
    Given the application is running
    And I am authenticated as a user

  # ---------------------------------------------------------------------------
  # Create Expense
  # ---------------------------------------------------------------------------

  Scenario: User can create a valid expense
    When I create an expense with the following details:
      | amount  | category | date       | description   |
      | 500.00  | food     | 2026-02-01 | Grocery shop  |
    Then the response status should be 201
    And the response body should contain "id"
    And the response body should contain "amount"
    And the response body should contain "500"

  Scenario: Expense with negative amount is rejected
    When I create an expense with amount -100.00 in category "food" on date "2026-02-01"
    Then the response status should be 422

  Scenario: Expense with zero amount is rejected
    When I create an expense with amount 0 in category "food" on date "2026-02-01"
    Then the response status should be 422

  Scenario: Expense with missing required fields is rejected
    When I create an expense with missing "category" field
    Then the response status should be 422

  # ---------------------------------------------------------------------------
  # Read Expenses
  # ---------------------------------------------------------------------------

  Scenario: User can retrieve their expense list
    Given I have created 3 expenses
    When I request GET "/api/v1/expenses"
    Then the response status should be 200
    And the response body should be a list with at least 3 items

  Scenario: User cannot see another user's expenses
    Given another user "other@example.com" has an expense
    When I request GET "/api/v1/expenses"
    Then the response should not contain the other user's expense

  # ---------------------------------------------------------------------------
  # Update Expense
  # ---------------------------------------------------------------------------

  Scenario: User can update their own expense
    Given I have created an expense
    When I update the expense with amount 750.00
    Then the response status should be 200
    And the response body should contain "750"

  Scenario: User cannot update another user's expense
    Given another user's expense exists with a known ID
    When I attempt to update that expense with amount 999.00
    Then the response status should be 403 or 404

  # ---------------------------------------------------------------------------
  # Delete Expense
  # ---------------------------------------------------------------------------

  Scenario: User can delete their own expense (soft delete)
    Given I have created an expense
    When I delete the expense
    Then the response status should be 200 or 204
    And the expense should no longer appear in the expense list

  # ---------------------------------------------------------------------------
  # Cache Invalidation
  # ---------------------------------------------------------------------------

  Scenario: Cache is invalidated after expense creation
    Given the expense list is cached
    When I create a new expense
    And I request the expense list again
    Then the response should include the newly created expense

  Scenario: Cache is invalidated after expense deletion
    Given I have created an expense and it appears in the cached list
    When I delete the expense
    And I request the expense list again
    Then the deleted expense should not appear in the response
