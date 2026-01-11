"""End-to-end tests for journal query through chat endpoint.

Tests the full flow: chat message -> Gemini function calling -> journal query tool -> response.
Uses Playwright for browser automation when testing UI, and direct API calls otherwise.
"""

import pytest
import httpx


class TestJournalQueryChatE2E:
    """E2E tests for journal query via chat endpoint.

    Prerequisites:
    - Backend running at localhost:8000
    - Foundry connected via WebSocket
    - "Cool Adventure" journal exists with "Part 2" page containing "Banana"
    """

    TEST_JOURNAL_NAME = "Cool Adventure"

    @pytest.fixture
    def client(self):
        """HTTP client for API calls."""
        return httpx.Client(base_url="http://localhost:8000", timeout=60.0)

    @pytest.mark.integration
    def test_chat_query_returns_sources(self, client):
        """Test that chat query returns sources with page links."""
        # Verify Foundry is connected first
        status = client.get("/api/foundry/status")
        assert status.status_code == 200
        status_data = status.json()
        assert status_data.get("status") == "connected", "Foundry not connected"

        # Send chat message asking about journal content
        response = client.post(
            "/api/chat",
            json={
                "message": f"What is in part 2 of {self.TEST_JOURNAL_NAME}",
                "conversation_history": [],
                "context": {}
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response has expected structure
        assert data.get("type") == "text", f"Expected text response, got {data.get('type')}"
        assert data.get("message"), "Response message is empty"

        # Verify sources are in the response
        message = data["message"]
        assert "Sources:" in message, f"No 'Sources:' in response: {message}"
        assert self.TEST_JOURNAL_NAME in message, f"Journal name not in response: {message}"
        assert "Part 2" in message, f"'Part 2' not in response: {message}"

        # Verify we have actual Foundry links (not just empty sources)
        assert "@UUID[" in message, f"No Foundry link in response: {message}"
        assert "JournalEntry." in message, f"No JournalEntry UUID in response: {message}"

        # Verify data contains sources with page_id
        sources = data.get("data", {}).get("sources", [])
        assert len(sources) > 0, "No sources in data"
        assert sources[0].get("page_id"), "Source has no page_id"
        assert sources[0].get("section") == "Part 2", f"Source section is not 'Part 2': {sources[0]}"

    @pytest.mark.integration
    def test_direct_tool_query_part3_strawberry(self, client):
        """Test querying Part 3 which contains 'Strawberry' via direct tool API."""
        # Use direct tool endpoint for reliable testing
        response = client.post(
            "/api/tools/query_journal",
            json={
                "query": "What is in part 3",
                "query_type": "question",
                "journal_name": self.TEST_JOURNAL_NAME,
                "folder": "Lost Mine of Phandelver test"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response mentions strawberry (case-insensitive)
        message = data["message"].lower()
        assert "strawberry" in message, f"'strawberry' not in response: {data['message']}"

        # Verify sources link to Part 3
        sources = data.get("data", {}).get("sources", [])
        assert len(sources) > 0, "No sources returned"
        assert sources[0].get("section") == "Part 3", f"Wrong section: {sources[0]}"
        assert sources[0].get("page_id"), f"No page_id: {sources[0]}"

    @pytest.mark.integration
    def test_direct_tool_endpoint_returns_sources(self, client):
        """Test direct tool endpoint returns sources correctly."""
        response = client.post(
            "/api/tools/query_journal",
            json={
                "query": f"What is in part 2 of {self.TEST_JOURNAL_NAME}",
                "query_type": "question",
                "folder": "Lost Mine of Phandelver test"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify source reference is complete
        sources = data.get("data", {}).get("sources", [])
        assert len(sources) > 0, "No sources returned"
        assert sources[0].get("page_id"), f"No page_id: {sources[0]}"
        assert sources[0].get("section") == "Part 2", f"Wrong section: {sources[0]}"

        # Verify foundry_links are generated
        links = data.get("data", {}).get("foundry_links", [])
        assert len(links) > 0, "No foundry_links returned"
        assert "@UUID[JournalEntry." in links[0], f"Invalid link format: {links[0]}"
