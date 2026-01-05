"""Tests for batch actor creator tool - parsing natural language into structured actor requests."""
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_parse_actor_requests_extracts_creatures():
    """Test that parse_actor_requests extracts creatures from natural language."""
    from app.tools.batch_actor_creator import parse_actor_requests

    # Mock Gemini response
    mock_response = MagicMock()
    mock_response.text = '''[
        {"description": "a goblin scout", "count": 1},
        {"description": "a bugbear", "count": 2},
        {"description": "a hobgoblin captain", "count": 1}
    ]'''

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("Create a goblin scout, two bugbears, and a hobgoblin captain")

    assert len(result) == 3
    assert result[0]["description"] == "a goblin scout"
    assert result[0]["count"] == 1
    assert result[1]["description"] == "a bugbear"
    assert result[1]["count"] == 2


@pytest.mark.asyncio
async def test_parse_actor_requests_empty_prompt():
    """Test that empty/unclear prompts return empty list."""
    from app.tools.batch_actor_creator import parse_actor_requests

    mock_response = MagicMock()
    mock_response.text = '[]'

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("hello world")

    assert result == []


@pytest.mark.asyncio
async def test_parse_actor_requests_handles_markdown_code_block():
    """Test that parse_actor_requests handles JSON wrapped in markdown code blocks."""
    from app.tools.batch_actor_creator import parse_actor_requests

    # Sometimes Gemini wraps JSON in markdown code blocks
    mock_response = MagicMock()
    mock_response.text = '''```json
[
    {"description": "a dragon", "count": 1}
]
```'''

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("Create a dragon")

    assert len(result) == 1
    assert result[0]["description"] == "a dragon"
    assert result[0]["count"] == 1


@pytest.mark.asyncio
async def test_parse_actor_requests_handles_invalid_json():
    """Test that parse_actor_requests gracefully handles invalid JSON."""
    from app.tools.batch_actor_creator import parse_actor_requests

    mock_response = MagicMock()
    mock_response.text = 'This is not valid JSON at all!'

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("Create a dragon")

    # Should return empty list on parse failure
    assert result == []


@pytest.mark.asyncio
async def test_parse_actor_requests_handles_non_list_json():
    """Test that parse_actor_requests handles JSON that's not a list."""
    from app.tools.batch_actor_creator import parse_actor_requests

    mock_response = MagicMock()
    mock_response.text = '{"description": "a goblin", "count": 1}'  # Object, not array

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("Create a goblin")

    # Should return empty list when not a list
    assert result == []


@pytest.mark.integration
@pytest.mark.slow
class TestParseActorRequestsIntegration:
    """Integration tests with real Gemini API calls."""

    @pytest.mark.asyncio
    async def test_parse_actor_requests_real_api(self):
        """
        Real integration test: Parse actor requests using real Gemini API.

        This test verifies that the function works with the actual Gemini API,
        not just mocked responses.

        Warning: This test costs money (Gemini API calls).
        """
        # FAIL with actionable message per CLAUDE.md - never skip silently
        api_key = os.getenv("GeminiImageAPI") or os.getenv("GEMINI_API_KEY")
        assert api_key, "Gemini API key not configured - set GeminiImageAPI or GEMINI_API_KEY"

        from app.tools.batch_actor_creator import parse_actor_requests

        # Test with a clear request for multiple creatures
        result = await parse_actor_requests(
            "Create a goblin archer, two orc warriors, and a hobgoblin captain"
        )

        # Verify we get multiple creatures
        assert len(result) >= 3, f"Expected at least 3 creatures, got {len(result)}: {result}"

        # Verify each result has required fields
        for item in result:
            assert "description" in item, f"Missing 'description' in {item}"
            assert "count" in item, f"Missing 'count' in {item}"
            assert isinstance(item["count"], int), f"Count should be int: {item}"
            assert item["count"] >= 1, f"Count should be at least 1: {item}"

        # Verify we got the right counts (at least one with count > 1)
        counts = [item["count"] for item in result]
        assert 2 in counts, f"Expected at least one creature with count=2: {result}"

        print(f"[INTEGRATION] Parsed {len(result)} actor requests: {result}")


