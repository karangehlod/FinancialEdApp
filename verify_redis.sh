#!/bin/bash
# Redis Implementation Verification Script
# Verifies that Redis is properly configured and integrated in the backend

echo "🔍 Redis Implementation Verification"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Redis Docker Image
echo "1️⃣  Checking Docker Redis Service..."
if docker ps | grep -q redis; then
    echo -e "${GREEN}✅ Redis container is running${NC}"
else
    echo -e "${YELLOW}⚠️  Redis container not running${NC}"
    echo "   Run: docker-compose up -d"
fi
echo ""

# Check 2: Redis Client Libraries
echo "2️⃣  Checking Redis Python Libraries..."
if grep -q "redis==" backend/requirements.txt; then
    echo -e "${GREEN}✅ redis library in requirements.txt${NC}"
    VERSION=$(grep "redis==" backend/requirements.txt)
    echo "   $VERSION"
else
    echo -e "${RED}❌ redis library not found in requirements.txt${NC}"
fi

if grep -q "aioredis==" backend/requirements.txt; then
    echo -e "${GREEN}✅ aioredis library in requirements.txt${NC}"
    VERSION=$(grep "aioredis==" backend/requirements.txt)
    echo "   $VERSION"
else
    echo -e "${YELLOW}⚠️  aioredis should be available via redis package${NC}"
fi
echo ""

# Check 3: RedisCache Implementation
echo "3️⃣  Checking RedisCache Implementation..."
if grep -q "class RedisCache(CacheProvider):" backend/app/core/provider_implementations.py; then
    echo -e "${GREEN}✅ RedisCache class found${NC}"
    
    if grep -q "self.redis = redis_client" backend/app/core/provider_implementations.py; then
        echo -e "${GREEN}✅ Using real Redis client (not in-memory dict)${NC}"
    else
        echo -e "${RED}❌ Still using in-memory dictionary${NC}"
    fi
    
    if grep -q "await self.redis.setex" backend/app/core/provider_implementations.py; then
        echo -e "${GREEN}✅ TTL/expiration support implemented${NC}"
    else
        echo -e "${RED}❌ TTL support missing${NC}"
    fi
else
    echo -e "${RED}❌ RedisCache class not found${NC}"
fi
echo ""

# Check 4: Redis Configuration
echo "4️⃣  Checking Redis Configuration..."
if grep -q "REDIS_URL" backend/.env; then
    echo -e "${GREEN}✅ REDIS_URL in backend/.env${NC}"
    REDIS_URL=$(grep "REDIS_URL" backend/.env | cut -d'=' -f2)
    echo "   REDIS_URL=$REDIS_URL"
else
    echo -e "${RED}❌ REDIS_URL not found in backend/.env${NC}"
fi

if grep -q "REDIS_URL" backend/.env.example; then
    echo -e "${GREEN}✅ REDIS_URL in backend/.env.example${NC}"
else
    echo -e "${YELLOW}⚠️  REDIS_URL not in backend/.env.example${NC}"
fi

if grep -q "REDIS_URL" .env.docker; then
    echo -e "${GREEN}✅ REDIS_URL in .env.docker${NC}"
else
    echo -e "${RED}❌ REDIS_URL not in .env.docker${NC}"
fi
echo ""

# Check 5: Startup Integration
echo "5️⃣  Checking Redis Initialization in Startup..."
if grep -q "redis_cache = RedisCache(redis_client)" backend/app/main.py; then
    echo -e "${GREEN}✅ RedisCache initialized in main.py startup${NC}"
else
    echo -e "${RED}❌ RedisCache initialization not found in main.py${NC}"
fi

if grep -q "await set_redis_cache(redis_cache)" backend/app/main.py; then
    echo -e "${GREEN}✅ Redis cache set globally on startup${NC}"
else
    echo -e "${RED}❌ Global redis cache setup missing${NC}"
fi
echo ""

# Check 6: Dependency Injection
echo "6️⃣  Checking Dependency Injection Setup..."
if grep -q "def get_redis_cache()" backend/app/dependencies.py; then
    echo -e "${GREEN}✅ get_redis_cache() dependency function found${NC}"
else
    echo -e "${RED}❌ get_redis_cache() dependency not found${NC}"
fi

if grep -q "async def set_redis_cache" backend/app/dependencies.py; then
    echo -e "${GREEN}✅ set_redis_cache() function found${NC}"
else
    echo -e "${RED}❌ set_redis_cache() function not found${NC}"
fi
echo ""

# Check 7: Auth Service Integration
echo "7️⃣  Checking Auth Service Redis Integration..."
if grep -q "async def cache_refresh_token" backend/app/services/auth_service.py; then
    echo -e "${GREEN}✅ cache_refresh_token() method implemented${NC}"
else
    echo -e "${RED}❌ cache_refresh_token() not found${NC}"
fi

if grep -q "async def is_user_blacklisted" backend/app/services/auth_service.py; then
    echo -e "${GREEN}✅ is_user_blacklisted() method implemented${NC}"
else
    echo -e "${RED}❌ is_user_blacklisted() not found${NC}"
fi

if grep -q "cache: Optional\[CacheProvider\]" backend/app/services/auth_service.py; then
    echo -e "${GREEN}✅ Cache parameter in AuthService __init__${NC}"
else
    echo -e "${RED}❌ Cache parameter not added to AuthService${NC}"
fi
echo ""

# Check 8: Docker Compose Redis Service
echo "8️⃣  Checking Docker Compose Configuration..."
if grep -q "redis:" docker-compose.yml; then
    echo -e "${GREEN}✅ Redis service in docker-compose.yml${NC}"
    
    if grep -q "image: redis:7" docker-compose.yml; then
        echo -e "${GREEN}✅ Using Redis 7${NC}"
    fi
    
    if grep -q "healthcheck:" docker-compose.yml; then
        echo -e "${GREEN}✅ Health check configured${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Redis service not found in docker-compose.yml${NC}"
fi
echo ""

# Check 9: Documentation
echo "9️⃣  Checking Documentation..."
if [ -f "REDIS_IMPLEMENTATION_COMPLETE.md" ]; then
    echo -e "${GREEN}✅ REDIS_IMPLEMENTATION_COMPLETE.md found${NC}"
else
    echo -e "${YELLOW}⚠️  REDIS_IMPLEMENTATION_COMPLETE.md not found${NC}"
fi

if [ -f "REDIS_USAGE_ANALYSIS.md" ]; then
    echo -e "${GREEN}✅ REDIS_USAGE_ANALYSIS.md found${NC}"
else
    echo -e "${YELLOW}⚠️  REDIS_USAGE_ANALYSIS.md not found${NC}"
fi
echo ""

# Summary
echo "===================================="
echo "✅ Redis Implementation Verification Complete"
echo ""
echo "📚 Documentation:"
echo "   - Read: REDIS_IMPLEMENTATION_COMPLETE.md"
echo "   - Read: REDIS_USAGE_ANALYSIS.md"
echo ""
echo "🚀 To test Redis:"
echo "   1. Start services: docker-compose up -d"
echo "   2. Start backend: cd backend && python -m uvicorn app.main:app --reload"
echo "   3. Check Redis CLI: docker exec -it redis_cache redis-cli -a finedu_redis_password"
echo ""
