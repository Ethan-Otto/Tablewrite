"""Models for representing XML documents and converting them to FoundryVTT journals.

This module provides Pydantic models that represent the structure of D&D module XML
documents and methods to parse XML files/strings and convert them to FoundryVTT
journal page format.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel, ConfigDict


class Content(BaseModel):
    """Represents a single content element within a page.

    Content IDs are auto-generated in the format: page_{num}_content_{idx}
    """
    model_config = ConfigDict(frozen=True)

    id: str
    type: Literal["paragraph", "section", "subsection", "subsubsection", "chapter_title"]
    data: str


class Page(BaseModel):
    """Represents a single page within an XML document."""
    model_config = ConfigDict(frozen=True)

    number: int
    content: List[Content]


class XMLDocument(BaseModel):
    """Represents a complete XML document (chapter).

    This is an immutable model that can be parsed from XML strings or files.
    """
    model_config = ConfigDict(frozen=True)

    title: str
    pages: List[Page]

    @classmethod
    def from_xml(cls, xml_string: str) -> 'XMLDocument':
        """Parse XML string to XMLDocument.

        Args:
            xml_string: XML content as a string

        Returns:
            XMLDocument representation of the XML

        Raises:
            xml.etree.ElementTree.ParseError: If the XML is malformed
        """
        root = ET.fromstring(xml_string)
        title = root.tag
        pages = []

        for page_elem in root.findall('page'):
            page_num = int(page_elem.get('number', '1'))
            content = []

            for idx, child in enumerate(page_elem):
                content_id = f"page_{page_num}_content_{idx}"
                content_type = child.tag
                content_data = child.text or ""
                content.append(Content(
                    id=content_id,
                    type=content_type,
                    data=content_data
                ))

            pages.append(Page(number=page_num, content=content))

        return cls(title=title, pages=pages)

    def to_journal_pages(self) -> List[dict]:
        """Convert the document to FoundryVTT journal page format.

        Returns:
            List of dicts with 'name' and 'content' keys for each page
        """
        journal_pages = []

        for page in self.pages:
            html_content = self._page_to_html(page)
            journal_pages.append({
                "name": f"Page {page.number}",
                "content": html_content
            })

        return journal_pages

    def _page_to_html(self, page: Page) -> str:
        """Convert a page to HTML content.

        Args:
            page: The Page to convert

        Returns:
            HTML string representation of the page
        """
        html_parts = []

        for content in page.content:
            if content.type == "chapter_title":
                html_parts.append(f"<h1>{content.data}</h1>")
            elif content.type == "section":
                html_parts.append(f"<h2>{content.data}</h2>")
            elif content.type == "subsection":
                html_parts.append(f"<h3>{content.data}</h3>")
            elif content.type == "subsubsection":
                html_parts.append(f"<h4>{content.data}</h4>")
            elif content.type == "paragraph":
                html_parts.append(self._paragraph_to_html(content.data))

        return "\n".join(html_parts)

    def _paragraph_to_html(self, text: str) -> str:
        """Convert paragraph to HTML, handling markdown-style formatting.

        Args:
            text: Text with markdown formatting

        Returns:
            HTML string with markdown converted to HTML tags
        """
        # Convert **bold** to <strong>
        text = self._convert_markdown_bold(text)
        # Convert *italic* to <em>
        text = self._convert_markdown_italic(text)
        return f"<p>{text}</p>"

    def _convert_markdown_bold(self, text: str) -> str:
        """Convert **bold** markdown to <strong> HTML tags.

        Args:
            text: Text with markdown formatting

        Returns:
            Text with bold converted to HTML
        """
        import re
        return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    def _convert_markdown_italic(self, text: str) -> str:
        """Convert *italic* markdown to <em> HTML tags.

        Args:
            text: Text with markdown formatting

        Returns:
            Text with italic converted to HTML
        """
        import re
        # Use negative lookbehind/lookahead to avoid matching ** from bold
        return re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)


def parse_xml_file(file_path: Path) -> XMLDocument:
    """Parse an XML file into an XMLDocument model.

    Args:
        file_path: Path to the XML file

    Returns:
        XMLDocument representation of the file

    Raises:
        FileNotFoundError: If the file doesn't exist
        xml.etree.ElementTree.ParseError: If the XML is malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"XML file not found: {file_path}")

    xml_string = file_path.read_text()
    return XMLDocument.from_xml(xml_string)


def parse_xml_string(xml_string: str) -> XMLDocument:
    """Parse an XML string into an XMLDocument model.

    Args:
        xml_string: XML content as a string

    Returns:
        XMLDocument representation of the XML

    Raises:
        xml.etree.ElementTree.ParseError: If the XML is malformed
    """
    return XMLDocument.from_xml(xml_string)