@pytest.mark.asyncio
async def test_expand_duplicates_generates_unique_names():
    """Test that expand_duplicates generates distinct names for count > 1."""
    from app.tools.batch_actor_creator import expand_duplicates

    requests = [
        {"description": "a bugbear", "count": 2},
        {"description": "a goblin", "count": 1}
    ]

    # Mock Gemini response for name generation
    mock_response = MagicMock()
    mock_response.text = '["Bugbear Brute", "Bugbear Tracker"]'

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await expand_duplicates(requests)

    # Should have 3 actors total (2 bugbears + 1 goblin)
    assert len(result) == 3
    # Bugbears should have unique names
    bugbear_names = [r["description"] for r in result if "bugbear" in r["description"].lower() or "Bugbear" in r["description"]]
    assert len(set(bugbear_names)) == 2  # All unique


@pytest.mark.asyncio
async def test_expand_duplicates_count_one_unchanged():
    """Test that entries with count=1 pass through unchanged."""
    from app.tools.batch_actor_creator import expand_duplicates

    requests = [
        {"description": "a goblin scout", "count": 1},
        {"description": "an orc warrior", "count": 1}
    ]

    # No Gemini call needed for count=1 items
    result = await expand_duplicates(requests)

    assert len(result) == 2
    assert result[0]["description"] == "a goblin scout"
    assert result[0]["count"] == 1
    assert result[1]["description"] == "an orc warrior"
    assert result[1]["count"] == 1


@pytest.mark.asyncio
async def test_expand_duplicates_handles_markdown_code_block():
    """Test that expand_duplicates handles JSON wrapped in markdown code blocks."""
    from app.tools.batch_actor_creator import expand_duplicates

    requests = [{"description": "an orc", "count": 3}]

    mock_response = MagicMock()
    mock_response.text = '''```json
["Orc Berserker", "Orc Shaman", "Orc Scout"]
```'''

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await expand_duplicates(requests)

    assert len(result) == 3
    names = [r["description"] for r in result]
    assert "Orc Berserker" in names
    assert "Orc Shaman" in names
    assert "Orc Scout" in names


@pytest.mark.asyncio
async def test_expand_duplicates_fallback_on_invalid_json():
    """Test that expand_duplicates falls back to numbered names on invalid JSON."""
    from app.tools.batch_actor_creator import expand_duplicates

    requests = [{"description": "a dragon", "count": 2}]

    mock_response = MagicMock()
    mock_response.text = 'Not valid JSON at all!'

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await expand_duplicates(requests)

    # Should fall back to numbered names
    assert len(result) == 2
    assert result[0]["description"] == "a dragon #1"
    assert result[1]["description"] == "a dragon #2"


@pytest.mark.asyncio
async def test_expand_duplicates_empty_list():
    """Test that expand_duplicates handles empty list."""
    from app.tools.batch_actor_creator import expand_duplicates

    result = await expand_duplicates([])

    assert result == []


@pytest.mark.integration
@pytest.mark.slow
class TestExpandDuplicatesIntegration:
    """Integration tests for expand_duplicates with real Gemini API."""

    @pytest.mark.asyncio
    async def test_expand_duplicates_real_api(self):
        """
        Real integration test: Expand duplicates using real Gemini API.

        Warning: This test costs money (Gemini API calls).
        """
        api_key = os.getenv("GeminiImageAPI") or os.getenv("GEMINI_API_KEY")
        assert api_key, "Gemini API key not configured - set GeminiImageAPI or GEMINI_API_KEY"

        from app.tools.batch_actor_creator import expand_duplicates

        requests = [
            {"description": "a bugbear warrior", "count": 3},
            {"description": "a goblin", "count": 1}
        ]

        result = await expand_duplicates(requests)

        # Should have 4 total (3 bugbears + 1 goblin)
        assert len(result) == 4, f"Expected 4 actors, got {len(result)}: {result}"

        # All entries should have count=1
        for item in result:
            assert item["count"] == 1, f"Expected count=1: {item}"

        # The 3 bugbear descriptions should all be unique
        bugbear_descriptions = [r["description"] for r in result[:3]]
        assert len(set(bugbear_descriptions)) == 3, f"Bugbear names not unique: {bugbear_descriptions}"

        print(f"[INTEGRATION] Expanded to {len(result)} unique actors: {[r['description'] for r in result]}")


