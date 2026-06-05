# Kubernetes Deployment Guide

Complete guide for deploying FinancialEdApp to Kubernetes clusters.

## Prerequisites

- Kubernetes cluster 1.24+
- kubectl CLI installed and configured
- Docker registry access (ECR, Docker Hub, etc.)
- Helm 3+ (optional, for easier management)
- Cert-Manager (for SSL/TLS)
- Ingress Controller (nginx-ingress)

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           Kubernetes Cluster                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │        Ingress (nginx)                   │  │
│  │   api.financialedapp.com                 │  │
│  └──────────────────────────────────────────┘  │
│              ↓                                  │
│  ┌──────────────────────────────────────────┐  │
│  │  Backend Service (ClusterIP)             │  │
│  └──────────────────────────────────────────┘  │
│         ↓              ↓              ↓         │
│  ┌────────┐      ┌────────┐     ┌────────┐    │
│  │Backend │      │Backend │     │Backend │    │
│  │Pod 1   │      │Pod 2   │     │Pod 3   │    │
│  │(HPA)   │      │(HPA)   │     │(HPA)   │    │
│  └────────┘      └────────┘     └────────┘    │
│         ↓              ↓              ↓         │
│  ┌─────────────────────────────────────────┐   │
│  │  PostgreSQL StatefulSet (1 replica)    │   │
│  │  - Persistent Volume: 20Gi             │   │
│  │  - Backup enabled                      │   │
│  └─────────────────────────────────────────┘   │
│         ↓                                      │
│  ┌─────────────────────────────────────────┐   │
│  │  Redis Deployment (1 replica)          │   │
│  │  - Persistent Volume: 5Gi              │   │
│  │  - RDB + AOF persistence               │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Monitoring (Prometheus + Grafana)      │  │
│  │  - ServiceMonitor                       │  │
│  │  - PrometheusRule for alerts            │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
```

## File Structure

```
k8s/
├── 00-namespace-config-secrets.yaml    # Namespace, ConfigMap, Secret
├── 01-postgres.yaml                     # PostgreSQL StatefulSet
├── 02-redis.yaml                        # Redis Deployment
├── 03-backend.yaml                      # Backend Deployment + HPA + PDB
├── 04-ingress.yaml                      # Ingress + NetworkPolicy
├── 05-monitoring.yaml                   # Prometheus monitoring
└── K8S_DEPLOYMENT_GUIDE.md             # This file
```

## Step-by-Step Deployment

### 1. Build and Push Docker Image

```bash
# Navigate to backend directory
cd backend

# Build Docker image
docker build -t your-registry/financialedapp-backend:1.0.0 .

# Push to registry
docker push your-registry/financialedapp-backend:1.0.0
```

### 2. Update Kubernetes Files

Update image reference in `03-backend.yaml`:

```yaml
image: your-registry/financialedapp-backend:1.0.0
```

### 3. Create Namespace and Base Configuration

```bash
# Apply namespace, ConfigMap, and Secrets
kubectl apply -f k8s/00-namespace-config-secrets.yaml

# Verify
kubectl get namespace financialedapp
kubectl get configmap -n financialedapp
kubectl get secret -n financialedapp
```

### 4. Deploy PostgreSQL Database

```bash
# Create storage class and StatefulSet
kubectl apply -f k8s/01-postgres.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n financialedapp --timeout=300s

# Verify
kubectl get statefulset -n financialedapp
kubectl get pvc -n financialedapp
```

### 5. Deploy Redis Cache

```bash
# Create Redis deployment
kubectl apply -f k8s/02-redis.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n financialedapp --timeout=300s

# Verify
kubectl get deployment -n financialedapp
```

### 6. Deploy Backend API

```bash
# Create backend deployment, HPA, and PDB
kubectl apply -f k8s/03-backend.yaml

# Wait for backend to be ready
kubectl wait --for=condition=ready pod -l app=backend -n financialedapp --timeout=300s

# Check pod status
kubectl get pods -n financialedapp -l app=backend

# Check logs
kubectl logs -n financialedapp -l app=backend -f
```

### 7. Configure Ingress

```bash
# Make sure you have nginx-ingress controller installed
# If not, install it:
# helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
# helm install nginx-ingress ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace

# Apply ingress configuration
kubectl apply -f k8s/04-ingress.yaml

# Get ingress status
kubectl get ingress -n financialedapp
```

### 8. Setup Monitoring (Optional)

```bash
# Install Prometheus Operator if not already installed
# helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
# helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Apply monitoring configuration
kubectl apply -f k8s/05-monitoring.yaml

# Verify
kubectl get servicemonitor -n financialedapp
kubectl get prometheusrule -n financialedapp
```

## Deployment Verification

### Check All Resources

```bash
# List all resources in financialedapp namespace
kubectl get all -n financialedapp

# Check running pods
kubectl get pods -n financialedapp

# Check services
kubectl get svc -n financialedapp

# Check persistent volumes
kubectl get pvc -n financialedapp

# Check ingress
kubectl get ingress -n financialedapp
```

### Test API Endpoint

```bash
# Get ingress IP/hostname
kubectl get ingress -n financialedapp -o wide

