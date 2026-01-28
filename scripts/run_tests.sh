#!/bin/bash
# Run the full test suite with parallel execution
# Usage: ./scripts/run_tests.sh [additional pytest args]

set -e

cd "$(dirname "$0")/.."

echo "Running full test suite with parallel execution..."
echo "Logs: tail -f test.log"
echo ""

uv run pytest --full -n auto --dist loadscope -v "$@" 2>&1
