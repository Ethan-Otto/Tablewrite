"""Integration tests for public API (require real API keys + backend running)."""
import pytest
import httpx
from pathlib import Path
import api
from api import create_actor, extract_maps, process_pdf_to_journal


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_create_actor_integration(check_api_key, ensure_foundry_connected):
    """Smoke test: End-to-end actor creation via HTTP API.

    Uses the backend HTTP endpoint (which uses WebSocket internally).
    Tests both the httpx direct call and the api.create_actor wrapper.
    """
    # Test using httpx directly (baseline)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/actors/create",
            json={
                "description": "A simple goblin scout with a shortbow",
                "challenge_rating": 0.25
            },
            timeout=120.0
        )

        assert response.status_code == 200, f"Actor creation failed: {response.text}"
        result = response.json()

        # Verify result structure
        assert result["success"] is True
        assert result["foundry_uuid"].startswith("Actor.")
        assert isinstance(result["name"], str) and len(result["name"]) > 0
        assert result["challenge_rating"] == 0.25
        assert result["output_dir"] is not None

        # Note: We don't verify file existence because the backend may be running
        # from a different directory/worktree than the tests. The API success and
        # output_dir presence confirms the pipeline completed successfully.


@pytest.mark.integration
@pytest.mark.slow
def test_create_actor_via_thin_client(check_api_key, ensure_foundry_connected):
    """Test api.create_actor thin HTTP client wrapper.

    Requires backend running at http://localhost:8000.
    """
    result = create_actor(
        description="A cunning kobold trap-maker",
        challenge_rating=0.5
    )

    # Verify result structure
    assert result.foundry_uuid.startswith("Actor.")
    assert len(result.name) > 0
    assert result.challenge_rating == 0.5


@pytest.mark.integration
def test_extract_maps_not_available():
    """Test extract_maps raises helpful error (not yet implemented)."""
    # Use api.APIError to avoid class identity issues from module reloads
    with pytest.raises(api.APIError) as exc_info:
        extract_maps("test.pdf")

    assert "not yet available via HTTP API" in str(exc_info.value)
    assert "extract_maps_from_pdf" in str(exc_info.value)


@pytest.mark.integration
def test_process_pdf_to_journal_not_available():
    """Test process_pdf_to_journal raises helpful error (not yet implemented)."""
    # Use api.APIError to avoid class identity issues from module reloads
    with pytest.raises(api.APIError) as exc_info:
        process_pdf_to_journal("test.pdf", "Test Journal")

    assert "not yet available via HTTP API" in str(exc_info.value)
    assert "full_pipeline.py" in str(exc_info.value)
