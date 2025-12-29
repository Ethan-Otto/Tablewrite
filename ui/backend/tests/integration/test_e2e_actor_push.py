"""End-to-end test: Actor creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled
3. Real Gemini API key (makes actual API calls)

Run with: pytest tests/integration/test_e2e_actor_push.py -v -m integration
"""
import pytest
import os
import sys
from fastapi.testclient import TestClient
from app.main import app

# Add src directory to path for FoundryClient import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'src'))
from foundry.client import FoundryClient


@pytest.mark.integration
class TestActorPushE2E:
    """End-to-end actor push tests (real Gemini API)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_create_actor_via_chat_pushes_to_foundry(self):
        """
        Full flow test:
        1. Connect WebSocket (simulating Foundry)
        2. Call /api/chat with actor creation request
        3. Verify WebSocket receives actor push

        Note: This uses REAL Gemini API and costs money.
        """
        client = TestClient(app)
        received_messages = []

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome message
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            client_id = welcome["client_id"]
            print(f"[TEST] Connected with client_id: {client_id}")

            # Request actor creation via chat
            # This will trigger the create_actor tool
            response = client.post("/api/chat", json={
                "message": "Create a simple goblin with CR 0.25",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check if the response indicates actor was created
            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Actor was created successfully, now check for WebSocket push
                # The push happens during the request, so we should receive it
                try:
                    pushed = ws.receive_json()
                    print(f"[TEST] Received WebSocket message: {pushed}")

                    assert pushed["type"] == "actor"
                    assert "name" in pushed["data"]
                    assert "uuid" in pushed["data"]
                    print(f"[TEST] Actor pushed: {pushed['data']['name']}")
                except Exception as e:
                    # WebSocket message might have been received before we checked
                    pytest.fail(f"WebSocket push not received: {e}")
            elif response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")
            else:
                # Tool might not have been triggered (Gemini didn't call it)
                pytest.skip(f"Actor tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_actor_push_contains_required_fields(self):
        """
        Verify actor push message has all required fields.

        Real data test: Uses actual Gemini API to create a creature.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"

            # Create actor with explicit CR
            response = client.post("/api/chat", json={
                "message": "Create a dire wolf creature with CR 1",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Check the pushed message structure
                pushed = ws.receive_json()

                assert pushed["type"] == "actor", f"Expected type 'actor', got '{pushed['type']}'"

                actor_data = pushed["data"]
                assert "name" in actor_data, "Actor data missing 'name'"
                assert "uuid" in actor_data, "Actor data missing 'uuid'"
                assert "cr" in actor_data, "Actor data missing 'cr'"

                # Verify UUID format (FoundryVTT format: Actor.xxxxx)
                assert actor_data["uuid"].startswith("Actor."), \
                    f"Invalid UUID format: {actor_data['uuid']}"

                print(f"[TEST] Verified actor push: {actor_data}")
            else:
                pytest.skip(f"Actor tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_multiple_clients_receive_actor_push(self):
        """
        Verify multiple connected clients all receive the actor push.

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

                # Create actor
                response = client.post("/api/chat", json={
                    "message": "Create a kobold with CR 0.125",
                    "context": {},
                    "conversation_history": []
                })

                assert response.status_code == 200
                response_data = response.json()

                if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                    # Both clients should receive the push
                    pushed1 = ws1.receive_json()
                    pushed2 = ws2.receive_json()

                    assert pushed1["type"] == "actor"
                    assert pushed2["type"] == "actor"

                    # Both should have same actor data
                    assert pushed1["data"]["name"] == pushed2["data"]["name"]
                    assert pushed1["data"]["uuid"] == pushed2["data"]["uuid"]

                    print(f"[TEST] Both clients received: {pushed1['data']['name']}")
                else:
                    pytest.skip(f"Actor tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_created_actor_can_be_fetched_from_foundry(self):
        """
        Verify that an actor created via chat actually exists in FoundryVTT.

        Full flow test:
        1. Create actor via chat (triggers Gemini + FoundryVTT creation)
        2. Get UUID from WebSocket push message
        3. Use FoundryClient to fetch the actor directly from FoundryVTT
        4. Verify fetched actor data matches what was pushed

        This test proves the actor is not just pushed via WebSocket but
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

            # Request actor creation via chat with specific CR for verification
            response = client.post("/api/chat", json={
                "message": "Create a simple skeleton warrior with CR 0.25",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Get the pushed actor data from WebSocket
                pushed = ws.receive_json()
                print(f"[TEST] WebSocket push received: {pushed}")

                assert pushed["type"] == "actor", f"Expected type 'actor', got '{pushed['type']}'"

                pushed_data = pushed["data"]
                actor_uuid = pushed_data["uuid"]
                pushed_name = pushed_data["name"]
                pushed_cr = pushed_data.get("cr")

                print(f"[TEST] Pushed actor - Name: {pushed_name}, UUID: {actor_uuid}, CR: {pushed_cr}")

                # Now fetch the actor directly from FoundryVTT using the UUID
                print(f"[TEST] Fetching actor from FoundryVTT: {actor_uuid}")
                try:
                    fetched_actor = foundry_client.actors.get_actor(actor_uuid)
                except Exception as e:
                    pytest.fail(f"Failed to fetch actor from FoundryVTT: {e}")

                print(f"[TEST] Fetched actor data: {fetched_actor}")

                # Verify the fetched actor matches what was pushed
                assert fetched_actor is not None, "Fetched actor should not be None"
                assert "name" in fetched_actor, "Fetched actor should have 'name'"

                fetched_name = fetched_actor["name"]
                assert fetched_name == pushed_name, \
                    f"Actor name mismatch: pushed '{pushed_name}' vs fetched '{fetched_name}'"

                # Verify CR if present in both
                if pushed_cr is not None:
                    fetched_cr = None
                    # CR is nested in system.details.cr for D&D 5e actors
                    if "system" in fetched_actor:
                        fetched_cr = fetched_actor.get("system", {}).get("details", {}).get("cr")

                    if fetched_cr is not None:
                        assert float(fetched_cr) == float(pushed_cr), \
                            f"Actor CR mismatch: pushed {pushed_cr} vs fetched {fetched_cr}"
                        print(f"[TEST] CR verified: {fetched_cr}")

                print(f"[TEST] SUCCESS: Actor '{fetched_name}' exists in FoundryVTT with UUID {actor_uuid}")

            elif response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")
            else:
                pytest.skip(f"Actor tool not triggered. Response: {response_data}")
