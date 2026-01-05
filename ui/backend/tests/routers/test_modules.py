"""Tests for modules router - module processing endpoint.

Run with: pytest ui/backend/tests/routers/test_modules.py -v
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# Path to test PDF relative to this file
TEST_PDF_PATH = Path(__file__).parent.parent.parent.parent.parent / "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"


@pytest.mark.unit
class TestProcessModuleEndpointUnit:
    """Unit tests for POST /api/modules/process with mocked processing."""

    def test_process_module_endpoint_exists(self):
        """POST /api/modules/process returns 422 when file is missing (endpoint exists)."""
        response = client.post(
            "/api/modules/process",
            data={
                "module_name": "Test Module",
                "extract_journal": "true",
                "extract_actors": "false",
                "extract_battle_maps": "false",
                "generate_scene_artwork": "false",
            }
            # No file provided
        )

        # 422 means endpoint exists but validation failed (missing required file)
        assert response.status_code == 422

    def test_process_module_rejects_non_pdf_file(self):
        """POST /api/modules/process returns 400 for non-PDF files."""
        response = client.post(
            "/api/modules/process",
            files={"file": ("document.txt", b"Not a PDF file", "text/plain")},
            data={
                "module_name": "Test Module",
            }
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Only PDF files are accepted"

    def test_process_module_success(self):
        """POST /api/modules/process returns success with stub result."""
        mock_result = {
            "success": True,
            "folders": {},
            "created": {
                "journal": None,
                "actors": [],
                "scenes": [],
                "artwork_journal": None
            }
        }

        mock_folders = {"actors": "folder1", "scenes": "folder2", "journals": "folder3"}

        with patch('app.routers.modules.process_module_sync', return_value=mock_result) as mock_process, \
             patch('app.routers.modules.create_folders_for_module', return_value=mock_folders):
            # Use actual test PDF file
            assert TEST_PDF_PATH.exists(), f"Test PDF not found: {TEST_PDF_PATH}"

            with open(TEST_PDF_PATH, "rb") as f:
                pdf_content = f.read()

            response = client.post(
                "/api/modules/process",
                files={"file": ("test_module.pdf", pdf_content, "application/pdf")},
                data={
                    "module_name": "Lost Mine of Phandelver",
                    "extract_journal": "true",
                    "extract_actors": "false",
                    "extract_battle_maps": "false",
                    "generate_scene_artwork": "false",
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "folders" in data
            assert "created" in data
            assert data["created"]["journal"] is None
            assert data["created"]["actors"] == []
            assert data["created"]["scenes"] == []
            assert data["created"]["artwork_journal"] is None

            # Verify process_module_sync was called
            mock_process.assert_called_once()

    def test_process_module_options_parsed(self):
        """POST /api/modules/process correctly parses form options."""
        mock_result = {
            "success": True,
            "folders": {},
            "created": {
                "journal": None,
                "actors": [],
                "scenes": [],
                "artwork_journal": None
            }
        }

        mock_folders = {"actors": "folder1", "scenes": "folder2", "journals": "folder3"}

        with patch('app.routers.modules.process_module_sync', return_value=mock_result) as mock_process, \
             patch('app.routers.modules.create_folders_for_module', return_value=mock_folders):
            assert TEST_PDF_PATH.exists(), f"Test PDF not found: {TEST_PDF_PATH}"

            with open(TEST_PDF_PATH, "rb") as f:
                pdf_content = f.read()

            response = client.post(
                "/api/modules/process",
                files={"file": ("module.pdf", pdf_content, "application/pdf")},
                data={
                    "module_name": "My Custom Module",
                    "extract_journal": "true",
                    "extract_actors": "true",
                    "extract_battle_maps": "false",
                    "generate_scene_artwork": "true",
                }
            )

            assert response.status_code == 200

            # Verify the call args
            call_args = mock_process.call_args
            # All args passed as keyword args (via lambda)
            kwargs = call_args.kwargs
            assert "pdf_path" in kwargs
            assert isinstance(kwargs["pdf_path"], Path)
            assert kwargs["module_name"] == "My Custom Module"
            assert kwargs["extract_journal"] is True
            assert kwargs["extract_actors"] is True
            assert kwargs["extract_battle_maps"] is False
            assert kwargs["generate_scene_artwork"] is True

    def test_process_module_all_options_false(self):
        """POST /api/modules/process handles all options set to false."""
        mock_result = {
            "success": True,
            "folders": {},
            "created": {
                "journal": None,
                "actors": [],
                "scenes": [],
                "artwork_journal": None
            }
        }

        mock_folders = {"actors": "folder1", "scenes": "folder2", "journals": "folder3"}

        with patch('app.routers.modules.process_module_sync', return_value=mock_result) as mock_process, \
             patch('app.routers.modules.create_folders_for_module', return_value=mock_folders):
            assert TEST_PDF_PATH.exists(), f"Test PDF not found: {TEST_PDF_PATH}"

            with open(TEST_PDF_PATH, "rb") as f:
                pdf_content = f.read()

            response = client.post(
                "/api/modules/process",
                files={"file": ("module.pdf", pdf_content, "application/pdf")},
                data={
                    "module_name": "Test",
                    "extract_journal": "false",
                    "extract_actors": "false",
                    "extract_battle_maps": "false",
                    "generate_scene_artwork": "false",
                }
            )

            assert response.status_code == 200

            # Verify all options are False
            kwargs = mock_process.call_args.kwargs
            assert kwargs["extract_journal"] is False
            assert kwargs["extract_actors"] is False
            assert kwargs["extract_battle_maps"] is False
            assert kwargs["generate_scene_artwork"] is False

    def test_process_module_default_options(self):
        """POST /api/modules/process uses default values when options not provided."""
        mock_result = {
            "success": True,
            "folders": {},
            "created": {
                "journal": None,
                "actors": [],
                "scenes": [],
                "artwork_journal": None
            }
        }

        mock_folders = {"actors": "folder1", "scenes": "folder2", "journals": "folder3"}

        with patch('app.routers.modules.process_module_sync', return_value=mock_result) as mock_process, \
             patch('app.routers.modules.create_folders_for_module', return_value=mock_folders):
            assert TEST_PDF_PATH.exists(), f"Test PDF not found: {TEST_PDF_PATH}"

            with open(TEST_PDF_PATH, "rb") as f:
                pdf_content = f.read()

            response = client.post(
                "/api/modules/process",
                files={"file": ("module.pdf", pdf_content, "application/pdf")},
                data={
                    "module_name": "Test Module",
                    # Options not provided - should use defaults
                }
            )

            assert response.status_code == 200

            # Verify defaults are used (all True per spec)
            kwargs = mock_process.call_args.kwargs
            assert kwargs["extract_journal"] is True  # Default: True
            assert kwargs["extract_actors"] is True  # Default: True
            assert kwargs["extract_battle_maps"] is True  # Default: True
            assert kwargs["generate_scene_artwork"] is True  # Default: True


@pytest.mark.unit
class TestCreateFoldersForModule:
    """Unit tests for create_folders_for_module helper function.

    Note: create_folders_for_module creates 2 folders per document type:
    1. Tablewrite root folder
    2. Module subfolder under Tablewrite

    So for 3 doc types (Actor, Scene, JournalEntry) = 6 total calls.
    On failure, it raises RuntimeError rather than returning partial results.
    """

    @pytest.mark.asyncio
    async def test_create_folders_for_module_success(self):
        """Test that folder creation works for all document types."""
        from app.routers.modules import create_folders_for_module

        with patch("app.routers.modules.get_or_create_folder") as mock_folder:
            # Return different IDs for root vs subfolder
            mock_folder.side_effect = [
                # Actor: Tablewrite root, then module subfolder
                MagicMock(success=True, folder_id="tablewrite_actor", folder_uuid="Folder.tablewrite_actor"),
                MagicMock(success=True, folder_id="module_actor", folder_uuid="Folder.module_actor"),
                # Scene: Tablewrite root, then module subfolder
                MagicMock(success=True, folder_id="tablewrite_scene", folder_uuid="Folder.tablewrite_scene"),
                MagicMock(success=True, folder_id="module_scene", folder_uuid="Folder.module_scene"),
                # JournalEntry: Tablewrite root, then module subfolder
                MagicMock(success=True, folder_id="tablewrite_journal", folder_uuid="Folder.tablewrite_journal"),
                MagicMock(success=True, folder_id="module_journal", folder_uuid="Folder.module_journal"),
            ]

            folders = await create_folders_for_module("Test Module")

            # 6 calls: 2 per doc type (root + subfolder)
            assert mock_folder.call_count == 6

            # Verify the module subfolder IDs are returned (not root folder IDs)
            assert folders["actors"] == "module_actor"
            assert folders["scenes"] == "module_scene"
            assert folders["journals"] == "module_journal"

    @pytest.mark.asyncio
    async def test_create_folders_for_module_partial_failure(self):
        """Test that folder creation raises on failure (fails fast)."""
        from app.routers.modules import create_folders_for_module

        with patch("app.routers.modules.get_or_create_folder") as mock_folder:
            # First root folder succeeds, then subfolder fails
            mock_folder.side_effect = [
                MagicMock(success=True, folder_id="tablewrite_actor", folder_uuid="Folder.tablewrite_actor"),
                MagicMock(success=False, folder_id=None, error="Connection error"),
            ]

            # Should raise RuntimeError on failure
            with pytest.raises(RuntimeError, match="Failed to create Actor subfolder"):
                await create_folders_for_module("Test Module")

    @pytest.mark.asyncio
    async def test_create_folders_for_module_all_fail(self):
        """Test that folder creation raises when root folder fails."""
        from app.routers.modules import create_folders_for_module

        with patch("app.routers.modules.get_or_create_folder") as mock_folder:
            mock_folder.return_value = MagicMock(
                success=False,
                folder_id=None,
                error="No Foundry connection"
            )

            # Should raise RuntimeError on first failure
            with pytest.raises(RuntimeError, match="Failed to create Tablewrite folder"):
                await create_folders_for_module("Test Module")


BACKEND_URL = "http://localhost:8000"


@pytest.mark.integration
@pytest.mark.slow
class TestProcessModuleIntegration:
    """Integration tests for module processing with real pipeline execution."""

    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_process_module_integration_journal_only(self):
        """
        Integration test: Process real test PDF with journal extraction only.

        This test runs the actual pipeline with:
        - extract_journal=True (uploads to Foundry)
        - extract_actors=False (skip for speed)
        - extract_battle_maps=False (skip for speed)
        - generate_scene_artwork=False (skip for speed)

        Verifies that a journal is created with a valid UUID.

        Requires: Backend running at localhost:8000 + Foundry connected.
        """
        import httpx

        # Ensure test PDF exists
        assert TEST_PDF_PATH.exists(), f"Test PDF not found: {TEST_PDF_PATH}"

        async with httpx.AsyncClient(timeout=600.0) as http_client:
            # First check Foundry connection
            status = await http_client.get(f"{BACKEND_URL}/api/foundry/status")
            if status.json()["status"] != "connected":
                pytest.fail("Foundry not connected - start backend and connect Foundry module")

            with open(TEST_PDF_PATH, "rb") as f:
                pdf_content = f.read()

            # Make the request - no mocking, real pipeline execution
            response = await http_client.post(
                f"{BACKEND_URL}/api/modules/process",
                files={"file": ("Lost_Mine_test.pdf", pdf_content, "application/pdf")},
                data={
                    "module_name": "Test Integration Module",
                    "extract_journal": "true",
                    "extract_actors": "false",
                    "extract_battle_maps": "false",
                    "generate_scene_artwork": "false",
                },
            )

        assert response.status_code == 200, f"Request failed: {response.text}"

        data = response.json()

        # Verify success
        assert data["success"] is True, f"Processing failed: {data.get('error')}"

        # Verify run directory was created
        assert data.get("run_dir") is not None, "No run_dir in response"
        assert Path(data["run_dir"]).exists(), f"Run directory does not exist: {data['run_dir']}"

        # Verify journal was created with valid UUID
        journal_uuid = data["created"]["journal"]
        assert journal_uuid is not None, "No journal UUID returned"
        assert journal_uuid.startswith("JournalEntry."), \
            f"Invalid journal UUID format: {journal_uuid}"

        # Verify documents directory has XML files
        run_dir = Path(data["run_dir"])
        documents_dir = run_dir / "documents"
        assert documents_dir.exists(), f"Documents directory not found: {documents_dir}"

        xml_files = list(documents_dir.glob("*.xml"))
        assert len(xml_files) > 0, "No XML files generated"
