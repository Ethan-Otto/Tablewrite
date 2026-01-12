"""Integration tests for actor orchestration pipeline.

These tests call the backend HTTP API which internally uses WebSocket
to communicate with Foundry. Requires:
- Backend running (localhost:8000 or BACKEND_URL env var)
- Foundry with Tablewrite module connected
"""

import os
import pytest
import httpx
from pathlib import Path

# Use environment variable for Docker compatibility
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class TestActorOrchestrationIntegration:
    """Integration tests for full actor creation pipeline."""

    @pytest.mark.smoke
    @pytest.mark.foundry
    @pytest.mark.gemini
    @pytest.mark.asyncio
    @pytest.mark.order("last")
    async def test_full_pipeline_end_to_end(self, tmp_path):
        """
        Smoke test: End-to-end actor creation via HTTP API.

        Calls POST /api/actors/create which runs the full pipeline:
        1. Generate stat block with Gemini
        2. Parse to models
        3. Upload to Foundry via WebSocket

        Requires backend + Foundry running.
        """
        description = "A small goblin warrior with a rusty short sword"
        challenge_rating = 0.25

        async with httpx.AsyncClient(timeout=120.0) as client:
            # First verify backend and Foundry are connected
            try:
                status = await client.get(f"{BACKEND_URL}/api/foundry/status")
                status.raise_for_status()
                if status.json().get("status") != "connected":
                    pytest.fail("Foundry not connected to backend")
            except httpx.ConnectError:
                pytest.fail("Backend not running on localhost:8000")

            # Create actor via HTTP API
            response = await client.post(
                f"{BACKEND_URL}/api/actors/create",
                json={
                    "description": description,
                    "challenge_rating": challenge_rating,
                    "output_dir_base": str(tmp_path)
                }
            )

            assert response.status_code == 200, f"Actor creation failed: {response.text}"

            result = response.json()

            # Verify result structure
            assert result["success"] is True
            assert result["foundry_uuid"] is not None
            assert result["foundry_uuid"].startswith("Actor.")
            assert result["name"] is not None
            assert result["challenge_rating"] == challenge_rating

            print(f"Actor created: {result['name']}")
            print(f"UUID: {result['foundry_uuid']}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_creates_output_directory(self, tmp_path):
        """Test that pipeline creates properly structured output directory."""
        description = "A simple test goblin"

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Verify backend is running
            try:
                status = await client.get(f"{BACKEND_URL}/api/foundry/status")
                status.raise_for_status()
                if status.json().get("status") != "connected":
                    pytest.fail("Foundry not connected to backend")
            except httpx.ConnectError:
                pytest.fail("Backend not running on localhost:8000")

            response = await client.post(
                f"{BACKEND_URL}/api/actors/create",
                json={
                    "description": description,
                    "challenge_rating": 0.25,
                    "output_dir_base": str(tmp_path)
                }
            )

            assert response.status_code == 200
            result = response.json()

            # Verify output directory was created
            assert result["output_dir"] is not None
            output_dir = Path(result["output_dir"])
            assert output_dir.exists()
            assert output_dir.name == "actors"
