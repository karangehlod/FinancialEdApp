#!/bin/bash

echo "=== Testing Auth Database ==="
docker exec -it finedu_postgres psql -U finedu_admin -d finedu_auth_db -c "
SELECT 
    email, 
    is_active, 
    is_verified, 
    created_at 
FROM users 
ORDER BY created_at;
"

echo ""
echo "=== Testing Data Database ==="
docker exec -it finedu_postgres psql -U finedu_admin -d finedu_data_db -c "
SELECT 
    'User Profiles' as table_name, 
    COUNT(*) as count 
FROM user_profiles
UNION ALL
SELECT 'Expenses', COUNT(*) FROM expenses
UNION ALL
SELECT 'Loans', COUNT(*) FROM loans
UNION ALL
SELECT 'Budgets', COUNT(*) FROM budgets
UNION ALL
SELECT 'Financial Concepts', COUNT(*) FROM financial_concepts;
"

echo ""
echo "=== Alice's Recent Expenses ==="
docker exec -it finedu_postgres psql -U finedu_admin -d finedu_data_db -c "
SELECT 
    date,
    category,
    amount,
    merchant
FROM expenses
WHERE user_id = '11111111-1111-1111-1111-111111111111'
ORDER BY date DESC
LIMIT 5;
"
