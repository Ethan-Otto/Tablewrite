"""FoundryVTT API integration module - network layer only.

Journal conversion has been moved to foundry_converters.journals.
This module provides network operations (FoundryClient) and
re-exports common functions from foundry_converters for backwards compatibility.
"""

from .client import FoundryClient

# Re-export journal converters from foundry_converters for backwards compatibility
from foundry_converters.journals.converter import (
    convert_xml_to_journal_data,
    convert_xml_directory_to_journals,
)

__all__ = [
    "FoundryClient",
    # Re-exported from foundry_converters
    "convert_xml_to_journal_data",
    "convert_xml_directory_to_journals",
]
