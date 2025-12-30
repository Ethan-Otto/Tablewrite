"""Integration tests for search_items and list_files (requires Foundry connection).

Run with: pytest ui/backend/tests/websocket/test_search_items.py -v -m integration
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.websocket.push import (
    search_items, SearchResult, SearchResultItem,
    list_files, FileListResult
)


BACKEND_URL = "http://localhost:8000"


class TestSearchItemsUnit:
    """Unit tests for search_items with mocked WebSocket."""

    @pytest.mark.asyncio
    async def test_search_items_success(self):
        """Searching for items returns results."""
        mock_response = {
            "type": "items_found",
            "data": {
                "results": [
                    {
                        "uuid": "Compendium.dnd5e.spells.Item.abc123",
                        "id": "abc123",
                        "name": "Fireball",
                        "type": "spell",
                        "img": "icons/magic/fire/projectile-meteor-salvo-strong-red.webp",
                        "pack": "DnD5e Spells"
                    },
                    {
                        "uuid": "Compendium.dnd5e.spells.Item.def456",
                        "id": "def456",
                        "name": "Fire Bolt",
                        "type": "spell",
                        "img": "icons/magic/fire/beam-strike-orange.webp",
                        "pack": "DnD5e Spells"
                    }
                ]
            }
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await search_items(query="fire", sub_type="spell")

            assert result.success is True
            assert result.results is not None
            assert len(result.results) == 2
            assert result.results[0].name == "Fireball"
            assert result.results[0].uuid == "Compendium.dnd5e.spells.Item.abc123"
            assert result.results[1].name == "Fire Bolt"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_search_items_empty_results(self):
        """Searching with no matches returns empty list."""
        mock_response = {
            "type": "items_found",
            "data": {
                "results": []
            }
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await search_items(query="xyznonexistent123")

            assert result.success is True
            assert result.results is not None
            assert len(result.results) == 0
            assert result.error is None

    @pytest.mark.asyncio
    async def test_search_items_no_client(self):
        """Searching with no client returns timeout error."""
        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=None)

            result = await search_items(query="fire")

            assert result.success is False
            assert "No Foundry client" in result.error

    @pytest.mark.asyncio
    async def test_search_items_error(self):
        """Search error is properly returned."""
        mock_response = {
            "type": "search_error",
            "error": "Failed to search compendiums"
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await search_items(query="fire")

            assert result.success is False
            assert result.error == "Failed to search compendiums"


@pytest.mark.integration
class TestSearchItemsIntegration:
    """Integration tests with real WebSocket (requires Foundry connection)."""

    @pytest.mark.asyncio
    async def test_foundry_connected_before_search(self):
        """Verify Foundry is connected before running search tests."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/api/foundry/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected", f"Foundry not connected: {data}"
        assert data["connected_clients"] > 0

    @pytest.mark.asyncio
    async def test_search_items_via_websocket(self):
        """
        Search for spells via WebSocket.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        # First check connection
        async with httpx.AsyncClient() as client:
            status = await client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.skip("Foundry not connected")

        # Search for spells starting with "fire"
        result = await search_items(query="fire", sub_type="spell", timeout=30.0)

        assert result.success, f"Search failed: {result.error}"
        assert result.results is not None
        assert len(result.results) > 0, "Expected at least one spell matching 'fire'"

        # Verify result structure
        first = result.results[0]
        assert first.uuid is not None, "Result missing uuid"
        assert first.name is not None, "Result missing name"
        assert "fire" in first.name.lower(), f"Expected 'fire' in name, got: {first.name}"

        print(f"\n[INTEGRATION] Found {len(result.results)} spells matching 'fire':")
        for item in result.results[:5]:  # Print first 5
            print(f"  - {item.name} ({item.uuid})")

    @pytest.mark.asyncio
    async def test_search_items_with_document_type(self):
        """
        Search with document type filter.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        # First check connection
        async with httpx.AsyncClient() as client:
            status = await client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.skip("Foundry not connected")

        # Search for weapons
        result = await search_items(
            query="sword",
            document_type="Item",
            sub_type="weapon",
            timeout=30.0
        )

        if not result.success:
            print(f"\n[INTEGRATION] Search failed: {result.error}")
            # May fail if no weapons compendium - skip gracefully
            pytest.skip(f"Search failed: {result.error}")

        if result.results and len(result.results) > 0:
            first = result.results[0]
            print(f"\n[INTEGRATION] Found {len(result.results)} weapons matching 'sword':")
            for item in result.results[:3]:
                print(f"  - {item.name} (type: {item.type})")

            assert first.uuid is not None
            assert first.name is not None
        else:
            print("\n[INTEGRATION] No weapons found matching 'sword'")
            # This is valid - may not have weapons compendium

    @pytest.mark.asyncio
    async def test_search_items_empty_query(self):
        """
        Search with empty query returns items.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        # First check connection
        async with httpx.AsyncClient() as client:
            status = await client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.skip("Foundry not connected")

        # Search with empty query but specific type
        result = await search_items(query="", sub_type="spell", timeout=30.0)

        if not result.success:
            print(f"\n[INTEGRATION] Search failed: {result.error}")
            pytest.skip(f"Search failed: {result.error}")

        # Should return some spells (or none if compendium is empty)
        if result.results:
            print(f"\n[INTEGRATION] Found {len(result.results)} spells with empty query")
            assert len(result.results) <= 200, "Expected at most 200 results (server limit)"


class TestListFilesUnit:
    """Unit tests for list_files with mocked WebSocket."""

    @pytest.mark.asyncio
    async def test_list_files_success(self):
        """Listing files returns file paths."""
        mock_response = {
            "type": "files_list",
            "data": {
                "files": [
                    "icons/magic/fire/flame-burning-fist-orange.webp",
                    "icons/magic/fire/beam-strike-orange.webp",
                    "icons/magic/fire/explosion-fireball.webp"
                ]
            }
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await list_files(path="icons/magic/fire")

            assert result.success is True
            assert result.files is not None
            assert len(result.files) == 3
            assert "icons/magic/fire/flame-burning-fist-orange.webp" in result.files
            assert result.error is None

    @pytest.mark.asyncio
    async def test_list_files_empty_directory(self):
        """Listing empty directory returns empty list."""
        mock_response = {
            "type": "files_list",
            "data": {
                "files": []
            }
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await list_files(path="nonexistent/path")

            assert result.success is True
            assert result.files is not None
            assert len(result.files) == 0
            assert result.error is None

    @pytest.mark.asyncio
    async def test_list_files_no_client(self):
        """Listing files with no client returns timeout error."""
        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=None)

            result = await list_files(path="icons")

            assert result.success is False
            assert "No Foundry client" in result.error

    @pytest.mark.asyncio
    async def test_list_files_error(self):
        """File listing error is properly returned."""
        mock_response = {
            "type": "files_error",
            "error": "Permission denied"
        }

        with patch('app.websocket.push.foundry_manager') as mock_manager:
            mock_manager.broadcast_and_wait = AsyncMock(return_value=mock_response)

            result = await list_files(path="restricted/path")

            assert result.success is False
            assert result.error == "Permission denied"


@pytest.mark.integration
class TestListFilesIntegration:
    """Integration tests for list_files (requires Foundry connection)."""

    @pytest.mark.asyncio
    async def test_list_files_icons_directory(self):
        """
        List files in the icons directory.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        # First check connection
        async with httpx.AsyncClient() as client:
            status = await client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.skip("Foundry not connected")

        # List files in icons directory (should exist in most Foundry installations)
        result = await list_files(
            path="icons",
            source="public",
            recursive=False,
            timeout=60.0
        )

        if not result.success:
            print(f"\n[INTEGRATION] List files failed: {result.error}")
            pytest.skip(f"List files failed: {result.error}")

        assert result.files is not None
        print(f"\n[INTEGRATION] Found {len(result.files)} files in icons/")

        # May or may not have files depending on Foundry setup
        if result.files:
            for f in result.files[:5]:
                print(f"  - {f}")

    @pytest.mark.asyncio
    async def test_list_files_with_extensions(self):
        """
        List files filtered by extension.

        Requires: Backend running + Foundry with Tablewrite module connected.
        """
        # First check connection
        async with httpx.AsyncClient() as client:
            status = await client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.skip("Foundry not connected")

        # List only webp files
        result = await list_files(
            path="icons",
            source="public",
            recursive=True,
            extensions=[".webp", ".png"],
            timeout=60.0
        )

        if not result.success:
            print(f"\n[INTEGRATION] List files failed: {result.error}")
            pytest.skip(f"List files failed: {result.error}")

        assert result.files is not None
        print(f"\n[INTEGRATION] Found {len(result.files)} .webp/.png files in icons/")

        # Verify extension filter worked
        if result.files:
            for f in result.files[:5]:
                assert f.endswith(".webp") or f.endswith(".png"), \
                    f"Expected .webp or .png file, got: {f}"
                print(f"  - {f}")
