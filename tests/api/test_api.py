"""Tests for public API facade (HTTP client)."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from api import (
    APIError,
    ActorCreationResult,
    MapExtractionResult,
    JournalCreationResult,
    create_actor,
    extract_maps,
    process_pdf_to_journal,
    BACKEND_URL,
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


def test_actor_creation_result_with_optional_fields():
    """Test ActorCreationResult can be created with optional fields as None."""
    result = ActorCreationResult(
        foundry_uuid="Actor.abc123",
        name="Goblin Warrior",
        challenge_rating=1.0,
    )

    assert result.foundry_uuid == "Actor.abc123"
    assert result.output_dir is None
    assert result.timestamp is None


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


@patch('api.requests.post')
def test_create_actor_happy_path(mock_post):
    """Test create_actor makes correct HTTP request."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "foundry_uuid": "Actor.abc123",
        "name": "Goblin Warrior",
        "challenge_rating": 1.0,
        "output_dir": "output/runs/test",
        "timestamp": "2025-11-05T12:00:00"
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    # Call our API function
    result = create_actor("A fierce goblin", challenge_rating=1.0)

    # Verify it called requests.post with correct args
    mock_post.assert_called_once_with(
        f"{BACKEND_URL}/api/actors/create",
        json={
            "description": "A fierce goblin",
            "challenge_rating": 1.0
        },
        timeout=120
    )

    # Verify result is our simplified dataclass
    assert isinstance(result, ActorCreationResult)
    assert result.foundry_uuid == "Actor.abc123"
    assert result.name == "Goblin Warrior"
    assert result.challenge_rating == 1.0
    assert result.output_dir == Path("output/runs/test")


@patch('api.requests.post')
def test_create_actor_default_challenge_rating(mock_post):
    """Test create_actor uses default CR when None provided."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "foundry_uuid": "Actor.abc123",
        "name": "Goblin",
        "challenge_rating": 1.0,
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = create_actor("A goblin")

    # Should default to 1.0
    call_args = mock_post.call_args
    assert call_args[1]["json"]["challenge_rating"] == 1.0


@patch('api.requests.post')
def test_create_actor_http_error(mock_post):
    """Test create_actor wraps HTTP errors as APIError."""
    import requests
    mock_post.side_effect = requests.exceptions.ConnectionError("Backend not running")

    with pytest.raises(APIError, match="Failed to create actor"):
        create_actor("broken description")


@patch('api.requests.post')
def test_create_actor_api_failure_response(mock_post):
    """Test create_actor handles API failure response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": False,
        "detail": "Gemini API error"
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    with pytest.raises(APIError, match="Actor creation failed"):
        create_actor("broken description")


@patch('api.requests.post')
def test_create_actor_preserves_cause(mock_post):
    """Test create_actor preserves original exception as cause."""
    import requests
    original = requests.exceptions.Timeout("Request timed out")
    mock_post.side_effect = original

    try:
        create_actor("broken description")
    except APIError as e:
        assert isinstance(e.__cause__, requests.exceptions.Timeout)
        assert str(e.__cause__) == "Request timed out"


def test_extract_maps_not_implemented():
    """Test extract_maps raises APIError with helpful message."""
    with pytest.raises(APIError) as exc_info:
        extract_maps("test.pdf", chapter="Chapter 1")

    assert "not yet available via HTTP API" in str(exc_info.value)
    assert "extract_maps_from_pdf" in str(exc_info.value)


def test_process_pdf_to_journal_not_implemented():
    """Test process_pdf_to_journal raises APIError with helpful message."""
    with pytest.raises(APIError) as exc_info:
        process_pdf_to_journal("test.pdf", "Test Journal")

    assert "not yet available via HTTP API" in str(exc_info.value)
    assert "full_pipeline.py" in str(exc_info.value)


def test_backend_url_default():
    """Test BACKEND_URL has sensible default."""
    assert BACKEND_URL == "http://localhost:8000"


@patch.dict('os.environ', {'BACKEND_URL': 'http://custom:9000'})
def test_backend_url_from_env():
    """Test BACKEND_URL can be overridden by environment."""
    # Need to reload the module to pick up new env var
    import importlib
    import api
    importlib.reload(api)

    assert api.BACKEND_URL == "http://custom:9000"

    # Reload again to restore default for other tests
    import os
    if 'BACKEND_URL' in os.environ:
        del os.environ['BACKEND_URL']
    importlib.reload(api)
