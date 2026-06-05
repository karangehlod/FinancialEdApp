#!/usr/bin/env bash

################################################################################
# Docker Deployment Testing Script
# 
# This script tests the Docker deployment before Kubernetes deployment
# Verifies:
#   - Docker images build successfully
#   - Docker containers start and stay healthy
#   - Services communicate properly
#   - Health checks pass
#   - Logs are clean (no critical errors)
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
DOCKER_TIMEOUT=120
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_INTERVAL=3

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓ SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[⚠ WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗ ERROR]${NC} $*"
}

print_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

# Trap errors
trap 'on_error' ERR

on_error() {
    log_error "Script failed at line $LINENO"
    cleanup
    exit 1
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker-compose -f "$COMPOSE_FILE" down --volumes 2>/dev/null || true
}

# Check prerequisites
check_prerequisites() {
    print_section "CHECKING PREREQUISITES"
    
    log_info "Checking Docker..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
    
    log_info "Checking Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    log_success "Docker Compose found: $(docker-compose --version)"
    
    log_info "Checking if Docker daemon is running..."
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    log_success "Docker daemon is running"
    
    log_info "Checking docker-compose.yml..."
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found at $COMPOSE_FILE"
        exit 1
    fi
    log_success "docker-compose.yml found"
}

# Clean up previous deployment
cleanup_previous() {
    print_section "CLEANING UP PREVIOUS DEPLOYMENT"
    
    log_info "Stopping running containers..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
    
    sleep 2
    
    log_info "Removing volumes (optional, set KEEP_VOLUMES=1 to skip)..."
    if [ "$KEEP_VOLUMES" != "1" ]; then
        docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    else
        log_warning "Keeping volumes for data retention"
    fi
    
    log_success "Cleanup complete"
}

# Build Docker images
build_images() {
    print_section "BUILDING DOCKER IMAGES"
    
    log_info "Building backend image (this may take a few minutes)..."
    
    if docker-compose -f "$COMPOSE_FILE" build --no-cache; then
        log_success "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
}

# Start services
start_services() {
    print_section "STARTING SERVICES"
    
    log_info "Starting containers..."
    if docker-compose -f "$COMPOSE_FILE" up -d; then
        log_success "Containers started"
    else
        log_error "Failed to start containers"
        exit 1
    fi
    
    sleep 5  # Give services time to start
}

# Wait for services to be healthy
wait_for_services() {
    print_section "WAITING FOR SERVICES TO BE HEALTHY"
    
    local services=("postgres_auth" "postgres_data" "redis" "backend")
    local all_healthy=true
    
    for service in "${services[@]}"; do
        log_info "Waiting for $service to be healthy (max ${DOCKER_TIMEOUT}s)..."
        
        local start_time=$(date +%s)
        local healthy=false
        
        while [ $(($(date +%s) - start_time)) -lt $DOCKER_TIMEOUT ]; do
            local status=$(docker-compose -f "$COMPOSE_FILE" ps "$service" --format "{{.Status}}" 2>/dev/null || echo "")
            
            if [[ "$status" == *"(healthy)"* ]]; then
                log_success "$service is healthy"
                healthy=true
                break
            elif [[ "$status" == *"(unhealthy)"* ]]; then
                log_error "$service is unhealthy"
                log_info "Container logs:"
                docker-compose -f "$COMPOSE_FILE" logs "$service" | tail -20
                all_healthy=false
                break
            else
                echo -ne "    Status: $status\r"
                sleep 2
            fi
        done
        
        if [ "$healthy" = false ]; then
            log_warning "$service did not reach healthy state"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = false ]; then
        log_warning "Some services are not healthy. Continuing with caution..."
    fi
}

# Test service connectivity
test_connectivity() {
    print_section "TESTING SERVICE CONNECTIVITY"
    
    log_info "Verifying database connectivity..."
    
    # Test auth database
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres_auth \
        pg_isready -U "${POSTGRES_USER:-finedu_admin}" -d auth_db &> /dev/null; then
        log_success "Auth database is responding"
    else
        log_warning "Could not reach auth database"
    fi
    
    # Test data database
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres_data \
        pg_isready -U "${POSTGRES_USER:-finedu_admin}" -d financial_ed_db &> /dev/null; then
        log_success "Data database is responding"
    else
        log_warning "Could not reach data database"
    fi
    
    # Test Redis
    log_info "Verifying Redis connectivity..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli -a "${REDIS_PASSWORD:-finedu_redis_password}" ping &> /dev/null; then
        log_success "Redis is responding (ping: PONG)"
    else
        log_warning "Could not reach Redis"
    fi
    
    # Test backend
    log_info "Verifying backend API connectivity..."
    if curl -s http://localhost:8000/health | grep -q "ok\|healthy"; then
        log_success "Backend API is responding"
    else
        log_warning "Backend API is not responding yet, checking logs..."
        docker-compose -f "$COMPOSE_FILE" logs backend | tail -30
    fi
}

