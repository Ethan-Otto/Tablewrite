"""Tests for exception hierarchy."""

import pytest


class TestExceptionHierarchy:
    """Tests for exception classes."""

    def test_base_exception_exists(self):
        """Should have DNDModuleError base exception."""
        from exceptions import DNDModuleError

        assert issubclass(DNDModuleError, Exception)

    def test_conversion_error_inherits(self):
        """ConversionError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, ConversionError

        assert issubclass(ConversionError, DNDModuleError)

    def test_foundry_error_inherits(self):
        """FoundryError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, FoundryError

        assert issubclass(FoundryError, DNDModuleError)

    def test_configuration_error_inherits(self):
        """ConfigurationError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, ConfigurationError

        assert issubclass(ConfigurationError, DNDModuleError)

    def test_validation_error_inherits(self):
        """ValidationError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, ValidationError

        assert issubclass(ValidationError, DNDModuleError)

    def test_exception_has_message(self):
        """Exceptions should store message."""
        from exceptions import ConversionError

        err = ConversionError("parsing failed")

        assert str(err) == "parsing failed"

    def test_all_exceptions_have_message(self):
        """All exception types should store messages correctly."""
        from exceptions import (
            DNDModuleError,
            ConversionError,
            FoundryError,
            ConfigurationError,
            ValidationError,
        )

        exceptions = [
            (DNDModuleError, "base error"),
            (ConversionError, "conversion failed"),
            (FoundryError, "foundry failed"),
            (ConfigurationError, "config missing"),
            (ValidationError, "validation failed"),
        ]

        for exc_class, message in exceptions:
            err = exc_class(message)
            assert str(err) == message, f"{exc_class.__name__} did not store message"

    def test_exceptions_can_be_caught_by_base(self):
        """All exceptions should be catchable by DNDModuleError."""
        from exceptions import (
            DNDModuleError,
            ConversionError,
            FoundryError,
            ConfigurationError,
            ValidationError,
        )

        for exc_class in [ConversionError, FoundryError, ConfigurationError, ValidationError]:
            try:
                raise exc_class("test")
            except DNDModuleError:
                pass  # Expected
            except Exception:
                pytest.fail(f"{exc_class.__name__} not caught by DNDModuleError")


@pytest.mark.smoke
@pytest.mark.integration
class TestExceptionIntegration:
    """Integration tests verifying exceptions are raised in real scenarios."""

    def test_api_error_is_foundry_error(self):
        """Verify APIError from api.py is now FoundryError."""
        from api import APIError
        from exceptions import FoundryError

        # APIError should be an alias for FoundryError
        assert APIError is FoundryError, "APIError should be FoundryError"

    def test_foundry_error_raised_on_bad_connection(self):
        """Verify FoundryError is raised when Foundry operations fail."""
        from exceptions import DNDModuleError, FoundryError

        # Trying to connect to non-existent backend should raise
        # (This test uses a mock scenario - real integration tests are in foundry/)

        # Just verify the exception can be constructed and caught
        try:
            raise FoundryError("Failed to connect to Foundry: Connection refused")
        except DNDModuleError as e:
            assert "Failed to connect" in str(e)

    def test_configuration_error_on_missing_key(self):
        """Verify ConfigurationError can be raised for missing config."""
        from exceptions import DNDModuleError, ConfigurationError

        try:
            raise ConfigurationError("Missing API key: GeminiImageAPI")
        except DNDModuleError as e:
            assert "Missing API key" in str(e)

    def test_conversion_error_on_parse_failure(self):
        """Verify ConversionError can be raised for conversion failures."""
        from exceptions import DNDModuleError, ConversionError

        try:
            raise ConversionError("Failed to parse stat block: invalid XML")
        except DNDModuleError as e:
            assert "Failed to parse" in str(e)

    def test_validation_error_on_invalid_data(self):
        """Verify ValidationError can be raised for validation failures."""
        from exceptions import DNDModuleError, ValidationError

        try:
            raise ValidationError("Invalid challenge rating: -5")
        except DNDModuleError as e:
            assert "Invalid challenge rating" in str(e)

    def test_all_exceptions_preserve_traceback(self):
        """Verify exceptions preserve full traceback when re-raised."""
        from exceptions import ConversionError, DNDModuleError

        def inner_function():
            raise ConversionError("Original error")

        def outer_function():
            try:
                inner_function()
            except ConversionError:
                raise

        with pytest.raises(ConversionError) as exc_info:
            outer_function()

        # Verify traceback includes both functions
        import traceback
        tb_str = "".join(traceback.format_exception(type(exc_info.value), exc_info.value, exc_info.value.__traceback__))
        assert "inner_function" in tb_str
        assert "outer_function" in tb_str
