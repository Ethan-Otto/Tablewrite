#!/bin/bash
# Stop FoundryVTT REST API relay server

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELAY_DIR="$PROJECT_ROOT/relay-server"

echo "Stopping FoundryVTT REST API relay server..."
cd "$RELAY_DIR"

docker-compose -f docker-compose.local.yml down

echo "✓ Relay server stopped"
