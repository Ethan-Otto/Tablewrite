# XMLDocument and Journal Models Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create Pydantic data models to replace raw XML handling, enabling type-safe processing with XMLDocument (immutable record) and Journal (mutable working representation with rich features).

**Architecture:** Two-layer design - XMLDocument mirrors XML structure exactly (preserves pages), Journal flattens to semantic hierarchy (chapters/sections) and supports entity linking, image insertion, and multiple export formats.

**Tech Stack:** Pydantic 2.x, Python 3.11+, xml.etree.ElementTree

**Reference:** See `docs/plans/2025-11-05-xmldocument-journal-architecture.md` for complete design rationale.

---

## Task 1: Create XMLDocument Base Models

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/xml_document.py`
- Test: `tests/models/test_xml_document.py`

### Step 1: Write failing test for XMLDocument.from_xml()

```python
# tests/models/test_xml_document.py
import pytest
from models.xml_document import XMLDocument

def test_xmldocument_parses_simple_xml():
    """Test XMLDocument can parse basic XML with pages and content"""
    xml_string = """
    <Chapter_01_Introduction>
      <page number="1">
        <section>Test Section</section>
        <p>Test paragraph</p>
      </page>
    </Chapter_01_Introduction>
    """
    doc = XMLDocument.from_xml(xml_string)

    assert doc.title == "Chapter_01_Introduction"
    assert len(doc.pages) == 1
    assert doc.pages[0].number == 1
    assert len(doc.pages[0].content) == 2
    assert doc.pages[0].content[0].type == "section"
    assert doc.pages[0].content[1].type == "paragraph"
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_simple_xml -v`
**Expected:** FAIL - ModuleNotFoundError: No module named 'models'

### Step 2: Create models package structure

```python
# src/models/__init__.py
"""Pydantic models for D&D module data structures."""
from .xml_document import XMLDocument, Page, Content

__all__ = ["XMLDocument", "Page", "Content"]
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_simple_xml -v`
**Expected:** FAIL - ImportError: cannot import name 'XMLDocument'

### Step 3: Write minimal XMLDocument implementation

```python
# src/models/xml_document.py
"""XMLDocument - Immutable record of generated XML."""
import xml.etree.ElementTree as ET
from typing import List, Union, Literal
from pydantic import BaseModel, ConfigDict


class Content(BaseModel):
    """Single content element with auto-generated ID."""
    id: str
    type: Literal["paragraph", "section", "subsection", "subsubsection", "chapter_title"]
    data: str


class Page(BaseModel):
    """Single PDF page with numbered content."""
    number: int
    content: List[Content]


class XMLDocument(BaseModel):
    """Immutable XML record - preserves page structure."""
    model_config = ConfigDict(frozen=True)

    title: str
    pages: List[Page]

    @classmethod
    def from_xml(cls, xml_string: str) -> 'XMLDocument':
        """Parse XML string to XMLDocument. Raises ValueError on invalid XML."""
        root = ET.fromstring(xml_string)
        title = root.tag

        pages = []
        for page_elem in root.findall('page'):
            page_num = int(page_elem.get('number'))
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
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_simple_xml -v`
**Expected:** PASS

### Step 4: Commit

```bash
git add src/models/ tests/models/
git commit -m "feat(models): add XMLDocument base model with parsing

