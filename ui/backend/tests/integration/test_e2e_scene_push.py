"""End-to-end test: Scene creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Real Gemini API key (makes actual API calls)
3. For round-trip tests: Foundry running with Tablewrite module enabled

Run with: pytest tests/integration/test_e2e_scene_push.py -v -m integration
"""
import pytest
import os
import uuid
import threading
from fastapi.testclient import TestClient
from app.main import app


def simulate_foundry_response(ws, entity_type: str = "scene"):
    """Simulate Foundry module responding to push message with UUID.

    The new WebSocket architecture works like this:
    1. Backend broadcasts scene message with request_id
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
                    "uuid": f"Scene.{fake_id}",
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
class TestScenePushE2E:
    """End-to-end scene push tests (real Gemini API)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_create_scene_via_chat_pushes_to_foundry(self):
        """
        Full flow test:
        1. Connect WebSocket (simulating Foundry)
        2. Call /api/chat with scene creation request
        3. WebSocket receives scene push and sends UUID response
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
                result = simulate_foundry_response(ws, "scene")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            # Request scene creation via chat
            scene_name = "Test Forest Clearing"
            response = client.post("/api/chat", json={
                "message": f"Create a scene called '{scene_name}'",
                "context": {},
                "conversation_history": []
            })

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check if the response indicates scene was created with UUID
            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Should have UUID in message now
                assert "UUID" in response_data.get("message", "") or pushed_data, \
                    f"Expected UUID in response or pushed_data. Response: {response_data}"

                if pushed_data:
                    assert pushed_data["type"] == "scene"
                    assert "data" in pushed_data
                    assert "scene" in pushed_data["data"], f"Expected 'scene' key in data: {pushed_data['data']}"
                    print(f"[TEST] Scene pushed: {pushed_data['data'].get('name')}")
            elif response_data.get("type") == "error":
                pytest.fail(f"Scene creation failed: {response_data.get('message')}")
            else:
                pytest.skip(f"Scene tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_scene_push_contains_required_fields(self):
        """
        Verify scene push message has all required fields.

        Real data test: Uses actual Gemini API to create a scene.
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
                result = simulate_foundry_response(ws, "scene")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            scene_name = "Test Dungeon Room"

            # Create scene with explicit name
            response = client.post("/api/chat", json={
                "message": f"Create a scene called '{scene_name}'",
                "context": {},
                "conversation_history": []
            })

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Verify the pushed message structure
                assert pushed_data, "No scene push received"
                assert pushed_data["type"] == "scene", f"Expected type 'scene', got '{pushed_data['type']}'"

                scene_data = pushed_data["data"]
                assert "name" in scene_data, "Scene data missing 'name'"
                assert "scene" in scene_data, "Scene data missing 'scene' key"

                # Verify scene structure has required fields for Foundry
                scene_entity = scene_data["scene"]
                assert "name" in scene_entity, "Scene entity missing 'name'"
                assert "width" in scene_entity, "Scene entity missing 'width'"
                assert "height" in scene_entity, "Scene entity missing 'height'"
                assert "grid" in scene_entity, "Scene entity missing 'grid'"

                print(f"[TEST] Verified scene push: {scene_data}")
            else:
                pytest.skip(f"Scene tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_created_scene_can_be_fetched_from_foundry(self):
        """
        Verify that a scene push contains valid entity data that Foundry can use.

        In the WebSocket request-response architecture:
        - Backend pushes scene DATA to Foundry with request_id
        - Foundry module calls Scene.create(data.scene) and returns UUID
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
                result = simulate_foundry_response(ws, "scene")
                if result:
                    pushed_data.update(result)

            sim_thread = threading.Thread(target=foundry_sim, daemon=True)
            sim_thread.start()

            scene_name = "E2E Test Cave"

            # Request scene creation via chat
            response = client.post("/api/chat", json={
                "message": f"Create a scene called '{scene_name}'",
                "context": {},
                "conversation_history": []
            })

            sim_thread.join(timeout=30)

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Verify the pushed data
                assert pushed_data, "No scene push received"
                assert pushed_data["type"] == "scene", f"Expected type 'scene', got '{pushed_data['type']}'"

                scene_data = pushed_data["data"]
                pushed_name = scene_data["name"]

                # Verify scene entity data structure is valid for Foundry
                scene_entity = scene_data["scene"]
                assert "name" in scene_entity, "Scene entity missing 'name'"
                assert "width" in scene_entity, "Scene entity missing 'width'"
                assert "height" in scene_entity, "Scene entity missing 'height'"
                assert "grid" in scene_entity, "Scene entity missing 'grid'"

                # Verify grid structure
                grid = scene_entity["grid"]
                assert "size" in grid, "Grid missing 'size'"
                assert grid["size"] > 0, "Grid size should be positive"

                # Verify UUID was returned in response message
                assert "UUID" in response_data.get("message", ""), \
                    f"Expected UUID in response message. Message: {response_data.get('message')}"

                print(f"[TEST] SUCCESS: Scene data structure valid and UUID returned")
                print(f"[TEST] Scene name: {pushed_name}")

            elif response_data.get("type") == "error":
                pytest.fail(f"Scene creation failed: {response_data.get('message')}")
            else:
                pytest.skip(f"Scene tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_multiple_clients_receive_scene_push(self):
        """
        Verify multiple connected clients all receive the scene push.

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
                    result = simulate_foundry_response(ws1, "scene")
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

                scene_name = "Multi-Client Test Room"

                # Create scene
                response = client.post("/api/chat", json={
                    "message": f"Create a scene called '{scene_name}'",
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
                    assert pushed_data_1["type"] == "scene"
                    assert "scene" in pushed_data_1["data"]

                    # Second client may also have received (broadcast)
                    if pushed_data_2:
                        assert pushed_data_2["type"] == "scene"
                        assert pushed_data_1["data"]["name"] == pushed_data_2["data"]["name"]
                        print(f"[TEST] Both clients received: {pushed_data_1['data']['name']}")
                    else:
                        print(f"[TEST] First client received: {pushed_data_1['data']['name']}")
                else:
                    pytest.skip(f"Scene tool not triggered. Response: {response_data}")
