#!/bin/bash
#
# ScenGen - Stop all services
# Usage: ./stop.sh
#
# Kills all processes by pattern matching (not just PID files).
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 ScenGen - Stopping services...${NC}"
echo ""

stopped=0

# ============ Stop Backend API ============
if pkill -f "python.*api\.py" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Backend API stopped"
    ((stopped++))
fi

# ============ Stop Frontend (vite) ============
if pkill -f "node.*vite.*--host" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Frontend stopped"
    ((stopped++))
fi

# ============ Stop CARLA ============
if pkill -f "CarlaUE4" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} CARLA stopped"
    ((stopped++))
fi

# ============ Clean up PID files ============
rm -f .pids/*.pid 2>/dev/null

# ============ Free ports (in case of orphaned connections) ============
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8080/tcp 2>/dev/null || true

# ============ Summary ============
echo ""
if [ $stopped -gt 0 ]; then
    echo -e "${GREEN}✅ All services stopped${NC}"
else
    echo -e "${YELLOW}No running services found${NC}"
fi
echo ""
