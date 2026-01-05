"""End-to-end test: Journal creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled

Run with: pytest tests/integration/test_e2e_journal_push.py -v -m integration
"""
import pytest
import os
import uuid
import httpx

from tests.conftest import get_or_create_tests_folder, check_backend_and_foundry

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
class TestJournalPushE2E:
    """End-to-end journal push tests (real Foundry)."""

    @pytest.mark.asyncio
    async def test_create_journal_via_api(self):
        """
        Full flow test: Create journal via API and verify.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for JournalEntry
        folder_id = await get_or_create_tests_folder("JournalEntry")

        async with httpx.AsyncClient() as client:
            # Generate unique title to avoid conflicts
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Journal {unique_id}"

            # Create journal entry via direct API
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/journal",
                json={
                    "name": journal_title,
                    "folder": folder_id,
                    "pages": [
                        {
                            "name": "Page 1",
                            "type": "text",
                            "text": {"content": "<p>Test content</p>"}
                        }
                    ]
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()

            if not result.get("success"):
                pytest.fail(f"Journal creation failed: {result.get('error')}")

            created_uuid = result.get("uuid")
            assert created_uuid, "No UUID returned"
            assert created_uuid.startswith("JournalEntry."), f"Invalid UUID format: {created_uuid}"

            print(f"[TEST] Created journal: {created_uuid}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/journal/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_journal_push_contains_required_fields(self):
        """
        Verify journal with pages is created with correct structure.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for JournalEntry
        folder_id = await get_or_create_tests_folder("JournalEntry")

        async with httpx.AsyncClient() as client:
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Fields Journal {unique_id}"

            response = await client.post(
                f"{BACKEND_URL}/api/foundry/journal",
                json={
                    "name": journal_title,
                    "folder": folder_id,
                    "pages": [
                        {
                            "name": "Introduction",
                            "type": "text",
                            "text": {"content": "<h1>Introduction</h1><p>Welcome!</p>"}
                        },
                        {
                            "name": "Chapter 1",
                            "type": "text",
                            "text": {"content": "<h1>Chapter 1</h1><p>Content here.</p>"}
                        }
                    ]
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()

            if not result.get("success"):
                pytest.fail(f"Journal creation failed: {result.get('error')}")

            created_uuid = result.get("uuid")
            assert created_uuid, "No UUID returned"

            # Fetch journal to verify pages
            fetch_response = await client.get(f"{BACKEND_URL}/api/foundry/journal/{created_uuid}")
            assert fetch_response.status_code == 200

            fetch_result = fetch_response.json()
            if fetch_result.get("success"):
                journal = fetch_result.get("entity", {})
                pages = journal.get("pages", [])
                assert len(pages) >= 2, f"Expected 2+ pages, got {len(pages)}"
                print(f"[TEST] Journal has {len(pages)} pages")
            else:
                pytest.fail(f"Failed to fetch journal: {fetch_result.get('error')}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/journal/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_created_journal_can_be_fetched_from_foundry(self):
        """
        Verify created journal can be fetched back from Foundry.
        """
        await check_backend_and_foundry()
        created_uuid = None

        # Get or create /tests folder for JournalEntry
        folder_id = await get_or_create_tests_folder("JournalEntry")

        async with httpx.AsyncClient() as client:
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Fetch Journal {unique_id}"

            # Create
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/journal",
                json={
                    "name": journal_title,
                    "folder": folder_id,
                    "pages": [
                        {"name": "Content", "type": "text", "text": {"content": "<p>Fetchable!</p>"}}
                    ]
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"
            created_uuid = result.get("uuid")

            # Fetch
            fetch_response = await client.get(f"{BACKEND_URL}/api/foundry/journal/{created_uuid}")
            assert fetch_response.status_code == 200

            fetch_result = fetch_response.json()
            assert fetch_result.get("success"), f"Fetch failed: {fetch_result.get('error')}"

            journal = fetch_result.get("entity", {})
            assert journal.get("name") == journal_title

            print(f"[TEST] Successfully fetched: {journal.get('name')}")

            # Cleanup
            if created_uuid:
                try:
                    await client.delete(f"{BACKEND_URL}/api/foundry/journal/{created_uuid}")
                except Exception as e:
                    print(f"Warning: Cleanup failed: {e}")

    @pytest.mark.asyncio
    async def test_journal_can_be_deleted(self):
        """
        Verify journal can be created and deleted.
        """
        await check_backend_and_foundry()

        # Get or create /tests folder for JournalEntry
        folder_id = await get_or_create_tests_folder("JournalEntry")

        async with httpx.AsyncClient() as client:
            unique_id = str(uuid.uuid4())[:8]
            journal_title = f"Test Delete Journal {unique_id}"

            # Create
            response = await client.post(
                f"{BACKEND_URL}/api/foundry/journal",
                json={
                    "name": journal_title,
                    "folder": folder_id,
                    "pages": [
                        {"name": "Content", "type": "text", "text": {"content": "<p>Delete me!</p>"}}
                    ]
                },
                timeout=30.0
            )

            assert response.status_code == 200
            result = response.json()
            assert result.get("success"), f"Create failed: {result.get('error')}"
            created_uuid = result.get("uuid")

            # Delete
            delete_response = await client.delete(f"{BACKEND_URL}/api/foundry/journal/{created_uuid}")
            assert delete_response.status_code == 200

            delete_result = delete_response.json()
            assert delete_result.get("success"), f"Delete failed: {delete_result.get('error')}"

            print(f"[TEST] Successfully deleted journal")
