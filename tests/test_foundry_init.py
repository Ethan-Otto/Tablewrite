"""
Tests for foundry_init module.

These tests verify that the Foundry initialization script works correctly
with real backend and Foundry connections.
"""

import pytest

from tests.foundry_init import (
    check_backend_health,
    check_foundry_connected,
    BACKEND_URL,
    FOUNDRY_URL,
)


class TestFoundryInitFunctions:
    """Test individual functions from foundry_init module."""

    @pytest.mark.integration
    def test_check_backend_health_real_connection(self, require_foundry):
        """Backend health check returns True when backend is running."""
        # require_foundry ensures backend is running
        is_healthy = check_backend_health()
        assert is_healthy is True, f"Backend at {BACKEND_URL} should be healthy"

    @pytest.mark.integration
    def test_check_foundry_connected_real_connection(self, require_foundry):
        """Foundry connection check returns True with client count when connected."""
        is_connected, client_count = check_foundry_connected()

        assert is_connected is True, "Foundry should be connected"
        assert client_count >= 1, "Should have at least 1 connected client"

    @pytest.mark.integration
    def test_foundry_status_endpoint_returns_expected_structure(self, require_foundry):
        """
        The /api/foundry/status endpoint returns expected JSON structure.

        Uses real Foundry connection to verify the status endpoint works.
        """
        import httpx

        with httpx.Client() as client:
            response = client.get(f"{BACKEND_URL}/api/foundry/status", timeout=10.0)

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "connected_clients" in data
        assert data["status"] == "connected"
        assert isinstance(data["connected_clients"], int)
        assert data["connected_clients"] >= 1

    @pytest.mark.integration
    def test_can_list_actors_via_websocket(self, require_foundry):
        """
        Can list actors through the WebSocket-based API.

        This proves end-to-end WebSocket communication with Foundry works.
        """
        import httpx

        with httpx.Client() as client:
            response = client.get(
                f"{BACKEND_URL}/api/foundry/actors",
                timeout=30.0  # Actor listing can take a moment
            )

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "actors" in data
        assert isinstance(data["actors"], list)
        # We don't assert on count since world may have 0 actors


class TestFoundryFixtures:
    """Test that the pytest fixtures work correctly."""

    @pytest.mark.integration
    def test_require_foundry_fixture_provides_status(self, require_foundry):
        """The require_foundry fixture provides connection status dict."""
        assert require_foundry is not None
        assert isinstance(require_foundry, dict)
        assert "backend_running" in require_foundry
        assert "foundry_connected" in require_foundry
        assert require_foundry["backend_running"] is True
        assert require_foundry["foundry_connected"] is True

    @pytest.mark.integration
    def test_foundry_status_fixture_same_as_require(self, foundry_status, require_foundry):
        """Both fixtures return the same initialization result."""
        # foundry_status is the raw result
        # require_foundry skips if not connected
        assert foundry_status == require_foundry


class TestConfigurationValues:
    """Test that configuration values are set correctly."""

    def test_backend_url_is_localhost(self):
        """Backend URL defaults to localhost:8000."""
        assert "localhost:8000" in BACKEND_URL or "127.0.0.1:8000" in BACKEND_URL

    def test_foundry_url_is_localhost(self):
        """Foundry URL defaults to localhost:30000."""
        assert "localhost:30000" in FOUNDRY_URL or "127.0.0.1:30000" in FOUNDRY_URL
