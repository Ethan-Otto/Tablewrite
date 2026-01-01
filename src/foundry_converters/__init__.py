"""FoundryVTT format converters.

Pure conversion logic for transforming domain models to FoundryVTT format.
No network calls - all I/O is handled by ui/backend/.
"""

from .actors import ParsedActorData, Attack, Trait, convert_to_foundry

# These will be added in subsequent tasks
# from .journals import convert_xml_to_journal_data  # Task 1.5

__all__ = [
    "convert_to_foundry",
    "ParsedActorData",
    "Attack",
    "Trait",
    # "convert_xml_to_journal_data",  # Task 1.5
]
