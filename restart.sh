#!/bin/bash
#
# ScenGen - Restart all services
# Usage: ./restart.sh [--no-carla]
#
# Equivalent to: ./stop.sh && ./start.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔄 ScenGen - Restarting services...${NC}"
echo ""

# Stop everything first
./stop.sh

# Small delay to ensure ports are released
sleep 1

# Start with any passed arguments (e.g., --no-carla)
./start.sh "$@"