- Create XMLDocument, Page, Content Pydantic models
- Implement from_xml() class method with basic XML parsing
- Support section and paragraph content types
- Auto-generate content IDs (page_N_content_M format)"
```

---

## Task 2: Add Complex Content Types

**Files:**
- Modify: `src/models/xml_document.py`
- Modify: `tests/models/test_xml_document.py`

### Step 1: Write test for table content

```python
# tests/models/test_xml_document.py (add to existing file)
def test_xmldocument_parses_table():
    """Test XMLDocument can parse table structures"""
    xml_string = """
    <Chapter_01>
      <page number="1">
        <table>
          <table_row>
            <table_cell>Name</table_cell>
            <table_cell>HP</table_cell>
          </table_row>
          <table_row>
            <table_cell>Goblin</table_cell>
            <table_cell>7</table_cell>
          </table_row>
        </table>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)

    assert doc.pages[0].content[0].type == "table"
    table_data = doc.pages[0].content[0].data
    assert isinstance(table_data, Table)
    assert len(table_data.rows) == 2
    assert table_data.rows[0].cells == ["Name", "HP"]
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_table -v`
**Expected:** FAIL - AttributeError: 'str' object has no attribute 'rows'

### Step 2: Add Table models

```python
# src/models/xml_document.py (add before Content class)
class TableRow(BaseModel):
    """Single table row with cells."""
    cells: List[str]


class Table(BaseModel):
    """Table with rows and cells."""
    rows: List[TableRow]


# Update Content.data type annotation
class Content(BaseModel):
    id: str
    type: Literal["paragraph", "section", "subsection", "subsubsection",
                  "chapter_title", "table", "list", "definition_list",
                  "boxed_text", "stat_block", "image_ref"]
    data: Union[str, Table, 'ListContent', 'DefinitionList', 'StatBlockRaw', 'ImageRef']
```

### Step 3: Update from_xml() to parse tables

```python
# src/models/xml_document.py (in from_xml method)
def _parse_content_data(child: ET.Element) -> Union[str, Table]:
    """Parse content data based on element type."""
    if child.tag == "table":
        rows = []
        for row_elem in child.findall('table_row'):
            cells = [cell.text or "" for cell in row_elem.findall('table_cell')]
            rows.append(TableRow(cells=cells))
        return Table(rows=rows)
    else:
        return child.text or ""

# Update content parsing in from_xml()
for idx, child in enumerate(page_elem):
    content_id = f"page_{page_num}_content_{idx}"
    content_type = child.tag
    content_data = _parse_content_data(child)

    content.append(Content(
        id=content_id,
        type=content_type,
        data=content_data
    ))
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_table -v`
**Expected:** PASS

### Step 4: Write test for list content

```python
# tests/models/test_xml_document.py (add test)
def test_xmldocument_parses_list():
    """Test XMLDocument can parse list structures"""
    xml_string = """
    <Chapter_01>
      <page number="1">
        <list>
          <item>First item</item>
          <item>Second item</item>
        </list>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)

    list_data = doc.pages[0].content[0].data
    assert isinstance(list_data, ListContent)
    assert list_data.items == ["First item", "Second item"]
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_list -v`
**Expected:** FAIL

### Step 5: Add ListContent and DefinitionList models

```python
# src/models/xml_document.py (add after Table)
class ListContent(BaseModel):
    """Unordered or ordered list."""
    items: List[str]


class DefinitionItem(BaseModel):
    """Term-definition pair."""
    term: str
    definition: str


class DefinitionList(BaseModel):
    """Definition list with term-definition pairs."""
    items: List[DefinitionItem]


# Update _parse_content_data()
def _parse_content_data(child: ET.Element) -> Union[str, Table, ListContent, DefinitionList]:
    if child.tag == "table":
        # ... existing table logic
    elif child.tag == "list":
        items = [item.text or "" for item in child.findall('item')]
        return ListContent(items=items)
    elif child.tag == "definition_list":
        items = []
        for def_item in child.findall('definition_item'):
            term_elem = def_item.find('term')
            def_elem = def_item.find('definition')
            items.append(DefinitionItem(
                term=term_elem.text or "",
                definition=def_elem.text or ""
            ))
        return DefinitionList(items=items)
    else:
        return child.text or ""
```

**Run:** `uv run pytest tests/models/test_xml_document.py -v`
**Expected:** All tests PASS

### Step 6: Commit

```bash
git add src/models/xml_document.py tests/models/test_xml_document.py
git commit -m "feat(models): add complex content types (table, list, definitions)

- Add Table, TableRow models for structured tables
- Add ListContent for unordered/ordered lists
- Add DefinitionList, DefinitionItem for glossaries
- Update Content.data to Union type for multiple formats
- Extract _parse_content_data() helper for cleaner parsing"
```

---

## Task 3: Add StatBlock and ImageRef Support

**Files:**
- Modify: `src/models/xml_document.py`
- Modify: `tests/models/test_xml_document.py`

### Step 1: Write test for stat block

```python
# tests/models/test_xml_document.py
def test_xmldocument_parses_stat_block():
    """Test XMLDocument preserves raw stat block XML"""
    xml_string = """
    <Chapter_01>
      <page number="1">
        <stat_block name="Goblin">
GOBLIN
Small humanoid, neutral evil
Armor Class 15
Hit Points 7 (2d6)
        </stat_block>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)

    stat_block = doc.pages[0].content[0].data
    assert isinstance(stat_block, StatBlockRaw)
    assert stat_block.name == "Goblin"
    assert "GOBLIN" in stat_block.xml_element
    assert "Armor Class 15" in stat_block.xml_element
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_stat_block -v`
**Expected:** FAIL

### Step 2: Add StatBlockRaw model

```python
# src/models/xml_document.py (add after DefinitionList)
class StatBlockRaw(BaseModel):
    """Raw stat block XML for later parsing."""
    name: str
    xml_element: str


class ImageRef(BaseModel):
    """Image placeholder from Gemini."""
    key: str


# Update Content.data type
data: Union[str, Table, ListContent, DefinitionList, StatBlockRaw, ImageRef]
```

### Step 3: Update _parse_content_data() for stat blocks

```python
# src/models/xml_document.py
def _parse_content_data(child: ET.Element) -> Union[str, Table, ListContent, DefinitionList, StatBlockRaw, ImageRef]:
    if child.tag == "stat_block":
        name = child.get('name', 'Unknown')
        # Preserve complete XML element as string
        xml_str = ET.tostring(child, encoding='unicode')
        return StatBlockRaw(name=name, xml_element=xml_str)
    elif child.tag == "image_ref":
        key = child.get('key', '')
        return ImageRef(key=key)
    # ... rest of existing logic
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_stat_block -v`
**Expected:** PASS

### Step 4: Write test for image_ref

```python
# tests/models/test_xml_document.py
def test_xmldocument_parses_image_ref():
    """Test XMLDocument parses image references"""
    xml_string = """
    <Chapter_01>
      <page number="5">
        <p>Before image</p>
        <image_ref key="page_5_top_battle_map" />
        <p>After image</p>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)

    assert doc.pages[0].content[1].type == "image_ref"
    img_ref = doc.pages[0].content[1].data
    assert isinstance(img_ref, ImageRef)
    assert img_ref.key == "page_5_top_battle_map"
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_image_ref -v`
**Expected:** PASS

### Step 5: Commit

```bash
git add src/models/xml_document.py tests/models/test_xml_document.py
git commit -m "feat(models): add StatBlockRaw and ImageRef support