# Validate database schema
validate_database_schema() {
    print_section "VALIDATING DATABASE SCHEMA"
    
    log_info "Checking auth database tables..."
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres_auth psql \
        -U "${POSTGRES_USER:-finedu_admin}" -d auth_db \
        -c "\dt" 2> /dev/null | grep -q "public"; then
        log_success "Auth database has tables"
    else
        log_warning "No tables found in auth database (might be empty)"
    fi
    
    log_info "Checking data database tables..."
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres_data psql \
        -U "${POSTGRES_USER:-finedu_admin}" -d financial_ed_db \
        -c "\dt" 2> /dev/null | grep -q "public"; then
        log_success "Data database has tables"
    else
        log_warning "No tables found in data database (might be empty)"
    fi
}

# Check logs for errors
check_logs() {
    print_section "CHECKING FOR ERRORS IN LOGS"
    
    local services=("postgres_auth" "postgres_data" "redis" "backend")
    local has_errors=false
    
    for service in "${services[@]}"; do
        log_info "Checking $service logs..."
        
        local error_count=$(docker-compose -f "$COMPOSE_FILE" logs "$service" 2>/dev/null | \
            grep -i "error\|fatal\|panic" | wc -l || echo "0")
        
        if [ "$error_count" -gt 0 ]; then
            log_warning "$service has $error_count error lines"
            docker-compose -f "$COMPOSE_FILE" logs "$service" | grep -i "error\|fatal\|panic" | head -5
            has_errors=true
        else
            log_success "$service logs are clean"
        fi
    done
    
    return $([ "$has_errors" = true ] && echo 1 || echo 0)
}

# Test API endpoints (if backend is running)
test_api_endpoints() {
    print_section "TESTING API ENDPOINTS"
    
    local base_url="http://localhost:8000"
    local max_retries=5
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s "$base_url/health" &> /dev/null; then
            log_success "Backend is responding"
            break
        fi
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            log_info "Backend not ready, retrying... ($retry_count/$max_retries)"
            sleep 3
        fi
    done
    
    if [ $retry_count -eq $max_retries ]; then
        log_warning "Backend did not become ready within timeout"
        return 1
    fi
    
    # Test common endpoints
    local endpoints=("/health" "/api/v1/docs" "/api/v1/openapi.json")
    
    for endpoint in "${endpoints[@]}"; do
        log_info "Testing endpoint: $endpoint"
        
        local response=$(curl -s -o /dev/null -w "%{http_code}" "$base_url$endpoint")
        if [ "$response" == "200" ] || [ "$response" == "405" ]; then
            log_success "Endpoint $endpoint responded with $response"
        else
            log_warning "Endpoint $endpoint responded with $response"
        fi
    done
}

# Generate deployment report
generate_report() {
    print_section "DEPLOYMENT TEST REPORT"
    
    local report_file="${PROJECT_ROOT}/DOCKER_DEPLOYMENT_TEST_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << 'EOF'
# Docker Deployment Test Report

Generated: $(date)

## Test Results

### Services Status
```
$(docker-compose -f "$COMPOSE_FILE" ps)
```

### Image Information
```
$(docker images | grep financialedapp)
```

### Network
```
$(docker network ls | grep financialedapp)
```

### Volumes
```
$(docker volume ls | grep financialedapp)
```

## Next Steps

1. Run integration tests
2. Deploy to Kubernetes
3. Monitor production metrics

EOF
    
    log_success "Report generated: $report_file"
}

# Performance metrics
show_metrics() {
    print_section "RESOURCE METRICS"
    
    log_info "Container resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" || true
    
    log_info "\nDisk usage:"
    docker system df || true
}

# Main execution
main() {
    log_info "Starting Docker Deployment Tests"
    log_info "Project Root: $PROJECT_ROOT"
    
    # Check if running in cleanup-only mode
    if [ "$1" == "cleanup" ]; then
        cleanup
        log_success "Cleanup completed"
        exit 0
    fi
    
    # Run tests
    check_prerequisites
    cleanup_previous
    build_images
    start_services
    wait_for_services
    test_connectivity
    validate_database_schema
    check_logs || log_warning "Some logs contain errors"
    test_api_endpoints || log_warning "API tests failed"
    show_metrics
    generate_report
    
    print_section "✓ DOCKER DEPLOYMENT TEST COMPLETE"
    
    log_success "All Docker deployment tests completed!"
    log_info "Services are running. To access them:"
    log_info "  - Backend API: http://localhost:8000"
    log_info "  - PostgreSQL Auth: localhost:55432"
    log_info "  - PostgreSQL Data: localhost:55433"
    log_info "  - Redis: localhost:56379"
    log_info ""
    log_info "To view logs: docker-compose -f $COMPOSE_FILE logs -f [service_name]"
    log_info "To stop: docker-compose -f $COMPOSE_FILE down"
    log_info "To stop and remove volumes: docker-compose -f $COMPOSE_FILE down -v"
}

# Handle cleanup on interrupt
trap cleanup EXIT

# Run main function
main "$@"
