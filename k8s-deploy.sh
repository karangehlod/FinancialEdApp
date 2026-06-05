#!/bin/bash

################################################################################
# FinancialEdApp - Kubernetes Deployment Script
# 
# Usage: ./k8s-deploy.sh [OPTIONS] [COMMAND]
# 
# COMMANDS:
#   deploy      Deploy all resources
#   delete      Delete all resources
#   status      Show deployment status
#   logs        Show pod logs
#   shell       Open shell in pod
#   migrate     Run database migrations
#   backup      Backup database
#   restore     Restore database
#
# OPTIONS:
#   -n, --namespace NS   Kubernetes namespace (default: financialedapp)
#   -r, --registry URL   Docker registry URL
#   --dry-run            Show what would be deployed without making changes
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
NAMESPACE="financialedapp"
K8S_DIR="./k8s"
REGISTRY=""
DRY_RUN=false

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
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
    fi
    print_success "kubectl is installed"
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please configure kubectl."
    fi
    print_success "Connected to Kubernetes cluster"
}

# Deploy all resources
deploy() {
    print_header "Deploying to Kubernetes"
    
    local dry_run_flag=""
    if [ "$DRY_RUN" = true ]; then
        dry_run_flag="--dry-run=client"
        print_info "DRY RUN MODE - No changes will be made"
    fi
    
    # Create namespace
    kubectl apply $dry_run_flag -f "$K8S_DIR/00-namespace-config-secrets.yaml"
    print_success "Namespace and configuration created"
    
    # Wait for namespace
    sleep 2
    
    # Deploy PostgreSQL
    kubectl apply $dry_run_flag -f "$K8S_DIR/01-postgres.yaml"
    print_success "PostgreSQL deployed"
    
    if [ "$DRY_RUN" != true ]; then
        print_info "Waiting for PostgreSQL to be ready..."
        kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s || true
    fi
    
    # Deploy Redis
    kubectl apply $dry_run_flag -f "$K8S_DIR/02-redis.yaml"
    print_success "Redis deployed"
    
    if [ "$DRY_RUN" != true ]; then
        print_info "Waiting for Redis to be ready..."
        kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s || true
    fi
    
    # Deploy Backend
    kubectl apply $dry_run_flag -f "$K8S_DIR/03-backend.yaml"
    print_success "Backend deployed"
    
    if [ "$DRY_RUN" != true ]; then
        print_info "Waiting for Backend to be ready..."
        kubectl wait --for=condition=ready pod -l app=backend -n $NAMESPACE --timeout=300s || true
    fi
    
    # Deploy Ingress
    kubectl apply $dry_run_flag -f "$K8S_DIR/04-ingress.yaml"
    print_success "Ingress configured"
    
    # Deploy Monitoring
    kubectl apply $dry_run_flag -f "$K8S_DIR/05-monitoring.yaml"
    print_success "Monitoring configured"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN COMPLETED - Review above output and run without --dry-run to apply"
    else
        print_success "Deployment completed successfully"
    fi
}

# Delete all resources
delete() {
    print_header "Deleting Kubernetes Resources"
    
    read -p "Are you sure you want to delete all resources in namespace '$NAMESPACE'? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace $NAMESPACE --ignore-not-found=true
        print_success "Namespace deleted"
    else
        print_info "Deletion cancelled"
    fi
}

# Show deployment status
show_status() {
    print_header "Deployment Status"
    
    echo -e "${YELLOW}Namespace:${NC}"
    kubectl get namespace $NAMESPACE 2>/dev/null || print_error "Namespace does not exist"
    
    echo -e "\n${YELLOW}Pods:${NC}"
    kubectl get pods -n $NAMESPACE
    
    echo -e "\n${YELLOW}Services:${NC}"
    kubectl get svc -n $NAMESPACE
    
    echo -e "\n${YELLOW}Deployments:${NC}"
    kubectl get deployment -n $NAMESPACE
    
    echo -e "\n${YELLOW}StatefulSets:${NC}"
    kubectl get statefulset -n $NAMESPACE
    
    echo -e "\n${YELLOW}Ingress:${NC}"
    kubectl get ingress -n $NAMESPACE
    
    echo -e "\n${YELLOW}PersistentVolumes:${NC}"
    kubectl get pvc -n $NAMESPACE
    
    echo -e "\n${YELLOW}HPA Status:${NC}"
    kubectl get hpa -n $NAMESPACE
}