- Add StatBlockRaw model to preserve complete stat block XML
- Add ImageRef model for image placeholders
- Preserve stat block name attribute
- Support self-closing image_ref tags with key attribute"
```

---

## Task 4: Add Real XML Integration Test

**Files:**
- Modify: `tests/models/test_xml_document.py`

### Step 1: Write test using real XML file

```python
# tests/models/test_xml_document.py
from pathlib import Path

def test_xmldocument_parses_real_xml():
    """Test XMLDocument can parse actual generated XML files"""
    # Find a real XML file
    xml_path = Path("output/runs").glob("*/documents/01_Introduction.xml")
    xml_file = next(xml_path, None)

    if not xml_file or not xml_file.exists():
        pytest.skip("No real XML files found in output/runs")

    xml_string = xml_file.read_text()
    doc = XMLDocument.from_xml(xml_string)

    # Validate structure
    assert doc.title.startswith("Chapter_")
    assert len(doc.pages) > 0
    assert all(page.number > 0 for page in doc.pages)
    assert all(len(page.content) > 0 for page in doc.pages)

    # Validate content IDs are unique
    all_ids = [c.id for page in doc.pages for c in page.content]
    assert len(all_ids) == len(set(all_ids))
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_real_xml -v`
**Expected:** May PASS or FAIL depending on what content types exist in real XML

### Step 2: Handle unknown content types gracefully

If test fails due to unknown content types, update the model:

```python
# src/models/xml_document.py
# Add to Content.type Literal
type: Literal["paragraph", "section", "subsection", "subsubsection",
              "chapter_title", "table", "list", "definition_list",
              "boxed_text", "stat_block", "image_ref", "header", "footer",
              "page_number"]

# Update _parse_content_data() to handle unknown types
def _parse_content_data(child: ET.Element) -> Union[...]:
    # ... existing cases
    else:
        # Default: store as plain text
        return child.text or ""
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_parses_real_xml -v`
**Expected:** PASS

### Step 3: Commit

```bash
git add tests/models/test_xml_document.py src/models/xml_document.py
git commit -m "test(models): add integration test with real XML files

