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
    """Test tool execute method with mocking."""

    @pytest.mark.asyncio
    async def test_single_entity_deletion_returns_success(self):
        """Single entity found should delete immediately and return success."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        # Mock find_entities to return a single match
        mock_entity = EntityMatch(
            uuid="Actor.abc123",
            name="Test Goblin",
            entity_type="actor",
            folder_id="tablewrite_folder"
        )

        # Mock delete_actor to succeed
        mock_delete_result = MagicMock()
        mock_delete_result.success = True

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[mock_entity]), \
             patch("app.tools.asset_deleter.delete_actor", new_callable=AsyncMock, return_value=mock_delete_result):
            result = await tool.execute(entity_type="actor", search_query="goblin")

            assert result.type == "text"
            assert "Deleted" in result.message
            assert "Test Goblin" in result.message
            assert result.data["deleted"][0]["uuid"] == "Actor.abc123"

    @pytest.mark.asyncio
    async def test_bulk_deletion_without_confirm_returns_confirmation_required(self):
        """Multiple entities found without confirm_bulk should return confirmation_required."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        # Mock find_entities to return multiple matches
        mock_entities = [
            EntityMatch(uuid="Actor.1", name="Goblin 1", entity_type="actor", folder_id="tw"),
            EntityMatch(uuid="Actor.2", name="Goblin 2", entity_type="actor", folder_id="tw"),
            EntityMatch(uuid="Actor.3", name="Goblin 3", entity_type="actor", folder_id="tw"),
        ]

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=mock_entities):
            result = await tool.execute(entity_type="actor", search_query="goblin", confirm_bulk=False)

            assert result.type == "confirmation_required"
            assert "3" in result.message
            assert result.data["pending_deletion"]["count"] == 3
            assert len(result.data["pending_deletion"]["entities"]) == 3

    @pytest.mark.asyncio
    async def test_bulk_deletion_with_confirm_deletes_all(self):
        """Multiple entities found with confirm_bulk=True should delete all."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        # Mock find_entities to return multiple matches
        mock_entities = [
            EntityMatch(uuid="Actor.1", name="Goblin 1", entity_type="actor", folder_id="tw"),
            EntityMatch(uuid="Actor.2", name="Goblin 2", entity_type="actor", folder_id="tw"),
        ]

        # Mock delete_actor to succeed
        mock_delete_result = MagicMock()
        mock_delete_result.success = True

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=mock_entities), \
             patch("app.tools.asset_deleter.delete_actor", new_callable=AsyncMock, return_value=mock_delete_result):
            result = await tool.execute(entity_type="actor", search_query="goblin", confirm_bulk=True)

            assert result.type == "text"
            assert "Deleted 2" in result.message
            assert len(result.data["deleted"]) == 2

    @pytest.mark.asyncio
    async def test_no_matches_returns_appropriate_message(self):
        """No entities found should return appropriate message."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[]):
            result = await tool.execute(entity_type="actor", search_query="nonexistent")

            assert result.type == "text"
            assert "No actor" in result.message
            assert "nonexistent" in result.message
            assert "Tablewrite" in result.message

    @pytest.mark.asyncio
    async def test_actor_item_uses_remove_actor_items(self):
        """actor_item entity_type should use remove_actor_items."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        # Mock is_in_tablewrite_folder to return True
        mock_remove_result = MagicMock()
        mock_remove_result.success = True
        mock_remove_result.items_removed = 2
        mock_remove_result.removed_names = ["Longsword", "Shield"]

        with patch("app.tools.asset_deleter.is_in_tablewrite_folder", new_callable=AsyncMock, return_value=True), \
             patch("app.tools.asset_deleter.remove_actor_items", new_callable=AsyncMock, return_value=mock_remove_result) as mock_remove:
            result = await tool.execute(
                entity_type="actor_item",
                actor_uuid="Actor.abc123",
                item_names=["sword", "shield"]
            )

            mock_remove.assert_called_once_with("Actor.abc123", ["sword", "shield"])
            assert result.type == "text"
            assert "Removed 2" in result.message
            assert "Longsword" in result.message

    @pytest.mark.asyncio
    async def test_invalid_entity_type_returns_error(self):
        """Invalid entity_type should return error."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        # find_entities returns empty for invalid types
        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[]):
            result = await tool.execute(entity_type="invalid_type", search_query="test")

            assert result.type == "text"
            assert "No invalid_type" in result.message

    @pytest.mark.asyncio
    async def test_actor_item_without_actor_uuid_returns_error(self):
        """actor_item deletion without actor_uuid should return error."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        result = await tool.execute(entity_type="actor_item", item_names=["sword"])

        assert result.type == "error"
        assert "actor_uuid" in result.message

    @pytest.mark.asyncio
    async def test_actor_item_without_item_names_returns_error(self):
        """actor_item deletion without item_names should return error."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        result = await tool.execute(entity_type="actor_item", actor_uuid="Actor.abc123")

        assert result.type == "error"
        assert "item_names" in result.message

    @pytest.mark.asyncio
    async def test_actor_item_outside_tablewrite_returns_error(self):
        """actor_item deletion for actor outside Tablewrite should return error."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        with patch("app.tools.asset_deleter.is_in_tablewrite_folder", new_callable=AsyncMock, return_value=False):
            result = await tool.execute(
                entity_type="actor_item",
                actor_uuid="Actor.abc123",
                item_names=["sword"]
            )

            assert result.type == "error"
            assert "Tablewrite" in result.message

    @pytest.mark.asyncio
    async def test_delete_scene_uses_delete_scene(self):
        """scene entity_type should use delete_scene."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        mock_entity = EntityMatch(
            uuid="Scene.xyz789",
            name="Test Cave",
            entity_type="scene",
            folder_id="tablewrite_folder"
        )

        mock_delete_result = MagicMock()
        mock_delete_result.success = True

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[mock_entity]), \
             patch("app.tools.asset_deleter.delete_scene", new_callable=AsyncMock, return_value=mock_delete_result) as mock_delete:
            result = await tool.execute(entity_type="scene", search_query="cave")

            mock_delete.assert_called_once_with("Scene.xyz789")
            assert result.type == "text"
            assert "Deleted" in result.message
            assert "Test Cave" in result.message

    @pytest.mark.asyncio
    async def test_delete_journal_uses_delete_journal(self):
        """journal entity_type should use delete_journal."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        mock_entity = EntityMatch(
            uuid="JournalEntry.jnl123",
            name="Chapter 1",
            entity_type="journal",
            folder_id="tablewrite_folder"
        )

        mock_delete_result = MagicMock()
        mock_delete_result.success = True

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[mock_entity]), \
             patch("app.tools.asset_deleter.delete_journal", new_callable=AsyncMock, return_value=mock_delete_result) as mock_delete:
            result = await tool.execute(entity_type="journal", search_query="chapter")

            mock_delete.assert_called_once_with("JournalEntry.jnl123")
            assert result.type == "text"
            assert "Deleted" in result.message
            assert "Chapter 1" in result.message

    @pytest.mark.asyncio
    async def test_delete_folder_uses_delete_folder(self):
        """folder entity_type should use delete_folder."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        mock_entity = EntityMatch(
            uuid="Folder.fld456",
            name="Lost Mine",
            entity_type="folder",
            folder_id="tablewrite_id"
        )

        mock_delete_result = MagicMock()
        mock_delete_result.success = True

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[mock_entity]), \
             patch("app.tools.asset_deleter.delete_folder", new_callable=AsyncMock, return_value=mock_delete_result) as mock_delete:
            result = await tool.execute(entity_type="folder", search_query="lost mine")

            # delete_folder takes folder_id, not uuid, but the EntityMatch uuid is the folder_id here
            mock_delete.assert_called_once_with("Folder.fld456", delete_contents=True)
            assert result.type == "text"
            assert "Deleted" in result.message
            assert "Lost Mine" in result.message

    @pytest.mark.asyncio
    async def test_delete_failure_returns_error(self):
        """Failed deletion should return error."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        mock_entity = EntityMatch(
            uuid="Actor.abc123",
            name="Test Goblin",
            entity_type="actor",
            folder_id="tablewrite_folder"
        )

        mock_delete_result = MagicMock()
        mock_delete_result.success = False

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=[mock_entity]), \
             patch("app.tools.asset_deleter.delete_actor", new_callable=AsyncMock, return_value=mock_delete_result):
            result = await tool.execute(entity_type="actor", search_query="goblin")

            assert result.type == "error"
            assert "Failed" in result.message

    @pytest.mark.asyncio
    async def test_remove_actor_items_no_matches_returns_message(self):
        """remove_actor_items with no matches should return appropriate message."""
        from app.tools.asset_deleter import AssetDeleterTool

        tool = AssetDeleterTool()

        mock_remove_result = MagicMock()
        mock_remove_result.success = True
        mock_remove_result.items_removed = 0
        mock_remove_result.removed_names = []

        with patch("app.tools.asset_deleter.is_in_tablewrite_folder", new_callable=AsyncMock, return_value=True), \
             patch("app.tools.asset_deleter.remove_actor_items", new_callable=AsyncMock, return_value=mock_remove_result):
            result = await tool.execute(
                entity_type="actor_item",
                actor_uuid="Actor.abc123",
                item_names=["nonexistent"]
            )

            assert result.type == "text"
            assert "No items matching" in result.message

    @pytest.mark.asyncio
    async def test_bulk_deletion_shows_max_10_names(self):
        """Bulk confirmation should show max 10 names with '... and N more'."""
        from app.tools.asset_deleter import AssetDeleterTool, EntityMatch

        tool = AssetDeleterTool()

        # Create 15 mock entities
        mock_entities = [
            EntityMatch(uuid=f"Actor.{i}", name=f"Goblin {i}", entity_type="actor", folder_id="tw")
            for i in range(15)
        ]

        with patch("app.tools.asset_deleter.find_entities", new_callable=AsyncMock, return_value=mock_entities):
            result = await tool.execute(entity_type="actor", search_query="goblin", confirm_bulk=False)

            assert result.type == "confirmation_required"
            assert "15" in result.message
            assert "... and 5 more" in result.message


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


class TestFindEntitiesUnit:
    """Unit tests for find_entities with mocking."""

    @pytest.mark.asyncio
    async def test_find_by_uuid_returns_single_entity(self):
        """If UUID is provided, return single entity if in Tablewrite."""
        from app.tools.asset_deleter import find_entities, EntityMatch

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Actor", "folder": "tablewrite_id"}

        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_list_result):
            entities = await find_entities("actor", uuid="Actor.abc123")

            assert len(entities) == 1
            assert entities[0].uuid == "Actor.abc123"
            assert entities[0].name == "Test Actor"
            assert entities[0].entity_type == "actor"

    @pytest.mark.asyncio
    async def test_find_by_uuid_not_in_tablewrite_returns_empty(self):
        """If UUID entity is not in Tablewrite, return empty list."""
        from app.tools.asset_deleter import find_entities

        mock_fetch_result = MagicMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {"name": "Test Actor", "folder": None}

        with patch("app.tools.asset_deleter.fetch_actor", new_callable=AsyncMock, return_value=mock_fetch_result):
            entities = await find_entities("actor", uuid="Actor.abc123")
            assert entities == []

    @pytest.mark.asyncio
    async def test_search_by_name_returns_partial_matches(self):
        """Search by name returns case-insensitive partial matches."""
        from app.tools.asset_deleter import find_entities

        # Mock list_actors
        mock_actor1 = MagicMock()
        mock_actor1.uuid = "Actor.1"
        mock_actor1.name = "Test Goblin Scout"
        mock_actor1.folder = "tablewrite_id"

        mock_actor2 = MagicMock()
        mock_actor2.uuid = "Actor.2"
        mock_actor2.name = "Orc Warrior"
        mock_actor2.folder = "tablewrite_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.actors = [mock_actor1, mock_actor2]

        # Mock list_folders
        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_folders_result = MagicMock()
        mock_folders_result.success = True
        mock_folders_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.list_actors", new_callable=AsyncMock, return_value=mock_list_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_folders_result):
            entities = await find_entities("actor", search_query="goblin")

            assert len(entities) == 1
            assert entities[0].name == "Test Goblin Scout"

    @pytest.mark.asyncio
    async def test_search_with_wildcard_returns_all(self):
        """Search with '*' returns all entities in Tablewrite."""
        from app.tools.asset_deleter import find_entities

        # Mock list_actors
        mock_actor1 = MagicMock()
        mock_actor1.uuid = "Actor.1"
        mock_actor1.name = "Goblin"
        mock_actor1.folder = "tablewrite_id"

        mock_actor2 = MagicMock()
        mock_actor2.uuid = "Actor.2"
        mock_actor2.name = "Orc"
        mock_actor2.folder = "tablewrite_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.actors = [mock_actor1, mock_actor2]

        # Mock list_folders
        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_folders_result = MagicMock()
        mock_folders_result.success = True
        mock_folders_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.list_actors", new_callable=AsyncMock, return_value=mock_list_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_folders_result):
            entities = await find_entities("actor", search_query="*")

            assert len(entities) == 2

    @pytest.mark.asyncio
    async def test_search_with_folder_name_filters_to_subfolder(self):
        """Search with folder_name filters to specific Tablewrite subfolder."""
        from app.tools.asset_deleter import find_entities

        # Mock list_actors
        mock_actor1 = MagicMock()
        mock_actor1.uuid = "Actor.1"
        mock_actor1.name = "Lost Mine Goblin"
        mock_actor1.folder = "lostmine_id"

        mock_actor2 = MagicMock()
        mock_actor2.uuid = "Actor.2"
        mock_actor2.name = "Other Module Goblin"
        mock_actor2.folder = "othermodule_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.actors = [mock_actor1, mock_actor2]

        # Mock folders: Tablewrite has two subfolders
        mock_tablewrite = MagicMock()
        mock_tablewrite.id = "tablewrite_id"
        mock_tablewrite.name = "Tablewrite"
        mock_tablewrite.parent = None

        mock_lostmine = MagicMock()
        mock_lostmine.id = "lostmine_id"
        mock_lostmine.name = "Lost Mine"
        mock_lostmine.parent = "tablewrite_id"

        mock_othermodule = MagicMock()
        mock_othermodule.id = "othermodule_id"
        mock_othermodule.name = "Other Module"
        mock_othermodule.parent = "tablewrite_id"

        mock_folders_result = MagicMock()
        mock_folders_result.success = True
        mock_folders_result.folders = [mock_tablewrite, mock_lostmine, mock_othermodule]

        with patch("app.tools.asset_deleter.list_actors", new_callable=AsyncMock, return_value=mock_list_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_folders_result):
            entities = await find_entities("actor", search_query="*", folder_name="Lost Mine")

            assert len(entities) == 1
            assert entities[0].name == "Lost Mine Goblin"

    @pytest.mark.asyncio
    async def test_entities_not_in_tablewrite_are_excluded(self):
        """Entities not in Tablewrite folder hierarchy are excluded."""
        from app.tools.asset_deleter import find_entities

        # Mock list_actors - one in Tablewrite, one not
        mock_actor_tw = MagicMock()
        mock_actor_tw.uuid = "Actor.1"
        mock_actor_tw.name = "Tablewrite Goblin"
        mock_actor_tw.folder = "tablewrite_id"

        mock_actor_other = MagicMock()
        mock_actor_other.uuid = "Actor.2"
        mock_actor_other.name = "Root Goblin"
        mock_actor_other.folder = None

        mock_actor_other_folder = MagicMock()
        mock_actor_other_folder.uuid = "Actor.3"
        mock_actor_other_folder.name = "Other Folder Goblin"
        mock_actor_other_folder.folder = "other_folder_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.actors = [mock_actor_tw, mock_actor_other, mock_actor_other_folder]

        # Mock folders
        mock_tablewrite = MagicMock()
        mock_tablewrite.id = "tablewrite_id"
        mock_tablewrite.name = "Tablewrite"
        mock_tablewrite.parent = None

        mock_other_folder = MagicMock()
        mock_other_folder.id = "other_folder_id"
        mock_other_folder.name = "Other Folder"
        mock_other_folder.parent = None

        mock_folders_result = MagicMock()
        mock_folders_result.success = True
        mock_folders_result.folders = [mock_tablewrite, mock_other_folder]

        with patch("app.tools.asset_deleter.list_actors", new_callable=AsyncMock, return_value=mock_list_result), \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_folders_result):
            entities = await find_entities("actor", search_query="goblin")

            # Only the one in Tablewrite should be returned
            assert len(entities) == 1
            assert entities[0].name == "Tablewrite Goblin"

    @pytest.mark.asyncio
    async def test_invalid_entity_type_returns_empty(self):
        """Invalid entity type returns empty list."""
        from app.tools.asset_deleter import find_entities

        entities = await find_entities("invalid_type", search_query="test")
        assert entities == []

    @pytest.mark.asyncio
    async def test_find_scenes_uses_list_scenes(self):
        """find_entities for scenes uses list_scenes."""
        from app.tools.asset_deleter import find_entities

        mock_scene = MagicMock()
        mock_scene.uuid = "Scene.1"
        mock_scene.name = "Test Scene"
        mock_scene.folder = "tablewrite_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.scenes = [mock_scene]

        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_folders_result = MagicMock()
        mock_folders_result.success = True
        mock_folders_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.list_scenes", new_callable=AsyncMock, return_value=mock_list_result) as mock_list, \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_folders_result):
            entities = await find_entities("scene", search_query="test")

            mock_list.assert_called_once()
            assert len(entities) == 1
            assert entities[0].entity_type == "scene"

    @pytest.mark.asyncio
    async def test_find_journals_uses_list_journals(self):
        """find_entities for journals uses list_journals."""
        from app.tools.asset_deleter import find_entities

        mock_journal = MagicMock()
        mock_journal.uuid = "JournalEntry.1"
        mock_journal.name = "Test Journal"
        mock_journal.folder = "tablewrite_id"

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.journals = [mock_journal]

        mock_folder = MagicMock()
        mock_folder.id = "tablewrite_id"
        mock_folder.name = "Tablewrite"
        mock_folder.parent = None

        mock_folders_result = MagicMock()
        mock_folders_result.success = True
        mock_folders_result.folders = [mock_folder]

        with patch("app.tools.asset_deleter.list_journals", new_callable=AsyncMock, return_value=mock_list_result) as mock_list, \
             patch("app.tools.asset_deleter.list_folders", new_callable=AsyncMock, return_value=mock_folders_result):
            entities = await find_entities("journal", search_query="test")

            mock_list.assert_called_once()
            assert len(entities) == 1
            assert entities[0].entity_type == "journal"


@pytest.mark.integration
@pytest.mark.asyncio
class TestFindEntitiesIntegration:
    """Integration tests for find_entities with real Foundry data."""

    async def test_find_actors_by_partial_name(self, ensure_foundry_connected, test_folders):
        """Should find actors by partial name match in Tablewrite folder."""
        from app.tools.asset_deleter import find_entities
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create test actor in Tablewrite
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success, f"Failed to create folder: {folder_result.error}"

        actor_result = await push_actor({
            "name": "Test Goblin Scout FindEntities",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert actor_result.success, f"Failed to create actor: {actor_result.error}"

        try:
            entities = await find_entities("actor", search_query="goblin scout findentities")
            assert len(entities) >= 1
            assert any(e.name == "Test Goblin Scout FindEntities" for e in entities)
        finally:
            await delete_actor(actor_result.uuid)

    async def test_find_entities_filters_to_tablewrite(self, ensure_foundry_connected, test_folders):
        """Should only return entities in Tablewrite folders."""
        from app.tools.asset_deleter import find_entities
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create one actor in Tablewrite, one outside
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success

        tablewrite_actor = await push_actor({
            "name": "Tablewrite Test Actor FindEntities",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert tablewrite_actor.success

        root_actor = await push_actor({
            "name": "Root Test Actor FindEntities",
            "type": "npc"
        })
        assert root_actor.success

        try:
            entities = await find_entities("actor", search_query="test actor findentities")
            names = [e.name for e in entities]

            assert "Tablewrite Test Actor FindEntities" in names
            assert "Root Test Actor FindEntities" not in names
        finally:
            await delete_actor(tablewrite_actor.uuid)
            await delete_actor(root_actor.uuid)

    async def test_find_entity_by_uuid(self, ensure_foundry_connected, test_folders):
        """Should find entity by specific UUID."""
        from app.tools.asset_deleter import find_entities
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create test actor in Tablewrite
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success

        actor_result = await push_actor({
            "name": "UUID Test Actor FindEntities",
            "type": "npc",
            "folder": folder_result.folder_id
        })
        assert actor_result.success

        try:
            entities = await find_entities("actor", uuid=actor_result.uuid)
            assert len(entities) == 1
            assert entities[0].uuid == actor_result.uuid
            assert entities[0].name == "UUID Test Actor FindEntities"
        finally:
            await delete_actor(actor_result.uuid)

    async def test_find_all_with_wildcard(self, ensure_foundry_connected, test_folders):
        """Search with '*' should return all entities in Tablewrite."""
        from app.tools.asset_deleter import find_entities
        from app.websocket.push import push_actor, delete_actor, get_or_create_folder

        # Create test actors in Tablewrite
        folder_result = await get_or_create_folder("Tablewrite", "Actor")
        assert folder_result.success

        actors = []
        for i in range(2):
            result = await push_actor({
                "name": f"Wildcard Test Actor {i} FindEntities",
                "type": "npc",
                "folder": folder_result.folder_id
            })
            assert result.success
            actors.append(result.uuid)

        try:
            entities = await find_entities("actor", search_query="*")
            # Should find at least our test actors
            names = [e.name for e in entities]
            assert "Wildcard Test Actor 0 FindEntities" in names
            assert "Wildcard Test Actor 1 FindEntities" in names
        finally:
            for uuid in actors:
                await delete_actor(uuid)
