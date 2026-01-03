"""Tests for SceneCreatorTool using public API."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
class TestSceneCreatorTool:
    """Unit tests for SceneCreatorTool."""

    @pytest.mark.asyncio
    async def test_scene_creator_schema(self):
        """Tool schema has correct name and required parameters."""
        from app.tools.scene_creator import SceneCreatorTool

        tool = SceneCreatorTool()
        schema = tool.get_schema()

        assert schema.name == "create_scene"
        assert "image_path" in schema.parameters["properties"]
        assert "image_path" in schema.parameters["required"]
        assert "name" in schema.parameters["properties"]
        assert "skip_walls" in schema.parameters["properties"]
        assert "grid_size" in schema.parameters["properties"]

    @pytest.mark.asyncio
    async def test_scene_creator_name(self):
        """Tool name property matches schema name."""
        from app.tools.scene_creator import SceneCreatorTool

        tool = SceneCreatorTool()
        assert tool.name == "create_scene"
        assert tool.name == tool.get_schema().name

    @pytest.mark.asyncio
    async def test_scene_creator_execute_success(self):
        """Scene creator returns success response with scene details."""
        from app.tools.scene_creator import SceneCreatorTool

        # Mock the create_scene function from the public API
        mock_result = MagicMock()
        mock_result.uuid = "Scene.abc123"
        mock_result.name = "Castle Ruins"
        mock_result.wall_count = 150
        mock_result.grid_size = 100
        mock_result.output_dir = Path("/tmp/scenes/castle")
        mock_result.foundry_image_path = "worlds/myworld/uploaded-maps/castle.webp"

        with patch('app.tools.scene_creator.create_scene', return_value=mock_result) as mock_create:
            tool = SceneCreatorTool()
            result = await tool.execute(
                image_path="/path/to/castle.png",
                name="Castle Ruins",
                skip_walls=False,
                grid_size=100
            )

            # Verify create_scene was called with correct parameters
            mock_create.assert_called_once_with(
                image_path="/path/to/castle.png",
                name="Castle Ruins",
                skip_wall_detection=False,
                grid_size=100
            )

            # Verify response format
            assert result.type == "text"
            assert "Castle Ruins" in result.message
            assert "Scene.abc123" in result.message
            assert "150" in result.message  # wall count
            assert result.data["uuid"] == "Scene.abc123"
            assert result.data["name"] == "Castle Ruins"
            assert result.data["wall_count"] == 150

    @pytest.mark.asyncio
    async def test_scene_creator_execute_without_optional_params(self):
        """Scene creator works with only required image_path."""
        from app.tools.scene_creator import SceneCreatorTool

        mock_result = MagicMock()
        mock_result.uuid = "Scene.xyz789"
        mock_result.name = "dungeon_map"
        mock_result.wall_count = 75
        mock_result.grid_size = None  # Gridless
        mock_result.output_dir = Path("/tmp/scenes/dungeon")
        mock_result.foundry_image_path = "worlds/myworld/uploaded-maps/dungeon.webp"

        with patch('app.tools.scene_creator.create_scene', return_value=mock_result) as mock_create:
            tool = SceneCreatorTool()
            result = await tool.execute(
                image_path="/path/to/dungeon.png"
            )

            # Verify defaults are passed correctly
            mock_create.assert_called_once_with(
                image_path="/path/to/dungeon.png",
                name=None,
                skip_wall_detection=False,
                grid_size=None
            )

            assert result.type == "text"
            assert result.data["uuid"] == "Scene.xyz789"

    @pytest.mark.asyncio
    async def test_scene_creator_execute_skip_walls(self):
        """Scene creator can skip wall detection."""
        from app.tools.scene_creator import SceneCreatorTool

        mock_result = MagicMock()
        mock_result.uuid = "Scene.nowalls"
        mock_result.name = "Simple Map"
        mock_result.wall_count = 0
        mock_result.grid_size = 50
        mock_result.output_dir = Path("/tmp/scenes/simple")
        mock_result.foundry_image_path = "worlds/myworld/uploaded-maps/simple.webp"

        with patch('app.tools.scene_creator.create_scene', return_value=mock_result) as mock_create:
            tool = SceneCreatorTool()
            result = await tool.execute(
                image_path="/path/to/simple.png",
                skip_walls=True,
                grid_size=50
            )

            mock_create.assert_called_once_with(
                image_path="/path/to/simple.png",
                name=None,
                skip_wall_detection=True,
                grid_size=50
            )

            assert result.type == "text"
            assert result.data["wall_count"] == 0

    @pytest.mark.asyncio
    async def test_scene_creator_execute_error(self):
        """Scene creator returns error response on failure."""
        from app.tools.scene_creator import SceneCreatorTool
        from api import APIError

        with patch('app.tools.scene_creator.create_scene', side_effect=APIError("File not found: /bad/path.png")):
            tool = SceneCreatorTool()
            result = await tool.execute(
                image_path="/bad/path.png"
            )

            assert result.type == "error"
            assert "File not found" in result.message
            assert result.data is None

    @pytest.mark.asyncio
    async def test_scene_creator_execute_generic_exception(self):
        """Scene creator handles unexpected exceptions."""
        from app.tools.scene_creator import SceneCreatorTool

        with patch('app.tools.scene_creator.create_scene', side_effect=RuntimeError("Unexpected error")):
            tool = SceneCreatorTool()
            result = await tool.execute(
                image_path="/path/to/map.png"
            )

            assert result.type == "error"
            assert "Unexpected error" in result.message
            assert result.data is None

    @pytest.mark.asyncio
    async def test_scene_creator_runs_in_thread_pool(self):
        """Scene creator runs blocking API call in thread pool."""
        from app.tools.scene_creator import SceneCreatorTool
        import asyncio

        mock_result = MagicMock()
        mock_result.uuid = "Scene.thread123"
        mock_result.name = "Threaded Scene"
        mock_result.wall_count = 50
        mock_result.grid_size = 100
        mock_result.output_dir = Path("/tmp/scenes/thread")
        mock_result.foundry_image_path = "worlds/myworld/uploaded-maps/thread.webp"

        # Track if run_in_executor was used
        executor_used = False
        original_run_in_executor = asyncio.get_event_loop().run_in_executor

        async def mock_run_in_executor(executor, func, *args):
            nonlocal executor_used
            executor_used = True
            return func(*args)

        with patch('app.tools.scene_creator.create_scene', return_value=mock_result):
            with patch.object(asyncio.get_event_loop(), 'run_in_executor', side_effect=mock_run_in_executor):
                tool = SceneCreatorTool()
                result = await tool.execute(
                    image_path="/path/to/map.png"
                )

                # The tool should use run_in_executor for the blocking call
                assert executor_used, "Tool should run blocking call in thread pool"
                assert result.type == "text"
