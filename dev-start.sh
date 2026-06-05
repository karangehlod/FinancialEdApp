#!/usr/bin/env bash
# =============================================================================
# FinancialEdApp — Local Development Startup Script
# =============================================================================
# Usage:
#   ./dev-start.sh          # start infra + backend
#   ./dev-start.sh stop     # stop backend + infra containers
#   ./dev-start.sh restart  # stop then start
#   ./dev-start.sh status   # show container + backend status
#
# Requirements:
#   - Docker (for Postgres + Redis)
#   - Python 3.11 venv in backend/venv  OR  uv installed
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV="$BACKEND_DIR/venv"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.dev.yml"
PID_FILE="/tmp/finedu-backend.pid"
LOG_FILE="/tmp/finedu-backend.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
wait_healthy() {
    local container="$1" max_wait="${2:-60}" waited=0
    info "Waiting for $container to be healthy..."
    while ! docker inspect "$container" --format '{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; do
        if (( waited >= max_wait )); then
            error "$container did not become healthy in ${max_wait}s"
            docker logs "$container" --tail 20
            return 1
        fi
        sleep 2; (( waited += 2 ))
        echo -n "."
    done
    echo ""
    success "$container is healthy"
}

# ---------------------------------------------------------------------------
cmd_start() {
    info "=== FinancialEdApp Dev Start ==="

    # --- Infrastructure ---
    info "Starting Docker infrastructure (Postgres auth, Postgres data, Redis)..."
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

    wait_healthy finedu-auth-db 60
    wait_healthy finedu-data-db 60
    wait_healthy finedu-cache 30

    # --- Backend ---
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        warn "Backend already running (PID $(cat "$PID_FILE")). Skipping."
    else
        info "Starting FastAPI backend (uvicorn with --reload)..."
        cd "$BACKEND_DIR"

        # Prefer uv run if available, fall back to venv activation
        if command -v uv &>/dev/null && [[ -f "$BACKEND_DIR/pyproject.toml" ]]; then
            nohup uv run --active uvicorn app.main:app \
                --host 0.0.0.0 --port 8000 --reload \
                > "$LOG_FILE" 2>&1 &
        else
            # shellcheck disable=SC1091
            source "$VENV/bin/activate"
            nohup uvicorn app.main:app \
                --host 0.0.0.0 --port 8000 --reload \
                > "$LOG_FILE" 2>&1 &
        fi

        echo $! > "$PID_FILE"
        info "Backend PID $(cat "$PID_FILE") — logs at $LOG_FILE"

        # Health poll
        local retries=0
        while ! curl -sf http://localhost:8000/health >/dev/null 2>&1; do
            (( retries++ )) || true
            if (( retries > 20 )); then
                error "Backend did not start in time. Check $LOG_FILE"
                exit 1
            fi
            sleep 2; echo -n "."
        done
        echo ""
        success "Backend is healthy at http://localhost:8000"
        success "API docs: http://localhost:8000/docs"
    fi

    echo ""
    echo -e "${GREEN}=== All services running ===${NC}"
    echo "  Auth DB  : localhost:55432 (auth_db / finedu_admin)"
    echo "  Data DB  : localhost:55433 (financial_ed_db / finedu_admin)"
    echo "  Redis    : localhost:56379"
    echo "  Backend  : http://localhost:8000"
    echo "  API docs : http://localhost:8000/docs"
    echo ""
    echo "  Stop:    ./dev-start.sh stop"
    echo "  Logs:    tail -f $LOG_FILE"
}

cmd_stop() {
    info "Stopping backend..."
    if [[ -f "$PID_FILE" ]]; then
        local pid; pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && success "Backend stopped (PID $pid)"
        fi
        rm -f "$PID_FILE"
    else
        warn "No PID file found — backend may not be running"
    fi

    # Also kill any orphaned uvicorn processes on port 8000
    lsof -ti :8000 | xargs kill 2>/dev/null || true

    info "Stopping Docker infrastructure..."
    docker compose -f "$COMPOSE_FILE" down
    success "All services stopped"
}

cmd_status() {
    echo ""
    echo -e "${BLUE}=== Container Status ===${NC}"
    docker compose -f "$COMPOSE_FILE" ps

    echo ""
    echo -e "${BLUE}=== Backend Status ===${NC}"
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        success "Backend responding at http://localhost:8000"
        curl -s http://localhost:8000/health
    else
        warn "Backend not responding on port 8000"
    fi
}

# ---------------------------------------------------------------------------
COMMAND="${1:-start}"
case "$COMMAND" in
    start)   cmd_start   ;;
    stop)    cmd_stop    ;;
    restart) cmd_stop; sleep 2; cmd_start ;;
    status)  cmd_status  ;;
    *)       error "Unknown command: $COMMAND. Use start|stop|restart|status"; exit 1 ;;
esac
