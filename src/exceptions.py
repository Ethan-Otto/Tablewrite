"""Centralized exception hierarchy for D&D module converter.

Usage:
    from exceptions import ConversionError, FoundryError

    raise ConversionError("Failed to parse stat block")
    raise FoundryError("Failed to upload actor")
"""


class DNDModuleError(Exception):
    """Base exception for all D&D module converter errors."""
    pass


class ConversionError(DNDModuleError):
    """Raised when parsing or conversion fails.

    Examples:
        - XML parsing failure
        - StatBlock parsing failure
        - Invalid data format
    """
    pass


class FoundryError(DNDModuleError):
    """Raised when FoundryVTT operations fail.

    Examples:
        - WebSocket connection failure
        - Actor creation failure
        - Journal upload failure
    """
    pass


class ConfigurationError(DNDModuleError):
    """Raised when configuration is invalid or missing.

    Examples:
        - Missing API key
        - Invalid file path
        - Missing .env file
    """
    pass


class ValidationError(DNDModuleError):
    """Raised when validation fails.

    Examples:
        - Invalid challenge rating
        - Missing required fields
        - Data integrity check failure
    """
    pass
