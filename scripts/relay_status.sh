#!/bin/bash
# Check FoundryVTT REST API relay server status

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELAY_DIR="$PROJECT_ROOT/relay-server"

echo "Checking relay server status..."
echo ""

# Docker container status
echo "Docker Container:"
cd "$RELAY_DIR"
docker-compose -f docker-compose.local.yml ps

echo ""

# Health endpoint
echo "Health Endpoint:"
if curl -sf http://localhost:3010/health 2>/dev/null | python3 -m json.tool; then
    echo ""
    echo "✓ Relay server is healthy"
else
    echo "✗ Relay server is not responding"
    exit 1
fi

echo ""

# Resource usage
echo "Resource Usage:"
docker stats foundryvtt-rest-api-relay --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "Container not running"
