"""Models for representing XML documents and converting them to FoundryVTT journals.

This module provides Pydantic models that represent the structure of D&D module XML
documents and methods to parse XML files/strings and convert them to FoundryVTT
journal page format.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class XMLElement(BaseModel):
    """Base class for XML elements."""

    tag: str
    text: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class XMLParagraph(XMLElement):
    """Represents a paragraph element (<p>)."""

    def __init__(self, text: str = "", **kwargs):
        super().__init__(tag="p", text=text, **kwargs)


class XMLListItem(XMLElement):
    """Represents a list item element (<item>)."""

    def __init__(self, text: str = "", **kwargs):
        super().__init__(tag="item", text=text, **kwargs)


class XMLList(XMLElement):
    """Represents a list element (<list>) containing items."""

    items: List[XMLListItem] = Field(default_factory=list)

    def __init__(self, items: List[XMLListItem] = None, **kwargs):
        if items is None:
            items = []
        super().__init__(tag="list", items=items, **kwargs)


class XMLStatBlock(XMLElement):
    """Represents a stat block element (<stat_block>)."""

    name: str
    content: str

    def __init__(self, name: str, content: str, **kwargs):
        attributes = kwargs.get("attributes", {})
        attributes["name"] = name
        super().__init__(
            tag="stat_block",
            text=content,
            name=name,
            content=content,
            attributes=attributes,
            **{k: v for k, v in kwargs.items() if k != "attributes"}
        )


class XMLSection(XMLElement):
    """Represents a section element (<section>) containing other elements."""

    title: str
    elements: List[Union[XMLParagraph, XMLList, XMLStatBlock]] = Field(default_factory=list)

    def __init__(self, title: str, elements: List = None, **kwargs):
        if elements is None:
            elements = []
        super().__init__(tag="section", text=title, title=title, elements=elements, **kwargs)


class XMLPage(XMLElement):
    """Represents a page element (<page>) containing sections."""

    number: int
    sections: List[XMLSection] = Field(default_factory=list)

    def __init__(self, number: int, sections: List[XMLSection] = None, **kwargs):
        if sections is None:
            sections = []
        attributes = kwargs.get("attributes", {})
        attributes["number"] = str(number)
        super().__init__(
            tag="page",
            number=number,
            sections=sections,
            attributes=attributes,
            **{k: v for k, v in kwargs.items() if k != "attributes"}
        )


class XMLDocument(BaseModel):
    """Represents a complete XML document (chapter)."""

    chapter_name: str
    pages: List[XMLPage] = Field(default_factory=list)

    def to_journal_pages(self) -> List[Dict[str, str]]:
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

    def _page_to_html(self, page: XMLPage) -> str:
        """Convert a page to HTML content.

        Args:
            page: The XMLPage to convert

        Returns:
            HTML string representation of the page
        """
        html_parts = []

        for section in page.sections:
            # Add section title as heading
            if section.title:
                html_parts.append(f"<h2>{section.title}</h2>")

            # Convert section elements
            for element in section.elements:
                if isinstance(element, XMLParagraph):
                    html_parts.append(self._paragraph_to_html(element))
                elif isinstance(element, XMLList):
                    html_parts.append(self._list_to_html(element))
                elif isinstance(element, XMLStatBlock):
                    html_parts.append(self._stat_block_to_html(element))

        return "\n".join(html_parts)

    def _paragraph_to_html(self, para: XMLParagraph) -> str:
        """Convert paragraph to HTML, handling markdown-style formatting.

        Args:
            para: XMLParagraph to convert

        Returns:
            HTML string with markdown converted to HTML tags
        """
        text = para.text or ""
        # Convert **bold** to <strong>
        text = self._convert_markdown_bold(text)
        # Convert *italic* to <em>
        text = self._convert_markdown_italic(text)
        return f"<p>{text}</p>"

    def _list_to_html(self, list_elem: XMLList) -> str:
        """Convert list to HTML.

        Args:
            list_elem: XMLList to convert

        Returns:
            HTML unordered list string
        """
        if not list_elem.items:
            return "<ul></ul>"

        items_html = []
        for item in list_elem.items:
            text = item.text or ""
            items_html.append(f"  <li>{text}</li>")

        return "<ul>\n" + "\n".join(items_html) + "\n</ul>"

    def _stat_block_to_html(self, stat_block: XMLStatBlock) -> str:
        """Convert stat block to HTML.

        Args:
            stat_block: XMLStatBlock to convert

        Returns:
            HTML representation of the stat block
        """
        content = stat_block.content or ""
        # Preserve formatting with <pre> tag
        return f'<div class="stat-block"><h3>{stat_block.name}</h3><pre>{content}</pre></div>'

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

    tree = ET.parse(file_path)
    root = tree.getroot()
    return _parse_xml_element(root)


def parse_xml_string(xml_string: str) -> XMLDocument:
    """Parse an XML string into an XMLDocument model.

    Args:
        xml_string: XML content as a string

    Returns:
        XMLDocument representation of the XML

    Raises:
        xml.etree.ElementTree.ParseError: If the XML is malformed
    """
    root = ET.fromstring(xml_string)
    return _parse_xml_element(root)


def _parse_xml_element(root: ET.Element) -> XMLDocument:
    """Parse XML element tree into XMLDocument.

    Args:
        root: Root element of the XML tree

    Returns:
        XMLDocument representation
    """
    chapter_name = root.tag
    pages = []

    for page_elem in root.findall("page"):
        page_number = int(page_elem.get("number", "1"))
        sections = []

        current_section_title = None
        current_section_elements = []

        for child in page_elem:
            if child.tag == "section":
                # Save previous section if exists
                if current_section_title is not None:
                    sections.append(XMLSection(
                        title=current_section_title,
                        elements=current_section_elements
                    ))
                # Start new section
                current_section_title = child.text or ""
                current_section_elements = []

            elif child.tag == "p":
                # If no section yet, create a default one
                if current_section_title is None:
                    current_section_title = ""
                para = XMLParagraph(text=child.text or "")
                current_section_elements.append(para)

            elif child.tag == "list":
                if current_section_title is None:
                    current_section_title = ""
                items = []
                for item_elem in child.findall("item"):
                    items.append(XMLListItem(text=item_elem.text or ""))
                list_obj = XMLList(items=items)
                current_section_elements.append(list_obj)

            elif child.tag == "stat_block":
                if current_section_title is None:
                    current_section_title = ""
                name = child.get("name", "")
                content = child.text or ""
                stat_block = XMLStatBlock(name=name, content=content)
                current_section_elements.append(stat_block)

        # Add the last section
        if current_section_title is not None:
            sections.append(XMLSection(
                title=current_section_title,
                elements=current_section_elements
            ))

        pages.append(XMLPage(number=page_number, sections=sections))

    return XMLDocument(chapter_name=chapter_name, pages=pages)
