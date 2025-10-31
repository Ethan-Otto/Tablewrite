#!/bin/bash
# Start FoundryVTT REST API relay server

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELAY_DIR="$PROJECT_ROOT/relay-server"

echo "Starting FoundryVTT REST API relay server..."
cd "$RELAY_DIR"

if [ ! -f "docker-compose.local.yml" ]; then
    echo "Error: docker-compose.local.yml not found in $RELAY_DIR"
    exit 1
fi

docker-compose -f docker-compose.local.yml up -d

echo "Waiting for relay to start..."
sleep 3

# Test health endpoint
if curl -sf http://localhost:3010/health > /dev/null 2>&1; then
    echo "✓ Relay server started successfully"
    echo "  Health: http://localhost:3010/health"
    echo "  Logs: ./scripts/relay_logs.sh"
else
    echo "✗ Relay server may not be healthy"
    echo "  Check logs with: ./scripts/relay_logs.sh"
    exit 1
fi