# Show pod logs
show_logs() {
    print_header "Pod Logs"
    
    read -p "Show logs for pod (default: backend): " pod_name
    pod_name=${pod_name:-backend}
    
    print_info "Fetching logs for pods matching: $pod_name"
    kubectl logs -n $NAMESPACE -l app=$pod_name -f --all-containers=true --timestamps=true
}

# Open shell in pod
open_shell() {
    print_header "Opening Shell"
    
    read -p "Enter pod name (or partial name) to connect to: " pod_name
    
    if [ -z "$pod_name" ]; then
        print_error "Pod name cannot be empty"
    fi
    
    # Find the pod
    local pod=$(kubectl get pods -n $NAMESPACE -o name | grep "$pod_name" | head -1 | cut -d'/' -f2)
    
    if [ -z "$pod" ]; then
        print_error "Pod not found matching: $pod_name"
    fi
    
    print_info "Connecting to pod: $pod"
    kubectl exec -it -n $NAMESPACE "$pod" -- /bin/bash
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"
    
    local backend_pod=$(kubectl get pods -n $NAMESPACE -l app=backend -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$backend_pod" ]; then
        print_error "No backend pod found"
    fi
    
    print_info "Running migrations in pod: $backend_pod"
    kubectl exec -n $NAMESPACE "$backend_pod" -- alembic upgrade head
    
    print_success "Migrations completed"
}

# Backup database
backup_database() {
    print_header "Backing Up Database"
    
    local postgres_pod=$(kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$postgres_pod" ]; then
        print_error "No PostgreSQL pod found"
    fi
    
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    print_info "Creating backup: $backup_file"
    kubectl exec -n $NAMESPACE "$postgres_pod" -- \
        pg_dump -U financialuser financialedapp_db > "$backup_file"
    
    print_success "Backup created: $backup_file"
}

# Restore database
restore_database() {
    print_header "Restoring Database"
    
    read -p "Enter backup file path: " backup_file
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
    fi
    
    local postgres_pod=$(kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$postgres_pod" ]; then
        print_error "No PostgreSQL pod found"
    fi
    
    read -p "This will overwrite the database. Are you sure? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Restoring database from: $backup_file"
        cat "$backup_file" | kubectl exec -i -n $NAMESPACE "$postgres_pod" -- \
            psql -U financialuser financialedapp_db
        
        print_success "Database restored"
    else
        print_info "Restore cancelled"
    fi
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            deploy)
                deploy
                shift
                ;;
            delete)
                delete
                shift
                ;;
            status)
                show_status
                shift
                ;;
            logs)
                show_logs
                shift
                ;;
            shell)
                open_shell
                shift
                ;;
            migrate)
                run_migrations
                shift
                ;;
            backup)
                backup_database
                shift
                ;;
            restore)
                restore_database
                shift
                ;;
            -h|--help)
                echo "Usage: ./k8s-deploy.sh [OPTIONS] [COMMAND]"
                echo ""
                echo "COMMANDS:"
                echo "  deploy      Deploy all resources"
                echo "  delete      Delete all resources"
                echo "  status      Show deployment status"
                echo "  logs        Show pod logs"
                echo "  shell       Open shell in pod"
                echo "  migrate     Run database migrations"
                echo "  backup      Backup database"
                echo "  restore     Restore database"
                echo ""
                echo "OPTIONS:"
                echo "  -n, --namespace NS   Kubernetes namespace (default: financialedapp)"
                echo "  -r, --registry URL   Docker registry URL"
                echo "  --dry-run            Show what would be deployed without making changes"
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
║      FinancialEdApp - Kubernetes Deployment             ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    print_info "Namespace: $NAMESPACE"
    
    # Check requirements
    check_requirements
    
    # Parse arguments
    if [ $# -eq 0 ]; then
        print_info "No command provided. Use -h for help."
        show_status
        exit 0
    fi
    
    parse_args "$@"
}

main "$@"
