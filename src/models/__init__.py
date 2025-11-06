"""Models for representing XML documents and their conversion to FoundryVTT journals."""

from models.xml_document import (
    Content,
    DefinitionItem,
    DefinitionList,
    ImageRef,
    ListContent,
    ListItem,
    Page,
    StatBlockRaw,
    Table,
    TableRow,
    XMLDocument,
    parse_xml_file,
    parse_xml_string,
)

from models.journal import (
    Chapter,
    ImageMetadata,
    Journal,
    Section,
    Subsection,
    Subsubsection,
)

__all__ = [
    # XMLDocument models
    "Content",
    "DefinitionItem",
    "DefinitionList",
    "ImageRef",
    "ListContent",
    "ListItem",
    "Page",
    "StatBlockRaw",
    "Table",
    "TableRow",
    "XMLDocument",
    "parse_xml_file",
    "parse_xml_string",
    # Journal models
    "Chapter",
    "ImageMetadata",
    "Journal",
    "Section",
    "Subsection",
    "Subsubsection",
]
