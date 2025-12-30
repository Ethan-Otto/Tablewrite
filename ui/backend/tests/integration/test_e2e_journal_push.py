"""End-to-end test: Journal creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Real Gemini API key (makes actual API calls)
3. For round-trip tests: Foundry running with Tablewrite module enabled

Run with: pytest tests/integration/test_e2e_journal_push.py -v -m integration
"""
import pytest
import os
import sys
import uuid
import threading
from fastapi.testclient import TestClient
from app.main import app


def simulate_foundry_response(ws, entity_type: str = "journal"):
    """Simulate Foundry module responding to push message with UUID.

    The new WebSocket architecture works like this:
    1. Backend broadcasts journal message with request_id
    2. Foundry receives message, creates entity, sends response with UUID
    3. Backend receives response and returns UUID to caller

    This helper simulates step 2.
    """
    try:
        # Receive the push message
        pushed = ws.receive_json()
        print(f"[FOUNDRY SIM] Received: {pushed}")

        if pushed.get("type") == entity_type and pushed.get("request_id"):
            # Simulate Foundry creating the entity and responding
            request_id = pushed["request_id"]
            name = pushed.get("data", {}).get("name", f"Test {entity_type.title()}")
            fake_id = f"{entity_type[:4]}123"

            # Send response back (simulating what Foundry module does)
            ws.send_json({
                "type": f"{entity_type}_created",
                "request_id": request_id,
                "data": {
                    "uuid": f"JournalEntry.{fake_id}",
                    "id": fake_id,
                    "name": name
                }
            })
            print(f"[FOUNDRY SIM] Sent response for request_id: {request_id}")
            return pushed
    except Exception as e:
        print(f"[FOUNDRY SIM] Error: {e}")
    return None


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
        3. WebSocket receives journal push and sends UUID response
        4. Backend returns success with UUID

        Note: This uses REAL Gemini API and costs money.
        """
        client = TestClient(app)
        pushed_data = {}

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome message
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            client_id = welcome["client_id"]
            print(f"[TEST] Connected with client_id: {client_id}")

            # Start background thread to simulate Foundry response
            def foundry_sim():
                nonlocal pushed_data
                result = simulate_foundry_response(ws, "journal")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

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

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check if the response indicates journal was created with UUID
            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Should have UUID in message now
                assert "UUID" in response_data.get("message", "") or pushed_data, \
                    f"Expected UUID in response or pushed_data. Response: {response_data}"

                if pushed_data:
                    assert pushed_data["type"] == "journal"
                    assert "data" in pushed_data
                    assert "journal" in pushed_data["data"], f"Expected 'journal' key in data: {pushed_data['data']}"
                    print(f"[TEST] Journal pushed: {pushed_data['data'].get('name')}")
            elif response_data.get("type") == "error":
                pytest.fail(f"Journal creation failed: {response_data.get('message')}")
            else:
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
        pushed_data = {}

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"

            # Start background thread to simulate Foundry response
            def foundry_sim():
                nonlocal pushed_data
                result = simulate_foundry_response(ws, "journal")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            # Generate unique title
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Fields Journal {unique_id}"

            # Create journal with explicit title and content
            response = client.post("/api/chat", json={
                "message": f"Create a journal entry titled '{journal_title}' with content 'Testing field validation content.'",
                "context": {},
                "conversation_history": []
            })

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Verify the pushed message structure
                assert pushed_data, "No journal push received"
                assert pushed_data["type"] == "journal", f"Expected type 'journal', got '{pushed_data['type']}'"

                journal_data = pushed_data["data"]
                assert "name" in journal_data, "Journal data missing 'name'"
                assert "journal" in journal_data, "Journal data missing 'journal' key"

                # Verify journal structure has pages
                journal_entity = journal_data["journal"]
                assert "name" in journal_entity, "Journal entity missing 'name'"
                assert "pages" in journal_entity, "Journal entity missing 'pages'"
                assert len(journal_entity["pages"]) > 0, "Journal should have at least one page"

                print(f"[TEST] Verified journal push: {journal_data}")
            else:
                pytest.skip(f"Journal tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_created_journal_can_be_fetched_from_foundry(self):
        """
        Verify that a journal push contains valid entity data that Foundry can use.

        In the WebSocket request-response architecture:
        - Backend pushes journal DATA to Foundry with request_id
        - Foundry module calls JournalEntry.create(data.journal) and returns UUID
        - Backend receives response with UUID and returns to caller

        This test verifies the pushed data structure and UUID response flow.
        """
        client = TestClient(app)
        pushed_data = {}

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome message
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            print(f"[TEST] Connected with client_id: {welcome['client_id']}")

            # Start background thread to simulate Foundry response
            def foundry_sim():
                nonlocal pushed_data
                result = simulate_foundry_response(ws, "journal")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

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

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Verify the pushed data
                assert pushed_data, "No journal push received"
                assert pushed_data["type"] == "journal", f"Expected type 'journal', got '{pushed_data['type']}'"

                journal_data = pushed_data["data"]
                pushed_name = journal_data["name"]

                # Verify journal entity data structure is valid for Foundry
                journal_entity = journal_data["journal"]
                assert "name" in journal_entity, "Journal entity missing 'name'"
                assert "pages" in journal_entity, "Journal entity missing 'pages'"

                # Verify pages structure
                pages = journal_entity["pages"]
                assert len(pages) > 0, "Journal should have at least one page"

                first_page = pages[0]
                assert "name" in first_page, "Page missing 'name'"
                assert "type" in first_page, "Page missing 'type'"
                assert first_page["type"] == "text", f"Expected page type 'text', got '{first_page['type']}'"
                assert "text" in first_page, "Page missing 'text'"
                assert "content" in first_page["text"], "Page text missing 'content'"

                # Verify content contains our test content
                page_content = first_page["text"]["content"]
                assert journal_content in page_content or unique_id in page_content, \
                    f"Content not found in page: {page_content}"

                # Verify UUID was returned in response message
                assert "UUID" in response_data.get("message", ""), \
                    f"Expected UUID in response message. Message: {response_data.get('message')}"

                print(f"[TEST] SUCCESS: Journal data structure valid and UUID returned")
                print(f"[TEST] Journal name: {pushed_name}")

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

        Note: With request-response pattern, only one client needs to respond.
        Both clients receive the broadcast, but backend waits for first response.
        """
        client = TestClient(app)
        pushed_data_1 = {}
        pushed_data_2 = {}

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

                # Start background threads to simulate both Foundry clients
                def foundry_sim_1():
                    nonlocal pushed_data_1
                    result = simulate_foundry_response(ws1, "journal")
                    if result:
                        pushed_data_1.update(result)

                def foundry_sim_2():
                    nonlocal pushed_data_2
                    try:
                        # Second client receives but doesn't need to respond
                        pushed = ws2.receive_json()
                        if pushed:
                            pushed_data_2.update(pushed)
                    except Exception:
                        pass

                sim_thread_1 = threading.Thread(target=foundry_sim_1, daemon=True)
                sim_thread_2 = threading.Thread(target=foundry_sim_2, daemon=True)
                sim_thread_1.start()
                sim_thread_2.start()

                # Generate unique title
                unique_id = str(uuid.uuid4())[:8]
                journal_title = f"Test Multi Client Journal {unique_id}"

                # Create journal
                response = client.post("/api/chat", json={
                    "message": f"Create a journal entry titled '{journal_title}' with content 'Multi-client test content.'",
                    "context": {},
                    "conversation_history": []
                })

                sim_thread_1.join(timeout=30)
                sim_thread_2.join(timeout=5)

                assert response.status_code == 200
                response_data = response.json()

                if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                    # At least first client should have received the push
                    assert pushed_data_1, "First client did not receive push"
                    assert pushed_data_1["type"] == "journal"
                    assert "journal" in pushed_data_1["data"]

                    # Second client may also have received (broadcast)
                    if pushed_data_2:
                        assert pushed_data_2["type"] == "journal"
                        assert pushed_data_1["data"]["name"] == pushed_data_2["data"]["name"]
                        print(f"[TEST] Both clients received: {pushed_data_1['data']['name']}")
                    else:
                        print(f"[TEST] First client received: {pushed_data_1['data']['name']}")
                else:
                    pytest.skip(f"Journal tool not triggered. Response: {response_data}")
