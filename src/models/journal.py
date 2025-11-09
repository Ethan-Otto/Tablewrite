"""Models for Journal representation - mutable working representation with semantic hierarchy.

This module provides the Journal class that transforms XMLDocument's flat page structure
into a semantic hierarchy (Chapters -> Sections -> Subsections -> Subsubsections).
Journal is mutable and owns the image registry for managing image references.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field, PrivateAttr

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
    _page_to_semantic_id_map: Dict[str, str] = PrivateAttr(default_factory=dict)

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

        # Build semantic hierarchy from pages and capture ID mapping
        chapters, id_map = cls._build_hierarchy(xml_doc)

        journal = cls(
            title=xml_doc.title,
            chapters=chapters,
            image_registry=image_registry,
            source=xml_doc
        )
        journal._page_to_semantic_id_map = id_map

        return journal

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
    def _build_hierarchy(xml_doc: XMLDocument) -> tuple[List[Chapter], Dict[str, str]]:
        """Build semantic hierarchy from page-based XMLDocument structure.

        Converts flat page structure to hierarchical structure where sections
        can span multiple pages. Reassigns content IDs to semantic format.

        Args:
            xml_doc: The source XMLDocument

        Returns:
            Tuple of (chapters, id_map) where id_map maps original page-based IDs
            to new semantic IDs (e.g., "page_5_content_3" -> "chapter_0_section_2_content_5")
        """
        chapters = []
        id_map = {}  # Maps original ID -> semantic ID
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

                    # Track the ID mapping (original -> semantic)
                    if content.id:
                        id_map[content.id] = new_id

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

        return chapters, id_map

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

    def add_map_assets(self, maps_metadata: List[Dict], image_dir):
        """Add map assets from extraction metadata to image registry.

        Automatically positions maps near their source page in the content stream.

        Args:
            maps_metadata: List of map metadata dicts from maps_metadata.json
            image_dir: Path to directory containing map image files (can be str or Path)
        """
        from pathlib import Path

        image_dir = Path(image_dir)

        for map_data in maps_metadata:
            # Generate key from page number and name
            page_num = map_data["page_num"]
            safe_name = map_data["name"].lower().replace(" ", "_")
            key = f"page_{page_num:03d}_{safe_name}"

            # Find file path
            file_path = None
            for ext in [".png", ".jpg", ".jpeg"]:
                candidate = image_dir / f"{key}{ext}"
                if candidate.exists():
                    file_path = candidate
                    break

            # Create ImageMetadata
            metadata = ImageMetadata(
                key=key,
                source_page=page_num,
                type="map",
                description=map_data.get("name"),
                file_path=str(file_path) if file_path else None
            )

            # Find insertion point: first content after source page
            insert_id = self._find_content_after_page(page_num)
            if insert_id:
                metadata.insert_before_content_id = insert_id

            self.image_registry[key] = metadata

    def _find_content_after_page(self, page_num: int) -> Optional[str]:
        """Find the first content ID that appears after a given source page.

        Uses source XMLDocument to find content on the page, then maps the original
        page-based ID to the semantic ID using the stored mapping.

        Args:
            page_num: Source page number (1-indexed)

        Returns:
            Semantic content ID or None if not found
        """
        if not self.source:
            return None

        # Find the page in source XMLDocument
        for page in self.source.pages:
            if page.number >= page_num:
                # Find the first non-heading content on this page
                for content in page.content:
                    if content.type not in ["chapter_title", "section", "subsection", "subsubsection"]:
                        # Map original page-based ID to semantic ID
                        if content.id and content.id in self._page_to_semantic_id_map:
                            return self._page_to_semantic_id_map[content.id]

        # Fallback: if we can't find a matching page, use heuristic
        return self._get_first_content_id_heuristic()

    def _get_first_content_id_heuristic(self) -> Optional[str]:
        """Get first content ID as fallback heuristic."""
        for chapter in self.chapters:
            if chapter.content:
                return chapter.content[0].id
            for section in chapter.sections:
                if section.content:
                    return section.content[0].id
        return None

    def add_scene_artwork(self, scenes: List[Dict], image_dir):
        """Add scene artwork to image registry with intelligent positioning.

        Positions scenes at section/subsection boundaries by fuzzy-matching
        section_path to Journal hierarchy.

        Args:
            scenes: List of scene dicts with section_path, name, description
            image_dir: Path to scene_artwork/images directory (can be str or Path)
        """
        import re
        from pathlib import Path

        image_dir = Path(image_dir)

        for i, scene in enumerate(scenes, start=1):
            # Generate key from scene name
            safe_name = re.sub(r'[^\w\s-]', '', scene["name"].lower())
            safe_name = re.sub(r'[-\s]+', '_', safe_name)
            key = f"scene_{safe_name}"

            # Find file path (format: scene_NNN_name.png)
            file_path = None
            for image_file in image_dir.glob(f"scene_{i:03d}_*.png"):
                file_path = image_file
                break

            # Create ImageMetadata
            metadata = ImageMetadata(
                key=key,
                source_page=0,  # Scene artwork doesn't have source page
                type="illustration",
                description=scene.get("description"),
                file_path=str(file_path) if file_path else None
            )

            # Find insertion point by matching section_path
            insert_id = self._find_section_by_path(scene["section_path"])
            if insert_id:
                metadata.insert_before_content_id = insert_id

            self.image_registry[key] = metadata

    def _find_section_by_path(self, section_path: str) -> Optional[str]:
        """Find content ID for a section by fuzzy-matching section_path.

        Section path format: "Chapter Title → Section Title → Subsection Title"

        Args:
            section_path: Hierarchical path from scene extraction

        Returns:
            Content ID of first content in matched section/subsection
        """
        import re

        # Parse section path
        parts = [p.strip() for p in section_path.split("→")]
        if len(parts) < 2:
            return None

        chapter_title = parts[0]
        section_title = parts[1] if len(parts) > 1 else None
        subsection_title = parts[2] if len(parts) > 2 else None

        # Normalize titles for fuzzy matching (lowercase, remove punctuation)
        def normalize(text):
            return re.sub(r'[^\w\s]', '', text.lower())

        chapter_norm = normalize(chapter_title)

        # Find matching chapter
        for chapter in self.chapters:
            if normalize(chapter.title) == chapter_norm:
                # If only chapter specified, insert at first section
                if not section_title:
                    if chapter.sections and chapter.sections[0].content:
                        return chapter.sections[0].content[0].id
                    return None

                # Find matching section
                section_norm = normalize(section_title)
                for section in chapter.sections:
                    if normalize(section.title) == section_norm:
                        # If only chapter + section, insert at first content
                        if not subsection_title:
                            if section.content:
                                return section.content[0].id
                            return None

                        # Find matching subsection
                        subsection_norm = normalize(subsection_title)
                        for subsection in section.subsections:
                            if normalize(subsection.title) == subsection_norm:
                                if subsection.content:
                                    return subsection.content[0].id

        return None

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

    def export_standalone_html(self, output_dir) -> str:
        """Export journal as standalone HTML with embedded images.

        Creates a self-contained HTML export with images copied to a local directory.
        Useful for viewing/sharing journals without FoundryVTT.

        Directory structure created:
            output_dir/
                journal.html       - Main HTML file
                images/            - Copied image files
                    *.png

        Args:
            output_dir: Path to output directory (can be str or Path)

        Returns:
            Path to generated journal.html file

        Raises:
            ValueError: If output_dir creation fails
        """
        from pathlib import Path
        import shutil

        output_dir = Path(output_dir)
        images_dir = output_dir / "images"

        # Create directories
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(exist_ok=True)

        # Build image mapping with relative paths and copy images
        image_mapping = {}
        for key, metadata in self.image_registry.items():
            if metadata.file_path:
                source_path = Path(metadata.file_path)
                if source_path.exists():
                    # Copy to images directory
                    dest_path = images_dir / source_path.name
                    shutil.copy2(source_path, dest_path)
                    # Use relative path in HTML
                    image_mapping[key] = f"images/{source_path.name}"

        # Generate HTML content
        html_content = self.to_foundry_html(image_mapping)

        # Wrap in complete HTML document with styling
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        body {{
            font-family: 'Bookman Old Style', Georgia, serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5dc;
            color: #2c1810;
            line-height: 1.6;
        }}
        h1 {{
            color: #8b4513;
            border-bottom: 3px solid #8b4513;
            padding-bottom: 10px;
            font-size: 2.5em;
        }}
        h2 {{
            color: #a0522d;
            margin-top: 40px;
            font-size: 2em;
            border-bottom: 2px solid #cd853f;
        }}
        h3 {{
            color: #cd853f;
            margin-top: 30px;
            font-size: 1.5em;
        }}
        h4 {{
            color: #d2691e;
            margin-top: 20px;
            font-size: 1.2em;
        }}
        p {{
            margin: 15px 0;
            text-align: justify;
        }}
        img {{
            display: block;
            max-width: 100%;
            height: auto;
            margin: 30px auto;
            border: 3px solid #8b4513;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            border-radius: 4px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background: white;
        }}
        table td {{
            border: 1px solid #8b4513;
            padding: 8px;
        }}
        aside {{
            background: #fffaf0 !important;
            border-left: 4px solid #8b4513 !important;
            padding: 15px 20px !important;
            margin: 20px 0 !important;
            font-style: italic;
        }}
        ul, ol {{
            margin: 15px 0;
            padding-left: 40px;
        }}
        li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

        # Write to file
        output_file = output_dir / "journal.html"
        output_file.write_text(full_html, encoding='utf-8')

        return str(output_file)
