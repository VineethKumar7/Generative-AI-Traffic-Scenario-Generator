#!/bin/bash
#
# ScenGen - Start all services
# Usage: ./start.sh [--no-carla]
#
# Automatically kills any existing processes before starting fresh.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
START_CARLA=true
for arg in "$@"; do
    case $arg in
        --no-carla)
            START_CARLA=false
            shift
            ;;
    esac
done

# ============ Clean up any existing processes ============
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"

# Kill any existing API processes
pkill -f "python.*api\.py" 2>/dev/null && echo "   Killed existing API" || true

# Kill any existing vite/frontend processes (node with vite)
pkill -f "node.*vite.*--host" 2>/dev/null && echo "   Killed existing frontend" || true

# Kill any existing CARLA processes
pkill -f "CarlaUE4" 2>/dev/null && echo "   Killed existing CARLA" || true

# Clean up stale PID files
rm -f .pids/*.pid 2>/dev/null

# Wait for ports to free up
sleep 1

# Free up ports if still occupied
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8080/tcp 2>/dev/null || true

sleep 1

echo ""
echo -e "${GREEN}🚗 ScenGen - Starting services...${NC}"
echo ""

# Create directories
mkdir -p .pids logs

# ============ Backend API ============
echo -e "${YELLOW}[1/3] Starting Backend API...${NC}"

source venv/bin/activate
nohup python api.py > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > .pids/api.pid
echo -e "      API started (PID: $API_PID)"
echo -e "      → http://localhost:8000"

# ============ Frontend ============
echo -e "${YELLOW}[2/3] Starting Frontend...${NC}"

cd frontend
nohup npm run dev -- --host > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.pids/frontend.pid
cd ..
echo -e "      Frontend started (PID: $FRONTEND_PID)"
echo -e "      → http://localhost:8080"

# ============ CARLA Server ============
if [ "$START_CARLA" = true ]; then
    echo -e "${YELLOW}[3/3] Starting CARLA Server...${NC}"
    
    CARLA_ROOT="${CARLA_ROOT:-/opt/carla}"
    
    if [ -f "$CARLA_ROOT/CarlaUE4.sh" ]; then
        # Force NVIDIA GPU on hybrid laptops
        export __NV_PRIME_RENDER_OFFLOAD=1
        export __GLX_VENDOR_LIBRARY_NAME=nvidia
        export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
        
        nohup "$CARLA_ROOT/CarlaUE4.sh" -RenderOffScreen -quality-level=Low -prefernvidia > logs/carla.log 2>&1 &
        CARLA_PID=$!
        echo $CARLA_PID > .pids/carla.pid
        echo -e "      CARLA started (PID: $CARLA_PID)"
        echo -e "      → localhost:2000"
    else
        echo -e "      ${RED}CARLA not found at $CARLA_ROOT${NC}"
        echo -e "      Continuing without CARLA (mock mode)..."
    fi
else
    echo -e "${YELLOW}[3/3] Skipping CARLA (--no-carla flag)${NC}"
fi

# ============ Summary ============
echo ""
echo -e "${GREEN}✅ ScenGen is running!${NC}"
echo ""
echo "   Services:"
echo "   ├── Backend API:  http://localhost:8000"
echo "   ├── Frontend:     http://localhost:8080"
if [ "$START_CARLA" = true ] && [ -f .pids/carla.pid ]; then
echo "   └── CARLA:        localhost:2000"
else
echo "   └── CARLA:        (not running - mock mode)"
fi
echo ""
echo "   Logs: $SCRIPT_DIR/logs/"
echo "   Stop: ./stop.sh"
echo ""
