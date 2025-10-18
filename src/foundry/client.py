"""FoundryVTT REST API client."""

import os
import logging
import requests
from typing import Literal, Dict, Any, Optional

from .journals import JournalManager

logger = logging.getLogger(__name__)


class FoundryClient:
    """Client for interacting with FoundryVTT via REST API."""

    def __init__(self, target: Literal["local", "forge"] = "local"):
        """
        Initialize FoundryVTT API client.

        Args:
            target: Target environment ('local' or 'forge')

        Raises:
            ValueError: If required environment variables are not set
        """
        self.target = target
        self.relay_url = os.getenv("FOUNDRY_RELAY_URL")

        if not self.relay_url:
            raise ValueError("FOUNDRY_RELAY_URL not set in environment")

        if target == "local":
            self.foundry_url = os.getenv("FOUNDRY_LOCAL_URL")
            self.api_key = os.getenv("FOUNDRY_LOCAL_API_KEY")
            self.client_id = os.getenv("FOUNDRY_LOCAL_CLIENT_ID")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_LOCAL_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_LOCAL_API_KEY not set in environment")
            if not self.client_id:
                raise ValueError("FOUNDRY_LOCAL_CLIENT_ID not set in environment")
        elif target == "forge":
            self.foundry_url = os.getenv("FOUNDRY_FORGE_URL")
            self.api_key = os.getenv("FOUNDRY_FORGE_API_KEY")
            self.client_id = os.getenv("FOUNDRY_FORGE_CLIENT_ID")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_FORGE_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_FORGE_API_KEY not set in environment")
            if not self.client_id:
                raise ValueError("FOUNDRY_FORGE_CLIENT_ID not set in environment")
        else:
            raise ValueError(f"Invalid target: {target}. Must be 'local' or 'forge'")

        # Initialize journal manager
        self.journals = JournalManager(
            relay_url=self.relay_url,
            foundry_url=self.foundry_url,
            api_key=self.api_key,
            client_id=self.client_id
        )

        logger.info(f"Initialized FoundryClient for {target} at {self.foundry_url}")

    # Journal operations (delegated to JournalManager)

    def create_journal_entry(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """Create a new journal entry in FoundryVTT."""
        return self.journals.create_journal_entry(name, pages, content, folder)

    def find_journal_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a journal entry by name."""
        return self.journals.find_journal_by_name(name)

    def get_journal_entry(self, journal_uuid: str) -> Dict[str, Any]:
        """Get a journal entry by UUID."""
        return self.journals.get_journal_entry(journal_uuid)

    def update_journal_entry(
        self,
        journal_uuid: str,
        pages: list = None,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """Update an existing journal entry."""
        return self.journals.update_journal_entry(journal_uuid, pages, content, name)

    def delete_journal_entry(self, journal_uuid: str) -> Dict[str, Any]:
        """Delete a journal entry."""
        return self.journals.delete_journal_entry(journal_uuid)

    def create_or_replace_journal(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """Create or replace a journal entry."""
        return self.journals.create_or_replace_journal(name, pages, content, folder)
