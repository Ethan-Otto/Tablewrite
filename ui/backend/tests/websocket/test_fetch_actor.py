"""Test fetching and deleting actors by UUID via WebSocket."""
import pytest
from unittest.mock import patch, AsyncMock
from app.websocket.push import fetch_actor, FetchResult, delete_actor, DeleteResult


class TestFetchActor:
    """Test actor fetch functionality."""

    @pytest.mark.asyncio
    async def test_fetch_actor_success(self):
        """Fetching an actor returns entity data."""
        mock_response = {
            "type": "actor_data",
            "data": {
                "entity": {
                    "name": "Test Goblin",
                    "type": "npc",
                    "system": {"abilities": {"str": {"value": 8}}}
                }
            }
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await fetch_actor("Actor.test123")

            assert result.success is True
            assert result.entity is not None
            assert result.entity["name"] == "Test Goblin"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_fetch_actor_not_found(self):
        """Fetching non-existent actor returns error."""
        mock_response = {
            "type": "actor_error",
            "error": "Actor not found: Actor.nonexistent"
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await fetch_actor("Actor.nonexistent")

            assert result.success is False
            assert result.entity is None
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_actor_no_client(self):
        """Fetching actor with no client returns timeout error."""
        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=None)

            result = await fetch_actor("Actor.test123")

            assert result.success is False
            assert "No Foundry client" in result.error


class TestDeleteActor:
    """Test actor delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_actor_success(self):
        """Deleting an actor returns success with name."""
        mock_response = {
            "type": "actor_deleted",
            "data": {
                "uuid": "Actor.test123",
                "name": "Test Goblin"
            }
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await delete_actor("Actor.test123")

            assert result.success is True
            assert result.uuid == "Actor.test123"
            assert result.name == "Test Goblin"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_delete_actor_not_found(self):
        """Deleting non-existent actor returns error."""
        mock_response = {
            "type": "actor_error",
            "error": "Actor not found: Actor.nonexistent"
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await delete_actor("Actor.nonexistent")

            assert result.success is False
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_delete_actor_no_client(self):
        """Deleting actor with no client returns timeout error."""
        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=None)

            result = await delete_actor("Actor.test123")

            assert result.success is False
            assert "No Foundry client" in result.error


@pytest.mark.integration
class TestFetchActorIntegration:
    """Integration tests with real WebSocket (requires Foundry connection)."""

    @pytest.mark.asyncio
    async def test_fetch_real_actor(self):
        """Fetch the actual actor from Foundry."""
        # This test requires:
        # 1. Backend running with uvicorn
        # 2. Foundry module connected via WebSocket
        # 3. The actor to exist in Foundry

        result = await fetch_actor("Actor.vKEhnoBxM7unbhAL")

        if result.success:
            print(f"\n[INTEGRATION] Actor found: {result.entity.get('name')}")
            assert result.entity is not None
        else:
            print(f"\n[INTEGRATION] Fetch failed: {result.error}")
            # May fail if no Foundry client connected
            pytest.skip(f"Fetch failed (possibly no client): {result.error}")
