"""Tests for public API facade."""
import pytest
from pathlib import Path
from api import (
    APIError,
    ActorCreationResult,
    MapExtractionResult,
    JournalCreationResult
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