- Test XMLDocument.from_xml() with actual generated XML
- Validate page structure and content IDs
- Add header, footer, page_number content types
- Skip test gracefully if no XML files available"
```

---

## Task 5: Add XMLDocument.to_xml() Serialization

**Files:**
- Modify: `src/models/xml_document.py`
- Modify: `tests/models/test_xml_document.py`

### Step 1: Write test for round-trip serialization

```python
# tests/models/test_xml_document.py
def test_xmldocument_round_trip():
    """Test XMLDocument can serialize back to XML"""
    original_xml = """<Chapter_01>
  <page number="1">
    <section>Test</section>
    <p>Content</p>
  </page>
</Chapter_01>"""

    doc = XMLDocument.from_xml(original_xml)
    serialized_xml = doc.to_xml()

    # Re-parse to validate
    doc2 = XMLDocument.from_xml(serialized_xml)

    assert doc2.title == doc.title
    assert len(doc2.pages) == len(doc.pages)
    assert doc2.pages[0].content[0].data == doc.pages[0].content[0].data
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_round_trip -v`
**Expected:** FAIL - AttributeError: 'XMLDocument' object has no attribute 'to_xml'

### Step 2: Implement to_xml() method

```python
# src/models/xml_document.py
class XMLDocument(BaseModel):
    # ... existing code

    def to_xml(self) -> str:
        """Serialize XMLDocument back to XML string."""
        root = ET.Element(self.title)

        for page in self.pages:
            page_elem = ET.SubElement(root, 'page', number=str(page.number))

            for content in page.content:
                self._add_content_to_element(page_elem, content)

        # Pretty print
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding='unicode')

    def _add_content_to_element(self, parent: ET.Element, content: Content):
        """Add content to XML element based on type."""
        if isinstance(content.data, str):
            elem = ET.SubElement(parent, content.type)
            elem.text = content.data
        elif isinstance(content.data, Table):
            table_elem = ET.SubElement(parent, 'table')
            for row in content.data.rows:
                row_elem = ET.SubElement(table_elem, 'table_row')
                for cell in row.cells:
                    cell_elem = ET.SubElement(row_elem, 'table_cell')
                    cell_elem.text = cell
        elif isinstance(content.data, ListContent):
            list_elem = ET.SubElement(parent, 'list')
            for item in content.data.items:
                item_elem = ET.SubElement(list_elem, 'item')
                item_elem.text = item
        elif isinstance(content.data, DefinitionList):
            def_list_elem = ET.SubElement(parent, 'definition_list')
            for item in content.data.items:
                def_item_elem = ET.SubElement(def_list_elem, 'definition_item')
                term_elem = ET.SubElement(def_item_elem, 'term')
                term_elem.text = item.term
                def_elem = ET.SubElement(def_item_elem, 'definition')
                def_elem.text = item.definition
        elif isinstance(content.data, StatBlockRaw):
            # Parse and re-add the preserved XML
            stat_elem = ET.fromstring(content.data.xml_element)
            parent.append(stat_elem)
        elif isinstance(content.data, ImageRef):
            ET.SubElement(parent, 'image_ref', key=content.data.key)
```

**Run:** `uv run pytest tests/models/test_xml_document.py::test_xmldocument_round_trip -v`
**Expected:** PASS

### Step 3: Commit

```bash
git add src/models/xml_document.py tests/models/test_xml_document.py
git commit -m "feat(models): add XMLDocument.to_xml() serialization

- Implement to_xml() method for round-trip conversion
- Add _add_content_to_element() helper for type-specific serialization
- Handle all content types (str, Table, List, DefinitionList, StatBlock, ImageRef)
- Pretty-print output with 2-space indentation
- Test round-trip: XML → XMLDocument → XML → XMLDocument"
```

---

## Task 6: Create Journal Base Models

**Files:**
- Create: `src/models/journal.py`
- Test: `tests/models/test_journal.py`

### Step 1: Write test for Journal.from_xml_document()

```python
# tests/models/test_journal.py
from models.xml_document import XMLDocument
from models.journal import Journal

def test_journal_flattens_pages_to_chapters():
    """Test Journal creates semantic hierarchy from pages"""
    xml_string = """
    <Chapter_01_Introduction>
      <page number="1">
        <chapter_title>INTRODUCTION</chapter_title>
        <section>Running the Adventure</section>
        <p>This is the intro.</p>
      </page>
      <page number="2">
        <section>The Dungeon Master</section>
        <p>DM info here.</p>
      </page>
    </Chapter_01_Introduction>
    """
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    assert len(journal.chapters) == 1
    assert journal.chapters[0].title == "INTRODUCTION"
    assert len(journal.chapters[0].sections) == 2
    assert journal.chapters[0].sections[0].heading == "Running the Adventure"
    assert journal.chapters[0].sections[1].heading == "The Dungeon Master"
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_flattens_pages_to_chapters -v`
**Expected:** FAIL - ModuleNotFoundError

### Step 2: Create Journal base models

```python
# src/models/journal.py
"""Journal - Semantic working representation with rich features."""
from typing import List, Dict, Optional
from pydantic import BaseModel
from .xml_document import XMLDocument, Content


class Subsubsection(BaseModel):
    """Lowest-level heading (subsubsection)."""
    id: str
    heading: str
    content: List[Content]


class Subsection(BaseModel):
    """Mid-level heading (subsection)."""
    id: str
    heading: str
    content: List[Content]
    subsubsections: List[Subsubsection] = []


class Section(BaseModel):
    """Top-level heading (section)."""
    id: str
    heading: str
    content: List[Content]
    subsections: List[Subsection] = []


class Chapter(BaseModel):
    """Chapter with semantic hierarchy."""
    id: str
    title: str
    sections: List[Section] = []


class ImageMetadata(BaseModel):
    """Image metadata owned by Journal."""
    page_num: Optional[int] = None
    type: str  # "battle_map", "navigation_map", "scene_illustration", "generated_scene"
    position: str = ""
    description: Optional[str] = None
    insert_before_content_id: Optional[str] = None
    source: str = "gemini_detected"  # "gemini_detected", "scene_generated", "manual"


