# tests/ui/test_journal_query_e2e.py
"""
Playwright E2E tests for journal query feature.

Prerequisites:
1. Backend running: cd ui/backend && uvicorn app.main:app --reload
2. FoundryVTT running with Tablewrite module connected
3. Chrome with debug port: open -a "Google Chrome" --args --remote-debugging-port=9222
"""
import pytest
import requests
import time

# Skip entire module if playwright not installed (CI doesn't have it)
pytest.importorskip("playwright", reason="Playwright not installed - skipping UI tests")

# Add foundry_helper to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"))

from foundry_helper import FoundrySession

BACKEND_URL = "http://localhost:8000"


def create_test_journal(name: str, content: str, folder_id: str = None) -> str:
    """Create a test journal and return its UUID."""
    payload = {"name": name, "content": content}
    if folder_id:
        payload["folder"] = folder_id

    response = requests.post(f"{BACKEND_URL}/api/foundry/journal", json=payload)
    assert response.status_code == 200, f"Failed to create journal: {response.text}"
    return response.json()["uuid"]


def delete_journal(uuid: str):
    """Delete a journal by UUID."""
    try:
        requests.delete(f"{BACKEND_URL}/api/foundry/journal/{uuid}")
    except Exception as e:
        print(f"Warning: Failed to delete journal {uuid}: {e}")


def get_or_create_test_folder() -> str:
    """Get or create a /tests folder for JournalEntry."""
    # Check if tests folder exists
    response = requests.get(f"{BACKEND_URL}/api/foundry/folders")
    if response.status_code == 200:
        folders = response.json().get("folders", [])
        for folder in folders:
            if folder.get("name") == "tests" and folder.get("type") == "JournalEntry":
                return folder.get("_id")

    # Create if not exists
    response = requests.post(
        f"{BACKEND_URL}/api/foundry/folder",
        json={"name": "tests", "type": "JournalEntry"}
    )
    if response.status_code == 200:
        return response.json().get("_id")
    return None


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_journal_query_via_chat_ui():
    """
    E2E test: Create journal, query it via chat UI, verify answer contains expected content.
    """
    journal_uuid = None
    folder_id = get_or_create_test_folder()

    try:
        # Step 1: Create test journal with known content
        journal_content = """
        <h1>The Dragon's Lair</h1>
        <h2>Treasure Hoard</h2>
        <p>Inside the dragon's lair, adventurers discover a pile of 10,000 gold coins,
        a magical Staff of Power, and three potions of healing.</p>
        <h2>The Guardian</h2>
        <p>An ancient red dragon named Infernus guards this treasure.</p>
        """

        journal_uuid = create_test_journal(
            "E2E Test Dragon Journal",
            journal_content,
            folder_id
        )
        print(f"Created test journal: {journal_uuid}")

        # Step 2: Query via chat UI
        with FoundrySession(headless=True) as session:
            session.goto_tablewrite()
            time.sleep(1)

            # Ask about the treasure
            session.send_message(
                "What treasure is in E2E Test Dragon Journal?",
                wait=30
            )

            response_text = session.get_message_text()
            print(f"Response: {response_text[:500]}...")

            # Step 3: Verify response contains expected content
            response_lower = response_text.lower()

            # Should mention at least some of the treasure
            treasure_found = any(item in response_lower for item in [
                "gold", "staff of power", "potion", "10,000"
            ])

            assert treasure_found, \
                f"Expected treasure info in response: {response_text[:300]}"

            print("Query response validated successfully")

    finally:
        # Step 4: Cleanup
        if journal_uuid:
            delete_journal(journal_uuid)
            print(f"Deleted test journal: {journal_uuid}")


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_journal_summary_via_chat_ui():
    """
    E2E test: Create journal, request summary via chat UI, verify summary is returned.
    """
    journal_uuid = None
    folder_id = get_or_create_test_folder()

    try:
        # Step 1: Create test journal with story content
        journal_content = """
        <h1>Chapter 1: The Call to Adventure</h1>
        <p>In the village of Millbrook, a mysterious stranger arrives seeking heroes.</p>
        <h2>The Quest</h2>
        <p>The stranger reveals that goblins have stolen the village's sacred relic.</p>
        <h2>The Party Assembles</h2>
        <p>A fighter, a wizard, and a cleric agree to help recover the relic.</p>
        """

        journal_uuid = create_test_journal(
            "E2E Test Summary Journal",
            journal_content,
            folder_id
        )
        print(f"Created test journal: {journal_uuid}")

        # Step 2: Request summary via chat UI
        with FoundrySession(headless=True) as session:
            session.goto_tablewrite()
            time.sleep(1)

            session.send_message(
                "Summarize E2E Test Summary Journal",
                wait=30
            )

            response_text = session.get_message_text()
            print(f"Response: {response_text[:500]}...")

            # Step 3: Verify summary contains key elements
            response_lower = response_text.lower()

            key_elements = ["goblin", "relic", "village", "stranger", "quest"]
            elements_found = sum(1 for elem in key_elements if elem in response_lower)

            assert elements_found >= 2, \
                f"Expected summary to mention key story elements, found {elements_found}: {response_text[:300]}"

            print("Summary response validated successfully")

    finally:
        if journal_uuid:
            delete_journal(journal_uuid)
            print(f"Deleted test journal: {journal_uuid}")


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_journal_extraction_via_chat_ui():
    """
    E2E test: Create journal with NPCs, extract list via chat UI.
    """
    journal_uuid = None
    folder_id = get_or_create_test_folder()

    try:
        # Step 1: Create test journal with NPC content
        journal_content = """
        <h1>NPCs of Millbrook</h1>
        <p>Mayor Thornwick is the elderly human leader of the village.</p>
        <p>Elara Moonwhisper is an elven herbalist who runs the apothecary.</p>
        <p>Grimjaw is a half-orc blacksmith known for his exceptional weapons.</p>
        """

        journal_uuid = create_test_journal(
            "E2E Test NPCs Journal",
            journal_content,
            folder_id
        )
        print(f"Created test journal: {journal_uuid}")

        # Step 2: Request NPC list via chat UI
        with FoundrySession(headless=True) as session:
            session.goto_tablewrite()
            time.sleep(1)

            session.send_message(
                "List all NPCs in E2E Test NPCs Journal",
                wait=30
            )

            response_text = session.get_message_text()
            print(f"Response: {response_text[:500]}...")

            # Step 3: Verify NPCs are listed
            response_lower = response_text.lower()

            npcs = ["thornwick", "elara", "grimjaw"]
            npcs_found = sum(1 for npc in npcs if npc in response_lower)

            assert npcs_found >= 2, \
                f"Expected at least 2 NPCs listed, found {npcs_found}: {response_text[:300]}"

            print("Extraction response validated successfully")

    finally:
        if journal_uuid:
            delete_journal(journal_uuid)
            print(f"Deleted test journal: {journal_uuid}")
