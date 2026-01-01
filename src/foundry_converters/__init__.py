"""FoundryVTT format converters.

Pure conversion logic for transforming domain models to FoundryVTT format.
No network calls - all I/O is handled by ui/backend/.
"""

from .actors import ParsedActorData, Attack, Trait, convert_to_foundry
from .journals import convert_xml_to_journal_data

__all__ = [
    # Actors
    "convert_to_foundry",
    "ParsedActorData",
    "Attack",
    "Trait",
    # Journals
    "convert_xml_to_journal_data",
]
