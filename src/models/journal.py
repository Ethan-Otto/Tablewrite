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
    insert_before_content_id: Optional[str] = None  # For repositioning images


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

        Extracts all ImageRef elements from the XMLDocument's pages and creates
        ImageMetadata entries for each one. The ImageRef elements remain in the
        content stream for later rendering.

        Page number parsing:
        - If key format is "page_X_..." (e.g., "page_5_top_battle_map"), extract X
        - Otherwise, use the actual page number where the ImageRef appears

        Type inference:
        - If key contains "battle_map" or "map": type = "map"
        - If key contains "illustration": type = "illustration"
        - If key contains "diagram": type = "diagram"
        - Otherwise: type = "unknown"

        Args:
            xml_doc: The source XMLDocument

        Returns:
            Dictionary mapping image keys to ImageMetadata
        """
        import re
        registry = {}

        for page in xml_doc.pages:
            for content in page.content:
                if content.type == "image_ref":
                    image_ref = content.data
                    key = image_ref.key

                    # Parse page number from key if format is page_X_...
                    page_num_match = re.match(r'page_(\d+)_', key)
                    if page_num_match:
                        source_page = int(page_num_match.group(1))
                    else:
                        # Fall back to actual page number
                        source_page = page.number

                    # Infer type from key
                    if "battle_map" in key or "_map" in key or key.endswith("_map"):
                        img_type = "map"
                    elif "illustration" in key:
                        img_type = "illustration"
                    elif "diagram" in key:
                        img_type = "diagram"
                    else:
                        img_type = "unknown"

                    # Create ImageMetadata entry
                    registry[key] = ImageMetadata(
                        key=key,
                        source_page=source_page,
                        type=img_type
                    )

        return registry

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

    def add_image(self, key: str, metadata: ImageMetadata):
        """Add new image (scene artwork, custom, etc.) to registry.

        Args:
            key: Unique identifier for the image
            metadata: ImageMetadata object with image details
        """
        self.image_registry[key] = metadata

    def reposition_image(self, key: str, new_content_id: str):
        """Move image to different location by setting insert_before_content_id.

        Args:
            key: Image key in the registry
            new_content_id: Content ID to insert the image before
        """
        if key in self.image_registry:
            self.image_registry[key].insert_before_content_id = new_content_id

    def remove_image(self, key: str):
        """Remove image from registry.

        Args:
            key: Image key to remove
        """
        if key in self.image_registry:
            del self.image_registry[key]

    def to_foundry_html(self, image_mapping: Optional[Dict[str, str]] = None) -> str:
        """Export journal to FoundryVTT-ready HTML format.

        Renders the semantic hierarchy (Chapters -> Sections -> Subsections -> Subsubsections)
        into HTML with proper heading levels (h1 -> h2 -> h3 -> h4) and inserts images
        from the image_mapping.

        Args:
            image_mapping: Dictionary mapping image keys to URLs/paths for rendering.
                          Keys should match those in image_registry.

        Returns:
            HTML string with semantic structure and embedded images
        """
        if image_mapping is None:
            image_mapping = {}

        html_parts = []

        # Render each chapter
        for chapter in self.chapters:
            html_parts.append(f"<h1>{chapter.title}</h1>\n")

            # Render chapter-level content
            for content in chapter.content:
                html_parts.append(self._render_content(content, image_mapping))

            # Render sections
            for section in chapter.sections:
                html_parts.append(self._render_section(section, image_mapping, level=2))

        return "".join(html_parts)

    def _render_section(self, section: Section, image_mapping: Dict[str, str], level: int) -> str:
        """Render a section with proper heading level.

        Args:
            section: Section to render
            image_mapping: Dictionary mapping image keys to URLs/paths
            level: Heading level (2 for section, increments for nested levels)

        Returns:
            HTML string for the section
        """
        html_parts = []

        # Render section title
        html_parts.append(f"<h{level}>{section.title}</h{level}>\n")

        # Render section-level content
        for content in section.content:
            html_parts.append(self._render_content(content, image_mapping))

        # Render subsections
        for subsection in section.subsections:
            html_parts.append(self._render_subsection(subsection, image_mapping, level + 1))

        return "".join(html_parts)

    def _render_subsection(self, subsection: Subsection, image_mapping: Dict[str, str], level: int) -> str:
        """Render a subsection with proper heading level.

        Args:
            subsection: Subsection to render
            image_mapping: Dictionary mapping image keys to URLs/paths
            level: Heading level (3 for subsection, increments for nested levels)

        Returns:
            HTML string for the subsection
        """
        html_parts = []

        # Render subsection title
        html_parts.append(f"<h{level}>{subsection.title}</h{level}>\n")

        # Render subsection-level content
        for content in subsection.content:
            html_parts.append(self._render_content(content, image_mapping))

        # Render subsubsections
        for subsubsection in subsection.subsubsections:
            html_parts.append(self._render_subsubsection(subsubsection, image_mapping, level + 1))

        return "".join(html_parts)

    def _render_subsubsection(self, subsubsection: Subsubsection, image_mapping: Dict[str, str], level: int) -> str:
        """Render a subsubsection with proper heading level.

        Args:
            subsubsection: Subsubsection to render
            image_mapping: Dictionary mapping image keys to URLs/paths
            level: Heading level (4 for subsubsection)

        Returns:
            HTML string for the subsubsection
        """
        html_parts = []

        # Render subsubsection title
        html_parts.append(f"<h{level}>{subsubsection.title}</h{level}>\n")

        # Render content
        for content in subsubsection.content:
            html_parts.append(self._render_content(content, image_mapping))

        return "".join(html_parts)

    def _render_content(self, content: Content, image_mapping: Dict[str, str]) -> str:
        """Render a single content element with image insertion support.

        Checks if any images should be inserted before this content element
        (via insert_before_content_id in image_registry) and renders them first.
        Then renders the content element itself.

        Args:
            content: Content element to render
            image_mapping: Dictionary mapping image keys to URLs/paths

        Returns:
            HTML string for the content element (including any images to insert before it)
        """
        import re
        html_parts = []

        # Check if any images should be inserted before this content
        for key, metadata in self.image_registry.items():
            if metadata.insert_before_content_id == content.id:
                # Insert image before this content
                if key in image_mapping:
                    html_parts.append(f'<img src="{image_mapping[key]}" alt="{metadata.type}" />\n')

        # Render the content element itself
        if content.type == "paragraph":
            # Convert markdown formatting to HTML
            text = self._convert_markdown_to_html(content.data)
            html_parts.append(f"<p>{text}</p>\n")

        elif content.type == "boxed_text":
            # Render boxed text using <aside> with decorative styling
            text = self._convert_markdown_to_html(content.data)
            html_parts.append(
                '<aside style="position: relative; background: #fef9e7; padding: 20px 50px; '
                'margin: 20px 0; box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);">\n'
                '  <span style="position: absolute; left: 15px; top: 10px; bottom: 10px; width: 4px; '
                'background: linear-gradient(to bottom, #5c3317 0%, #8b4513 20%, #5c3317 50%, #8b4513 80%, #5c3317 100%); '
                'border-radius: 2px;"></span>\n'
                '  <span style="position: absolute; right: 15px; top: 10px; bottom: 10px; width: 4px; '
                'background: linear-gradient(to bottom, #5c3317 0%, #8b4513 20%, #5c3317 50%, #8b4513 80%, #5c3317 100%); '
                'border-radius: 2px;"></span>\n'
                f'  <p>{text}</p>\n'
                '</aside>\n'
            )

        elif content.type == "image_ref":
            # Render image_ref at its original location
            key = content.data.key
            if key in image_mapping:
                img_type = self.image_registry.get(key, ImageMetadata(key=key, source_page=0, type="image")).type
                html_parts.append(f'<img src="{image_mapping[key]}" alt="{img_type}" />\n')

        elif content.type == "table":
            # Render table structure
            html_parts.append('<table border="1">\n')
            for row in content.data.rows:
                html_parts.append('  <tr>\n')
                for cell in row.cells:
                    cell_text = self._convert_markdown_to_html(cell)
                    html_parts.append(f'    <td>{cell_text}</td>\n')
                html_parts.append('  </tr>\n')
            html_parts.append('</table>\n')

        elif content.type == "list":
            # Render list (ordered or unordered)
            list_tag = "ol" if content.data.list_type == "ordered" else "ul"
            html_parts.append(f'<{list_tag}>\n')
            for item in content.data.items:
                item_text = self._convert_markdown_to_html(item.text)
                html_parts.append(f'  <li>{item_text}</li>\n')
            html_parts.append(f'</{list_tag}>\n')

        elif content.type == "definition_list":
            # Render definition list
            html_parts.append('<dl>\n')
            for definition in content.data.definitions:
                term_text = self._convert_markdown_to_html(definition.term)
                desc_text = self._convert_markdown_to_html(definition.description)
                html_parts.append(f'  <dt>{term_text}</dt>\n')
                html_parts.append(f'  <dd>{desc_text}</dd>\n')
            html_parts.append('</dl>\n')

        # Skip other content types (footer, page_number, stat_block, etc.)
        # These are handled elsewhere or not rendered in journal HTML

        return "".join(html_parts)

    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert Markdown formatting to HTML tags.

        Args:
            text: Text with Markdown formatting (**bold**, *italic*)

        Returns:
            Text with HTML tags (<strong>, <em>)
        """
        import re

        if not text:
            return text

        # Convert bold first (to avoid conflicts with italic)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Then convert italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

        return text

    def to_html(self, image_mapping: Optional[Dict[str, str]] = None) -> str:
        """Export journal to HTML format.

        Currently a stub that calls to_foundry_html(). May be extended in the future
        to support different HTML export formats (e.g., standalone HTML pages).

        Args:
            image_mapping: Dictionary mapping image keys to URLs/paths for rendering

        Returns:
            HTML string
        """
        return self.to_foundry_html(image_mapping)

    def to_markdown(self, image_mapping: Optional[Dict[str, str]] = None) -> str:
        """Export journal to Markdown format.

        Args:
            image_mapping: Dictionary mapping image keys to URLs/paths for rendering

        Returns:
            Markdown string (currently a placeholder)
        """
        return "TODO: Markdown export not yet implemented"
