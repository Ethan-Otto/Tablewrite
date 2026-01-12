"""Tests for JournalEditorTool including WebSocket operations."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestJournalEditorTool:
    """Unit tests for JournalEditorTool."""

    @pytest.mark.asyncio
    async def test_edit_journal_by_uuid_rename(self):
        """Test renaming a journal by UUID."""
        from app.tools.journal_editor import JournalEditorTool
        from app.websocket.push import FetchResult

        # Mock fetch_journal to return current state
        mock_fetch_result = FetchResult(
            success=True,
            entity={"name": "Old Name", "pages": [{"_id": "page1", "text": {"content": "test"}}]}
        )

        # Mock update_journal to return success
        mock_update_result = MagicMock()
        mock_update_result.success = True
        mock_update_result.uuid = "JournalEntry.test123"
        mock_update_result.name = "New Name"

        with patch('app.tools.journal_editor.update_journal', new_callable=AsyncMock, return_value=mock_update_result):
            tool = JournalEditorTool()
            result = await tool.execute(
                journal_uuid="JournalEntry.test123",
                new_name="New Name"
            )

            assert result.type == "text"
            assert "Updated" in result.message
            assert "New Name" in result.message

    @pytest.mark.asyncio
    async def test_edit_journal_by_name_search(self):
        """Test finding and editing a journal by name."""
        from app.tools.journal_editor import JournalEditorTool
        from app.websocket.push import FetchResult

        # Mock list_journals to return matching journal
        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_journal = MagicMock()
        mock_journal.name = "Session Notes"
        mock_journal.uuid = "JournalEntry.found123"
        mock_list_result.journals = [mock_journal]

        # Mock fetch_journal
        mock_fetch_result = FetchResult(
            success=True,
            entity={"name": "Session Notes", "pages": [{"_id": "page1", "text": {"content": "old content"}}]}
        )

        # Mock update_journal
        mock_update_result = MagicMock()
        mock_update_result.success = True
        mock_update_result.uuid = "JournalEntry.found123"
        mock_update_result.name = "Session Notes"

        with patch('app.tools.journal_editor.list_journals', new_callable=AsyncMock, return_value=mock_list_result), \
             patch('app.tools.journal_editor.fetch_journal', new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch('app.tools.journal_editor.update_journal', new_callable=AsyncMock, return_value=mock_update_result):
            tool = JournalEditorTool()
            result = await tool.execute(
                journal_name="Session Notes",
                new_content="<p>Updated content</p>"
            )

            assert result.type == "text"
            assert "Updated" in result.message
            assert "Session Notes" in result.message

    @pytest.mark.asyncio
    async def test_edit_journal_not_found(self):
        """Test error when journal not found."""
        from app.tools.journal_editor import JournalEditorTool

        # Mock list_journals to return empty
        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.journals = []

        with patch('app.tools.journal_editor.list_journals', new_callable=AsyncMock, return_value=mock_list_result):
            tool = JournalEditorTool()
            result = await tool.execute(
                journal_name="Nonexistent Journal",
                new_name="New Name"
            )

            assert result.type == "error"
            assert "Could not find" in result.message

    @pytest.mark.asyncio
    async def test_edit_journal_no_updates(self):
        """Test error when no updates provided."""
        from app.tools.journal_editor import JournalEditorTool

        tool = JournalEditorTool()
        result = await tool.execute(journal_uuid="JournalEntry.test123")

        assert result.type == "error"
        assert "No updates provided" in result.message

    @pytest.mark.asyncio
    async def test_edit_journal_no_identifier(self):
        """Test error when neither name nor UUID provided."""
        from app.tools.journal_editor import JournalEditorTool

        tool = JournalEditorTool()
        result = await tool.execute(new_name="New Name")

        assert result.type == "error"
        assert "provide either a journal name or UUID" in result.message

    @pytest.mark.asyncio
    async def test_edit_journal_append_content(self):
        """Test appending content to a journal."""
        from app.tools.journal_editor import JournalEditorTool
        from app.websocket.push import FetchResult

        # Mock fetch_journal
        mock_fetch_result = FetchResult(
            success=True,
            entity={
                "name": "Test Journal",
                "pages": [{"_id": "page1", "text": {"content": "<p>Original</p>"}}]
            }
        )

        # Mock update_journal
        mock_update_result = MagicMock()
        mock_update_result.success = True
        mock_update_result.uuid = "JournalEntry.test123"
        mock_update_result.name = "Test Journal"

        with patch('app.tools.journal_editor.fetch_journal', new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch('app.tools.journal_editor.update_journal', new_callable=AsyncMock, return_value=mock_update_result) as mock_update:
            tool = JournalEditorTool()
            result = await tool.execute(
                journal_uuid="JournalEntry.test123",
                append_content="<p>Appended</p>"
            )

            assert result.type == "text"
            assert "appended content" in result.message

            # Verify update was called with appended content
            call_args = mock_update.call_args
            updates = call_args[0][1]  # Second positional arg is updates
            assert "pages" in updates

    @pytest.mark.asyncio
    async def test_edit_journal_add_pages(self):
        """Test adding new pages to a journal."""
        from app.tools.journal_editor import JournalEditorTool
        from app.websocket.push import FetchResult

        # Mock fetch_journal
        mock_fetch_result = FetchResult(
            success=True,
            entity={"name": "Test Journal", "pages": []}
        )

        # Mock update_journal
        mock_update_result = MagicMock()
        mock_update_result.success = True
        mock_update_result.uuid = "JournalEntry.test123"
        mock_update_result.name = "Test Journal"

        with patch('app.tools.journal_editor.fetch_journal', new_callable=AsyncMock, return_value=mock_fetch_result), \
             patch('app.tools.journal_editor.update_journal', new_callable=AsyncMock, return_value=mock_update_result):
            tool = JournalEditorTool()
            result = await tool.execute(
                journal_uuid="JournalEntry.test123",
                new_pages=[
                    {"name": "Chapter 1", "content": "<p>Content 1</p>"},
                    {"name": "Chapter 2", "content": "<p>Content 2</p>"}
                ]
            )

            assert result.type == "text"
            assert "added pages" in result.message
            assert "Chapter 1" in result.message
            assert "Chapter 2" in result.message


class TestFindJournalByName:
    """Tests for the find_journal_by_name helper."""

    @pytest.mark.asyncio
    async def test_exact_match(self):
        """Test exact name matching (case-insensitive)."""
        from app.tools.journal_editor import find_journal_by_name

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_journal = MagicMock()
        mock_journal.name = "Session Notes"
        mock_journal.uuid = "JournalEntry.exact123"
        mock_list_result.journals = [mock_journal]

        with patch('app.tools.journal_editor.list_journals', new_callable=AsyncMock, return_value=mock_list_result):
            result = await find_journal_by_name("session notes")
            assert result == "JournalEntry.exact123"

    @pytest.mark.asyncio
    async def test_partial_match(self):
        """Test partial name matching."""
        from app.tools.journal_editor import find_journal_by_name

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_journal = MagicMock()
        mock_journal.name = "Lost Mine of Phandelver Notes"
        mock_journal.uuid = "JournalEntry.partial123"
        mock_list_result.journals = [mock_journal]

        with patch('app.tools.journal_editor.list_journals', new_callable=AsyncMock, return_value=mock_list_result):
            result = await find_journal_by_name("Phandelver")
            assert result == "JournalEntry.partial123"

    @pytest.mark.asyncio
    async def test_no_match(self):
        """Test when no journal matches."""
        from app.tools.journal_editor import find_journal_by_name

        mock_list_result = MagicMock()
        mock_list_result.success = True
        mock_list_result.journals = []

        with patch('app.tools.journal_editor.list_journals', new_callable=AsyncMock, return_value=mock_list_result):
            result = await find_journal_by_name("Nonexistent")
            assert result is None


@pytest.mark.integration
class TestJournalEditorIntegration:
    """Integration tests with real Foundry connection via HTTP API."""

    BACKEND_URL = "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_journal_edit_roundtrip(self, test_folders):
        """
        Round-trip test: Create journal, edit it via PATCH endpoint, verify changes.

        This test:
        1. Creates a journal in /tests folder
        2. Edits the journal (rename + content change) via PATCH
        3. Fetches it back and verifies changes
        4. Cleans up by deleting the journal
        """
        import httpx
        import uuid as uuid_mod
        from tests.conftest import check_backend_and_foundry, get_or_create_test_folder

        await check_backend_and_foundry()

        folder_id = await get_or_create_test_folder("JournalEntry")
        unique_id = str(uuid_mod.uuid4())[:8]
        journal_uuid = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create a test journal
            create_response = await client.post(
                f"{self.BACKEND_URL}/api/foundry/journal",
                json={
                    "name": f"Test Journal for Editing {unique_id}",
                    "folder": folder_id,
                    "pages": [{
                        "name": "Original Page",
                        "type": "text",
                        "text": {"content": "<p>Original content</p>"}
                    }]
                }
            )
            assert create_response.status_code == 200
            create_result = create_response.json()
            assert create_result.get("success"), f"Failed to create journal: {create_result.get('error')}"
            journal_uuid = create_result.get("uuid")
            print(f"[INTEGRATION] Created test journal: {journal_uuid}")

            try:
                # Step 2: Edit the journal via PATCH endpoint
                edit_response = await client.patch(
                    f"{self.BACKEND_URL}/api/foundry/journal/{journal_uuid}",
                    json={
                        "updates": {
                            "name": f"Edited Journal Name {unique_id}"
                        }
                    }
                )
                assert edit_response.status_code == 200
                edit_result = edit_response.json()
                assert edit_result.get("success"), f"Edit failed: {edit_result.get('error')}"
                print(f"[INTEGRATION] Edit result: {edit_result}")

                # Step 3: Fetch the journal back and verify changes
                fetch_response = await client.get(f"{self.BACKEND_URL}/api/foundry/journal/{journal_uuid}")
                assert fetch_response.status_code == 200
                fetch_result = fetch_response.json()
                assert fetch_result.get("success"), f"Fetch failed: {fetch_result.get('error')}"

                fetched = fetch_result.get("entity", {})
                assert f"Edited Journal Name {unique_id}" in fetched["name"], f"Name not updated: {fetched['name']}"
                print(f"[INTEGRATION] Verified journal edit: name='{fetched['name']}'")

            finally:
                # Cleanup: delete the test journal
                if journal_uuid:
                    delete_response = await client.delete(f"{self.BACKEND_URL}/api/foundry/journal/{journal_uuid}")
                    if delete_response.status_code == 200:
                        print(f"[INTEGRATION] Cleaned up test journal: {journal_uuid}")

    @pytest.mark.asyncio
    async def test_journal_edit_tool_integration(self, test_folders):
        """
        Test the JournalEditorTool directly with mocked WebSocket functions
        that call through to the real HTTP API.

        This verifies the tool logic works correctly with real Foundry data.
        """
        import httpx
        import uuid as uuid_mod
        from tests.conftest import check_backend_and_foundry, get_or_create_test_folder
        from app.tools.journal_editor import JournalEditorTool
        from app.websocket.push import FetchResult, JournalListResult, JournalInfo
        from unittest.mock import AsyncMock

        await check_backend_and_foundry()

        folder_id = await get_or_create_test_folder("JournalEntry")
        unique_id = str(uuid_mod.uuid4())[:8]
        unique_name = f"ToolTestJournal{unique_id}"
        journal_uuid = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create a test journal via API
            create_response = await client.post(
                f"{self.BACKEND_URL}/api/foundry/journal",
                json={
                    "name": unique_name,
                    "folder": folder_id,
                    "pages": [{
                        "name": "Page 1",
                        "type": "text",
                        "text": {"content": "<p>Original tool test content</p>"}
                    }]
                }
            )
            assert create_response.status_code == 200
            create_result = create_response.json()
            assert create_result.get("success"), f"Failed to create journal: {create_result.get('error')}"
            journal_uuid = create_result.get("uuid")
            print(f"[INTEGRATION] Created journal for tool test: {journal_uuid}")

            try:
                # Create mock functions that call the real HTTP API
                async def mock_list_journals():
                    resp = await client.get(f"{self.BACKEND_URL}/api/foundry/journals")
                    data = resp.json()
                    if data.get("success"):
                        journals = [
                            JournalInfo(
                                uuid=j["uuid"],
                                id=j["id"],
                                name=j["name"],
                                folder=j.get("folder")
                            )
                            for j in data.get("journals", [])
                        ]
                        return JournalListResult(success=True, journals=journals)
                    return JournalListResult(success=False, error=data.get("error"))

                async def mock_fetch_journal(uuid, timeout=10.0):
                    resp = await client.get(f"{self.BACKEND_URL}/api/foundry/journal/{uuid}")
                    data = resp.json()
                    if data.get("success"):
                        return FetchResult(success=True, entity=data.get("entity"))
                    return FetchResult(success=False, error=data.get("error"))

                async def mock_update_journal(uuid, updates, timeout=10.0):
                    resp = await client.patch(
                        f"{self.BACKEND_URL}/api/foundry/journal/{uuid}",
                        json={"updates": updates}
                    )
                    data = resp.json()
                    result = type('UpdateResult', (), {
                        'success': data.get("success", False),
                        'uuid': data.get("uuid"),
                        'name': data.get("name"),
                        'error': data.get("error") if not data.get("success") else None
                    })()
                    return result

                # Test the tool with these mocked API calls
                with patch('app.tools.journal_editor.list_journals', side_effect=mock_list_journals), \
                     patch('app.tools.journal_editor.fetch_journal', side_effect=mock_fetch_journal), \
                     patch('app.tools.journal_editor.update_journal', side_effect=mock_update_journal):

                    tool = JournalEditorTool()

                    # Edit by name search
                    edit_result = await tool.execute(
                        journal_name=unique_name,
                        new_name=f"Renamed{unique_id}"
                    )

                    assert edit_result.type == "text", f"Edit failed: {edit_result.message}"
                    assert "Updated" in edit_result.message
                    print(f"[INTEGRATION] Tool edit result: {edit_result.message}")

                # Verify changes via direct API
                fetch_response = await client.get(f"{self.BACKEND_URL}/api/foundry/journal/{journal_uuid}")
                fetch_result = fetch_response.json()
                assert fetch_result.get("success")
                assert f"Renamed{unique_id}" in fetch_result["entity"]["name"]
                print(f"[INTEGRATION] Verified tool edit via API")

            finally:
                if journal_uuid:
                    await client.delete(f"{self.BACKEND_URL}/api/foundry/journal/{journal_uuid}")
                    print(f"[INTEGRATION] Cleaned up: {journal_uuid}")
