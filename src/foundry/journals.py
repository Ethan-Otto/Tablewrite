"""FoundryVTT Journal operations."""

import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _is_running_in_tests() -> bool:
    """Check if running in pytest."""
    import sys
    return "pytest" in sys.modules


class JournalManager:
    """Manages journal entry operations for FoundryVTT."""

    def __init__(
        self,
        relay_url: str,
        foundry_url: str,
        api_key: str,
        client_id: str,
        folder_manager: Optional[Any] = None
    ):
        """
        Initialize journal manager.

        Args:
            relay_url: URL of the relay server
            foundry_url: URL of the FoundryVTT instance
            api_key: API key for authentication
            client_id: Client ID for the FoundryVTT instance
            folder_manager: Optional FolderManager instance for organizing journals
        """
        self.relay_url = relay_url
        self.foundry_url = foundry_url
        self.api_key = api_key
        self.client_id = client_id
        self.folder_manager = folder_manager

    def create_journal_entry(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create a journal entry in FoundryVTT via the relay API.
        
        Builds the journal payload from either a list of pages or a single HTML content string and submits it to the relay. If running under pytest and no folder is provided, attempts to place the journal in a "tests" folder when a folder_manager is available. When provided, the folder ID is embedded under the returned document's data.
        
        Parameters:
            name (str): Title of the journal entry.
            pages (list, optional): List of page objects with keys "name" and "content"; preferred for multi-page entries.
            content (str, optional): HTML content for a single-page entry (legacy alternative to `pages`).
            folder (str, optional): Folder ID to assign to the journal entry.
        
        Returns:
            dict: Parsed JSON response from the relay API representing the created journal entry.
        
        Raises:
            ValueError: If neither `pages` nor `content` is provided.
            RuntimeError: If the API request fails or returns a non-200 response.
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Build pages array
        if pages:
            # Multiple pages provided
            pages_data = [
                {
                    "name": page["name"],
                    "type": "text",
                    "text": {
                        "content": page["content"]
                    }
                }
                for page in pages
            ]
        elif content is not None:
            # Legacy single-page mode
            pages_data = [
                {
                    "name": name,
                    "type": "text",
                    "text": {
                        "content": content
                    }
                }
            ]
        else:
            raise ValueError("Must provide either 'pages' or 'content'")

        # Auto-organize test journals into "tests" folder
        if not folder and _is_running_in_tests() and self.folder_manager:
            try:
                folder = self.folder_manager.get_or_create_folder("tests", "JournalEntry")
                logger.debug("Adding journal to 'tests' folder (running in pytest)")
            except Exception as e:
                logger.warning(f"Failed to set test folder: {e}")

        payload = {
            "entityType": "JournalEntry",
            "data": {
                "name": name,
                "pages": pages_data
            }
        }

        # Add folder to document data if provided
        if folder:
            payload["data"]["folder"] = folder

        page_count = len(pages_data)
        logger.debug(f"Creating journal entry: {name} with {page_count} page(s)")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create journal: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create journal entry: {response.status_code} - {response.text}"
                )

            result = response.json()
            # Response format: {"entity": {"_id": "..."}, "uuid": "JournalEntry.xxx"}
            entity_id = result.get('entity', {}).get('_id') or result.get('uuid', 'unknown')
            logger.info(f"Created journal entry: {name} with {page_count} page(s) (ID: {entity_id})")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RuntimeError(f"Failed to create journal entry: {e}") from e

    def get_all_journals_by_name(self, name: str) -> list[Dict[str, Any]]:
        """
        Get all journals matching the given name.

        Args:
            name: Name of the journal to search for

        Returns:
            List of matching journal dicts (empty list if none found)
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "clientId": self.client_id,
            "type": "JournalEntry",
            "query": name
        }

        logger.debug(f"Searching for journal: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Search failed: {response.status_code} - search not available")
                return []  # Search failed, return empty list

            results = response.json()

            # Check for QuickInsert error (search module not available)
            if isinstance(results, dict) and results.get("error"):
                logger.warning(f"Search error: {results['error']}")
                return []

            # Check for empty results
            if not results or (isinstance(results, dict) and not results.get("results")):
                logger.debug(f"No journals found with name: {name}")
                return []

            # Handle both list and dict response formats
            search_results = results if isinstance(results, list) else results.get("results", [])

            # Normalize all results (convert 'id' to '_id')
            normalized = []
            for journal in search_results:
                if 'id' in journal and '_id' not in journal:
                    journal['_id'] = journal['id']
                normalized.append(journal)

            logger.debug(f"Found {len(normalized)} journal(s) matching: {name}")
            return normalized

        except requests.exceptions.RequestException as e:
            logger.warning(f"Search request failed: {e}")
            return []  # Network error, return empty list

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

        Args:
            journal_uuid: UUID of the journal entry (format: JournalEntry.{id})

        Returns:
            Dict containing journal entry data including pages

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/get?clientId={self.client_id}&uuid={journal_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.debug(f"Getting journal entry: {journal_uuid}")

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Get failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to get journal: {response.status_code} - {response.text}")

            result = response.json()
            logger.debug(f"Retrieved journal entry: {journal_uuid}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Get request failed: {e}")
            raise RuntimeError(f"Failed to get journal: {e}") from e

    def update_journal_entry(
        self,
        journal_uuid: str,
        pages: list = None,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Update an existing journal entry.

        Args:
            journal_uuid: UUID of the journal entry (format: JournalEntry.{id})
            pages: List of page dicts with 'name' and 'content' keys (preferred)
            content: New HTML content for single page (legacy, use pages instead)
            name: New name (optional)

        Returns:
            Dict containing updated journal entry data

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/update?clientId={self.client_id}&uuid={journal_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "data": {}
        }

        # Build pages array if content provided
        if pages:
            # Multiple pages provided
            payload["data"]["pages"] = [
                {
                    "name": page["name"],
                    "type": "text",
                    "text": {
                        "content": page["content"]
                    }
                }
                for page in pages
            ]
        elif content is not None:
            # Legacy single-page mode
            payload["data"]["pages"] = [
                {
                    "name": name or "Content",
                    "type": "text",
                    "text": {
                        "content": content
                    }
                }
            ]

        if name is not None:
            payload["data"]["name"] = name

        page_info = f" with {len(pages)} page(s)" if pages else ""
        logger.debug(f"Updating journal entry: {journal_uuid}{page_info}")

        try:
            response = requests.put(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Update failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to update journal: {response.status_code} - {response.text}")

            result = response.json()
            logger.info(f"Updated journal entry: {journal_uuid}{page_info}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Update request failed: {e}")
            raise RuntimeError(f"Failed to update journal: {e}") from e

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
        url = f"{self.relay_url}/delete?clientId={self.client_id}&uuid={journal_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.debug(f"Deleting journal entry: {journal_uuid}")

        try:
            response = requests.delete(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Delete failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to delete journal: {response.status_code} - {response.text}")

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

        Searches for existing journal by name. If found, deletes it and creates a new one
        (to ensure pages are replaced, not appended).
        If not found, creates a new journal entry.

        Args:
            name: Name of the journal entry
            pages: List of page dicts with 'name' and 'content' keys (preferred)
            content: HTML content for single-page journal (legacy, use pages instead)
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
            # Search results may have 'uuid' field or we construct from 'id'/'_id'
            journal_uuid = existing.get('uuid')
            if not journal_uuid:
                journal_id = existing.get('_id') or existing.get('id')
                if journal_id:
                    journal_uuid = f"JournalEntry.{journal_id}"

            if journal_uuid:
                # Delete old journal to ensure clean replacement
                logger.info(f"Deleting existing journal for replacement: {name} (UUID: {journal_uuid})")
                try:
                    self.delete_journal_entry(journal_uuid)
                except RuntimeError as e:
                    logger.warning(f"Failed to delete old journal, will try creating new one: {e}")
            else:
                logger.warning(f"Found journal but no UUID available, creating new: {name}")

        # Create new journal (either fresh or replacement)
        logger.info(f"Creating journal entry: {name}")
        return self.create_journal_entry(
            name=name,
            pages=pages,
            content=content,
            folder=folder
        )