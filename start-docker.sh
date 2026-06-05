#!/bin/bash

# FinancialEdApp Docker Startup Script
# This script starts all services (Backend, Frontend, Databases, Redis)

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "================================"
echo "FinancialEdApp Docker Setup"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "📝 Creating .env file with default values..."
    cat > "$PROJECT_DIR/.env" << EOF
# Database Configuration
POSTGRES_USER=finedu_admin
POSTGRES_PASSWORD=finedu_admin_password

# Redis Configuration
REDIS_PASSWORD=finedu_redis_password

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production

# API Configuration
API_V1_PREFIX=/api/v1
ENVIRONMENT=development
EOF
    echo "✅ .env file created with default values"
    echo "   ⚠️  Please update the values for production use"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🚀 Starting services..."
echo ""

# Pull latest images
echo "📥 Pulling latest images..."
cd "$PROJECT_DIR"
docker-compose pull

# Build services
echo "🔨 Building services..."
docker-compose build

# Start services
echo "⬆️  Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
echo "================================"
docker-compose ps

echo ""
echo "================================"
echo "✅ All services started successfully!"
echo "================================"
echo ""
echo "📍 Access the application:"
echo "   🌐 Frontend:        http://localhost:3000"
echo "   🔗 Backend API:     http://localhost:8000"
echo "   🗄️  Auth Database:   localhost:55432"
echo "   🗄️  Data Database:   localhost:55433"
echo "   🔴 Redis Cache:     localhost:56379"
echo ""
echo "📚 Useful commands:"
echo "   View logs:         docker-compose logs -f [service-name]"
echo "   Stop services:     docker-compose down"
echo "   Stop + remove data: docker-compose down -v"
echo ""
echo "🎯 Next steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Create an account"
echo "   3. Add expenses and budgets"
echo "   4. Check the dashboard for real-time calculations"
echo ""
