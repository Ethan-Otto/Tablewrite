#!/bin/bash
# View FoundryVTT REST API relay server logs

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELAY_DIR="$PROJECT_ROOT/relay-server"

echo "Tailing relay server logs (Ctrl+C to exit)..."
echo ""

cd "$RELAY_DIR"
docker-compose -f docker-compose.local.yml logs -f relay