class Journal(BaseModel):
    """Mutable working representation with semantic hierarchy."""
    source: XMLDocument
    chapters: List[Chapter]
    image_registry: Dict[str, ImageMetadata] = {}

    @classmethod
    def from_xml_document(cls, doc: XMLDocument, context: Optional[object] = None) -> 'Journal':
        """Build Journal from XMLDocument by flattening pages to semantic hierarchy."""
        chapters = cls._build_hierarchy(doc)
        journal = cls(source=doc, chapters=chapters, image_registry={})

        # Extract ImageRef placeholders into registry
        journal._extract_image_refs()

        return journal

    @classmethod
    def _build_hierarchy(cls, doc: XMLDocument) -> List[Chapter]:
        """Flatten XMLDocument.pages into semantic Chapter hierarchy."""
        chapters = []
        current_chapter = None
        current_section = None
        current_subsection = None
        current_subsubsection = None

        chapter_idx = 0
        section_idx = 0
        subsection_idx = 0
        subsubsection_idx = 0
        content_idx = 0

        for page in doc.pages:
            for content in page.content:
                if content.type == "chapter_title":
                    # Start new chapter
                    chapter_idx += 1
                    section_idx = 0
                    current_chapter = Chapter(
                        id=f"chapter_{chapter_idx}",
                        title=content.data if isinstance(content.data, str) else "",
                        sections=[]
                    )
                    chapters.append(current_chapter)
                    current_section = None
                    current_subsection = None
                    current_subsubsection = None

                elif content.type == "section":
                    # Start new section
                    section_idx += 1
                    subsection_idx = 0
                    content_idx = 0
                    current_section = Section(
                        id=f"chapter_{chapter_idx}_section_{section_idx}",
                        heading=content.data if isinstance(content.data, str) else "",
                        content=[],
                        subsections=[]
                    )
                    if current_chapter:
                        current_chapter.sections.append(current_section)
                    current_subsection = None
                    current_subsubsection = None

                elif content.type == "subsection":
                    # Start new subsection
                    subsection_idx += 1
                    subsubsection_idx = 0
                    content_idx = 0
                    current_subsection = Subsection(
                        id=f"chapter_{chapter_idx}_section_{section_idx}_subsection_{subsection_idx}",
                        heading=content.data if isinstance(content.data, str) else "",
                        content=[],
                        subsubsections=[]
                    )
                    if current_section:
                        current_section.subsections.append(current_subsection)
                    current_subsubsection = None

                elif content.type == "subsubsection":
                    # Start new subsubsection
                    subsubsection_idx += 1
                    content_idx = 0
                    current_subsubsection = Subsubsection(
                        id=f"chapter_{chapter_idx}_section_{section_idx}_subsection_{subsection_idx}_subsubsection_{subsubsection_idx}",
                        heading=content.data if isinstance(content.data, str) else "",
                        content=[]
                    )
                    if current_subsection:
                        current_subsection.subsubsections.append(current_subsubsection)

                else:
                    # Regular content - add to current container
                    content_idx += 1
                    # Update content ID to semantic format
                    if current_subsubsection:
                        content.id = f"{current_subsubsection.id}_content_{content_idx}"
                        current_subsubsection.content.append(content)
                    elif current_subsection:
                        content.id = f"{current_subsection.id}_content_{content_idx}"
                        current_subsection.content.append(content)
                    elif current_section:
                        content.id = f"{current_section.id}_content_{content_idx}"
                        current_section.content.append(content)

        return chapters

    def _extract_image_refs(self):
        """Extract ImageRef placeholders into image_registry."""
        # Will implement in next task
        pass
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_flattens_pages_to_chapters -v`
**Expected:** PASS

### Step 3: Commit

```bash
git add src/models/journal.py tests/models/test_journal.py
git commit -m "feat(models): add Journal base models with hierarchy flattening

- Create Chapter, Section, Subsection, Subsubsection models
- Create ImageMetadata model for Journal's image registry
- Implement Journal.from_xml_document() class method
- Implement _build_hierarchy() to flatten pages to semantic structure
- Generate semantic IDs (chapter_N_section_M_content_K format)
- Sections span page boundaries correctly"
```

---

## Task 7: Extract ImageRef into Journal Registry

**Files:**
- Modify: `src/models/journal.py`
- Modify: `tests/models/test_journal.py`

### Step 1: Write test for image registry extraction

```python
# tests/models/test_journal.py
from models.xml_document import ImageRef

