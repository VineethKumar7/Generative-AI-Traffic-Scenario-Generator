#!/bin/bash
#
# ScenGen - Start all services
# Usage: ./start.sh [--no-carla]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚗 ScenGen - Starting services...${NC}"
echo ""

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

# Create pids directory
mkdir -p .pids

# ============ Backend API ============
echo -e "${YELLOW}[1/3] Starting Backend API...${NC}"

# Kill existing if running
if [ -f .pids/api.pid ]; then
    kill $(cat .pids/api.pid) 2>/dev/null || true
    rm -f .pids/api.pid
fi

# Activate venv and start
source venv/bin/activate
nohup python api.py > logs/api.log 2>&1 &
echo $! > .pids/api.pid
echo -e "      API started (PID: $(cat .pids/api.pid))"
echo -e "      → http://localhost:8000"

# ============ Frontend ============
echo -e "${YELLOW}[2/3] Starting Frontend...${NC}"

# Kill existing if running
if [ -f .pids/frontend.pid ]; then
    kill $(cat .pids/frontend.pid) 2>/dev/null || true
    rm -f .pids/frontend.pid
fi

cd frontend
nohup npm run dev -- --host > ../logs/frontend.log 2>&1 &
echo $! > ../.pids/frontend.pid
cd ..
echo -e "      Frontend started (PID: $(cat .pids/frontend.pid))"
echo -e "      → http://localhost:8080"

# ============ CARLA Server ============
if [ "$START_CARLA" = true ]; then
    echo -e "${YELLOW}[3/3] Starting CARLA Server...${NC}"
    
    # Check if CARLA is installed
    CARLA_ROOT="${CARLA_ROOT:-/opt/carla}"
    
    if [ -f "$CARLA_ROOT/CarlaUE4.sh" ]; then
        # Kill existing if running
        if [ -f .pids/carla.pid ]; then
            kill $(cat .pids/carla.pid) 2>/dev/null || true
            rm -f .pids/carla.pid
        fi
        
        # Start CARLA in background (force NVIDIA GPU on hybrid laptops)
        export __NV_PRIME_RENDER_OFFLOAD=1
        export __GLX_VENDOR_LIBRARY_NAME=nvidia
        export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
        nohup "$CARLA_ROOT/CarlaUE4.sh" -RenderOffScreen -quality-level=Low -prefernvidia > logs/carla.log 2>&1 &
        echo $! > .pids/carla.pid
        echo -e "      CARLA started (PID: $(cat .pids/carla.pid))"
        echo -e "      → localhost:2000"
    else
        echo -e "      ${RED}CARLA not found at $CARLA_ROOT${NC}"
        echo -e "      Set CARLA_ROOT environment variable or install CARLA"
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
