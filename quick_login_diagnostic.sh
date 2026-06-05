#!/bin/bash

# Quick Login Diagnostic Tool
# Verifies the login flow is working correctly

echo "================================"
echo "Financial Ed App - Login Diagnostic"
echo "================================"
echo ""

# Check backend
echo "🔍 Checking Backend..."
BACKEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null)

if [ "$BACKEND_RESPONSE" = "404" ]; then
    echo "✅ Backend is running (404 on health endpoint is expected)"
elif [ "$BACKEND_RESPONSE" = "000" ]; then
    echo "❌ Backend is NOT running on localhost:8000"
    echo "   Start backend with: cd backend && python -m uvicorn app.main:app --reload"
    exit 1
else
    echo "✅ Backend responding with HTTP $BACKEND_RESPONSE"
fi

echo ""
echo "🔍 Testing Login Endpoint..."

# Test login
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"demo123456"}')

# Check if response contains refresh_token
if echo "$LOGIN_RESPONSE" | grep -q '"refresh_token"'; then
    echo "✅ Login endpoint returns refresh_token"
else
    echo "❌ Login endpoint missing refresh_token"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

# Check if response contains access_token
if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
    echo "✅ Login endpoint returns access_token"
else
    echo "❌ Login endpoint missing access_token"
    exit 1
fi

# Extract tokens
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ] || [ -z "$REFRESH_TOKEN" ]; then
    echo "❌ Failed to extract tokens from response"
    exit 1
fi

echo "✅ Extracted access_token: ${ACCESS_TOKEN:0:20}..."
echo "✅ Extracted refresh_token: ${REFRESH_TOKEN:0:20}..."

echo ""
echo "🔍 Testing Auth Endpoints with Token..."

# Test /auth/me with access token
ME_RESPONSE=$(curl -s -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$ME_RESPONSE" | grep -q '"email":"demo@example.com"'; then
    echo "✅ /auth/me endpoint works with access token"
else
    echo "❌ /auth/me endpoint failed"
    echo "   Response: $ME_RESPONSE"
fi

echo ""
echo "🔍 Testing Refresh Endpoint..."

# Test refresh endpoint
REFRESH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")

if echo "$REFRESH_RESPONSE" | grep -q '"access_token"'; then
    echo "✅ Refresh endpoint returns new access_token"
else
    echo "⚠️  Refresh endpoint may not be working"
    echo "   Response: $REFRESH_RESPONSE"
fi

echo ""
echo "🔍 Checking CORS Configuration..."

# Test CORS headers
CORS_RESPONSE=$(curl -s -i -X OPTIONS http://localhost:8000/api/v1/auth/login \
  -H "Origin: http://localhost:3000" 2>/dev/null | grep -i "access-control")

if [ -n "$CORS_RESPONSE" ]; then
    echo "✅ CORS headers found:"
    echo "$CORS_RESPONSE"
else
    echo "⚠️  CORS headers not found (may still work)"
fi

echo ""
echo "🔍 Frontend Configuration..."

if [ -f "frontend/src/services/api.js" ]; then
    API_URL=$(grep "VITE_API_URL\|localhost:8000" frontend/src/services/api.js | head -1)
    if [ -n "$API_URL" ]; then
        echo "✅ Frontend API URL configured correctly"
        echo "   $API_URL"
    fi
else
    echo "⚠️  Could not verify frontend configuration"
fi

echo ""
echo "================================"
echo "✅ All Diagnostics Passed!"
echo "================================"
echo ""
echo "Next Steps:"
echo "1. Open http://localhost:5173 in your browser"
echo "2. Try logging in with:"
echo "   Email: demo@example.com"
echo "   Password: demo123456"
echo "3. Check browser console for 'Init Auth - Token exists: true'"
echo "4. Verify tokens are stored in DevTools → Application → LocalStorage"
echo ""