def test_journal_extracts_image_refs_to_registry():
    """Test Journal extracts ImageRef placeholders into image_registry"""
    xml_string = """
    <Chapter_01>
      <page number="5">
        <section>Test Section</section>
        <p>Before image</p>
        <image_ref key="page_5_top_battle_map" />
        <p>After image</p>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    # ImageRef should be in registry
    assert "page_5_top_battle_map" in journal.image_registry
    metadata = journal.image_registry["page_5_top_battle_map"]
    assert metadata.page_num == 5
    assert metadata.source == "gemini_detected"

    # ImageRef should still be in content (for rendering)
    section_content = journal.chapters[0].sections[0].content
    image_content = [c for c in section_content if c.type == "image_ref"]
    assert len(image_content) == 1
    assert image_content[0].data.key == "page_5_top_battle_map"
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_extracts_image_refs_to_registry -v`
**Expected:** FAIL - AssertionError: assert 'page_5_top_battle_map' in {}

### Step 2: Implement _extract_image_refs()

```python
# src/models/journal.py
def _extract_image_refs(self):
    """Extract ImageRef placeholders from content into image_registry."""
    for page in self.source.pages:
        for content in page.content:
            if content.type == "image_ref" and isinstance(content.data, ImageRef):
                key = content.data.key
                if key and key not in self.image_registry:
                    # Parse page number from key (format: page_5_top_battle_map)
                    page_num = None
                    if key.startswith("page_"):
                        parts = key.split("_")
                        if len(parts) > 1 and parts[1].isdigit():
                            page_num = int(parts[1])

                    self.image_registry[key] = ImageMetadata(
                        page_num=page_num,
                        type="unknown",  # Will be determined by extraction
                        position="",
                        source="gemini_detected"
                    )
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_extracts_image_refs_to_registry -v`
**Expected:** PASS

### Step 3: Commit

```bash
git add src/models/journal.py tests/models/test_journal.py
git commit -m "feat(journal): extract ImageRef placeholders to registry

- Implement _extract_image_refs() to build image_registry
- Parse page number from ImageRef key
- Create ImageMetadata entries for detected images
- Preserve ImageRef in content stream for rendering"
```

---

## Task 8: Add Journal Image Manipulation Methods

**Files:**
- Modify: `src/models/journal.py`
- Modify: `tests/models/test_journal.py`

### Step 1: Write test for add_image()

```python
# tests/models/test_journal.py
def test_journal_add_image():
    """Test Journal.add_image() adds new image to registry"""
    xml_string = """<Chapter_01><page number="1"><section>Test</section></page></Chapter_01>"""
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    # Add scene artwork
    journal.add_image("scene_chapter1_intro", ImageMetadata(
        page_num=None,
        type="generated_scene",
        source="scene_generated",
        insert_before_content_id="chapter_1_section_1_content_0"
    ))

    assert "scene_chapter1_intro" in journal.image_registry
    assert journal.image_registry["scene_chapter1_intro"].type == "generated_scene"
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_add_image -v`
**Expected:** FAIL - AttributeError: 'Journal' object has no attribute 'add_image'

### Step 2: Implement image manipulation methods

```python
# src/models/journal.py (add to Journal class)
def add_image(self, key: str, metadata: ImageMetadata):
    """Add new image (scene artwork, custom, etc.) to registry."""
    self.image_registry[key] = metadata

def reposition_image(self, key: str, new_content_id: str):
    """Move image to different location."""
    if key in self.image_registry:
        self.image_registry[key].insert_before_content_id = new_content_id

def remove_image(self, key: str):
    """Remove image from registry."""
    if key in self.image_registry:
        del self.image_registry[key]
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_add_image -v`
**Expected:** PASS

### Step 3: Write test for reposition_image()

```python
# tests/models/test_journal.py
def test_journal_reposition_image():
    """Test Journal.reposition_image() updates insert location"""
    xml_string = """<Chapter_01><page number="5">
      <section>Test</section>
      <image_ref key="page_5_map" />
    </page></Chapter_01>"""
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    # Initially no insert position
    assert journal.image_registry["page_5_map"].insert_before_content_id is None

    # Reposition
    journal.reposition_image("page_5_map", "chapter_1_section_2_content_1")

    assert journal.image_registry["page_5_map"].insert_before_content_id == "chapter_1_section_2_content_1"
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_reposition_image -v`
**Expected:** PASS

### Step 4: Commit

```bash
git add src/models/journal.py tests/models/test_journal.py
git commit -m "feat(journal): add image manipulation methods

- Implement add_image() for scene artwork and custom images
- Implement reposition_image() to change image placement
- Implement remove_image() to delete from registry
- Test adding, repositioning images"
```

---

## Task 9: Add Journal Export Methods (Stubs)

**Files:**
- Modify: `src/models/journal.py`
- Modify: `tests/models/test_journal.py`

### Step 1: Write test for to_foundry_html()

```python
# tests/models/test_journal.py
def test_journal_to_foundry_html():
    """Test Journal.to_foundry_html() generates basic HTML"""
    xml_string = """
    <Chapter_01>
      <page number="1">
        <chapter_title>Introduction</chapter_title>
        <section>Getting Started</section>
        <p>Welcome to the adventure.</p>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    html = journal.to_foundry_html(image_mapping={})

    assert "<h1>Introduction</h1>" in html
    assert "<h2>Getting Started</h2>" in html
    assert "Welcome to the adventure" in html
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_to_foundry_html -v`
**Expected:** FAIL - AttributeError

### Step 2: Implement basic export methods

```python
# src/models/journal.py (add to Journal class)
def to_foundry_html(self, image_mapping: Dict[str, str]) -> str:
    """Generate FoundryVTT HTML with @UUID links."""
    html_parts = []

    for chapter in self.chapters:
        html_parts.append(f"<h1>{chapter.title}</h1>")

        for section in chapter.sections:
            html_parts.append(self._render_section(section, image_mapping, level=2))

    return "\n".join(html_parts)

