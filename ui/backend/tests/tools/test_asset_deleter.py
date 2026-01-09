"""Tests for AssetDeleterTool."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestAssetDeleterToolSchema:
    """Test tool schema validation."""

    def test_tool_has_correct_name(self):
        """Tool name should be 'delete_assets'."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        assert tool.name == "delete_assets"

    def test_schema_has_required_parameters(self):
        """Schema should define entity_type as required."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert schema.name == "delete_assets"
        assert "entity_type" in schema.parameters["properties"]
        assert "entity_type" in schema.parameters["required"]

    def test_schema_entity_type_enum(self):
        """entity_type should be enum with valid values."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        entity_type = schema.parameters["properties"]["entity_type"]
        assert entity_type["enum"] == ["actor", "journal", "scene", "folder", "actor_item"]

    def test_schema_has_search_query_parameter(self):
        """Schema should have search_query parameter."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "search_query" in schema.parameters["properties"]
        assert schema.parameters["properties"]["search_query"]["type"] == "string"

    def test_schema_has_uuid_parameter(self):
        """Schema should have uuid parameter."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "uuid" in schema.parameters["properties"]
        assert schema.parameters["properties"]["uuid"]["type"] == "string"

    def test_schema_has_folder_name_parameter(self):
        """Schema should have folder_name parameter."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "folder_name" in schema.parameters["properties"]
        assert schema.parameters["properties"]["folder_name"]["type"] == "string"

    def test_schema_has_actor_uuid_parameter(self):
        """Schema should have actor_uuid parameter for actor_item deletion."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "actor_uuid" in schema.parameters["properties"]
        assert schema.parameters["properties"]["actor_uuid"]["type"] == "string"

    def test_schema_has_item_names_parameter(self):
        """Schema should have item_names parameter as array."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "item_names" in schema.parameters["properties"]
        item_names = schema.parameters["properties"]["item_names"]
        assert item_names["type"] == "array"
        assert item_names["items"]["type"] == "string"

    def test_schema_has_confirm_bulk_parameter(self):
        """Schema should have confirm_bulk boolean parameter."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "confirm_bulk" in schema.parameters["properties"]
        assert schema.parameters["properties"]["confirm_bulk"]["type"] == "boolean"

    def test_schema_description_mentions_safety_constraint(self):
        """Schema description should mention Tablewrite folder safety constraint."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        schema = tool.get_schema()

        assert "Tablewrite" in schema.description
        assert "safety" in schema.description.lower()


class TestAssetDeleterToolExecute:
    """Test tool execute method (placeholder for now)."""

    @pytest.mark.asyncio
    async def test_execute_returns_not_implemented(self):
        """Execute should return error for now (not implemented yet)."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()
        result = await tool.execute(entity_type="actor")

        assert result.type == "error"
        assert "Not implemented" in result.message


