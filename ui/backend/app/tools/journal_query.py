"""Journal query tool for Q&A, summaries, and extraction from journals."""
import logging
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from bs4 import BeautifulSoup

from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import list_journals, fetch_journal

logger = logging.getLogger(__name__)

# In-memory session context storage
_session_contexts: dict[str, "JournalContext"] = {}


class JournalContext(BaseModel):
    """Context for conversational follow-ups."""
    journal_uuid: str
    journal_name: str
    last_sections: list[str]
    timestamp: datetime


class SourceReference(BaseModel):
    """Reference to source location in a journal."""
    journal_name: str
    journal_uuid: str
    chapter: Optional[str]
    section: Optional[str]
    page_id: Optional[str]


class JournalQueryTool(BaseTool):
    """Tool for querying journals for Q&A, summaries, and content extraction."""

    @property
    def name(self) -> str:
        return "query_journal"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="query_journal",
            description=(
                "Query Foundry VTT journal entries to answer questions about their content. "
                "MUST be used when user asks about: journal content, what's in a page/chapter/section, "
                "NPCs, locations, treasures, encounters, storylines, or wants summaries. "
                "This tool reads the ACTUAL journal content from Foundry - do not answer from general D&D knowledge."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question or request"
                    },
                    "journal_name": {
                        "type": "string",
                        "description": "Optional - specific journal to search (if user mentioned one)"
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["question", "summary", "extraction"],
                        "description": "Type of query: question for Q&A, summary for overviews, extraction for listing entities"
                    }
                },
                "required": ["query", "query_type"]
            }
        )

    async def execute(
        self,
        query: str,
        query_type: str,
        journal_name: str = None,
        session_id: str = None
    ) -> ToolResponse:
        """
        Execute journal query for Q&A, summaries, or extraction.

        Args:
            query: User's question or request
            query_type: One of "question", "summary", "extraction"
            journal_name: Optional specific journal name
            session_id: Optional session ID for context

        Returns:
            ToolResponse with answer and source references
        """
        try:
            # 1. Resolve which journal to query
            if journal_name:
                journal = await self._fetch_journal_by_name(journal_name)
            elif session_id and self._has_context(session_id):
                context = self._get_context(session_id)
                journal = await self._fetch_journal_by_uuid(context.journal_uuid)
            else:
                journal = await self._select_journal_via_gemini(query)
                if journal is None:
                    journal_names = await self._list_journal_names()
                    return ToolResponse(
                        type="clarification",
                        message=f"Which journal are you asking about?\n\nAvailable journals:\n" +
                                "\n".join(f"- {name}" for name in journal_names),
                        data={"available_journals": journal_names}
                    )

            if journal is None:
                return ToolResponse(
                    type="error",
                    message=f"Could not find journal: {journal_name or 'unknown'}",
                    data=None
                )

            # 2. Check for page-specific query - if user asks about specific page, use just that page
            target_page = self._detect_page_query(query, journal)
            if target_page:
                content, section_map = self._extract_page_content(target_page, journal)
            else:
                # Extract text content with section markers from entire journal
                content, section_map = self._extract_text_with_section_markers(journal)

            # 3. Build and send prompt to Gemini
            prompt = self._build_prompt(query, query_type, content)
            response = await self._query_gemini(prompt)

            # 4. Parse response and build source references
            answer, sources = self._parse_response_with_sources(response, journal, section_map)

            # 5. Store context for follow-ups
            if session_id:
                self._update_context(session_id, journal, sources)

            # 6. Build Foundry links with descriptive labels
            foundry_links = [
                self._build_foundry_link(s.page_id, s.section or s.chapter or "Open")
                for s in sources if s.page_id
            ]

            # 7. Format and return response
            formatted = self._format_response(answer, sources, foundry_links)

            return ToolResponse(
                type="text",
                message=formatted,
                data={
                    "answer": answer,
                    "sources": [s.model_dump() for s in sources],
                    "foundry_links": foundry_links,
                    "journal_name": journal["name"],
                    "journal_uuid": journal["_id"]
                }
            )

        except Exception as e:
            logger.error(f"Journal query failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to query journal: {str(e)}",
                data=None
            )

    async def _fetch_journal_by_name(self, name: str) -> Optional[dict]:
        """Fetch journal by name from Foundry."""
        journals_result = await list_journals()
        if not journals_result.success:
            return None

        journals = [{"uuid": j.uuid, "name": j.name} for j in journals_result.journals]
        matched = self._fuzzy_match_journal(name, journals)

        if matched:
            return await self._fetch_journal_by_uuid(matched["uuid"])
        return None

    async def _fetch_journal_by_uuid(self, uuid: str) -> Optional[dict]:
        """Fetch full journal content by UUID from Foundry."""
        result = await fetch_journal(uuid)
        if result.success:
            return result.entity
        return None

    async def _list_journal_names(self) -> list[str]:
        """Get list of all journal names."""
        result = await list_journals()
        if result.success:
            return [j.name for j in result.journals]
        return []

    async def _select_journal_via_gemini(self, query: str) -> Optional[dict]:
        """Ask Gemini to pick the most relevant journal."""
        journals_result = await list_journals()
        if not journals_result.success:
            return None

        journals = [{"uuid": j.uuid, "name": j.name} for j in journals_result.journals]
        if not journals:
            return None

        journal_list = "\n".join(f"- {j['name']}" for j in journals)

        prompt = f"""Given these available D&D module journals:
{journal_list}

User question: "{query}"

Which journal most likely contains the answer?
- If clearly one journal, respond with ONLY the exact journal name
- If unclear or could be multiple, respond with "CLARIFY"
"""

        response = await self._query_gemini(prompt)

        if "CLARIFY" in response.upper():
            return None

        # Try to match response to a journal (reusing journals list from above)
        matched = self._fuzzy_match_journal(response.strip(), journals)

        if matched:
            return await self._fetch_journal_by_uuid(matched["uuid"])

        return None

    async def _query_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini and get response."""
        import asyncio
        from app.services.gemini_service import GeminiService

        def _generate():
            service = GeminiService()
            return service.api.generate_content(prompt).text

        return await asyncio.to_thread(_generate)

    def _extract_text_with_section_markers(self, journal: dict) -> tuple[str, dict]:
        """
        Parse journal HTML, preserve structure for source tracking.

        Returns:
            tuple: (extracted_text, section_to_page_id_map)
        """
        sections = []
        section_map = {}  # section_name -> page_id

        for page in journal.get("pages", []):
            page_id = page.get("_id")
            page_name = page.get("name", "")
            html_content = page.get("text", {}).get("content", "") or ""

            # Track page for section mapping
            section_map[page_name] = page_id
            sections.append(f"\n[PAGE: {page_name}]\n")

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            for element in soup.descendants:
                if element.name == "h1":
                    text = element.get_text(strip=True)
                    section_map[text] = page_id
                    sections.append(f"\n[CHAPTER: {text}]\n")
                elif element.name == "h2":
                    text = element.get_text(strip=True)
                    section_map[text] = page_id
                    sections.append(f"\n[SECTION: {text}]\n")
                elif element.name == "h3":
                    text = element.get_text(strip=True)
                    section_map[text] = page_id
                    sections.append(f"\n[SUBSECTION: {text}]\n")
                elif element.name == "p":
                    text = element.get_text(strip=True)
                    if text:
                        sections.append(text + "\n")

        return "".join(sections), section_map

    def _detect_page_query(self, query: str, journal: dict) -> Optional[dict]:
        """
        Detect if query is asking about a specific page.

        Looks for patterns like:
        - "What's in Part 2 page"
        - "What's in the Part2 page"
        - "Show me Part 2"

        Returns:
            The matching page dict if found, None otherwise
        """
        query_lower = query.lower()
        pages = journal.get("pages", [])

        # Common patterns indicating page-specific query
        page_patterns = [
            # "What's in Part2 page of the Lost Mine" -> captures "Part2"
            r"(?:what'?s?\s+in|show\s+me|tell\s+me\s+about|summarize)\s+(?:the\s+)?(.+?)\s+page(?:\s+of|\s*$)",
            # "What's in the Part2 page" at end of string
            r"(?:what'?s?\s+in|show\s+me|tell\s+me\s+about|summarize)\s+(?:the\s+)?(.+?)\s*(?:page|section|chapter)\s*$",
            # "the Part2 page content/contains/has"
            r"(?:the\s+)?(.+?)\s+page\s+(?:content|contains|has)",
        ]

        for pattern in page_patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                page_ref = match.group(1).strip()
                # Try to match against page names
                matched_page = self._fuzzy_match_page(page_ref, pages)
                if matched_page:
                    return matched_page

        # Also try direct page name matching without patterns
        for page in pages:
            page_name = page.get("name", "").lower()
            # Check if page name appears in query (normalized)
            page_words = self._normalize_words(page_name)
            query_words = self._normalize_words(query_lower)

            # If all page words appear in query, it might be asking about that page
            if page_words and all(self._word_matches(pw, query_words) for pw in page_words):
                return page

        return None

    def _fuzzy_match_page(self, name: str, pages: list[dict]) -> Optional[dict]:
        """Fuzzy match a page name against available pages."""
        if not name or not name.strip():
            return None

        name_lower = name.lower().strip()
        query_words = self._normalize_words(name_lower)

        # Try exact match first
        for page in pages:
            page_name = page.get("name", "")
            if page_name.lower() == name_lower:
                return page

        # Try substring match
        for page in pages:
            page_name = page.get("name", "")
            if name_lower in page_name.lower() or page_name.lower() in name_lower:
                return page

        # Try word-based match (handles "Part 2" vs "Part2")
        for page in pages:
            page_name = page.get("name", "")
            page_words = self._normalize_words(page_name.lower())
            if query_words and page_words:
                if all(self._word_matches(qw, page_words) for qw in query_words):
                    return page

        # Try numeric matching (Part2 -> Part 2)
        name_normalized = re.sub(r'(\d+)', r' \1 ', name_lower).strip()
        name_normalized = ' '.join(name_normalized.split())
        for page in pages:
            page_name = page.get("name", "")
            page_normalized = re.sub(r'(\d+)', r' \1 ', page_name.lower()).strip()
            page_normalized = ' '.join(page_normalized.split())
            if name_normalized == page_normalized:
                return page

        return None

    def _extract_page_content(self, page: dict, journal: dict) -> tuple[str, dict]:
        """
        Extract content from a single page.

        Returns:
            tuple: (extracted_text, section_to_page_id_map)
        """
        sections = []
        section_map = {}

        page_id = page.get("_id")
        page_name = page.get("name", "")
        html_content = page.get("text", {}).get("content", "") or ""

        section_map[page_name] = page_id
        sections.append(f"\n[PAGE: {page_name}]\n")

        soup = BeautifulSoup(html_content, "html.parser")

        for element in soup.descendants:
            if element.name == "h1":
                text = element.get_text(strip=True)
                section_map[text] = page_id
                sections.append(f"\n[CHAPTER: {text}]\n")
            elif element.name == "h2":
                text = element.get_text(strip=True)
                section_map[text] = page_id
                sections.append(f"\n[SECTION: {text}]\n")
            elif element.name == "h3":
                text = element.get_text(strip=True)
                section_map[text] = page_id
                sections.append(f"\n[SUBSECTION: {text}]\n")
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    sections.append(text + "\n")

        return "".join(sections), section_map

    def _fuzzy_match_journal(self, name: str, journals: list[dict]) -> Optional[dict]:
        """
        Fuzzy match a journal name against available journals.

        Args:
            name: Name to search for (case-insensitive, handles plural/singular)
            journals: List of journal dicts with 'uuid' and 'name' keys

        Returns:
            Matching journal dict or None. Returns first match for ambiguous cases.
        """
        if not name or not name.strip():
            return None

        name_lower = name.lower().strip()
        query_words = self._normalize_words(name_lower)

        # Try exact match first
        for j in journals:
            j_name = j.get("name", "")
            if j_name.lower() == name_lower:
                return j

        # Try substring match
        for j in journals:
            j_name = j.get("name", "")
            if name_lower in j_name.lower():
                return j

        # Try word-based match (all query words found in journal name)
        for j in journals:
            j_name = j.get("name", "")
            j_words = self._normalize_words(j_name.lower())
            if all(self._word_matches(qw, j_words) for qw in query_words):
                return j

        return None

    def _normalize_words(self, text: str) -> list[str]:
        """Extract words from text, removing common filler words."""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        # Remove common filler words
        filler = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for'}
        return [w for w in words if w not in filler]

    def _word_matches(self, query_word: str, target_words: list[str]) -> bool:
        """Check if query word matches any target word (handles plurals)."""
        for tw in target_words:
            # Exact match
            if query_word == tw:
                return True
            # Singular/plural: "mines" matches "mine", "mine" matches "mines"
            if query_word.rstrip('s') == tw.rstrip('s'):
                return True
            # Check if one is prefix of other (for partial matches like "lost" in "lostmine")
            if query_word.startswith(tw) or tw.startswith(query_word):
                return True
        return False

    def _build_foundry_link(self, page_id: str, label: str = "Open") -> str:
        """Build a Foundry link to a specific journal page."""
        return f"@UUID[JournalEntryPage.{page_id}]{{{label}}}"

    def _format_response(self, answer: str, sources: list[SourceReference], links: list[str]) -> str:
        """
        Format the final response with answer and sources.

        Args:
            answer: The answer text
            sources: List of source references
            links: List of Foundry page links

        Returns:
            Formatted response string
        """
        response_parts = [answer, "", "---", "**Sources:**"]

        for source, link in zip(sources, links):
            location = source.journal_name
            if source.chapter:
                location += f" > {source.chapter}"
            if source.section:
                location += f" > {source.section}"
            response_parts.append(f"- {location}")
            response_parts.append(f"  {link}")

        return "\n".join(response_parts)

    def _has_context(self, session_id: str) -> bool:
        """Check if session has recent (non-expired) context."""
        if session_id not in _session_contexts:
            return False

        context = _session_contexts[session_id]
        # Expire after 30 minutes
        if (datetime.now() - context.timestamp).total_seconds() > 1800:
            del _session_contexts[session_id]
            return False

        return True

    def _get_context(self, session_id: str) -> Optional[JournalContext]:
        """Get context for a session if it exists and is not expired."""
        if self._has_context(session_id):
            return _session_contexts.get(session_id)
        return None

    def _update_context(self, session_id: str, journal: dict, sources: list[SourceReference]):
        """Store context for follow-up questions."""
        _session_contexts[session_id] = JournalContext(
            journal_uuid=journal["_id"],
            journal_name=journal["name"],
            last_sections=[s.section for s in sources if s.section],
            timestamp=datetime.now()
        )

    def _build_prompt(self, query: str, query_type: str, content: str) -> str:
        """
        Build a prompt for Gemini based on query type.

        Args:
            query: User's question
            query_type: One of "question", "summary", "extraction"
            content: Extracted journal content with section markers

        Returns:
            Formatted prompt string
        """
        base_instructions = """You are a D&D module assistant. Answer based ONLY on the provided journal content.
