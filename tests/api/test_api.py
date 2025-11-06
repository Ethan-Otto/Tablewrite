"""Tests for public API facade."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from api import (
    APIError,
    ActorCreationResult,
    MapExtractionResult,
    JournalCreationResult,
    create_actor
)


def test_api_error_can_be_raised():
    """Test that APIError can be raised and caught."""
    with pytest.raises(APIError, match="test error"):
        raise APIError("test error")


def test_api_error_preserves_cause():
    """Test that APIError preserves original exception."""
    original = ValueError("original error")

    try:
        try:
            raise original
        except ValueError as e:
            raise APIError("wrapped error") from e
    except APIError as api_err:
        assert api_err.__cause__ is original


def test_actor_creation_result_instantiation():
    """Test ActorCreationResult can be created."""
    result = ActorCreationResult(
        foundry_uuid="Actor.abc123",
        name="Goblin Warrior",
        challenge_rating=1.0,
        output_dir=Path("output/runs/test"),
        timestamp="2025-11-05T12:00:00"
    )

    assert result.foundry_uuid == "Actor.abc123"
    assert result.name == "Goblin Warrior"
    assert result.challenge_rating == 1.0


def test_map_extraction_result_instantiation():
    """Test MapExtractionResult can be created."""
    result = MapExtractionResult(
        maps=[{"name": "Test Map", "type": "battle_map"}],
        output_dir=Path("output/runs/test"),
        total_maps=1,
        timestamp="2025-11-05T12:00:00"
    )

    assert result.total_maps == 1
    assert len(result.maps) == 1


def test_journal_creation_result_instantiation():
    """Test JournalCreationResult can be created."""
    result = JournalCreationResult(
        journal_uuid="JournalEntry.xyz789",
        journal_name="Test Journal",
        output_dir=Path("output/runs/test"),
        chapter_count=5,
        timestamp="2025-11-05T12:00:00"
    )

    assert result.journal_uuid == "JournalEntry.xyz789"
    assert result.chapter_count == 5


@patch('api.orchestrate_create_actor_from_description_sync')
def test_create_actor_happy_path(mock_create):
    """Test create_actor wraps orchestrate correctly."""
    # Mock the orchestrate function
    from actors.models import ActorCreationResult as OrchestrateResult

    mock_result = OrchestrateResult(
        description="A fierce goblin",
        challenge_rating=1.0,
        raw_stat_block_text="RAW TEXT",
        stat_block=Mock(),
        parsed_actor_data=Mock(name="Goblin Warrior"),
        foundry_uuid="Actor.abc123",
        output_dir=Path("output/runs/test"),
        raw_text_file=Path("output/runs/test/01.txt"),
        stat_block_file=Path("output/runs/test/02.json"),
        parsed_data_file=Path("output/runs/test/03.json"),
        foundry_json_file=Path("output/runs/test/04.json"),
        timestamp="2025-11-05T12:00:00",
        model_used="gemini-2.0-flash"
    )
    mock_create.return_value = mock_result

    # Call our API function
    result = create_actor("A fierce goblin", challenge_rating=1.0)

    # Verify it called orchestrate with correct args
    mock_create.assert_called_once_with(
        description="A fierce goblin",
        challenge_rating=1.0
    )

    # Verify result is our simplified dataclass
    assert isinstance(result, ActorCreationResult)
    assert result.foundry_uuid == "Actor.abc123"
    assert result.challenge_rating == 1.0
    assert result.output_dir == Path("output/runs/test")


@patch('api.orchestrate_create_actor_from_description_sync')
def test_create_actor_error_handling(mock_create):
    """Test create_actor wraps exceptions as APIError."""
    mock_create.side_effect = ValueError("Gemini API error")

    with pytest.raises(APIError, match="Failed to create actor"):
        create_actor("broken description")

    # Verify original exception is preserved
    try:
        create_actor("broken description")
    except APIError as e:
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "Gemini API error"


@patch('api.extract_maps_from_pdf')
def test_extract_maps_happy_path(mock_extract):
    """Test extract_maps wraps map extraction correctly."""
    from pdf_processing.image_asset_processing.models import MapMetadata

    # Mock extraction results
    mock_maps = [
        MapMetadata(
            name="Cave Entrance",
            page_num=1,
            type="battle_map",
            source="extracted",
            chapter="Chapter 1"
        ),
        MapMetadata(
            name="Goblin Hideout",
            page_num=2,
            type="battle_map",
            source="segmented",
            chapter="Chapter 1"
        )
    ]
    mock_extract.return_value = mock_maps

    # Import after patching
    from api import extract_maps

    # Call API function
    result = extract_maps("test.pdf", chapter="Chapter 1")

    # Verify extraction was called
    mock_extract.assert_called_once()

    # Verify result
    assert isinstance(result, MapExtractionResult)
    assert result.total_maps == 2
    assert len(result.maps) == 2
    assert result.maps[0]["name"] == "Cave Entrance"


@patch('api.extract_maps_from_pdf')
def test_extract_maps_error_handling(mock_extract):
    """Test extract_maps wraps exceptions."""
    mock_extract.side_effect = FileNotFoundError("PDF not found")

    # Import after patching
    from api import extract_maps

    with pytest.raises(APIError, match="Failed to extract maps"):
        extract_maps("missing.pdf")
