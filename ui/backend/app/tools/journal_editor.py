"""Journal editing tool - allows modifications to existing journals."""
import logging
from typing import Optional, List, Dict, Any
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import update_journal, fetch_journal, list_journals

logger = logging.getLogger(__name__)


async def find_journal_by_name(journal_name: str) -> Optional[str]:
    """
    Search for a journal by name and return its UUID.

    Uses fuzzy matching - returns the first journal whose name contains
    the search term (case-insensitive).

    Returns:
        Journal UUID if found, None otherwise
    """
    result = await list_journals()
    if not result.success or not result.journals:
        return None

    # Try exact match first (case-insensitive)
    search_lower = journal_name.lower()
    for journal in result.journals:
        if journal.name and journal.name.lower() == search_lower:
            return journal.uuid

    # Try partial match (name contains search term)
    for journal in result.journals:
        if journal.name and search_lower in journal.name.lower():
            return journal.uuid

    return None


class JournalEditorTool(BaseTool):
    """Tool for editing existing journal entries in FoundryVTT."""

    @property
    def name(self) -> str:
        return "edit_journal"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="edit_journal",
            description=(
                "Edit an existing journal entry in FoundryVTT. Use when user asks to "
                "modify, change, update, or adjust a journal's title, content, or pages. "
                "Can search by journal name or use UUID directly."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "journal_name": {
                        "type": "string",
                        "description": "The journal's name to search for (e.g., 'Session Notes', 'Tavern Lore')"
                    },
                    "journal_uuid": {
                        "type": "string",
                        "description": "The journal's UUID if known (e.g., 'JournalEntry.abc123'). Optional if journal_name is provided."
                    },
                    "new_name": {
                        "type": "string",
                        "description": "New name/title for the journal (to rename it)"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New HTML or plain text content to replace the first page's content"
                    },
                    "append_content": {
                        "type": "string",
                        "description": "HTML or plain text content to append to the first page"
                    },
                    "new_pages": {
                        "type": "array",
                        "description": "New pages to add to the journal",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Page title"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Page content (HTML or plain text)"
                                },
                                "type": {
                                    "type": "string",
                                    "description": "Page type: 'text' (default), 'image', 'pdf', 'video'"
                                }
                            },
                            "required": ["name", "content"]
                        }
                    }
                },
                "required": []
            }
        )

    async def execute(
        self,
        journal_name: Optional[str] = None,
        journal_uuid: Optional[str] = None,
        new_name: Optional[str] = None,
        new_content: Optional[str] = None,
        append_content: Optional[str] = None,
        new_pages: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> ToolResponse:
        """Execute journal edit using WebSocket connection to Foundry."""
        try:
            # Resolve journal UUID - either use provided UUID or search by name
            resolved_uuid = journal_uuid
            searched_name = None

            if not resolved_uuid and journal_name:
                # Search for journal by name
                logger.info(f"Searching for journal by name: {journal_name}")
                resolved_uuid = await find_journal_by_name(journal_name)
                searched_name = journal_name

                if not resolved_uuid:
                    return ToolResponse(
                        type="error",
                        message=f"Could not find a journal named '{journal_name}'. Please check the name or provide the UUID.",
                        data=None
                    )
                logger.info(f"Found journal '{journal_name}' with UUID: {resolved_uuid}")

            if not resolved_uuid:
                return ToolResponse(
                    type="error",
                    message="Please provide either a journal name or UUID to edit.",
                    data=None
                )

            # Build updates dictionary based on provided parameters
            updates: Dict[str, Any] = {}

            if new_name is not None:
                updates["name"] = new_name

            # Handle content updates - need to fetch current journal first if appending
            if new_content is not None or append_content is not None:
                # Fetch current journal to get existing pages
                fetch_result = await fetch_journal(resolved_uuid)
                if not fetch_result.success:
                    return ToolResponse(
                        type="error",
                        message=f"Failed to fetch journal for editing: {fetch_result.error}",
                        data=None
                    )

                current_pages = fetch_result.entity.get("pages", []) if fetch_result.entity else []

                if current_pages:
                    # Update the first page's content
                    first_page = current_pages[0]
                    page_id = first_page.get("_id")

                    if new_content is not None:
                        # Replace content entirely
                        final_content = new_content
                    elif append_content is not None:
                        # Append to existing content
                        existing_content = first_page.get("text", {}).get("content", "")
                        final_content = existing_content + append_content

                    # Foundry uses dot notation for embedded document updates
                    updates[f"pages"] = [{
                        "_id": page_id,
                        "text.content": final_content
                    }]
                else:
                    # No pages exist, create one
                    content = new_content if new_content is not None else append_content
                    updates["pages"] = [{
                        "name": "Page 1",
                        "type": "text",
                        "text": {"content": content}
                    }]

            # Handle adding new pages
            if new_pages:
                # Fetch current journal to get existing pages if not already fetched
                if "pages" not in updates:
                    fetch_result = await fetch_journal(resolved_uuid)
                    if not fetch_result.success:
                        return ToolResponse(
                            type="error",
                            message=f"Failed to fetch journal for editing: {fetch_result.error}",
                            data=None
                        )
                    current_pages = fetch_result.entity.get("pages", []) if fetch_result.entity else []
                else:
                    current_pages = []

                # Format new pages for Foundry
                formatted_new_pages = []
                for page in new_pages:
                    formatted_new_pages.append({
                        "name": page.get("name", "New Page"),
                        "type": page.get("type", "text"),
                        "text": {"content": page.get("content", "")}
                    })

                # If we already have page updates (content change), we need to merge
                if "pages" in updates:
                    # The updates["pages"] contains update objects, not full pages
                    # We need to add new pages separately
                    # Foundry handles this via createEmbeddedDocuments, but update() can also add
                    updates["pages"].extend(formatted_new_pages)
                else:
                    # Just adding new pages
                    updates["pages"] = formatted_new_pages

            # Check if we have any modifications to make
            if not updates:
                return ToolResponse(
                    type="error",
                    message="No updates provided. Specify at least one attribute to change.",
                    data=None
                )

            logger.info(f"Updating journal {resolved_uuid} with: {list(updates.keys())}")
            result = await update_journal(resolved_uuid, updates)

            if not result.success:
                return ToolResponse(
                    type="error",
                    message=f"Failed to update journal: {result.error}",
                    data=None
                )

            journal_display_name = result.name or searched_name or "the journal"
            final_uuid = result.uuid or resolved_uuid

            # Build summary of changes
            change_summary = []
            if new_name is not None:
                change_summary.append(f"renamed to **{new_name}**")
            if new_content is not None:
                change_summary.append("replaced page content")
            if append_content is not None:
                change_summary.append("appended content")
            if new_pages:
                page_names = [p.get("name", "New Page") for p in new_pages]
                change_summary.append(f"added pages: **{', '.join(page_names)}**")

            changes_text = ", ".join(change_summary) if change_summary else "updated"

            # Create FoundryVTT content link format
            journal_link = f"@UUID[{final_uuid}]{{{journal_display_name}}}"

            message = (
                f"Updated **{journal_display_name}**: {changes_text}\n\n"
                f"**Link:** `{journal_link}`"
            )

            return ToolResponse(
                type="text",
                message=message,
                data={
                    "uuid": final_uuid,
                    "name": journal_display_name,
                    "updates": list(updates.keys()),
                    "link": journal_link
                }
            )

        except Exception as e:
            logger.error(f"Journal edit failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to edit journal: {str(e)}",
                data=None
            )