class TestIsInTablewriteFolderUnit:
    """Unit tests for is_in_tablewrite_folder with mocking."""

    @pytest.mark.asyncio
    async def test_entity_not_found_returns_false(self):
        """If entity cannot be fetched, return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.entity = None

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_result) as mock_fetch:
            result = await is_in_tablewrite_folder("Actor.nonexistent", "actor")
            assert result is False
            mock_fetch.assert_called_once_with("Actor.nonexistent")

    @pytest.mark.asyncio
    async def test_entity_has_no_folder_returns_false(self):
        """If entity has no folder (root level), return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.entity = {"name": "Test Actor", "folder": None}

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_result):
            result = await is_in_tablewrite_folder("Actor.abc123", "actor")
            assert result is False

    @pytest.mark.asyncio
    async def test_entity_in_tablewrite_root_returns_true(self):
        """If entity is directly in Tablewrite folder, return True."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Actor", "folder": "tablewrite_folder_id"}

        # Folder hierarchy: Tablewrite is the direct parent
        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_folder_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            result = await is_in_tablewrite_folder("Actor.abc123", "actor")
            assert result is True

    @pytest.mark.asyncio
    async def test_entity_in_nested_tablewrite_subfolder_returns_true(self):
        """If entity is in a subfolder of Tablewrite, return True."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Actor", "folder": "subfolder_id"}

        # Folder hierarchy: subfolder -> Tablewrite
        mock_tablewrite = MagicMock()
        mock_tablewrite.id = "tablewrite_folder_id"
        mock_tablewrite.name = "Tablewrite"
        mock_tablewrite.parent = None

        mock_subfolder = MagicMock()
        mock_subfolder.id = "subfolder_id"
        mock_subfolder.name = "Lost Mine"
        mock_subfolder.parent = "tablewrite_folder_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.folders = [mock_tablewrite, mock_subfolder]

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            result = await is_in_tablewrite_folder("Actor.abc123", "actor")
            assert result is True

    @pytest.mark.asyncio
    async def test_entity_in_non_tablewrite_folder_returns_false(self):
        """If entity is in a folder that's not Tablewrite or its subfolder, return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Actor", "folder": "other_folder_id"}

        # Folder hierarchy: "Other" is not Tablewrite
        mock_other = MagicMock()
        mock_other.id = "other_folder_id"
        mock_other.name = "Other"
        mock_other.parent = None

        mock_tablewrite = MagicMock()
        mock_tablewrite.id = "tablewrite_folder_id"
        mock_tablewrite.name = "Tablewrite"
        mock_tablewrite.parent = None

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.folders = [mock_other, mock_tablewrite]

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            result = await is_in_tablewrite_folder("Actor.abc123", "actor")
            assert result is False

    @pytest.mark.asyncio
    async def test_scene_entity_type(self):
        """Test is_in_tablewrite_folder works for scenes."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Scene", "folder": "tablewrite_folder_id"}

        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_folder_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.fetch_scene", new_callable=AsyncMock, return_value=mock_fetch_result) as mock_fetch, \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            result = await is_in_tablewrite_folder("Scene.abc123", "scene")
            assert result is True
            mock_fetch.assert_called_once_with("Scene.abc123")

    @pytest.mark.asyncio
    async def test_journal_entity_type(self):
        """Test is_in_tablewrite_folder works for journals."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Journal", "folder": "tablewrite_folder_id"}

        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_folder_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.fetch_journal", new_callable=AsyncMock, return_value=mock_fetch_result) as mock_fetch, \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            result = await is_in_tablewrite_folder("JournalEntry.abc123", "journal")
            assert result is True
            mock_fetch.assert_called_once_with("JournalEntry.abc123")

    @pytest.mark.asyncio
    async def test_invalid_entity_type_returns_false(self):
        """Unknown entity type should return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        result = await is_in_tablewrite_folder("Unknown.abc123", "unknown")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_folders_failure_returns_false(self):
        """If list_folders fails, return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Actor", "folder": "some_folder_id"}

        # But list_folders fails
        mock_list_result = MagicMock()
        mock_list_result.success = False
        mock_list_result.folders = None

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            result = await is_in_tablewrite_folder("Actor.abc123", "actor")
            assert result is False


@pytest.mark.integration
@pytest.mark.asyncio
class TestTablewriteFolderValidation:
    """Integration tests for Tablewrite folder validation using real Foundry."""

    async def test_is_in_tablewrite_folder_with_tablewrite_actor(self, ensure_foundry_connected, test_folders):
        """Actor in Tablewrite folder should return True."""
        from app.tools.asset_deleter import is_in_tablewrite_folder
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create Tablewrite folder
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success, f"Failed to create folder: {folder_result.error}"
        folder_id = folder_result.folder_id

        # Create actor in Tablewrite folder
        actor_result = await push_actor({
            "name": "Test Tablewrite Actor",
            "type": "npc",
            "folder": folder_id
        })
        assert actor_result.success, f"Failed to create actor: {actor_result.error}"
        actor_uuid = actor_result.uuid

        try:
            # Call is_in_tablewrite_folder directly
            result = await is_in_tablewrite_folder(actor_uuid, "actor")
            assert result is True, "Actor in Tablewrite folder should return True"
        finally:
            await delete_actor(actor_uuid)

    async def test_is_in_tablewrite_folder_with_non_tablewrite_actor(self, ensure_foundry_connected, test_folders):
        """Actor outside Tablewrite folder should return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder
        from app.websocket.push import push_actor, delete_actor

        # Create actor without folder (root level)
        actor_result = await push_actor({
            "name": "Test Root Actor",
            "type": "npc"
        })
        assert actor_result.success, f"Failed to create actor: {actor_result.error}"
        actor_uuid = actor_result.uuid

        try:
            # Call is_in_tablewrite_folder directly
            result = await is_in_tablewrite_folder(actor_uuid, "actor")
            assert result is False, "Actor at root level should return False"
        finally:
            await delete_actor(actor_uuid)

    async def test_is_in_tablewrite_folder_with_nested_subfolder(self, ensure_foundry_connected, test_folders):
        """Actor in subfolder of Tablewrite folder should return True."""
        from app.tools.asset_deleter import is_in_tablewrite_folder
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create Tablewrite folder first
        tablewrite_result = await get_or_create_folder("Tablewrite", "Actor")
        assert tablewrite_result.success, f"Failed to create Tablewrite folder: {tablewrite_result.error}"
        tablewrite_id = tablewrite_result.folder_id

        # Create a subfolder inside Tablewrite
        # Note: get_or_create_folder creates folders with parent if we use hierarchical naming
        # For nested folders, we need to use HTTP API directly or use the push interface
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            subfolder_response = await client.post(
                "http://localhost:8000/api/foundry/folder",
                json={"name": "Lost Mine Test", "type": "Actor", "parent": tablewrite_id}
            )
            subfolder_data = subfolder_response.json()
            assert subfolder_data.get("success"), f"Failed to create subfolder: {subfolder_data}"
            subfolder_id = subfolder_data.get("folder_id")

        # Create actor in the subfolder
        actor_result = await push_actor({
            "name": "Test Nested Actor",
            "type": "npc",
            "folder": subfolder_id
        })
        assert actor_result.success, f"Failed to create actor: {actor_result.error}"
        actor_uuid = actor_result.uuid

        try:
            # Call is_in_tablewrite_folder directly
            result = await is_in_tablewrite_folder(actor_uuid, "actor")
            assert result is True, "Actor in Tablewrite subfolder should return True"
        finally:
            await delete_actor(actor_uuid)

    async def test_is_in_tablewrite_folder_with_other_folder(self, ensure_foundry_connected, test_folders):
        """Actor in non-Tablewrite folder should return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create a non-Tablewrite folder
        other_result = await get_or_create_folder("Other Folder", "Actor")
        assert other_result.success, f"Failed to create folder: {other_result.error}"

        # Create actor in the other folder
        actor_result = await push_actor({
            "name": "Test Other Folder Actor",
            "type": "npc",
            "folder": other_result.folder_id
        })
        assert actor_result.success, f"Failed to create actor: {actor_result.error}"
        actor_uuid = actor_result.uuid

        try:
            # Call is_in_tablewrite_folder directly
            result = await is_in_tablewrite_folder(actor_uuid, "actor")
            assert result is False, "Actor in non-Tablewrite folder should return False"
        finally:
            await delete_actor(actor_uuid)

    async def test_is_in_tablewrite_folder_nonexistent_actor(self, ensure_foundry_connected, test_folders):
        """Nonexistent actor should return False."""
        from app.tools.asset_deleter import is_in_tablewrite_folder

        # Use a UUID that doesn't exist
        result = await is_in_tablewrite_folder("Actor.nonexistent123", "actor")
        assert result is False, "Nonexistent actor should return False"