# Test health endpoint
curl -k https://api.financialedapp.com/health

# Test API endpoint
curl -k https://api.financialedapp.com/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Logs

```bash
# Backend logs
kubectl logs -n financialedapp -l app=backend -f

# PostgreSQL logs
kubectl logs -n financialedapp -l app=postgres -f

# Redis logs
kubectl logs -n financialedapp -l app=redis -f
```

## Database Management

### Run Database Migrations

```bash
# Port-forward to PostgreSQL
kubectl port-forward -n financialedapp svc/postgres 5432:5432 &

# Run migrations
export DATABASE_URL="postgresql://financialuser:SecurePassword123!@localhost:5432/financialedapp_db"
alembic upgrade head
```

### Backup Database

```bash
# Create backup
kubectl exec -it -n financialedapp postgres-0 -- pg_dump \
  -U financialuser financialedapp_db > backup.sql

# Restore from backup
kubectl exec -it -n financialedapp postgres-0 -- psql \
  -U financialuser financialedapp_db < backup.sql
```

## Scaling

### Manually Scale Backend

```bash
# Scale to 5 replicas
kubectl scale deployment backend -n financialedapp --replicas=5

# Check status
kubectl get deployment backend -n financialedapp
```

### Monitor HPA

```bash
# Watch HPA scaling
kubectl get hpa -n financialedapp -w

# Get HPA details
kubectl describe hpa backend-hpa -n financialedapp
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n financialedapp

# Check logs
kubectl logs <pod-name> -n financialedapp

# Check resource limits
kubectl top pods -n financialedapp
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -- \
  psql -h postgres -U financialuser -d financialedapp_db

# Check service DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup postgres.financialedapp
```

### High Memory/CPU Usage

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n financialedapp

# Adjust resource limits in 03-backend.yaml
# Redeploy: kubectl apply -f k8s/03-backend.yaml
```

## Production Best Practices

### 1. Secrets Management

Store sensitive data in proper secret management:
- Use HashiCorp Vault
- Use AWS Secrets Manager
- Use Azure Key Vault

```bash
# Example with Vault
kubectl create secret generic backend-secrets \
  --from-literal=DATABASE_URL=postgresql://... \
  -n financialedapp
```

### 2. Resource Quotas

```bash
kubectl set quota financial-quota \
  --hard=requests.cpu=10,requests.memory=20Gi,limits.cpu=20,limits.memory=40Gi \
  -n financialedapp
```

### 3. Network Policies

Already configured in `04-ingress.yaml` for:
- Ingress from external traffic
- Egress to services only

### 4. Pod Security Policies

```bash
# Apply pod security standards
kubectl label namespace financialedapp pod-security.kubernetes.io/enforce=restricted
```

### 5. Backup Strategy

```bash
# Setup persistent backup
- Enable automated PostgreSQL backups
- Configure incremental backup schedule
- Store backups in S3/GCS
- Test backup restoration regularly
```

## Monitoring and Alerts

### Access Prometheus

```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Access: http://localhost:9090
```

### Access Grafana

```bash
# Port-forward to Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access: http://localhost:3000
# Default: admin / prom-operator
```

### Important Metrics

- `http_requests_total` - Total requests
- `http_request_duration_seconds` - Request latency
- `database_connection_pool_size` - DB connections
- `redis_connected_clients` - Redis connections

## Cleanup

### Delete All Resources

```bash
# Delete in reverse order
kubectl delete -f k8s/05-monitoring.yaml
kubectl delete -f k8s/04-ingress.yaml
kubectl delete -f k8s/03-backend.yaml
kubectl delete -f k8s/02-redis.yaml
kubectl delete -f k8s/01-postgres.yaml
kubectl delete -f k8s/00-namespace-config-secrets.yaml

# Or delete entire namespace
kubectl delete namespace financialedapp
```

## Advanced Topics

### Blue-Green Deployment

```yaml
# Deploy new version with different label
kubectl apply -f k8s/03-backend-blue-green.yaml

# Switch traffic by updating service selector
kubectl patch service backend -p '{"spec":{"selector":{"version":"green"}}}'
```

### Canary Deployment

Use Flagger with Istio:
```bash
helm install flagger flagger/flagger -n istio-system --create-namespace
```

### Multi-Region Deployment

- Deploy to multiple regions
- Use Global Load Balancer
- Setup DNS failover

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to K8s

on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Build and push Docker image
      run: |
        docker build -t ${{ secrets.REGISTRY }}/financialedapp-backend:${{ github.sha }} .
        docker push ${{ secrets.REGISTRY }}/financialedapp-backend:${{ github.sha }}
    
    - name: Deploy to K8s
      run: |
        kubectl set image deployment/backend backend=${{ secrets.REGISTRY }}/financialedapp-backend:${{ github.sha }} -n financialedapp
```

## Support

For issues:
1. Check logs: `kubectl logs -n financialedapp <pod-name>`
2. Describe pod: `kubectl describe pod <pod-name> -n financialedapp`
3. Check events: `kubectl get events -n financialedapp`
4. Review metrics: Check Prometheus/Grafana

---

**Last Updated**: January 2026  
**Version**: 1.0  
**Status**: Production Ready