def _render_section(self, section: Section, image_mapping: Dict[str, str], level: int) -> str:
    """Render a section and its subsections recursively."""
    parts = []
    parts.append(f"<h{level}>{section.heading}</h{level}>")

    # Render content
    for content in section.content:
        parts.append(self._render_content(content, image_mapping))

    # Render subsections
    for subsection in section.subsections:
        parts.append(self._render_subsection(subsection, image_mapping, level + 1))

    return "\n".join(parts)

def _render_subsection(self, subsection: Subsection, image_mapping: Dict[str, str], level: int) -> str:
    """Render a subsection and its subsubsections."""
    parts = []
    parts.append(f"<h{level}>{subsection.heading}</h{level}>")

    for content in subsection.content:
        parts.append(self._render_content(content, image_mapping))

    for subsubsection in subsection.subsubsections:
        parts.append(self._render_subsubsection(subsubsection, image_mapping, level + 1))

    return "\n".join(parts)

def _render_subsubsection(self, subsubsection: Subsubsection, image_mapping: Dict[str, str], level: int) -> str:
    """Render a subsubsection."""
    parts = []
    parts.append(f"<h{level}>{subsubsection.heading}</h{level}>")

    for content in subsubsection.content:
        parts.append(self._render_content(content, image_mapping))

    return "\n".join(parts)

def _render_content(self, content: Content, image_mapping: Dict[str, str]) -> str:
    """Render individual content element."""
    # Check if images should insert before this content
    image_html = ""
    for key, metadata in self.image_registry.items():
        if metadata.insert_before_content_id == content.id:
            if key in image_mapping:
                image_html += f'<img src="{image_mapping[key]}" alt="{metadata.description or ""}" />\n'

    # Render content based on type
    content_html = ""
    if content.type == "paragraph":
        content_html = f"<p>{content.data}</p>"
    elif content.type == "image_ref":
        # Skip - handled via registry
        pass
    elif content.type == "boxed_text":
        content_html = f'<div class="boxed-text">{content.data}</div>'
    else:
        # Default: wrap in <p>
        if isinstance(content.data, str):
            content_html = f"<p>{content.data}</p>"

    return image_html + content_html

def to_html(self, image_mapping: Dict[str, str]) -> str:
    """Generate generic HTML export."""
    # For now, same as FoundryVTT (will differentiate later)
    return self.to_foundry_html(image_mapping)

def to_markdown(self, image_mapping: Dict[str, str]) -> str:
    """Generate Markdown export."""
    # Stub for now
    return f"# {self.chapters[0].title if self.chapters else 'Untitled'}\n\nMarkdown export coming soon."
```

**Run:** `uv run pytest tests/models/test_journal.py::test_journal_to_foundry_html -v`
**Expected:** PASS

### Step 3: Commit

```bash
git add src/models/journal.py tests/models/test_journal.py
git commit -m "feat(journal): add basic export methods (HTML/Markdown)

- Implement to_foundry_html() with basic rendering
- Add _render_section/subsection/subsubsection helpers
- Add _render_content() with image insertion support
- Handle paragraphs, headings, image_refs
- Add stub to_html() and to_markdown() methods"
```

---

## Task 10: Update Models __init__.py

**Files:**
- Modify: `src/models/__init__.py`

### Step 1: Export all public models

```python
# src/models/__init__.py
"""Pydantic models for D&D module data structures."""
from .xml_document import (
    XMLDocument,
    Page,
    Content,
    Table,
    TableRow,
    ListContent,
    DefinitionList,
    DefinitionItem,
    StatBlockRaw,
    ImageRef,
)
from .journal import (
    Journal,
    Chapter,
    Section,
    Subsection,
    Subsubsection,
    ImageMetadata,
)

__all__ = [
    # XMLDocument models
    "XMLDocument",
    "Page",
    "Content",
    "Table",
    "TableRow",
    "ListContent",
    "DefinitionList",
    "DefinitionItem",
    "StatBlockRaw",
    "ImageRef",
    # Journal models
    "Journal",
    "Chapter",
    "Section",
    "Subsection",
    "Subsubsection",
    "ImageMetadata",
]
```

### Step 2: Commit

```bash
git add src/models/__init__.py
git commit -m "feat(models): export all public models from package

