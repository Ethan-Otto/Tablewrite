"""Tests for FoundryVTT API client."""

import pytest
import os
from src.foundry.client import FoundryClient


class TestFoundryClientInit:
    """Tests for FoundryClient initialization."""

    def test_client_initialization_with_env_vars(self, monkeypatch):
        """Test client initializes with environment variables."""
        monkeypatch.setenv("FOUNDRY_LOCAL_URL", "http://localhost:30000")
        monkeypatch.setenv("FOUNDRY_LOCAL_API_KEY", "test-api-key")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="local")

        assert client.foundry_url == "http://localhost:30000"
        assert client.api_key == "test-api-key"
        assert client.relay_url == "https://relay.example.com"

    def test_client_initialization_forge(self, monkeypatch):
        """Test client initializes with forge environment."""
        monkeypatch.setenv("FOUNDRY_FORGE_URL", "https://game.forge-vtt.com")
        monkeypatch.setenv("FOUNDRY_FORGE_API_KEY", "forge-api-key")
        monkeypatch.setenv("FOUNDRY_RELAY_URL", "https://relay.example.com")

        client = FoundryClient(target="forge")

        assert client.foundry_url == "https://game.forge-vtt.com"
        assert client.api_key == "forge-api-key"

    def test_client_raises_on_missing_env_vars(self, monkeypatch):
        """Test client raises ValueError when required env vars missing."""
        # Clear all relevant env vars
        monkeypatch.delenv("FOUNDRY_LOCAL_URL", raising=False)
        monkeypatch.delenv("FOUNDRY_LOCAL_API_KEY", raising=False)
        monkeypatch.delenv("FOUNDRY_RELAY_URL", raising=False)

        with pytest.raises(ValueError, match="FOUNDRY_RELAY_URL not set"):
            FoundryClient(target="local")
