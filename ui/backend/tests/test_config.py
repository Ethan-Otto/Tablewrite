"""Tests for configuration."""
from app.config import Settings


class TestSettings:
    """Test Settings class."""

    def test_settings_defaults(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.MAX_IMAGES_PER_REQUEST == 4
        assert settings.IMAGE_STORAGE_DAYS == 7
        assert settings.GEMINI_MODEL == "gemini-2.0-flash"
        assert settings.GEMINI_TIMEOUT == 60
        assert settings.IMAGEN_CONCURRENT_LIMIT == 2
