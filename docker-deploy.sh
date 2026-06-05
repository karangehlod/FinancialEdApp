#!/bin/bash

################################################################################
# FinancialEdApp - Docker Deployment Script
# 
# Usage: ./docker-deploy.sh [OPTIONS]
# 
# OPTIONS:
#   -b, --build          Build Docker image
#   -u, --up             Start containers (docker-compose up)
#   -d, --down           Stop containers (docker-compose down)
#   -l, --logs           Show container logs
#   -p, --pull           Pull latest images
#   -c, --clean          Clean up containers and volumes
#   -t, --test           Run tests in container
#   -m, --migrate        Run database migrations
#   --build-only         Only build, don't start
#   --registry URL       Push to registry (requires -b)
#
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="financialedapp"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.docker"
BUILD_ONLY=false
REGISTRY=""

# Helper functions
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check prerequisites
check_requirements() {
    print_header "Checking Requirements"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    print_success "Docker Compose is installed"
    
    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env.docker file not found. Please create it first."
    fi
    print_success ".env.docker file found"
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"
    
    cd backend
    
    if [ -n "$REGISTRY" ]; then
        IMAGE_TAG="$REGISTRY/$PROJECT_NAME-backend:latest"
        print_info "Building for registry: $REGISTRY"
    else
        IMAGE_TAG="$PROJECT_NAME-backend:latest"
    fi
    
    docker build -t "$IMAGE_TAG" .
    print_success "Docker image built: $IMAGE_TAG"
    
    if [ -n "$REGISTRY" ]; then
        docker push "$IMAGE_TAG"
        print_success "Docker image pushed to registry"
    fi
    
    cd ..
}

# Start containers
start_containers() {
    print_header "Starting Containers"
    
    if [ "$BUILD_ONLY" = true ]; then
        print_info "Build only mode - skipping container startup"
        return
    fi
    
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  up -d
    
    print_success "Containers started"
    
    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 10
    
    # Check health
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
        print_success "Services are healthy"
    else
        print_info "Services are starting. Check status with: ./docker-deploy.sh --logs"
    fi
}

# Stop containers
stop_containers() {
    print_header "Stopping Containers"
    
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  down
    
    print_success "Containers stopped"
}

# Show logs
show_logs() {
    print_header "Container Logs"
    
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  logs -f
}

# Pull latest images
pull_images() {
    print_header "Pulling Latest Images"
    
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  pull
    
    print_success "Images pulled"
}

# Clean up
cleanup() {
    print_header "Cleaning Up"
    
    read -p "Are you sure you want to delete containers and volumes? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" \
                      --env-file "$ENV_FILE" \
                      -p "$PROJECT_NAME" \
                      down -v
        
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Run tests
run_tests() {
    print_header "Running Tests"
    
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  exec backend pytest tests/ -v
    
    print_success "Tests completed"
}

# Run migrations
run_migrations() {
    print_header "Running Database Migrations"
    
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  exec backend alembic upgrade head
    
    print_success "Migrations completed"
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--build)
                build_image
                shift
                ;;
            -u|--up)
                start_containers
                shift
                ;;
            -d|--down)
                stop_containers
                shift
                ;;
            -l|--logs)
                show_logs
                shift
                ;;
            -p|--pull)
                pull_images
                shift
                ;;
            -c|--clean)
                cleanup
                shift
                ;;
            -t|--test)
                run_tests
                shift
                ;;
            -m|--migrate)
                run_migrations
                shift
                ;;
            --build-only)
                BUILD_ONLY=true
                build_image
                shift
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: ./docker-deploy.sh [OPTIONS]"
                echo ""
                echo "OPTIONS:"
                echo "  -b, --build          Build Docker image"
                echo "  -u, --up             Start containers"
                echo "  -d, --down           Stop containers"
                echo "  -l, --logs           Show container logs"
                echo "  -p, --pull           Pull latest images"
                echo "  -c, --clean          Clean up containers and volumes"
                echo "  -t, --test           Run tests in container"
                echo "  -m, --migrate        Run database migrations"
                echo "  --build-only         Only build, don't start"
                echo "  --registry URL       Push to registry (requires -b)"
                echo "  -h, --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                ;;
        esac
    done
}

# Main execution
main() {
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║         FinancialEdApp - Docker Deployment              ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # Check requirements
    check_requirements
    
    # Show current status
    print_header "Current Status"
    docker-compose -f "$COMPOSE_FILE" \
                  --env-file "$ENV_FILE" \
                  -p "$PROJECT_NAME" \
                  ps || true
    
    # Parse arguments
    if [ $# -eq 0 ]; then
        print_info "No arguments provided. Use -h for help."
        exit 0
    fi
    
    parse_args "$@"
}

main "$@"