- Export XMLDocument and all content type models
- Export Journal and semantic hierarchy models
- Update __all__ for clean imports"
```

---

## Task 11: Integration Test with Full Pipeline

**Files:**
- Create: `tests/models/test_integration.py`

### Step 1: Write end-to-end test

```python
# tests/models/test_integration.py
"""Integration tests for XMLDocument → Journal → HTML workflow."""
import pytest
from pathlib import Path
from models import XMLDocument, Journal


def test_full_workflow_with_real_xml():
    """Test complete workflow: Load XML → Parse → Create Journal → Export HTML"""
    # Find a real XML file
    xml_files = list(Path("output/runs").glob("*/documents/*.xml"))
    if not xml_files:
        pytest.skip("No XML files found in output/runs")

    xml_path = xml_files[0]
    xml_string = xml_path.read_text()

    # Step 1: Parse to XMLDocument
    doc = XMLDocument.from_xml(xml_string)
    assert doc.title
    assert len(doc.pages) > 0

    # Step 2: Create Journal
    journal = Journal.from_xml_document(doc)
    assert len(journal.chapters) > 0

    # Step 3: Export to HTML
    html = journal.to_foundry_html(image_mapping={})
    assert len(html) > 0
    assert "<h1>" in html

    # Step 4: Validate round-trip
    xml_out = doc.to_xml()
    doc2 = XMLDocument.from_xml(xml_out)
    assert doc2.title == doc.title
    assert len(doc2.pages) == len(doc.pages)


def test_journal_preserves_content():
    """Test Journal doesn't lose content during hierarchy flattening"""
    xml_string = """
    <Chapter_01>
      <page number="1">
        <chapter_title>Title</chapter_title>
        <section>Section 1</section>
        <p>Para 1</p>
      </page>
      <page number="2">
        <p>Para 2</p>
        <section>Section 2</section>
        <p>Para 3</p>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    # Count all content elements
    total_content = 0
    for chapter in journal.chapters:
        for section in chapter.sections:
            total_content += len(section.content)

    # Should have 3 paragraphs
    assert total_content == 3
```

**Run:** `uv run pytest tests/models/test_integration.py -v`
**Expected:** PASS

### Step 2: Commit

```bash
git add tests/models/test_integration.py
git commit -m "test(models): add end-to-end integration tests

- Test full workflow: XML → XMLDocument → Journal → HTML
- Test with real XML files from output/runs
- Validate round-trip serialization
- Ensure Journal preserves all content during flattening"
```

---

## Task 12: Run Full Test Suite

**Files:** None (verification step)

### Step 1: Run all model tests

**Run:** `uv run pytest tests/models/ -v`
**Expected:** All tests PASS

### Step 2: Run all tests including existing

**Run:** `uv run pytest -m "not integration and not slow" -v`
**Expected:** All tests PASS (244+ tests)

### Step 3: Check test coverage

**Run:** `uv run pytest tests/models/ --cov=src/models --cov-report=term-missing`
**Expected:** >80% coverage on new models

### Step 4: Commit checkpoint

```bash
git add -A
git commit -m "test(models): verify all tests pass

- All XMLDocument tests passing
- All Journal tests passing
- Integration tests passing
- No regressions in existing test suite"
```

---

## Success Criteria

At this point, you should have:

- [ ] XMLDocument model parses all existing XML files
- [ ] XMLDocument.to_xml() successfully round-trips
- [ ] Journal flattens pages to semantic hierarchy
- [ ] Journal extracts ImageRef into registry
- [ ] Journal exports basic HTML
- [ ] All tests passing (244+ unit tests)
- [ ] Clean git history with incremental commits

---

## Next Steps (Future Tasks)

**Phase 2: Integration with Existing Code**
1. Update `pdf_to_xml.py` to validate with XMLDocument
2. Update `upload_to_foundry.py` to use Journal
3. Update `parse_stat_blocks.py` to accept XMLDocument

**Phase 3: Rich Features**
1. Implement link transformation functions (`add_npc_links`, etc.)
2. Add image extraction integration
3. Add dice roll detection
4. Improve HTML export (handle tables, lists, stat blocks)

**Phase 4: Image Support**
1. Update `valid_xml_tags.py` to include `image_ref`
2. Update `pdf_to_xml.py` Gemini prompt to detect images
3. Create `extract_and_map_images.py` workflow
4. Update Journal rendering to handle images properly

---

## Execution Options

**Plan complete and saved to `docs/plans/2025-11-05-xmldocument-journal-implementation.md`.**

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration with quality gates

**2. Parallel Session (separate)** - Open new session with superpowers:executing-plans, batch execution with checkpoints

Which approach would you prefer?
