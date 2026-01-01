"""FoundryVTT Journal operations via WebSocket backend."""

import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class JournalManager:
    """Manages journal entry operations for FoundryVTT via WebSocket backend.

    All operations go through the FastAPI backend HTTP API, which internally
    uses WebSocket to communicate with FoundryVTT. The relay server is no longer used.
    """

    def __init__(self, backend_url: str):
        """
        Initialize journal manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    def create_journal_entry(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create a journal entry in FoundryVTT via the backend WebSocket.

        Args:
            name: Title of the journal entry.
            pages: List of page objects with keys "name" and "content"
            content: HTML content for a single-page entry (legacy alternative to pages)
            folder: Folder ID to assign to the journal entry (not yet implemented)

        Returns:
            dict: Response with uuid, id, name of created journal

        Raises:
            ValueError: If neither pages nor content is provided.
            RuntimeError: If the API request fails.
        """
        endpoint = f"{self.backend_url}/api/foundry/journal"

        # Build pages array
        if pages:
            pages_data = pages
        elif content is not None:
            pages_data = [
                {
                    "name": name,
                    "type": "text",
                    "text": {"content": content}
                }
            ]
        else:
            raise ValueError("Must provide either 'pages' or 'content'")

        payload = {
            "name": name,
            "pages": pages_data
        }

        if folder:
            payload["folder"] = folder

        page_count = len(pages_data)
        logger.debug(f"Creating journal entry: {name} with {page_count} page(s)")

        try:
            response = requests.post(endpoint, json=payload, timeout=30)

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to create journal: {response.status_code} - {error_detail}")
                raise RuntimeError(
                    f"Failed to create journal entry: {response.status_code} - {error_detail}"
                )

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Failed to create journal: {result.get('error')}")

            uuid = result.get("uuid")
            logger.info(f"Created journal entry: {name} with {page_count} page(s) (UUID: {uuid})")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RuntimeError(f"Failed to create journal entry: {e}") from e

    def get_all_journals_by_name(self, name: str) -> list[Dict[str, Any]]:
        """
        Get all journals matching the given name.

        NOTE: Search functionality requires backend endpoint that uses WebSocket.

        Args:
            name: Name of the journal to search for

        Returns:
            List of matching journal dicts (empty list if none found)
        """
        endpoint = f"{self.backend_url}/api/foundry/search"

        params = {
            "query": name,
            "document_type": "JournalEntry"
        }

        logger.debug(f"Searching for journal: {name}")

        try:
            response = requests.get(endpoint, params=params, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Search failed: {response.status_code}")
                return []

            data = response.json()

            if not data.get("success"):
                return []

            results = data.get("results", [])

            # Normalize results
            normalized = []
            for journal in results:
                if 'id' in journal and '_id' not in journal:
                    journal['_id'] = journal['id']
                normalized.append(journal)

            logger.debug(f"Found {len(normalized)} journal(s) matching: {name}")
            return normalized

        except requests.exceptions.RequestException as e:
            logger.warning(f"Search request failed: {e}")
            return []

    def get_journal_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get first journal matching the given name.

        Args:
            name: Name of the journal to find

        Returns:
            Journal dict if found, None otherwise
        """
        results = self.get_all_journals_by_name(name)

        if not results:
            logger.debug(f"No journal found with name: {name}")
            return None

        # Return first exact name match
        for journal in results:
            if journal.get("name") == name:
                logger.debug(f"Found journal: {name} (ID: {journal.get('_id') or journal.get('id')})")
                return journal

        return None

    def get_journal(self, journal_uuid: str) -> Dict[str, Any]:
        """
        Get a journal entry by UUID.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            journal_uuid: UUID of the journal entry (format: JournalEntry.{id})

        Returns:
            Dict containing journal entry data including pages

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Get journal by UUID via WebSocket backend not yet implemented. "
            "Add GET /api/foundry/journal/{uuid} endpoint to backend."
        )

    def update_journal_entry(
        self,
        journal_uuid: str,
        pages: list = None,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Update an existing journal entry.

        NOTE: This functionality requires a backend endpoint that is not yet implemented.

        Args:
            journal_uuid: UUID of the journal entry
            pages: List of page dicts with 'name' and 'content' keys
            content: New HTML content for single page
            name: New name (optional)

        Raises:
            NotImplementedError: Backend endpoint not yet implemented
        """
        raise NotImplementedError(
            "Update journal via WebSocket backend not yet implemented. "
            "Add PUT /api/foundry/journal/{uuid} endpoint to backend."
        )

    def delete_journal_entry(self, journal_uuid: str) -> Dict[str, Any]:
        """
        Delete a journal entry.

        Args:
            journal_uuid: UUID of the journal entry (format: JournalEntry.{id})

        Returns:
            Dict with success status

        Raises:
            RuntimeError: If API request fails
        """
        endpoint = f"{self.backend_url}/api/foundry/journal/{journal_uuid}"

        logger.debug(f"Deleting journal entry: {journal_uuid}")

        try:
            response = requests.delete(endpoint, timeout=30)

            if response.status_code == 404:
                raise RuntimeError(f"Journal not found: {journal_uuid}")

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Delete failed: {response.status_code} - {error_detail}")
                raise RuntimeError(f"Failed to delete journal: {response.status_code} - {error_detail}")

            result = response.json()
            logger.info(f"Deleted journal entry: {journal_uuid}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Delete request failed: {e}")
            raise RuntimeError(f"Failed to delete journal: {e}") from e

    def create_or_replace_journal(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create or replace a journal entry.

        Searches for existing journal by name. If found, deletes it and creates a new one.
        If not found, creates a new journal entry.

        Args:
            name: Name of the journal entry
            pages: List of page dicts with 'name' and 'content' keys
            content: HTML content for single-page journal
            folder: Optional folder ID

        Returns:
            Dict containing journal entry data

        Raises:
            ValueError: If neither pages nor content provided
        """
        if not pages and content is None:
            raise ValueError("Must provide either 'pages' or 'content'")

        # Try to find existing journal
        existing = self.get_journal_by_name(name)

        if existing:
            # Extract UUID for deletion
            journal_uuid = existing.get('uuid')
            if not journal_uuid:
                journal_id = existing.get('_id') or existing.get('id')
                if journal_id:
                    journal_uuid = f"JournalEntry.{journal_id}"

            if journal_uuid:
                logger.info(f"Deleting existing journal for replacement: {name} (UUID: {journal_uuid})")
                try:
                    self.delete_journal_entry(journal_uuid)
                except RuntimeError as e:
                    logger.warning(f"Failed to delete old journal, will try creating new one: {e}")
            else:
                logger.warning(f"Found journal but no UUID available, creating new: {name}")

        # Create new journal
        logger.info(f"Creating journal entry: {name}")
        return self.create_journal_entry(
            name=name,
            pages=pages,
            content=content,
            folder=folder
        )
