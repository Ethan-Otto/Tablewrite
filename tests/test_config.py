"""Tests for centralized configuration module."""

import pytest
import os
from pathlib import Path


class TestProjectConfig:
    """Tests for project configuration."""

    def test_project_root_is_correct(self):
        """Should return the project root directory."""
        from config import PROJECT_ROOT

        # Project root should contain key files
        assert (PROJECT_ROOT / "pyproject.toml").exists()
        assert (PROJECT_ROOT / "src").is_dir()

    def test_src_dir_is_correct(self):
        """Should return the src directory."""
        from config import SRC_DIR

        assert SRC_DIR.is_dir()
        assert (SRC_DIR / "api.py").exists()

    def test_get_env_returns_value(self):
        """Should return environment variable value."""
        from config import get_env

        # Set a test variable
        os.environ["TEST_CONFIG_VAR"] = "test_value"

        result = get_env("TEST_CONFIG_VAR")

        assert result == "test_value"

        # Cleanup
        del os.environ["TEST_CONFIG_VAR"]

    def test_get_env_returns_default(self):
        """Should return default when env var not set."""
        from config import get_env

        result = get_env("NONEXISTENT_VAR_12345", default="fallback")

        assert result == "fallback"

    def test_get_env_raises_without_default(self):
        """Should raise KeyError when var not set and no default."""
        from config import get_env

        with pytest.raises(KeyError):
            get_env("NONEXISTENT_VAR_12345")


@pytest.mark.smoke
@pytest.mark.unit
class TestConfigEnvironment:
    """Tests for config module with real environment variables."""

    def test_gemini_api_key_loaded_from_env(self, check_api_key):
        """Verify GeminiImageAPI key is loaded from .env file."""
        from config import get_env

        # This test requires the .env file to exist with GeminiImageAPI set
        api_key = get_env("GeminiImageAPI")

        assert api_key is not None, "GeminiImageAPI should be set"
        assert len(api_key) > 10, "API key should be a valid length"
        assert api_key.startswith("AIza"), "API key should have valid prefix"

    def test_foundry_config_loaded_from_env(self):
        """Verify Foundry configuration is loaded from .env file."""
        from config import get_env

        # These should be in .env for development
        foundry_url = get_env("FOUNDRY_URL", default=None)

        # At least FOUNDRY_URL should be set for integration tests
        if foundry_url is None:
            pytest.skip("FOUNDRY_URL not set in .env - skipping")

        assert "localhost" in foundry_url or "http" in foundry_url, \
            "FOUNDRY_URL should be a valid URL"

    def test_project_root_contains_required_files(self):
        """Verify PROJECT_ROOT path is valid and contains required files."""
        from config import PROJECT_ROOT

        # Verify critical project files exist
        required_files = [
            "pyproject.toml",
            "CLAUDE.md",
            ".env",
            "src/api.py",
            "src/config.py",
            "src/exceptions.py",
        ]

        for file_path in required_files:
            full_path = PROJECT_ROOT / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"

    def test_src_dir_contains_all_modules(self):
        """Verify SRC_DIR contains all expected modules after refactoring."""
        from config import SRC_DIR

        # Verify refactored module structure
        expected_modules = [
            "actor_pipeline",  # Renamed from actors
            "caches",          # Extracted from foundry/
            "config.py",       # New centralized config
            "exceptions.py",   # New exception hierarchy
            "foundry",
            "foundry_converters",
            "models",
            "api.py",
        ]

        for module in expected_modules:
            module_path = SRC_DIR / module
            assert module_path.exists(), f"Expected module missing: {module}"
