"""Models for Journal representation - mutable working representation with semantic hierarchy.

This module provides the Journal class that transforms XMLDocument's flat page structure
into a semantic hierarchy (Chapters -> Sections -> Subsections -> Subsubsections).
Journal is mutable and owns the image registry for managing image references.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from models.xml_document import XMLDocument, Content


class ImageMetadata(BaseModel):
    """Metadata for an image reference in the journal.

    Tracks image references from the XML document and their metadata.
    """
    key: str
    source_page: int
    type: str  # "map", "illustration", "diagram", etc.
    description: Optional[str] = None
    file_path: Optional[str] = None


class Subsubsection(BaseModel):
    """Represents a level-4 heading (subsubsection) in the journal hierarchy."""
    title: str
    content: List[Content] = Field(default_factory=list)


class Subsection(BaseModel):
    """Represents a level-3 heading (subsection) in the journal hierarchy."""
    title: str
    subsubsections: List[Subsubsection] = Field(default_factory=list)
    content: List[Content] = Field(default_factory=list)


class Section(BaseModel):
    """Represents a level-2 heading (section) in the journal hierarchy."""
    title: str
    subsections: List[Subsection] = Field(default_factory=list)
    content: List[Content] = Field(default_factory=list)


class Chapter(BaseModel):
    """Represents a chapter in the journal hierarchy."""
    title: str
    sections: List[Section] = Field(default_factory=list)
    content: List[Content] = Field(default_factory=list)


class Journal(BaseModel):
    """Mutable working representation of a D&D module with semantic hierarchy.

    Transforms XMLDocument's flat page structure into a hierarchical structure:
    Chapters -> Sections -> Subsections -> Subsubsections

    The Journal owns the image registry and reassigns content IDs to semantic format:
    chapter_N_section_M_content_K instead of page_X_content_Y.
    """
    title: str
    chapters: List[Chapter] = Field(default_factory=list)
    image_registry: Dict[str, ImageMetadata] = Field(default_factory=dict)
    source: Optional[XMLDocument] = Field(default=None, exclude=True)

    @classmethod
    def from_xml_document(cls, xml_doc: XMLDocument) -> 'Journal':
        """Create a Journal from an XMLDocument.

        Flattens the page-based structure into a semantic hierarchy where
        sections can span multiple pages.

        Args:
            xml_doc: The source XMLDocument to convert

        Returns:
            Journal with semantic hierarchy
        """
        # Extract image references and build registry
        image_registry = cls._extract_image_refs(xml_doc)

        # Build semantic hierarchy from pages
        chapters = cls._build_hierarchy(xml_doc)

        return cls(
            title=xml_doc.title,
            chapters=chapters,
            image_registry=image_registry,
            source=xml_doc
        )

    @staticmethod
    def _extract_image_refs(xml_doc: XMLDocument) -> Dict[str, ImageMetadata]:
        """Extract image references from XMLDocument and build registry.

        Args:
            xml_doc: The source XMLDocument

        Returns:
            Dictionary mapping image keys to ImageMetadata
        """
        # Stub implementation - will be implemented in Task 7
        return {}

    @staticmethod
    def _build_hierarchy(xml_doc: XMLDocument) -> List[Chapter]:
        """Build semantic hierarchy from page-based XMLDocument structure.

        Converts flat page structure to hierarchical structure where sections
        can span multiple pages. Reassigns content IDs to semantic format.

        Args:
            xml_doc: The source XMLDocument

        Returns:
            List of Chapter objects with nested hierarchy
        """
        chapters = []
        current_chapter = None
        current_section = None
        current_subsection = None
        current_subsubsection = None

        chapter_idx = -1
        section_idx = -1
        subsection_idx = -1
        subsubsection_idx = -1
        content_counter = 0

        # Iterate through all pages and content
        for page in xml_doc.pages:
            for content in page.content:
                if content.type == "chapter_title":
                    # Close previous containers
                    if current_subsubsection is not None and current_subsection is not None:
                        current_subsection.subsubsections.append(current_subsubsection)
                    if current_subsection is not None and current_section is not None:
                        current_section.subsections.append(current_subsection)
                    if current_section is not None and current_chapter is not None:
                        current_chapter.sections.append(current_section)
                    if current_chapter is not None:
                        chapters.append(current_chapter)

                    # Start a new chapter
                    chapter_idx += 1
                    section_idx = -1
                    subsection_idx = -1
                    subsubsection_idx = -1
                    content_counter = 0

                    current_chapter = Chapter(title=content.data)
                    current_section = None
                    current_subsection = None
                    current_subsubsection = None

                elif content.type == "section":
                    # Close previous containers
                    if current_subsubsection is not None and current_subsection is not None:
                        current_subsection.subsubsections.append(current_subsubsection)
                    if current_subsection is not None and current_section is not None:
                        current_section.subsections.append(current_subsection)
                    if current_section is not None and current_chapter is not None:
                        current_chapter.sections.append(current_section)

                    # Start a new section
                    section_idx += 1
                    subsection_idx = -1
                    subsubsection_idx = -1
                    content_counter = 0

                    current_section = Section(title=content.data)
                    current_subsection = None
                    current_subsubsection = None

                elif content.type == "subsection":
                    # Close previous containers
                    if current_subsubsection is not None and current_subsection is not None:
                        current_subsection.subsubsections.append(current_subsubsection)
                    if current_subsection is not None and current_section is not None:
                        current_section.subsections.append(current_subsection)

                    # Start a new subsection
                    subsection_idx += 1
                    subsubsection_idx = -1
                    content_counter = 0

                    current_subsection = Subsection(title=content.data)
                    current_subsubsection = None

                elif content.type == "subsubsection":
                    # Close previous container
                    if current_subsubsection is not None and current_subsection is not None:
                        current_subsection.subsubsections.append(current_subsubsection)

                    # Start a new subsubsection
                    subsubsection_idx += 1
                    content_counter = 0

                    current_subsubsection = Subsubsection(title=content.data)

                else:
                    # Regular content - add to current container
                    # Reassign content ID to semantic format
                    new_id = f"chapter_{chapter_idx}_section_{section_idx}_content_{content_counter}"
                    content_counter += 1

                    # Create new content with reassigned ID
                    new_content = Content(
                        id=new_id,
                        type=content.type,
                        data=content.data
                    )

                    # Add to the most specific container available
                    if current_subsubsection is not None:
                        current_subsubsection.content.append(new_content)
                    elif current_subsection is not None:
                        current_subsection.content.append(new_content)
                    elif current_section is not None:
                        current_section.content.append(new_content)
                    elif current_chapter is not None:
                        current_chapter.content.append(new_content)

        # Close final containers
        if current_subsubsection is not None and current_subsection is not None:
            current_subsection.subsubsections.append(current_subsubsection)
        if current_subsection is not None and current_section is not None:
            current_section.subsections.append(current_subsection)
        if current_section is not None and current_chapter is not None:
            current_chapter.sections.append(current_section)
        if current_chapter is not None:
            chapters.append(current_chapter)

        return chapters
