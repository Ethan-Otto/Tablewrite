"""FoundryVTT API integration module."""

from .client import FoundryClient
from .xml_to_journal_html import convert_xml_to_journal_data, convert_xml_directory_to_journals

__all__ = [
    "FoundryClient",
    "convert_xml_to_journal_data",
    "convert_xml_directory_to_journals"
]
