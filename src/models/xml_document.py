"""Models for representing XML documents and converting them to FoundryVTT journals.

This module provides Pydantic models that represent the structure of D&D module XML
documents and methods to parse XML files/strings and convert them to FoundryVTT
journal page format.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Literal, Union
from pydantic import BaseModel, ConfigDict


class TableRow(BaseModel):
    """Represents a single row in a table."""
    model_config = ConfigDict(frozen=True)

    cells: List[str]


class Table(BaseModel):
    """Represents a table with rows and cells."""
    model_config = ConfigDict(frozen=True)

    rows: List[TableRow]


class ListItem(BaseModel):
    """Represents a single item in a list."""
    model_config = ConfigDict(frozen=True)

    text: str


class ListContent(BaseModel):
    """Represents an ordered or unordered list."""
    model_config = ConfigDict(frozen=True)

    list_type: Literal["ordered", "unordered"]
    items: List[ListItem]


class DefinitionItem(BaseModel):
    """Represents a single term/description pair in a definition list."""
    model_config = ConfigDict(frozen=True)

    term: str
    description: str


class DefinitionList(BaseModel):
    """Represents a definition list (glossary)."""
    model_config = ConfigDict(frozen=True)

    definitions: List[DefinitionItem]


class StatBlockRaw(BaseModel):
    """Represents raw stat block XML for later parsing.

    Preserves the complete stat block XML element as a string,
    along with the name attribute for identification.
    """
    model_config = ConfigDict(frozen=True)

    name: str
    xml_element: str


class ImageRef(BaseModel):
    """Represents an image placeholder from Gemini.

    Contains a key that identifies the image for later extraction
    and insertion into the rendered output.
    """
    model_config = ConfigDict(frozen=True)

    key: str


class Content(BaseModel):
    """Represents a single content element within a page.

    Content IDs are auto-generated in the format: page_{num}_content_{idx}
    """
    model_config = ConfigDict(frozen=True)

    id: str
    type: Literal["paragraph", "section", "subsection", "subsubsection", "chapter_title", "table", "list", "definition_list", "stat_block", "image_ref"]
    data: Union[str, Table, ListContent, DefinitionList, StatBlockRaw, ImageRef]


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
                content_data = cls._parse_content_data(child)
                content.append(Content(
                    id=content_id,
                    type=content_type,
                    data=content_data
                ))

            pages.append(Page(number=page_num, content=content))

        return cls(title=title, pages=pages)

    @staticmethod
    def _parse_content_data(element: ET.Element) -> Union[str, Table, ListContent, DefinitionList, StatBlockRaw, ImageRef]:
        """Parse content data from XML element.

        Args:
            element: XML element to parse

        Returns:
            Parsed content data (string for simple types, model for complex types)
        """
        if element.tag == "table":
            rows = []
            for row_elem in element.findall('row'):
                cells = [cell.text or "" for cell in row_elem.findall('cell')]
                rows.append(TableRow(cells=cells))
            return Table(rows=rows)

        elif element.tag == "list":
            list_type = element.get('type', 'unordered')
            items = []
            for item_elem in element.findall('item'):
                items.append(ListItem(text=item_elem.text or ""))
            return ListContent(list_type=list_type, items=items)

        elif element.tag == "definition_list":
            definitions = []
            for def_elem in element.findall('definition'):
                term_elem = def_elem.find('term')
                desc_elem = def_elem.find('description')
                term = term_elem.text or "" if term_elem is not None else ""
                description = desc_elem.text or "" if desc_elem is not None else ""
                definitions.append(DefinitionItem(term=term, description=description))
            return DefinitionList(definitions=definitions)

        elif element.tag == "stat_block":
            name = element.get('name', 'Unknown')
            # Preserve complete XML element as string
            xml_str = ET.tostring(element, encoding='unicode')
            return StatBlockRaw(name=name, xml_element=xml_str)

        elif element.tag == "image_ref":
            key = element.get('key', '')
            return ImageRef(key=key)

        else:
            # Simple text content for paragraph, section, etc.
            return element.text or ""

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
            elif content.type == "table":
                html_parts.append(self._table_to_html(content.data))
            elif content.type == "list":
                html_parts.append(self._list_to_html(content.data))
            elif content.type == "definition_list":
                html_parts.append(self._definition_list_to_html(content.data))

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

    def _table_to_html(self, table: Table) -> str:
        """Convert table to HTML table.

        Args:
            table: Table model to convert

        Returns:
            HTML table string
        """
        html_parts = ["<table>"]
        for row in table.rows:
            html_parts.append("<tr>")
            for cell in row.cells:
                html_parts.append(f"<td>{cell}</td>")
            html_parts.append("</tr>")
        html_parts.append("</table>")
        return "\n".join(html_parts)

    def _list_to_html(self, list_content: ListContent) -> str:
        """Convert list to HTML list.

        Args:
            list_content: ListContent model to convert

        Returns:
            HTML list string (ul or ol)
        """
        tag = "ol" if list_content.list_type == "ordered" else "ul"
        html_parts = [f"<{tag}>"]
        for item in list_content.items:
            html_parts.append(f"<li>{item.text}</li>")
        html_parts.append(f"</{tag}>")
        return "\n".join(html_parts)

    def _definition_list_to_html(self, def_list: DefinitionList) -> str:
        """Convert definition list to HTML definition list.

        Args:
            def_list: DefinitionList model to convert

        Returns:
            HTML definition list string
        """
        html_parts = ["<dl>"]
        for definition in def_list.definitions:
            html_parts.append(f"<dt>{definition.term}</dt>")
            html_parts.append(f"<dd>{definition.description}</dd>")
        html_parts.append("</dl>")
        return "\n".join(html_parts)


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
