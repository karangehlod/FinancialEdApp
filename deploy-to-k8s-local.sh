#!/usr/bin/env bash

################################################################################
# Local Kubernetes Deployment Script (Docker Desktop)
# 
# This script deploys FinancialEdApp to local Kubernetes using Docker Desktop
# Features:
#   - Pre-flight checks for K8s setup
#   - Validates K8s configuration files
#   - Deploys services in correct order
#   - Monitors deployment status
#   - Provides access commands
#   - Health verification
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${PROJECT_ROOT}/backend/k8s"
NAMESPACE="financialedapp"
DEPLOYMENT_TIMEOUT=300
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_INTERVAL=2

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

log_step() {
    echo -e "${MAGENTA}[STEP]${NC} $*"
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
    exit 1
}

# Check prerequisites
check_prerequisites() {
    print_section "CHECKING PREREQUISITES"
    
    log_info "Checking kubectl installation..."
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_success "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client | head -1)"
    
    log_info "Checking Kubernetes cluster..."
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes cluster not accessible. Is Docker Desktop K8s running?"
        exit 1
    fi
    log_success "Kubernetes cluster is accessible"
    
    log_info "Checking nodes..."
    local node_count=$(kubectl get nodes --no-headers | wc -l)
    if [ "$node_count" -lt 1 ]; then
        log_error "No Kubernetes nodes found"
        exit 1
    fi
    log_success "Found $node_count node(s)"
    kubectl get nodes
    
    log_info "Checking K8s configuration files..."
    if [ ! -d "$K8S_DIR" ]; then
        log_error "K8s directory not found: $K8S_DIR"
        exit 1
    fi
    log_success "K8s directory found"
    
    local required_files=(
        "00-namespace-config-secrets.yaml"
        "01-postgres.yaml"
        "02-redis.yaml"
        "03-backend.yaml"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$K8S_DIR/$file" ]; then
            log_error "Missing required file: $file"
            exit 1
        fi
        log_success "Found: $file"
    done
}

# Check system resources
check_system_resources() {
    print_section "CHECKING SYSTEM RESOURCES"
    
    log_info "Getting cluster resource information..."
    
    # Try to get resource info (varies by platform)
    if command -v docker &> /dev/null; then
        log_info "Docker Desktop status:"
        docker info --format "CPUs: {{.NCPU}}, Memory: {{.MemTotal | div 1073741824}}GB" || true
    fi
    
    log_info "Node resource allocation:"
    kubectl top nodes 2>/dev/null || log_warning "Could not retrieve node metrics (metrics-server may not be installed)"
    
    log_info "Available storage:"
    kubectl get storageclass 2>/dev/null || log_warning "No storage classes available"
}

# Validate configuration files
validate_config_files() {
    print_section "VALIDATING KUBERNETES CONFIGURATION FILES"
    
    log_info "Validating YAML syntax..."
    
    for file in "$K8S_DIR"/*.yaml; do
        if [ -f "$file" ]; then
            log_info "Validating $(basename "$file")..."
            if kubectl apply -f "$file" --dry-run=client -o yaml &> /dev/null; then
                log_success "$(basename "$file") is valid"
            else
                log_error "$(basename "$file") has validation errors"
                kubectl apply -f "$file" --dry-run=client -o yaml 2>&1 | head -20
                exit 1
            fi
        fi
    done
}

# Build and load Docker image
build_and_load_image() {
    print_section "BUILDING AND LOADING DOCKER IMAGE"
    
    log_info "Building backend Docker image..."
    
    cd "$PROJECT_ROOT/backend"
    
    if docker build -t financialedapp-backend:latest . ; then
        log_success "Backend Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
    
    log_info "Docker image details:"
    docker images | grep financialedapp
}

# Delete existing namespace if requested
cleanup_previous_deployment() {
    if [ "$FORCE_CLEAN" == "1" ]; then
        print_section "CLEANING UP PREVIOUS DEPLOYMENT"
        
        log_warning "Force clean requested. Deleting namespace $NAMESPACE..."
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
        
        # Wait for namespace deletion
        local timeout=60
        local elapsed=0
        while kubectl get namespace "$NAMESPACE" 2>/dev/null; do
            if [ $elapsed -ge $timeout ]; then
                log_warning "Namespace deletion timed out, proceeding anyway..."
                break
            fi
            echo -ne "Waiting for namespace deletion... ${elapsed}s\r"
            sleep 2
            elapsed=$((elapsed + 2))
        done
        
        log_success "Previous deployment cleaned up"
    fi
}

# Deploy namespace and configuration
deploy_namespace_config() {
    log_step "Deploying Namespace and Configuration (Step 1/4)"
    
    log_info "Applying namespace, ConfigMap, and Secrets..."
    
    if kubectl apply -f "$K8S_DIR/00-namespace-config-secrets.yaml"; then
        log_success "Namespace and configuration deployed"
    else
        log_error "Failed to deploy namespace configuration"
        exit 1
    fi
    
    # Verify namespace exists
    sleep 2
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace $NAMESPACE is ready"
    else
        log_error "Namespace was not created successfully"
        exit 1
    fi
    
    # Verify secrets
    if kubectl get secret backend-secrets -n "$NAMESPACE" &> /dev/null; then
        log_success "Secrets configured"
    else
        log_error "Secrets were not created"
        exit 1
    fi
}

# Deploy PostgreSQL database
deploy_database() {
    log_step "Deploying PostgreSQL Database (Step 2/4)"
    
    log_info "Creating storage class and PostgreSQL..."
    
    if kubectl apply -f "$K8S_DIR/01-postgres.yaml"; then
        log_success "PostgreSQL deployment started"
    else
        log_error "Failed to deploy PostgreSQL"
        exit 1
    fi
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL pod to be ready (max ${DEPLOYMENT_TIMEOUT}s)..."
    
    if kubectl wait --for=condition=ready pod \
        -l app=postgres \
        -n "$NAMESPACE" \
        --timeout="${DEPLOYMENT_TIMEOUT}s" 2>/dev/null; then
        log_success "PostgreSQL is ready"
    else
        log_warning "PostgreSQL pod is not ready yet, checking status..."
        kubectl get pods -n "$NAMESPACE" -l app=postgres
        kubectl describe pod -n "$NAMESPACE" -l app=postgres | tail -30
    fi
    
    sleep 3
}

# Deploy Redis cache
deploy_redis() {
    log_step "Deploying Redis Cache (Step 3/4)"
    
    log_info "Deploying Redis..."
    
    if kubectl apply -f "$K8S_DIR/02-redis.yaml"; then
        log_success "Redis deployment started"
    else
        log_error "Failed to deploy Redis"
        exit 1
    fi
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis pod to be ready (max ${DEPLOYMENT_TIMEOUT}s)..."
    
    if kubectl wait --for=condition=ready pod \
        -l app=redis \
        -n "$NAMESPACE" \
        --timeout="${DEPLOYMENT_TIMEOUT}s" 2>/dev/null; then
        log_success "Redis is ready"
    else
        log_warning "Redis pod is not ready yet, checking status..."
        kubectl get pods -n "$NAMESPACE" -l app=redis
        kubectl describe pod -n "$NAMESPACE" -l app=redis | tail -30
    fi
    
    sleep 2
}

# Deploy backend application
deploy_backend() {
    log_step "Deploying Backend API (Step 4/4)"
    
    log_info "Deploying backend application..."
    
    if kubectl apply -f "$K8S_DIR/03-backend.yaml"; then
        log_success "Backend deployment started"
    else
        log_error "Failed to deploy backend"
        exit 1
    fi
    
    # Wait for backend to be ready
    log_info "Waiting for backend pods to be ready (max ${DEPLOYMENT_TIMEOUT}s)..."
    
    if kubectl wait --for=condition=ready pod \
        -l app=backend \
        -n "$NAMESPACE" \
        --timeout="${DEPLOYMENT_TIMEOUT}s" 2>/dev/null; then
        log_success "Backend pods are ready"
    else
        log_warning "Backend pods are not ready yet, checking status..."
        kubectl get pods -n "$NAMESPACE" -l app=backend
        kubectl describe pod -n "$NAMESPACE" -l app=backend | tail -30
    fi
    
    sleep 3
}

# Optional: Deploy ingress and monitoring
deploy_optional_services() {
    if [ "$DEPLOY_MONITORING" == "1" ]; then
        print_section "DEPLOYING OPTIONAL SERVICES"
        
        if [ -f "$K8S_DIR/04-ingress.yaml" ]; then
            log_info "Deploying Ingress..."
            kubectl apply -f "$K8S_DIR/04-ingress.yaml"
            log_success "Ingress deployed"
        fi
        
        if [ -f "$K8S_DIR/05-monitoring.yaml" ]; then
            log_info "Deploying Monitoring..."
            kubectl apply -f "$K8S_DIR/05-monitoring.yaml"
            log_success "Monitoring deployed"
        fi
    fi
}

# Verify deployment
verify_deployment() {
    print_section "VERIFYING DEPLOYMENT"
    
    log_info "Checking namespace resources..."
    kubectl get all -n "$NAMESPACE"
    
    log_info "\nChecking persistent volumes..."
    kubectl get pvc -n "$NAMESPACE"
    
    log_info "\nChecking services..."
    kubectl get services -n "$NAMESPACE"
    
    log_info "\nChecking all pods..."
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Count ready replicas
    local total_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l)
    local ready_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers | wc -l)
    
    log_info "\nPod Status: $ready_pods/$total_pods running"
    
    if [ "$ready_pods" -eq "$total_pods" ]; then
        log_success "All pods are running!"
    else
        log_warning "Some pods are not running. Check status above."
    fi
}

# Test connectivity
test_connectivity() {
    print_section "TESTING CONNECTIVITY"
    
    log_info "Setting up port forwards (background)..."
    
    # Kill any existing port-forwards
    pkill -f "kubectl port-forward" 2>/dev/null || true
    sleep 1
    
    # Start new port-forwards
    kubectl port-forward -n "$NAMESPACE" svc/backend 8000:8000 &>/dev/null &
    kubectl port-forward -n "$NAMESPACE" svc/postgres 5432:5432 &>/dev/null &
    kubectl port-forward -n "$NAMESPACE" svc/redis 6379:6379 &>/dev/null &
    
    sleep 3
    
    log_info "Testing backend API..."
    if curl -s http://localhost:8000/health &> /dev/null; then
        log_success "Backend API is accessible at http://localhost:8000"
    else
        log_warning "Backend API is not responding yet"
    fi
    
    log_info "Testing PostgreSQL..."
    if command -v psql &> /dev/null; then
        if psql -h localhost -U financialuser -d financialedapp_db -c "SELECT 1;" &>/dev/null 2>&1; then
            log_success "PostgreSQL is accessible at localhost:5432"
        else
            log_warning "PostgreSQL is not responding"
        fi
    else
        log_info "psql not installed, skipping PostgreSQL test"
    fi
    
    log_info "Testing Redis..."
    if command -v redis-cli &> /dev/null; then
        if redis-cli -a "RedisPassword123!" ping &> /dev/null; then
            log_success "Redis is accessible at localhost:6379"
        else
            log_warning "Redis is not responding"
        fi
    else
        log_info "redis-cli not installed, skipping Redis test"
    fi
}

# Display access information
show_access_info() {
    print_section "✓ DEPLOYMENT COMPLETE - ACCESS INFORMATION"
    
    cat << EOF
${GREEN}Kubernetes Cluster${NC}
  Context: $(kubectl config current-context)
  Namespace: $NAMESPACE
  
${GREEN}Services${NC}
  Backend API:   http://localhost:8000
  Backend Docs:  http://localhost:8000/docs
  PostgreSQL:    localhost:5432
  Redis:         localhost:6379

${GREEN}Useful Commands${NC}
  View all resources:
    kubectl get all -n $NAMESPACE
  
  Watch pod status:
    kubectl get pods -n $NAMESPACE -w
  
  View backend logs:
    kubectl logs -n $NAMESPACE -l app=backend -f
  
  View database logs:
    kubectl logs -n $NAMESPACE -l app=postgres -f
  
  View Redis logs:
    kubectl logs -n $NAMESPACE -l app=redis -f
  
  Describe pod (for debugging):
    kubectl describe pod -n $NAMESPACE <pod-name>
  
  Execute command in pod:
    kubectl exec -it -n $NAMESPACE <pod-name> -- /bin/bash
  
  Scale backend replicas:
    kubectl scale deployment backend -n $NAMESPACE --replicas=3

${GREEN}Port Forwarding${NC}
  Active port forwards: $(pgrep -f "kubectl port-forward" | wc -l)
  
  To manually create port forwards:
    kubectl port-forward -n $NAMESPACE svc/backend 8000:8000
    kubectl port-forward -n $NAMESPACE svc/postgres 5432:5432
    kubectl port-forward -n $NAMESPACE svc/redis 6379:6379

${GREEN}Cleanup${NC}
  Delete entire deployment:
    kubectl delete namespace $NAMESPACE
  
  Or use this script with cleanup flag:
    $0 cleanup

${GREEN}Documentation${NC}
  See PRODUCTION_READINESS_CHECK.md for detailed information
  See backend/k8s/K8S_DEPLOYMENT_GUIDE.md for K8s setup details

EOF
}

# Cleanup function
cleanup_deployment() {
    print_section "CLEANING UP KUBERNETES DEPLOYMENT"
    
    log_info "Stopping port forwards..."
    pkill -f "kubectl port-forward" 2>/dev/null || true
    
    log_warning "Deleting namespace and all resources in $NAMESPACE..."
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    
    log_info "Waiting for namespace deletion..."
    local timeout=60
    local elapsed=0
    while kubectl get namespace "$NAMESPACE" 2>/dev/null; do
        if [ $elapsed -ge $timeout ]; then
            log_warning "Namespace deletion timed out"
            break
        fi
        echo -ne "Waiting... ${elapsed}s\r"
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    log_success "Deployment cleaned up"
}

# Generate deployment report
generate_report() {
    local report_file="${PROJECT_ROOT}/K8S_DEPLOYMENT_REPORT_$(date +%Y%m%d_%H%M%S).md"
    
    log_info "Generating deployment report: $report_file"
    
    cat > "$report_file" << EOF
# Kubernetes Deployment Report

**Generated:** $(date)  
**Environment:** Local Docker Desktop  
**Namespace:** $NAMESPACE

## Deployment Status

### Cluster Information
\`\`\`
$(kubectl cluster-info 2>/dev/null)
\`\`\`

### Nodes
\`\`\`
$(kubectl get nodes)
\`\`\`

### Resources in Namespace

#### Deployments
\`\`\`
$(kubectl get deployments -n "$NAMESPACE" -o wide)
\`\`\`

#### StatefulSets
\`\`\`
$(kubectl get statefulsets -n "$NAMESPACE" -o wide)
\`\`\`

#### Pods
\`\`\`
$(kubectl get pods -n "$NAMESPACE" -o wide)
\`\`\`

#### Services
\`\`\`
$(kubectl get services -n "$NAMESPACE" -o wide)
\`\`\`

#### Persistent Volumes
\`\`\`
$(kubectl get pvc -n "$NAMESPACE")
\`\`\`

## Configuration

### ConfigMap
\`\`\`
$(kubectl get configmap backend-config -n "$NAMESPACE" -o yaml | head -30)
\`\`\`

### Secrets (redacted)
\`\`\`
$(kubectl get secrets -n "$NAMESPACE" -o name)
\`\`\`

## Deployment Notes

- Deployment completed successfully
- Services are running in namespace: $NAMESPACE
- Port forwards available on localhost for local testing
- For production, configure proper Ingress and TLS

## Next Steps

1. Run integration tests
2. Verify all services communicate properly
3. Monitor application logs
4. Test failover scenarios
5. Configure backups and monitoring

---

**Status:** ✓ Deployment Complete  
**Date:** $(date)
EOF
    
    log_success "Report generated: $report_file"
}

# Display help
show_help() {
    cat << EOF
${MAGENTA}Kubernetes Deployment Script for FinancialEdApp${NC}

${BLUE}Usage:${NC}
  $0 [OPTIONS]

${BLUE}Options:${NC}
  --force-clean    Delete existing deployment before deploying
  --monitoring     Deploy monitoring stack (Prometheus/Grafana)
  --help          Show this help message
  cleanup         Delete the entire deployment

${BLUE}Environment Variables:${NC}
  FORCE_CLEAN=1       Same as --force-clean
  DEPLOY_MONITORING=1 Same as --monitoring

${BLUE}Examples:${NC}
  # Deploy with fresh namespace
  $0 --force-clean
  
  # Deploy with monitoring
  $0 --monitoring
  
  # Cleanup deployment
  $0 cleanup

${BLUE}Documentation:${NC}
  See PRODUCTION_READINESS_CHECK.md for detailed information

EOF
}

# Main execution
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-clean)
                export FORCE_CLEAN=1
                shift
                ;;
            --monitoring)
                export DEPLOY_MONITORING=1
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            cleanup)
                cleanup_deployment
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_section "KUBERNETES DEPLOYMENT - DOCKER DESKTOP"
    log_info "Project Root: $PROJECT_ROOT"
    log_info "K8s Directory: $K8S_DIR"
    log_info "Namespace: $NAMESPACE"
    
    # Run deployment steps
    check_prerequisites
    check_system_resources
    validate_config_files
    build_and_load_image
    cleanup_previous_deployment
    deploy_namespace_config
    deploy_database
    deploy_redis
    deploy_backend
    deploy_optional_services
    verify_deployment
    test_connectivity
    show_access_info
    generate_report
    
    print_section "✓ KUBERNETES DEPLOYMENT COMPLETE"
    
    log_success "FinancialEdApp is now running on Kubernetes!"
}

# Handle script arguments
if [ $# -eq 0 ]; then
    main
else
    main "$@"
fi
