"""
Public API for D&D Module Processing.

This module provides the official interface for external applications
(chat UI, CLI tools, etc.) to interact with the module processing system.

All functions use environment variables for configuration (.env file).
Operations are synchronous and may take several minutes for large PDFs.

Example usage:
    from api import create_actor, extract_maps, process_pdf_to_journal

    # Create actor from description
    result = create_actor("A fierce goblin warrior", challenge_rating=1.0)
    print(f"Created actor: {result.foundry_uuid}")

    # Extract maps from PDF
    maps = extract_maps("data/pdfs/module.pdf")
    print(f"Extracted {maps.total_maps} maps")

    # Process PDF to journal
    journal = process_pdf_to_journal(
        "data/pdfs/module.pdf",
        "Lost Mine of Phandelver"
    )
    print(f"Created journal: {journal.journal_uuid}")
"""

import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Raised when API operations fail.

    This exception wraps internal errors to provide a clean boundary
    between the public API and internal implementation details.

    The original exception is preserved as __cause__ for debugging.
    """
    pass
