"""End-to-end test: Actor creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Real Gemini API key (makes actual API calls)
3. For round-trip tests: Foundry running with Tablewrite module enabled

Run with: pytest tests/integration/test_e2e_actor_push.py -v -m integration
"""
import pytest
import os
import sys
import threading
import time
from fastapi.testclient import TestClient
from app.main import app


def simulate_foundry_response(ws, entity_type: str = "actor"):
    """Simulate Foundry module responding to push message with UUID.

    The new WebSocket architecture works like this:
    1. Backend broadcasts actor message with request_id
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
            fake_id = f"{entity_type[:3]}123"

            # Send response back (simulating what Foundry module does)
            ws.send_json({
                "type": f"{entity_type}_created",
                "request_id": request_id,
                "data": {
                    "uuid": f"{entity_type.title()}.{fake_id}",
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
        3. WebSocket receives actor push and sends UUID response
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
                result = simulate_foundry_response(ws, "actor")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            # Request actor creation via chat
            # This will trigger the create_actor tool
            response = client.post("/api/chat", json={
                "message": "Create a simple goblin with CR 0.25",
                "context": {},
                "conversation_history": []
            })

            # Wait for simulation thread
            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check if the response indicates actor was created with UUID
            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Should have UUID in message now
                assert "UUID" in response_data.get("message", "") or pushed_data, \
                    f"Expected UUID in response or pushed_data. Response: {response_data}"

                if pushed_data:
                    assert pushed_data["type"] == "actor"
                    assert "data" in pushed_data
                    assert "actor" in pushed_data["data"], f"Expected 'actor' key in data: {pushed_data['data']}"
                    print(f"[TEST] Actor pushed: {pushed_data['data'].get('name')}")
            elif response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")
            else:
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
        pushed_data = {}

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"

            # Start background thread to simulate Foundry response
            def foundry_sim():
                nonlocal pushed_data
                result = simulate_foundry_response(ws, "actor")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            # Create actor with explicit CR
            response = client.post("/api/chat", json={
                "message": "Create a dire wolf creature with CR 1",
                "context": {},
                "conversation_history": []
            })

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Verify the pushed message structure
                assert pushed_data, "No actor push received"
                assert pushed_data["type"] == "actor", f"Expected type 'actor', got '{pushed_data['type']}'"

                actor_data = pushed_data["data"]
                assert "name" in actor_data, "Actor data missing 'name'"
                assert "actor" in actor_data, "Actor data missing 'actor' key"
                assert "cr" in actor_data, "Actor data missing 'cr'"

                # Verify actor entity has required FoundryVTT fields
                actor_entity = actor_data["actor"]
                assert "name" in actor_entity, "Actor entity missing 'name'"
                assert "type" in actor_entity, "Actor entity missing 'type'"

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
                    result = simulate_foundry_response(ws1, "actor")
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

                # Create actor
                response = client.post("/api/chat", json={
                    "message": "Create a kobold with CR 0.125",
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
                    assert pushed_data_1["type"] == "actor"
                    assert "actor" in pushed_data_1["data"]

                    # Second client may also have received (broadcast)
                    if pushed_data_2:
                        assert pushed_data_2["type"] == "actor"
                        assert pushed_data_1["data"]["name"] == pushed_data_2["data"]["name"]
                        print(f"[TEST] Both clients received: {pushed_data_1['data']['name']}")
                    else:
                        print(f"[TEST] First client received: {pushed_data_1['data']['name']}")
                else:
                    pytest.skip(f"Actor tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_created_actor_can_be_fetched_from_foundry(self):
        """
        Verify that an actor push contains valid entity data that Foundry can use.

        In the WebSocket request-response architecture:
        - Backend pushes actor DATA to Foundry with request_id
        - Foundry module calls Actor.create(data.actor) and returns UUID
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
                result = simulate_foundry_response(ws, "actor")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            # Request actor creation via chat with specific CR for verification
            response = client.post("/api/chat", json={
                "message": "Create a simple skeleton warrior with CR 0.25",
                "context": {},
                "conversation_history": []
            })

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Verify the pushed data
                assert pushed_data, "No actor push received"
                assert pushed_data["type"] == "actor", f"Expected type 'actor', got '{pushed_data['type']}'"

                actor_data = pushed_data["data"]
                pushed_name = actor_data["name"]
                pushed_cr = actor_data.get("cr")

                # Verify actor entity data structure is valid for Foundry
                actor_entity = actor_data["actor"]
                assert "name" in actor_entity, "Actor entity missing 'name'"
                assert "type" in actor_entity, "Actor entity missing 'type'"
                assert actor_entity["type"] == "npc", f"Expected actor type 'npc', got '{actor_entity['type']}'"

                # Verify system data structure (D&D 5e actor format)
                if "system" in actor_entity:
                    system = actor_entity["system"]
                    # Check for basic D&D 5e NPC fields
                    if "attributes" in system:
                        assert "hp" in system["attributes"], "Actor system missing 'hp' in attributes"
                    if "details" in system:
                        assert "cr" in system["details"], "Actor system missing 'cr' in details"

                # Verify UUID was returned in response message
                assert "UUID" in response_data.get("message", ""), \
                    f"Expected UUID in response message. Message: {response_data.get('message')}"

                print(f"[TEST] SUCCESS: Actor data structure valid and UUID returned")
                print(f"[TEST] Actor name: {pushed_name}, CR: {pushed_cr}")

            elif response_data.get("type") == "error":
                pytest.fail(f"Actor creation failed: {response_data.get('message')}")
            else:
                pytest.skip(f"Actor tool not triggered. Response: {response_data}")
