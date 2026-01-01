"""FoundryVTT format converters.

Pure conversion logic for transforming domain models to FoundryVTT format.
No network calls - all I/O is handled by ui/backend/.
"""

from .actors import ParsedActorData, Attack, Trait

# These will be added in subsequent tasks
# from .actors import convert_to_foundry  # Task 1.3
# from .journals import convert_xml_to_journal_data  # Task 1.5

__all__ = [
    # "convert_to_foundry",  # Task 1.3
    "ParsedActorData",
    "Attack",
    "Trait",
    # "convert_xml_to_journal_data",  # Task 1.5
]
