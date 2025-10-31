#!/usr/bin/env python3
"""
Test connectivity to local FoundryVTT REST API relay server.

Verifies:
1. Relay server is accessible
2. Health endpoint responds
3. API authentication works
4. Basic search functionality works
"""
import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import requests
from dotenv import load_dotenv

def test_relay_health():
    """Test relay server health endpoint."""
    load_dotenv()
    relay_url = os.getenv("FOUNDRY_RELAY_URL")

    print(f"Testing relay health at: {relay_url}")

    try:
        response = requests.get(f"{relay_url}/health", timeout=5)
        response.raise_for_status()

        data = response.json()
        print(f"✓ Health check passed: {data}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_relay_api():
    """Test relay API with authentication."""
    load_dotenv()

    relay_url = os.getenv("FOUNDRY_RELAY_URL")
    api_key = os.getenv("FOUNDRY_LOCAL_API_KEY")
    client_id = os.getenv("FOUNDRY_LOCAL_CLIENT_ID")

    if not api_key or not client_id:
        print("✗ Missing API key or client ID in .env")
        return False

    print(f"\nTesting API search at: {relay_url}/search")
    print(f"Using client ID: {client_id}")

    try:
        response = requests.get(
            f"{relay_url}/search",
            params={"clientId": client_id, "query": "test", "filter": "JournalEntry"},
            headers={"x-api-key": api_key},
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        print(f"✓ API search successful: {data.get('totalResults', 0)} results")
        return True
    except Exception as e:
        print(f"✗ API search failed: {e}")
        return False

def main():
    """Run all relay tests."""
    print("=" * 60)
    print("FoundryVTT REST API Relay Connection Test")
    print("=" * 60)

    health_ok = test_relay_health()
    api_ok = test_relay_api()

    print("\n" + "=" * 60)
    if health_ok and api_ok:
        print("✓ All relay tests PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Some relay tests FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
