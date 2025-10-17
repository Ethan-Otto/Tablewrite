"""
Tests for src/util/gemini.py

Basic tests for Gemini API wrapper functionality.
"""

import pytest
from pathlib import Path
import sys
import os
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from util.gemini import GeminiAPI, GeminiFileContext, configure_gemini


class TestGeminiAPIBasics:
    """Test basic Gemini API functionality."""

    def test_configure_from_env(self, check_api_key):
        """Test configuration from environment variables."""
        api = GeminiAPI()
        assert api._configured is True
        assert api.model_name == "gemini-2.5-pro"

    def test_configure_with_custom_model(self, check_api_key):
        """Test configuration with custom model name."""
        api = GeminiAPI(model_name="gemini-1.5-pro")
        assert api.model_name == "gemini-1.5-pro"
        assert api._configured is True

    def test_configure_without_api_key_raises_error(self, monkeypatch, tmp_path):
        """Test that missing API key raises ValueError."""
        monkeypatch.delenv("GeminiImageAPI", raising=False)
        # Patch load_dotenv to prevent loading from actual .env file
        monkeypatch.setattr("util.gemini.load_dotenv", lambda **kwargs: None)
        with pytest.raises(ValueError, match="Gemini API key not found"):
            GeminiAPI()

    def test_convenience_function(self, check_api_key):
        """Test the configure_gemini convenience function."""
        api = configure_gemini()
        assert isinstance(api, GeminiAPI)
        assert api._configured is True

    def test_create_model(self, check_api_key):
        """Test creating a Gemini client instance."""
        api = GeminiAPI()
        client = api.create_model()
        assert client is not None
        assert hasattr(client, "models")

    def test_create_model_without_configuration(self):
        """Test that creating model without configuration raises error."""
        api = GeminiAPI.__new__(GeminiAPI)
        api._configured = False
        with pytest.raises(RuntimeError, match="Gemini API not configured"):
            api.create_model()


class TestGeminiAPIIntegration:
    """Integration tests that make real API calls."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_api
    def test_generate_text_content(self, check_api_key):
        """Test basic text generation."""
        api = GeminiAPI()
        response = api.generate_content("Say 'Hello World' and nothing else.")
        assert response is not None
        assert hasattr(response, "text")
        assert "Hello" in response.text or "hello" in response.text

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_api
    def test_file_upload_and_deletion(self, check_api_key):
        """Test file upload and deletion."""
        api = GeminiAPI()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file_path = f.name

        try:
            uploaded_file = api.upload_file(temp_file_path, display_name="test")
            assert uploaded_file is not None
            assert hasattr(uploaded_file, "name")
            api.delete_file(uploaded_file.name)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_api
    def test_context_manager(self, check_api_key):
        """Test context manager auto-cleanup."""
        api = GeminiAPI()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("The answer is: 42")
            temp_file_path = f.name

        try:
            with GeminiFileContext(api, temp_file_path, "test") as uploaded_file:
                response = api.generate_content(
                    "What is the answer in the file?",
                    file_obj=uploaded_file
                )
                assert response is not None
                assert "42" in response.text
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
