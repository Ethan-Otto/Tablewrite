"""Integration tests for JournalQueryTool with real Foundry and Gemini."""
import pytest
import os
import httpx

from tests.conftest import check_backend_and_foundry, get_or_create_test_folder

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_specific_journal_roundtrip():
    """
    Integration test: Create a test journal, query it, verify answer.

    1. Create a test journal with known content
    2. Query the journal with a question
    3. Verify the answer contains expected information
    4. Delete the test journal
    """
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("JournalEntry")

    # Create test journal with known content
    async with httpx.AsyncClient(timeout=60.0) as client:
        journal_content = """
        <h1>Test Adventure</h1>
        <h2>The Treasure Room</h2>
        <p>Inside the treasure room, the party finds a golden chalice worth 500 gold pieces
        and a magical sword called Dragonbane.</p>
        <h2>The Monster</h2>
        <p>A young red dragon named Scorchclaw guards the treasure.</p>
        """

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/journal",
            json={
                "name": "Test Query Journal",
                "content": journal_content,
                "folder": folder_id
            }
        )
        assert create_response.status_code == 200, f"Failed to create journal: {create_response.text}"
        journal_uuid = create_response.json()["uuid"]

        try:
            # Query the journal via chat
            chat_response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "What treasure is in Test Query Journal?",
                    "conversation_history": []
                }
            )
            assert chat_response.status_code == 200

            response_data = chat_response.json()

            # Verify the response contains expected content
            message = response_data.get("message", "")
            assert "golden chalice" in message.lower() or "500 gold" in message.lower() or "dragonbane" in message.lower(), \
                f"Expected treasure info in response: {message}"

        finally:
            # Clean up: delete the test journal
            delete_response = await client.delete(
                f"{BACKEND_URL}/api/foundry/journal/{journal_uuid}"
            )
            assert delete_response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_summary_request():
    """Test summary query type returns condensed information."""
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("JournalEntry")

    async with httpx.AsyncClient(timeout=60.0) as client:
        journal_content = """
        <h1>Chapter 1: The Beginning</h1>
        <p>Our heroes meet in a tavern. They receive a quest from an old wizard.</p>
        <h2>The Quest</h2>
        <p>The wizard asks them to retrieve a magical artifact from a dungeon.</p>
        <h2>The Journey</h2>
        <p>The party travels through forests and over mountains.</p>
        """

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/journal",
            json={
                "name": "Test Summary Journal",
                "content": journal_content,
                "folder": folder_id
            }
        )
        assert create_response.status_code == 200, f"Failed to create journal: {create_response.text}"
        journal_uuid = create_response.json()["uuid"]

        try:
            chat_response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "Summarize Test Summary Journal",
                    "conversation_history": []
                }
            )
            assert chat_response.status_code == 200

            message = chat_response.json().get("message", "")
            # Summary should mention key elements
            assert any(word in message.lower() for word in ["wizard", "quest", "artifact", "tavern"]), \
                f"Summary should contain key story elements: {message}"

        finally:
            await client.delete(f"{BACKEND_URL}/api/foundry/journal/{journal_uuid}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extraction_request():
    """Test extraction query type lists entities."""
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("JournalEntry")

    async with httpx.AsyncClient(timeout=60.0) as client:
        journal_content = """
        <h1>NPCs of the Town</h1>
        <p>Sildar Hallwinter is a human knight who seeks to restore order.</p>
        <p>Gundren Rockseeker is a dwarf merchant looking for the lost mine.</p>
        <p>Sister Garaele is an elf cleric at the shrine.</p>
        """

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/journal",
            json={
                "name": "Test NPCs Journal",
                "content": journal_content,
                "folder": folder_id
            }
        )
        assert create_response.status_code == 200, f"Failed to create journal: {create_response.text}"
        journal_uuid = create_response.json()["uuid"]

        try:
            chat_response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "List all NPCs in Test NPCs Journal",
                    "conversation_history": []
                }
            )
            assert chat_response.status_code == 200

            message = chat_response.json().get("message", "")
            # Should list the NPCs
            npc_count = sum(1 for name in ["sildar", "gundren", "garaele"] if name in message.lower())
            assert npc_count >= 2, f"Should list at least 2 NPCs: {message}"

        finally:
            await client.delete(f"{BACKEND_URL}/api/foundry/journal/{journal_uuid}")
