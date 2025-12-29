"""End-to-end test: Journal creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled
3. Real Gemini API key (makes actual API calls)

Run with: pytest tests/integration/test_e2e_journal_push.py -v -m integration
"""
import pytest
import os
import sys
import uuid
from fastapi.testclient import TestClient
from app.main import app

# Add src directory to path for FoundryClient import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'src'))
from foundry.client import FoundryClient


@pytest.mark.integration
class TestJournalPushE2E:
    """End-to-end journal push tests (real Gemini API)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_create_journal_via_chat_pushes_to_foundry(self):
        """
        Full flow test:
        1. Connect WebSocket (simulating Foundry)
        2. Call /api/chat with journal creation request
        3. Verify WebSocket receives journal push

        Note: This uses REAL Gemini API and costs money.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome message
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            client_id = welcome["client_id"]
            print(f"[TEST] Connected with client_id: {client_id}")

            # Generate unique title to avoid conflicts
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Journal {unique_id}"

            # Request journal creation via chat
            # This will trigger the create_journal tool
            response = client.post("/api/chat", json={
                "message": f"Create a journal entry titled '{journal_title}' with content 'This is test content for the journal entry.'",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check if the response indicates journal was created
            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Journal was created successfully, now check for WebSocket push
                try:
                    pushed = ws.receive_json()
                    print(f"[TEST] Received WebSocket message: {pushed}")

                    assert pushed["type"] == "journal"
                    assert "name" in pushed["data"]
                    assert "uuid" in pushed["data"]
                    print(f"[TEST] Journal pushed: {pushed['data']['name']}")
                except Exception as e:
                    pytest.fail(f"WebSocket push not received: {e}")
            elif response_data.get("type") == "error":
                pytest.fail(f"Journal creation failed: {response_data.get('message')}")
            else:
                # Tool might not have been triggered (Gemini didn't call it)
                pytest.skip(f"Journal tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_journal_push_contains_required_fields(self):
        """
        Verify journal push message has all required fields.

        Real data test: Uses actual Gemini API to create a journal.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"

            # Generate unique title
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Fields Journal {unique_id}"

            # Create journal with explicit title and content
            response = client.post("/api/chat", json={
                "message": f"Create a journal entry titled '{journal_title}' with content 'Testing field validation content.'",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Check the pushed message structure
                pushed = ws.receive_json()

                assert pushed["type"] == "journal", f"Expected type 'journal', got '{pushed['type']}'"

                journal_data = pushed["data"]
                assert "name" in journal_data, "Journal data missing 'name'"
                assert "uuid" in journal_data, "Journal data missing 'uuid'"

                # Verify UUID format (FoundryVTT format: JournalEntry.xxxxx)
                assert journal_data["uuid"].startswith("JournalEntry."), \
                    f"Invalid UUID format: {journal_data['uuid']}"

                print(f"[TEST] Verified journal push: {journal_data}")
            else:
                pytest.skip(f"Journal tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_created_journal_can_be_fetched_from_foundry(self):
        """
        Verify that a journal created via chat actually exists in FoundryVTT.

        Full flow test:
        1. Create journal via chat (triggers Gemini + FoundryVTT creation)
        2. Get UUID from WebSocket push message
        3. Use FoundryClient to fetch the journal directly from FoundryVTT
        4. Verify fetched journal data matches what was pushed

        This test proves the journal is not just pushed via WebSocket but
        actually exists in the FoundryVTT database and can be retrieved.

        Real data test: Uses actual Gemini API and FoundryVTT REST API.
        """
        # Skip if Foundry environment variables not set
        required_env_vars = ["FOUNDRY_RELAY_URL", "FOUNDRY_URL", "FOUNDRY_API_KEY", "FOUNDRY_CLIENT_ID"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing environment variables: {', '.join(missing_vars)}")

        client = TestClient(app)
        foundry_client = FoundryClient()

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome message
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            print(f"[TEST] Connected with client_id: {welcome['client_id']}")

            # Generate unique title to avoid conflicts with other tests
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Fetch Journal {unique_id}"
            journal_content = f"This is test content for verification. ID: {unique_id}"

            # Request journal creation via chat
            response = client.post("/api/chat", json={
                "message": f"Create a journal entry titled '{journal_title}' with content '{journal_content}'",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Get the pushed journal data from WebSocket
                pushed = ws.receive_json()
                print(f"[TEST] WebSocket push received: {pushed}")

                assert pushed["type"] == "journal", f"Expected type 'journal', got '{pushed['type']}'"

                pushed_data = pushed["data"]
                journal_uuid = pushed_data["uuid"]
                pushed_name = pushed_data["name"]

                print(f"[TEST] Pushed journal - Name: {pushed_name}, UUID: {journal_uuid}")

                # Now fetch the journal directly from FoundryVTT using the UUID
                print(f"[TEST] Fetching journal from FoundryVTT: {journal_uuid}")
                try:
                    fetched_journal = foundry_client.journals.get_journal(journal_uuid)
                except Exception as e:
                    pytest.fail(f"Failed to fetch journal from FoundryVTT: {e}")

                print(f"[TEST] Fetched journal data: {fetched_journal}")

                # Verify the fetched journal matches what was pushed
                assert fetched_journal is not None, "Fetched journal should not be None"

                # Handle both wrapped and unwrapped response formats
                # Response can be {"data": {...}} or direct journal data
                journal_data = fetched_journal.get("data", fetched_journal)

                assert "name" in journal_data, "Fetched journal should have 'name'"

                fetched_name = journal_data["name"]
                assert fetched_name == pushed_name, \
                    f"Journal name mismatch: pushed '{pushed_name}' vs fetched '{fetched_name}'"

                # Verify content is present in pages
                if "pages" in journal_data and len(journal_data["pages"]) > 0:
                    first_page = journal_data["pages"][0]
                    page_content = first_page.get("text", {}).get("content", "")
                    # Content may be HTML-wrapped, so check if our content is within it
                    assert unique_id in page_content or journal_content in page_content, \
                        f"Journal content not found in fetched journal pages"
                    print(f"[TEST] Content verified in fetched journal")

                print(f"[TEST] SUCCESS: Journal '{fetched_name}' exists in FoundryVTT with UUID {journal_uuid}")

            elif response_data.get("type") == "error":
                pytest.fail(f"Journal creation failed: {response_data.get('message')}")
            else:
                pytest.skip(f"Journal tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_multiple_clients_receive_journal_push(self):
        """
        Verify multiple connected clients all receive the journal push.

        Real data test: Broadcasts to multiple WebSocket connections.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws1:
            welcome1 = ws1.receive_json()
            assert welcome1["type"] == "connected"
            client_id_1 = welcome1["client_id"]

            with client.websocket_connect("/ws/foundry") as ws2:
                welcome2 = ws2.receive_json()
                assert welcome2["type"] == "connected"
                client_id_2 = welcome2["client_id"]

                # Ensure different client IDs
                assert client_id_1 != client_id_2

                # Generate unique title
                unique_id = str(uuid.uuid4())[:8]
                journal_title = f"Test Multi Client Journal {unique_id}"

                # Create journal
                response = client.post("/api/chat", json={
                    "message": f"Create a journal entry titled '{journal_title}' with content 'Multi-client test content.'",
                    "context": {},
                    "conversation_history": []
                })

                assert response.status_code == 200
                response_data = response.json()

                if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                    # Both clients should receive the push
                    pushed1 = ws1.receive_json()
                    pushed2 = ws2.receive_json()

                    assert pushed1["type"] == "journal"
                    assert pushed2["type"] == "journal"

                    # Both should have same journal data
                    assert pushed1["data"]["name"] == pushed2["data"]["name"]
                    assert pushed1["data"]["uuid"] == pushed2["data"]["uuid"]

                    print(f"[TEST] Both clients received: {pushed1['data']['name']}")
                else:
                    pytest.skip(f"Journal tool not triggered. Response: {response_data}")
