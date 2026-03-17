#!/bin/bash
#
# ScenGen - Stop all services
# Usage: ./stop.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 ScenGen - Stopping services...${NC}"
echo ""

stopped=0

# ============ Stop Backend API ============
if [ -f .pids/api.pid ]; then
    pid=$(cat .pids/api.pid)
    if kill -0 $pid 2>/dev/null; then
        kill $pid 2>/dev/null
        echo -e "   ${GREEN}✓${NC} Backend API stopped (PID: $pid)"
        ((stopped++))
    fi
    rm -f .pids/api.pid
fi

# Also kill any orphaned uvicorn/python api processes
pkill -f "python.*api.py" 2>/dev/null && echo -e "   ${GREEN}✓${NC} Cleaned up orphaned API processes" || true

# ============ Stop Frontend ============
if [ -f .pids/frontend.pid ]; then
    pid=$(cat .pids/frontend.pid)
    if kill -0 $pid 2>/dev/null; then
        kill $pid 2>/dev/null
        echo -e "   ${GREEN}✓${NC} Frontend stopped (PID: $pid)"
        ((stopped++))
    fi
    rm -f .pids/frontend.pid
fi

# Also kill any orphaned vite processes on port 8080/8081
pkill -f "vite.*808[01]" 2>/dev/null && echo -e "   ${GREEN}✓${NC} Cleaned up orphaned frontend processes" || true

# ============ Stop CARLA ============
if [ -f .pids/carla.pid ]; then
    pid=$(cat .pids/carla.pid)
    if kill -0 $pid 2>/dev/null; then
        kill $pid 2>/dev/null
        echo -e "   ${GREEN}✓${NC} CARLA stopped (PID: $pid)"
        ((stopped++))
    fi
    rm -f .pids/carla.pid
fi

# Also kill any orphaned CARLA processes
pkill -f "CarlaUE4" 2>/dev/null && echo -e "   ${GREEN}✓${NC} Cleaned up orphaned CARLA processes" || true

# ============ Summary ============
echo ""
if [ $stopped -gt 0 ]; then
    echo -e "${GREEN}✅ All services stopped${NC}"
else
    echo -e "${YELLOW}No running services found${NC}"
fi
echo ""
