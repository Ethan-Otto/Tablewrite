"""Integration tests for public API (require real API keys)."""
import pytest
import httpx
from pathlib import Path
from api import extract_maps, process_pdf_to_journal, APIError


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_create_actor_integration(check_api_key, ensure_foundry_connected):
    """Smoke test: End-to-end actor creation via HTTP API.

    Uses the backend HTTP endpoint (which uses WebSocket internally).
    The standalone public API (api.create_actor) is deprecated as it requires
    the relay server which has been removed.
    """
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

        # Verify output files exist (path is relative to backend working directory)
        backend_dir = Path(__file__).parent.parent.parent / "ui" / "backend"
        output_dir = backend_dir / result["output_dir"]
        assert (output_dir / "01_raw_stat_block.txt").exists(), f"Missing file in {output_dir}"
        assert (output_dir / "04_foundry_actor.json").exists(), f"Missing file in {output_dir}"


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.slow
def test_extract_maps_integration(test_pdf_path, check_api_key):
    """Smoke test: Map extraction from PDF via public API

    Test extract_maps with real PDF."""
    result = extract_maps(str(test_pdf_path))

    # May not have maps, but should complete without error
    assert isinstance(result.total_maps, int)
    assert result.total_maps >= 0
    assert len(result.maps) == result.total_maps


@pytest.mark.integration
@pytest.mark.slow
def test_process_pdf_to_journal_integration(test_pdf_path, check_api_key):
    """Test process_pdf_to_journal with real PDF (skip upload)."""
    # NOTE: This test is expected to fail with NotImplementedError
    # because run_pdf_to_xml() is not yet implemented
    with pytest.raises(APIError) as exc_info:
        result = process_pdf_to_journal(
            str(test_pdf_path),
            "Integration Test Journal",
            skip_upload=True  # Don't actually upload in tests
        )

    # Verify the underlying error is NotImplementedError
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, NotImplementedError)