# ============================================================================
# Task 4: BatchActorCreatorTool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_batch_actor_creator_tool_schema():
    """Test BatchActorCreatorTool has correct schema."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()
    schema = tool.get_schema()

    assert schema.name == "create_actors"
    assert "prompt" in schema.parameters["properties"]
    assert schema.parameters["required"] == ["prompt"]


@pytest.mark.asyncio
async def test_batch_actor_creator_tool_name_property():
    """Test BatchActorCreatorTool name property matches schema."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()
    assert tool.name == "create_actors"
    assert tool.name == tool.get_schema().name


@pytest.mark.asyncio
async def test_batch_actor_creator_executes_parallel():
    """Test that BatchActorCreatorTool creates actors in parallel."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    # Mock all dependencies
    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse, \
         patch('app.tools.batch_actor_creator.expand_duplicates') as mock_expand, \
         patch('app.tools.batch_actor_creator.load_caches') as mock_caches, \
         patch('app.tools.batch_actor_creator.create_single_actor') as mock_create, \
         patch('app.tools.batch_actor_creator.get_or_create_folder') as mock_folder:

        mock_parse.return_value = [{"description": "a goblin", "count": 1}]
        mock_expand.return_value = [{"description": "a goblin", "count": 1}]
        mock_caches.return_value = (MagicMock(), MagicMock())
        mock_create.return_value = {"uuid": "Actor.abc123", "name": "Goblin", "cr": 0.25}
        mock_folder.return_value = MagicMock(success=True, folder_id="folder123")

        response = await tool.execute(prompt="Create a goblin")

    assert response.type == "text"
    assert "Actor.abc123" in response.message or "Goblin" in response.message


@pytest.mark.asyncio
async def test_batch_actor_creator_handles_multiple_actors():
    """Test that BatchActorCreatorTool handles multiple actors correctly."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse, \
         patch('app.tools.batch_actor_creator.expand_duplicates') as mock_expand, \
         patch('app.tools.batch_actor_creator.load_caches') as mock_caches, \
         patch('app.tools.batch_actor_creator.create_single_actor') as mock_create, \
         patch('app.tools.batch_actor_creator.get_or_create_folder') as mock_folder:

        mock_parse.return_value = [
            {"description": "a goblin", "count": 1},
            {"description": "an orc", "count": 1}
        ]
        mock_expand.return_value = [
            {"description": "a goblin", "count": 1},
            {"description": "an orc", "count": 1}
        ]
        mock_caches.return_value = (MagicMock(), MagicMock())
        mock_create.side_effect = [
            {"uuid": "Actor.goblin1", "name": "Goblin", "cr": 0.25},
            {"uuid": "Actor.orc1", "name": "Orc", "cr": 0.5}
        ]
        mock_folder.return_value = MagicMock(success=True, folder_id="folder123")

        response = await tool.execute(prompt="Create a goblin and an orc")

    assert response.type == "text"
    assert "2 of 2" in response.message
    assert "Goblin" in response.message
    assert "Orc" in response.message


@pytest.mark.asyncio
async def test_batch_actor_creator_handles_partial_failure():
    """Test that BatchActorCreatorTool reports partial failures correctly."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse, \
         patch('app.tools.batch_actor_creator.expand_duplicates') as mock_expand, \
         patch('app.tools.batch_actor_creator.load_caches') as mock_caches, \
         patch('app.tools.batch_actor_creator.create_single_actor') as mock_create, \
         patch('app.tools.batch_actor_creator.get_or_create_folder') as mock_folder:

        mock_parse.return_value = [
            {"description": "a goblin", "count": 1},
            {"description": "an orc", "count": 1}
        ]
        mock_expand.return_value = [
            {"description": "a goblin", "count": 1},
            {"description": "an orc", "count": 1}
        ]
        mock_caches.return_value = (MagicMock(), MagicMock())
        # First actor succeeds, second fails
        mock_create.side_effect = [
            {"uuid": "Actor.goblin1", "name": "Goblin", "cr": 0.25},
            RuntimeError("Failed to create orc")
        ]
        mock_folder.return_value = MagicMock(success=True, folder_id="folder123")

        response = await tool.execute(prompt="Create a goblin and an orc")

    assert response.type == "text"
    assert "1 of 2" in response.message
    assert "Failed" in response.message


@pytest.mark.asyncio
async def test_batch_actor_creator_empty_parse_result():
    """Test that BatchActorCreatorTool handles empty parse results."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse:
        mock_parse.return_value = []

        response = await tool.execute(prompt="hello world")

    assert response.type == "text"
    assert "couldn't identify" in response.message.lower()


