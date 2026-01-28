# tests/ui/test_batch_actor_creation.py
"""
Playwright E2E tests for batch actor creation.

Prerequisites:
1. Backend running: cd ui/backend && uvicorn app.main:app --reload
2. FoundryVTT running with Tablewrite module connected
3. Chrome with debug port: open -a "Google Chrome" --args --remote-debugging-port=9222
"""
import pytest
import re
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


def validate_actor_content(actor: dict) -> list[str]:
    """
    Validate actor has appropriate D&D content.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    name = actor.get("name", "Unknown")
    system = actor.get("system", {})

    # Check abilities exist and are reasonable
    abilities = system.get("abilities", {})
    for ability in ["str", "dex", "con", "int", "wis", "cha"]:
        value = abilities.get(ability, {}).get("value", 0)
        if value < 1 or value > 30:
            errors.append(f"{name}: {ability} value {value} out of range")

    # Check HP is set (not default 4)
    hp = system.get("attributes", {}).get("hp", {})
    if hp.get("max", 0) <= 4:
        errors.append(f"{name}: HP too low ({hp.get('max', 0)})")

    # Check has items
    items = actor.get("items", [])
    if len(items) == 0:
        errors.append(f"{name}: No items (attacks, traits)")

    return errors


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_batch_actor_creation_e2e(playwright_user):
    """
    E2E test: Send batch request via chat UI, verify actors created with correct content.
    """
    created_uuids = []

    try:
        with FoundrySession(headless=True, user=playwright_user) as session:
            # Step 1: Navigate to Tablewrite tab
            session.goto_tablewrite()
            time.sleep(1)

            # Step 2: Send batch creation request
            session.send_message(
                "Create a goblin scout and a bugbear",
                wait=60  # Actor creation takes time
            )

            # Step 3: Get response and extract UUIDs
            response_text = session.get_message_text()
            response_html = session.get_message_html()
            print(f"Response text: {response_text[:500]}...")
            print(f"Response HTML: {response_html[:500]}...")
            session.screenshot("/tmp/batch_actor_test.png")

            # Check for success indicators
            assert "Created" in response_text or "@UUID" in response_text or response_text, \
                f"Expected success message, got: {response_text[:200]}"

            # Parse actor UUIDs from response - HTML uses <span data-uuid="Actor.xxx">
            # Pattern 1: @UUID[Actor.xxx]{Name} format (raw text)
            uuid_pattern_raw = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]\{([^}]+)\}'
            # Pattern 2: <span data-uuid="Actor.xxx">Name</span> format (rendered HTML)
            uuid_pattern_html = r'data-uuid="Actor\.([a-zA-Z0-9]+)"[^>]*>([^<]+)</span>'

            matches = re.findall(uuid_pattern_raw, response_html) or re.findall(uuid_pattern_raw, response_text)
            if not matches:
                matches = re.findall(uuid_pattern_html, response_html)

            assert len(matches) >= 2, f"Expected at least 2 actors, found {len(matches)}. HTML: {response_html[:500]}"

            created_uuids = [f"Actor.{m[0]}" for m in matches]
            actor_names = [m[1] for m in matches]
            print(f"Created actors: {list(zip(actor_names, created_uuids))}")

            # Step 4: Fetch and validate each actor
            for uuid, expected_name in zip(created_uuids, actor_names):
                response = requests.get(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                assert response.status_code == 200, f"Failed to fetch {uuid}"

                result = response.json()
                assert result["success"], f"Fetch failed: {result.get('error')}"

                actor = result["entity"]

                # Validate basic structure
                assert actor["name"] == expected_name, f"Name mismatch: {actor['name']} != {expected_name}"
                assert actor["type"] == "npc", f"Wrong type: {actor['type']}"

                # Validate content
                errors = validate_actor_content(actor)
                assert not errors, f"Validation errors for {expected_name}: {errors}"

                print(f"Validated {expected_name}: OK")

    finally:
        # Step 5: Cleanup - delete test actors
        for uuid in created_uuids:
            try:
                response = requests.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                if response.status_code == 200:
                    print(f"Deleted {uuid}")
            except Exception as e:
                print(f"Warning: Failed to delete {uuid}: {e}")


@pytest.mark.playwright
@pytest.mark.foundry
@pytest.mark.gemini
@pytest.mark.slow
def test_batch_actor_duplicates_have_unique_names(playwright_user):
    """Test that requesting multiple of same creature creates unique names."""
    created_uuids = []

    try:
        with FoundrySession(headless=True, user=playwright_user) as session:
            session.goto_tablewrite()
            time.sleep(1)

            # Request two of the same creature
            query = "Create two goblins"
            print(f"[DEBUG] Sending: {query}")
            session.send_message(query, wait=90)

            response_text = session.get_message_text()
            response_html = session.get_message_html()
            print(f"[DEBUG] Response text: {response_text[:500]}...")
            print(f"[DEBUG] Response HTML: {response_html[:500]}...")

            session.screenshot("/tmp/batch_duplicates.png")
            print("[DEBUG] Screenshot: /tmp/batch_duplicates.png")

            # Parse UUIDs - try both formats
            uuid_pattern_raw = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]\{([^}]+)\}'
            uuid_pattern_html = r'data-uuid="Actor\.([a-zA-Z0-9]+)"[^>]*>([^<]+)</span>'

            matches = re.findall(uuid_pattern_raw, response_html) or re.findall(uuid_pattern_raw, response_text)
            if not matches:
                matches = re.findall(uuid_pattern_html, response_html)

            print(f"[DEBUG] Matches found: {matches}")
            assert len(matches) >= 2, f"Expected 2 goblins, found {len(matches)}. Response: {response_text[:300]}"

            created_uuids = [f"Actor.{m[0]}" for m in matches]
            actor_names = [m[1] for m in matches]

            # Verify names are unique
            assert len(set(actor_names)) == len(actor_names), \
                f"Names not unique: {actor_names}"

            print(f"Created {len(actor_names)} goblins with unique names: {actor_names}")

    finally:
        for uuid in created_uuids:
            try:
                requests.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
            except:
                pass
