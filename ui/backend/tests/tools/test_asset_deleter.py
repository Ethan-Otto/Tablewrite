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
