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
def test_journal_query_via_chat_ui(playwright_user):
    """
    E2E test: Create journal, query it via chat UI, verify answer contains expected content.
    """
    journal_uuid = None
    folder_id = get_or_create_test_folder()
    print(f"\n[DEBUG] Test folder ID: {folder_id}")

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

        print("[DEBUG] Creating test journal...")
        journal_uuid = create_test_journal(
            "E2E Test Dragon Journal",
            journal_content,
            folder_id
        )
        print(f"[DEBUG] Created test journal: {journal_uuid}")

        # Step 2: Query via chat UI
        print("[DEBUG] Starting FoundrySession...")
        with FoundrySession(headless=True, user=playwright_user) as session:
            print("[DEBUG] FoundrySession started, navigating to Tablewrite tab...")
            session.goto_tablewrite()
            print("[DEBUG] On Tablewrite tab, waiting 1s...")
            time.sleep(1)

            # Take screenshot before sending message
            session.screenshot("/tmp/before_query.png")
            print("[DEBUG] Screenshot saved: /tmp/before_query.png")

            # Ask about the treasure
            query = "What treasure is in E2E Test Dragon Journal?"
            print(f"[DEBUG] Sending message: {query}")
            session.send_message(query, wait=30)
            print("[DEBUG] Message sent, waiting for response...")

            # Take screenshot after response
            session.screenshot("/tmp/after_query.png")
            print("[DEBUG] Screenshot saved: /tmp/after_query.png")

            response_text = session.get_message_text()
            response_html = session.get_message_html()
            print(f"[DEBUG] Response text length: {len(response_text)}")
            print(f"[DEBUG] Response text: {response_text[:500]}...")
            print(f"[DEBUG] Response HTML length: {len(response_html)}")

            # Get all messages for debugging
            all_messages = session.get_all_messages()
            print(f"[DEBUG] Total messages in chat: {len(all_messages)}")
            for i, msg in enumerate(all_messages[-5:]):  # Last 5 messages
                msg_str = str(msg)[:100] if msg else "(empty)"
                print(f"[DEBUG] Message {i}: {msg_str}...")

            # Step 3: Verify response contains expected content
            response_lower = response_text.lower()

            # Should mention at least some of the treasure
            treasure_found = any(item in response_lower for item in [
                "gold", "staff of power", "potion", "10,000"
            ])

            assert treasure_found, \
                f"Expected treasure info in response: {response_text[:300]}"

            print("[DEBUG] Query response validated successfully")

    finally:
        # Step 4: Cleanup
        if journal_uuid:
            delete_journal(journal_uuid)
            print(f"[DEBUG] Deleted test journal: {journal_uuid}")


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_journal_summary_via_chat_ui(playwright_user):
    """
    E2E test: Create journal, request summary via chat UI, verify summary is returned.
    """
    journal_uuid = None
    folder_id = get_or_create_test_folder()
    print(f"\n[DEBUG] Test folder ID: {folder_id}")

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

        print("[DEBUG] Creating test journal...")
        journal_uuid = create_test_journal(
            "E2E Test Summary Journal",
            journal_content,
            folder_id
        )
        print(f"[DEBUG] Created test journal: {journal_uuid}")

        # Step 2: Request summary via chat UI
        print("[DEBUG] Starting FoundrySession...")
        with FoundrySession(headless=True, user=playwright_user) as session:
            print("[DEBUG] FoundrySession started, navigating to Tablewrite tab...")
            session.goto_tablewrite()
            print("[DEBUG] On Tablewrite tab, waiting 1s...")
            time.sleep(1)

            session.screenshot("/tmp/before_summary.png")
            print("[DEBUG] Screenshot saved: /tmp/before_summary.png")

            query = "Summarize E2E Test Summary Journal"
            print(f"[DEBUG] Sending message: {query}")
            session.send_message(query, wait=30)
            print("[DEBUG] Message sent, waiting for response...")

            session.screenshot("/tmp/after_summary.png")
            print("[DEBUG] Screenshot saved: /tmp/after_summary.png")

            response_text = session.get_message_text()
            print(f"[DEBUG] Response text length: {len(response_text)}")
            print(f"[DEBUG] Response text: {response_text[:500]}...")

            all_messages = session.get_all_messages()
            print(f"[DEBUG] Total messages in chat: {len(all_messages)}")

            # Step 3: Verify summary contains key elements
            response_lower = response_text.lower()

            key_elements = ["goblin", "relic", "village", "stranger", "quest"]
            elements_found = sum(1 for elem in key_elements if elem in response_lower)
            print(f"[DEBUG] Key elements found: {elements_found}/5")

            assert elements_found >= 2, \
                f"Expected summary to mention key story elements, found {elements_found}: {response_text[:300]}"

            print("[DEBUG] Summary response validated successfully")

    finally:
        if journal_uuid:
            delete_journal(journal_uuid)
            print(f"[DEBUG] Deleted test journal: {journal_uuid}")


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_journal_extraction_via_chat_ui(playwright_user):
    """
    E2E test: Create journal with NPCs, extract list via chat UI.
    """
    journal_uuid = None
    folder_id = get_or_create_test_folder()
    print(f"\n[DEBUG] Test folder ID: {folder_id}")

    try:
        # Step 1: Create test journal with NPC content
        journal_content = """
        <h1>NPCs of Millbrook</h1>
        <p>Mayor Thornwick is the elderly human leader of the village.</p>
        <p>Elara Moonwhisper is an elven herbalist who runs the apothecary.</p>
        <p>Grimjaw is a half-orc blacksmith known for his exceptional weapons.</p>
        """

        print("[DEBUG] Creating test journal...")
        journal_uuid = create_test_journal(
            "E2E Test NPCs Journal",
            journal_content,
            folder_id
        )
        print(f"[DEBUG] Created test journal: {journal_uuid}")

        # Step 2: Request NPC list via chat UI
        print("[DEBUG] Starting FoundrySession...")
        with FoundrySession(headless=True, user=playwright_user) as session:
            print("[DEBUG] FoundrySession started, navigating to Tablewrite tab...")
            session.goto_tablewrite()
            print("[DEBUG] On Tablewrite tab, waiting 1s...")
            time.sleep(1)

            session.screenshot("/tmp/before_extraction.png")
            print("[DEBUG] Screenshot saved: /tmp/before_extraction.png")

            query = "List all NPCs in E2E Test NPCs Journal"
            print(f"[DEBUG] Sending message: {query}")
            session.send_message(query, wait=30)
            print("[DEBUG] Message sent, waiting for response...")

            session.screenshot("/tmp/after_extraction.png")
            print("[DEBUG] Screenshot saved: /tmp/after_extraction.png")

            response_text = session.get_message_text()
            print(f"[DEBUG] Response text length: {len(response_text)}")
            print(f"[DEBUG] Response text: {response_text[:500]}...")

            all_messages = session.get_all_messages()
            print(f"[DEBUG] Total messages in chat: {len(all_messages)}")

            # Step 3: Verify NPCs are listed
            response_lower = response_text.lower()

            npcs = ["thornwick", "elara", "grimjaw"]
            npcs_found = sum(1 for npc in npcs if npc in response_lower)
            print(f"[DEBUG] NPCs found: {npcs_found}/3")

            assert npcs_found >= 2, \
                f"Expected at least 2 NPCs listed, found {npcs_found}: {response_text[:300]}"

            print("[DEBUG] Extraction response validated successfully")

    finally:
        if journal_uuid:
            delete_journal(journal_uuid)
            print(f"[DEBUG] Deleted test journal: {journal_uuid}")