Include [SOURCE: section name] markers in your response to indicate where information came from.

Journal Content:
"""

        if query_type == "question":
            task = f"""

Answer the following question based on the journal content above.
Be specific and cite the relevant section.

Question: {query}

Answer:"""

        elif query_type == "summary":
            task = f"""

Provide a concise summary based on the journal content above.
Focus on the key points and important details.

Request: {query}

Summary:"""

        elif query_type == "extraction":
            task = f"""

Extract and list the requested information from the journal content above.
Format as a bulleted list with section references.

Request: {query}

Extracted Information:"""

        else:
            task = f"\n\nQuestion: {query}\n\nAnswer:"

        return base_instructions + content + task

    def _parse_response_with_sources(
        self,
        response: str,
        journal: dict,
        section_map: dict
    ) -> tuple[str, list[SourceReference]]:
        """
        Parse Gemini response and extract source references.

        Args:
            response: Raw response from Gemini
            journal: Journal dict with _id and name
            section_map: Map of section names to page IDs

        Returns:
            tuple: (cleaned_answer, list_of_source_references)
        """
        # Find all [SOURCE: ...] markers
        source_pattern = r'\[SOURCE:\s*([^\]]+)\]'
        matches = re.findall(source_pattern, response)

        # Clean the response by removing source markers
        cleaned = re.sub(source_pattern, '', response).strip()

        sources = []
        seen_sections = set()

        for match in matches:
            section_name = match.strip()
            if section_name in seen_sections:
                continue
            seen_sections.add(section_name)

            page_id = section_map.get(section_name)

            sources.append(SourceReference(
                journal_name=journal["name"],
                journal_uuid=journal["_id"],
                chapter=None,  # Could be enhanced to detect chapters
                section=section_name,
                page_id=page_id
            ))

        # If no sources found, add journal-level reference
        if not sources:
            first_page_id = None
            if journal.get("pages"):
                first_page_id = journal["pages"][0].get("_id")

            sources.append(SourceReference(
                journal_name=journal["name"],
                journal_uuid=journal["_id"],
                chapter=None,
                section=None,
                page_id=first_page_id
            ))

        return cleaned, sources