@pytest.mark.asyncio
async def test_batch_actor_creator_returns_image_urls():
    """Test that BatchActorCreatorTool returns image URLs when available."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse, \
         patch('app.tools.batch_actor_creator.expand_duplicates') as mock_expand, \
         patch('app.tools.batch_actor_creator.load_caches') as mock_caches, \
         patch('app.tools.batch_actor_creator.create_single_actor') as mock_create, \
         patch('app.tools.batch_actor_creator.get_or_create_folder') as mock_folder:

        mock_parse.return_value = [{"description": "a dragon", "count": 1}]
        mock_expand.return_value = [{"description": "a dragon", "count": 1}]
        mock_caches.return_value = (MagicMock(), MagicMock())
        mock_create.return_value = {
            "uuid": "Actor.dragon1",
            "name": "Dragon",
            "cr": 10,
            "image_url": "/api/images/dragon_123.png"
        }
        mock_folder.return_value = MagicMock(success=True, folder_id="folder123")

        response = await tool.execute(prompt="Create a dragon")

    assert response.type == "image"
    assert response.data is not None
    assert "image_urls" in response.data
    assert "/api/images/dragon_123.png" in response.data["image_urls"]


@pytest.mark.asyncio
async def test_batch_actor_creator_handles_exception():
    """Test that BatchActorCreatorTool handles unexpected exceptions."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse:
        mock_parse.side_effect = RuntimeError("Unexpected error")

        response = await tool.execute(prompt="Create a goblin")

    assert response.type == "error"
    assert "Failed to create actors" in response.message


@pytest.mark.asyncio
async def test_create_single_actor_with_mocks():
    """Test create_single_actor function with all dependencies mocked."""
    from app.tools.batch_actor_creator import create_single_actor

    mock_spell_cache = MagicMock()
    mock_icon_cache = MagicMock()

    with patch('app.tools.batch_actor_creator.create_actor_from_description') as mock_create, \
         patch('app.tools.batch_actor_creator.push_actor') as mock_push, \
         patch('app.tools.batch_actor_creator._image_generation_enabled', False):

        # Mock the create_actor_from_description result
        mock_result = MagicMock()
        mock_result.foundry_uuid = "Actor.test123"
        mock_result.stat_block = MagicMock()
        mock_result.stat_block.name = "Test Goblin"
        mock_result.challenge_rating = 0.25
        mock_create.return_value = mock_result

        # Mock push_actor result
        mock_push.return_value = MagicMock(success=True, uuid="Actor.test123")

        result = await create_single_actor(
            description="a goblin scout",
            spell_cache=mock_spell_cache,
            icon_cache=mock_icon_cache,
            folder_id="folder123"
        )

    assert result["uuid"] == "Actor.test123"
    assert result["name"] == "Test Goblin"
    assert result["cr"] == 0.25
    assert result["image_url"] is None


@pytest.mark.asyncio
async def test_create_single_actor_with_image():
    """Test create_single_actor includes image URL when generation is enabled."""
    from app.tools.batch_actor_creator import create_single_actor

    mock_spell_cache = MagicMock()
    mock_icon_cache = MagicMock()

    with patch('app.tools.batch_actor_creator.create_actor_from_description') as mock_create, \
         patch('app.tools.batch_actor_creator.push_actor') as mock_push, \
         patch('app.tools.batch_actor_creator.generate_actor_description') as mock_desc, \
         patch('app.tools.batch_actor_creator.generate_actor_image') as mock_img, \
         patch('app.tools.batch_actor_creator._image_generation_enabled', True):

        mock_result = MagicMock()
        mock_result.foundry_uuid = "Actor.dragon1"
        mock_result.stat_block = MagicMock()
        mock_result.stat_block.name = "Red Dragon"
        mock_result.challenge_rating = 10
        mock_create.return_value = mock_result

        mock_push.return_value = MagicMock(success=True, uuid="Actor.dragon1")
        mock_desc.return_value = "A fierce red dragon"
        mock_img.return_value = ("/api/images/dragon.png", "worlds/test/dragon.png")

        result = await create_single_actor(
            description="a red dragon",
            spell_cache=mock_spell_cache,
            icon_cache=mock_icon_cache,
            folder_id=None
        )

    assert result["uuid"] == "Actor.dragon1"
    assert result["name"] == "Red Dragon"
    assert result["image_url"] == "/api/images/dragon.png"
