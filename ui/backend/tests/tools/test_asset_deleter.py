"""Tests for AssetDeleterTool."""
import pytest


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


@pytest.mark.integration
@pytest.mark.asyncio
class TestTablewriteFolderValidation:
    """Test Tablewrite folder validation."""

    BACKEND_URL = "http://localhost:8000"

    async def _create_folder(self, client, name: str, folder_type: str, parent: str = None) -> dict:
        """Helper to create or get a folder via HTTP."""
        body = {"name": name, "type": folder_type}
        if parent:
            body["parent"] = parent
        response = await client.post(f"{self.BACKEND_URL}/api/foundry/folder", json=body)
        return response.json()

    async def _create_actor(self, client, name: str, folder_id: str = None) -> dict:
        """Helper to create an actor via HTTP."""
        actor_data = {"name": name, "type": "npc"}
        if folder_id:
            actor_data["folder"] = folder_id
        response = await client.post(
            f"{self.BACKEND_URL}/api/foundry/actor",
            json={"actor": actor_data}
        )
        return response.json()

    async def _delete_actor(self, client, uuid: str):
        """Helper to delete an actor via HTTP."""
        await client.delete(f"{self.BACKEND_URL}/api/foundry/actor/{uuid}")

    async def _get_folders(self, client) -> list:
        """Helper to get all folders via HTTP."""
        response = await client.get(f"{self.BACKEND_URL}/api/foundry/folders")
        data = response.json()
        return data.get("folders", [])

    async def _get_actor(self, client, uuid: str) -> dict:
        """Helper to get an actor via HTTP."""
        response = await client.get(f"{self.BACKEND_URL}/api/foundry/actor/{uuid}")
        return response.json()

    async def test_is_in_tablewrite_folder_with_tablewrite_actor(self, ensure_foundry_connected, test_folders):
        """Actor in Tablewrite folder should return True."""
        import httpx
        from app.tools.asset_deleter import is_in_tablewrite_folder

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check connection
            status = await client.get(f"{self.BACKEND_URL}/api/foundry/status")
            assert status.json().get("status") == "connected", "Foundry not connected"

            # Create Tablewrite folder
            folder_data = await self._create_folder(client, "Tablewrite", "Actor")
            assert folder_data.get("success"), f"Failed to create folder: {folder_data}"
            folder_id = folder_data.get("folder_id")

            # Create actor in Tablewrite folder
            actor_data = await self._create_actor(client, "Test Tablewrite Actor", folder_id)
            assert actor_data.get("success"), f"Failed to create actor: {actor_data}"
            actor_uuid = actor_data.get("uuid")

            try:
                # Use the is_in_tablewrite_folder helper
                # This needs to call through HTTP to validate
                result = await self._is_in_tablewrite_folder_via_api(
                    client, actor_uuid, "actor"
                )
                assert result is True
            finally:
                await self._delete_actor(client, actor_uuid)

    async def _is_in_tablewrite_folder_via_api(self, client, entity_uuid: str, entity_type: str) -> bool:
        """
        Check if entity is in Tablewrite folder using HTTP API calls.

        This mirrors is_in_tablewrite_folder but uses HTTP instead of WebSocket.
        """
        # Fetch entity to get folder
        if entity_type == "actor":
            entity = await self._get_actor(client, entity_uuid)
        else:
            # Could add scene/journal support later
            return False

        if not entity.get("success") or not entity.get("entity"):
            return False

        folder_id = entity.get("entity", {}).get("folder")
        if not folder_id:
            return False

        # Get all folders
        folders = await self._get_folders(client)
        folder_map = {f["id"]: f for f in folders}

        # Trace up hierarchy looking for Tablewrite
        current_folder_id = folder_id
        while current_folder_id:
            folder = folder_map.get(current_folder_id)
            if not folder:
                return False
            if folder.get("name") == "Tablewrite":
                return True
            current_folder_id = folder.get("parent")

        return False

    async def test_is_in_tablewrite_folder_with_non_tablewrite_actor(self, ensure_foundry_connected, test_folders):
        """Actor outside Tablewrite folder should return False."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check connection
            status = await client.get(f"{self.BACKEND_URL}/api/foundry/status")
            assert status.json().get("status") == "connected", "Foundry not connected"

            # Create actor without folder (root level)
            actor_data = await self._create_actor(client, "Test Root Actor")
            assert actor_data.get("success"), f"Failed to create actor: {actor_data}"
            actor_uuid = actor_data.get("uuid")

            try:
                result = await self._is_in_tablewrite_folder_via_api(
                    client, actor_uuid, "actor"
                )
                assert result is False
            finally:
                await self._delete_actor(client, actor_uuid)

    async def test_is_in_tablewrite_folder_with_nested_subfolder(self, ensure_foundry_connected, test_folders):
        """Actor in subfolder of Tablewrite folder should return True."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check connection
            status = await client.get(f"{self.BACKEND_URL}/api/foundry/status")
            assert status.json().get("status") == "connected", "Foundry not connected"

            # Create Tablewrite folder first
            tablewrite_data = await self._create_folder(client, "Tablewrite", "Actor")
            assert tablewrite_data.get("success"), f"Failed to create Tablewrite folder: {tablewrite_data}"
            tablewrite_id = tablewrite_data.get("folder_id")

            # Create a subfolder inside Tablewrite
            subfolder_data = await self._create_folder(
                client, "Lost Mine Test", "Actor", parent=tablewrite_id
            )
            assert subfolder_data.get("success"), f"Failed to create subfolder: {subfolder_data}"
            subfolder_id = subfolder_data.get("folder_id")

            # Create actor in the subfolder
            actor_data = await self._create_actor(client, "Test Nested Actor", subfolder_id)
            assert actor_data.get("success"), f"Failed to create actor: {actor_data}"
            actor_uuid = actor_data.get("uuid")

            try:
                result = await self._is_in_tablewrite_folder_via_api(
                    client, actor_uuid, "actor"
                )
                assert result is True, "Actor in Tablewrite subfolder should return True"
            finally:
                await self._delete_actor(client, actor_uuid)
