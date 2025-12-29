"""End-to-end test: Scene creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled
3. Real Gemini API key (makes actual API calls)

Run with: pytest tests/integration/test_e2e_scene_push.py -v -m integration
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
class TestScenePushE2E:
    """End-to-end scene push tests (real FoundryVTT API)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_create_scene_via_chat_pushes_to_foundry(self):
        """
        Full flow test:
        1. Connect WebSocket (simulating Foundry)
        2. Call /api/chat with scene creation request
        3. Verify WebSocket receives scene push

        Note: This uses REAL Gemini API and FoundryVTT REST API.
        """
        # Skip if Foundry environment variables not set
        required_env_vars = ["FOUNDRY_RELAY_URL", "FOUNDRY_URL", "FOUNDRY_API_KEY", "FOUNDRY_CLIENT_ID"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing environment variables: {', '.join(missing_vars)}")

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome message
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            client_id = welcome["client_id"]
            print(f"[TEST] Connected with client_id: {client_id}")

            # Request scene creation via chat
            # This will trigger the create_scene tool
            response = client.post("/api/chat", json={
                "message": "Create a simple scene called 'Test Forest Clearing'",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            # Check if the response indicates scene was created
            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Scene was created successfully, now check for WebSocket push
                try:
                    pushed = ws.receive_json()
                    print(f"[TEST] Received WebSocket message: {pushed}")

                    assert pushed["type"] == "scene"
                    assert "name" in pushed["data"]
                    assert "uuid" in pushed["data"]
                    print(f"[TEST] Scene pushed: {pushed['data']['name']}")
                except Exception as e:
                    pytest.fail(f"WebSocket push not received: {e}")
            elif response_data.get("type") == "error":
                pytest.fail(f"Scene creation failed: {response_data.get('message')}")
            else:
                # Tool might not have been triggered (Gemini didn't call it)
                pytest.skip(f"Scene tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_scene_push_contains_required_fields(self):
        """
        Verify scene push message has all required fields.

        Real data test: Uses actual FoundryVTT API to create a scene.
        """
        # Skip if Foundry environment variables not set
        required_env_vars = ["FOUNDRY_RELAY_URL", "FOUNDRY_URL", "FOUNDRY_API_KEY", "FOUNDRY_CLIENT_ID"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing environment variables: {', '.join(missing_vars)}")

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"

            # Create scene with explicit name
            response = client.post("/api/chat", json={
                "message": "Create a scene named 'Test Dungeon Room'",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Check the pushed message structure
                pushed = ws.receive_json()

                assert pushed["type"] == "scene", f"Expected type 'scene', got '{pushed['type']}'"

                scene_data = pushed["data"]
                assert "name" in scene_data, "Scene data missing 'name'"
                assert "uuid" in scene_data, "Scene data missing 'uuid'"

                # Verify UUID format (FoundryVTT format: Scene.xxxxx)
                assert scene_data["uuid"].startswith("Scene."), \
                    f"Invalid UUID format: {scene_data['uuid']}"

                print(f"[TEST] Verified scene push: {scene_data}")
            else:
                pytest.skip(f"Scene tool not triggered. Response: {response_data}")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_created_scene_can_be_fetched_from_foundry(self):
        """
        Verify that a scene created via chat actually exists in FoundryVTT.

        Full flow test:
        1. Create scene via chat (triggers FoundryVTT creation)
        2. Get UUID from WebSocket push message
        3. Use FoundryClient to fetch the scene directly from FoundryVTT
        4. Verify fetched scene matches (name)

        This test proves the scene is not just pushed via WebSocket but
        actually exists in the FoundryVTT database and can be retrieved.

        Real data test: Uses actual FoundryVTT REST API.
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

            # Request scene creation via chat with specific name for verification
            response = client.post("/api/chat", json={
                "message": "Create a scene named 'E2E Test Cave'",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200
            response_data = response.json()
            print(f"[TEST] Chat response: {response_data}")

            if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                # Get the pushed scene data from WebSocket
                pushed = ws.receive_json()
                print(f"[TEST] WebSocket push received: {pushed}")

                assert pushed["type"] == "scene", f"Expected type 'scene', got '{pushed['type']}'"

                pushed_data = pushed["data"]
                scene_uuid = pushed_data["uuid"]
                pushed_name = pushed_data["name"]

                print(f"[TEST] Pushed scene - Name: {pushed_name}, UUID: {scene_uuid}")

                # Now fetch the scene directly from FoundryVTT using the UUID
                print(f"[TEST] Fetching scene from FoundryVTT: {scene_uuid}")
                try:
                    fetched_scene = foundry_client.scenes.get_scene(scene_uuid)
                except Exception as e:
                    pytest.fail(f"Failed to fetch scene from FoundryVTT: {e}")

                print(f"[TEST] Fetched scene data: {fetched_scene}")

                # Verify the fetched scene matches what was pushed
                assert fetched_scene is not None, "Fetched scene should not be None"
                assert "name" in fetched_scene, "Fetched scene should have 'name'"

                fetched_name = fetched_scene["name"]
                assert fetched_name == pushed_name, \
                    f"Scene name mismatch: pushed '{pushed_name}' vs fetched '{fetched_name}'"

                print(f"[TEST] SUCCESS: Scene '{fetched_name}' exists in FoundryVTT with UUID {scene_uuid}")

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

        Real data test: Broadcasts to multiple WebSocket connections.
        """
        # Skip if Foundry environment variables not set
        required_env_vars = ["FOUNDRY_RELAY_URL", "FOUNDRY_URL", "FOUNDRY_API_KEY", "FOUNDRY_CLIENT_ID"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Missing environment variables: {', '.join(missing_vars)}")

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

                # Create scene
                response = client.post("/api/chat", json={
                    "message": "Create a scene called 'Multi-Client Test Room'",
                    "context": {},
                    "conversation_history": []
                })

                assert response.status_code == 200
                response_data = response.json()

                if response_data.get("type") == "text" and "Created" in response_data.get("message", ""):
                    # Both clients should receive the push
                    pushed1 = ws1.receive_json()
                    pushed2 = ws2.receive_json()

                    assert pushed1["type"] == "scene"
                    assert pushed2["type"] == "scene"

                    # Both should have same scene data
                    assert pushed1["data"]["name"] == pushed2["data"]["name"]
                    assert pushed1["data"]["uuid"] == pushed2["data"]["uuid"]

                    print(f"[TEST] Both clients received: {pushed1['data']['name']}")
                else:
                    pytest.skip(f"Scene tool not triggered. Response: {response_data}")
