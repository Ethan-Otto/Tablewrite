# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a D&D module converter that transforms official Dungeons & Dragons PDFs into structured XML assets for post-processing into FoundryVTT content. The pipeline uses Google's Gemini 2.5 Pro model for AI-powered document analysis and extraction.

## Environment Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: pip install uv
   ```

2. **Create Virtual Environment and Install Dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate  # Unix/macOS
   # .venv\Scripts\activate   # Windows
   uv pip sync
   ```
   - Key packages: `google-generativeai`, `PyMuPDF` (fitz), `pytesseract`, `Pillow`, `python-dotenv`

3. **Required Configuration**: Create `.env` file at project root with:
   ```
   # Gemini API
   GeminiImageAPI=<your_gemini_api_key>

   # FoundryVTT Configuration (optional - for journal upload)
   FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
   FOUNDRY_LOCAL_URL=http://localhost:30000
   FOUNDRY_LOCAL_API_KEY=<your_foundry_api_key>
   FOUNDRY_LOCAL_CLIENT_ID=<your_client_id>
   FOUNDRY_AUTO_UPLOAD=false
   FOUNDRY_TARGET=local
   ```

4. **Source PDFs**: Place D&D module PDFs in `data/pdfs/` (default expects `Lost_Mine_of_Phandelver.pdf`)

## Logging

All scripts use Python's standard `logging` module for structured output:

- **Log Levels**:
  - `DEBUG`: Detailed processing steps (page uploads, file creation, word frequency analysis)
  - `INFO`: Normal workflow progress (chapter/page processing, verification steps)
  - `WARNING`: Non-fatal issues (OCR fallback, retries, word count mismatches)
  - `ERROR`: Processing failures and unrecoverable errors

- **Log Outputs**:
  - Console: All log levels displayed with timestamps
  - File: `pdf_to_xml.py` writes logs to `<run_dir>/pdf_to_xml.log`

- **Configuration**: Centralized in `src/logging_config.py`
  - Use `setup_logging(__name__)` for simple console logging
  - Use `get_run_logger(script_name, run_dir)` for file + console logging

## Common Commands

**Full Pipeline (recommended):**
```bash
# Complete workflow: split → XML → upload to FoundryVTT → export HTML
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip steps as needed
uv run python scripts/full_pipeline.py --skip-split --skip-xml  # Only upload + export
uv run python scripts/full_pipeline.py --skip-export             # Skip final export
```

**Individual Steps:**
```bash
# 1. Split source PDF into chapter PDFs
uv run src/pdf_processing/split_pdf.py

# 2. Generate XML from chapter PDFs using Gemini
uv run src/pdf_processing/pdf_to_xml.py

# 3. Upload to FoundryVTT
uv run src/foundry/upload_to_foundry.py                          # Upload latest run
uv run src/foundry/upload_to_foundry.py --run-dir output/runs/20241017_123456

# 4. Export from FoundryVTT
uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver"
uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver" --format json

# Utilities
uv run src/pdf_processing/pdf_to_xml.py --file "01_Introduction.pdf"  # Single chapter
uv run src/pdf_processing/get_toc.py                                   # Extract TOC
uv run python -m compileall src                                        # Syntax check

# Testing
uv run pytest                                    # All tests
uv run pytest -m "not integration and not slow"  # Unit tests only
uv run pytest -v                                 # Verbose output
```

Or activate the virtual environment manually first:
```bash
source .venv/bin/activate  # Unix/macOS
# Then run scripts normally:
python src/pdf_processing/split_pdf.py
python src/pdf_processing/pdf_to_xml.py
python src/pdf_processing/xml_to_html.py
```

## Architecture & Data Flow

### Processing Pipeline

The system follows a four-stage pipeline (orchestrated by `scripts/full_pipeline.py`):

1. **PDF Splitting** (`src/pdf_processing/split_pdf.py`):
   - Input: `data/pdfs/Lost_Mine_of_Phandelver.pdf`
   - Output: Chapter PDFs in `pdf_sections/Lost_Mine_of_Phandelver/`
   - Hardcoded chapter boundaries based on manual TOC analysis

2. **PDF to XML Conversion** (`src/pdf_processing/pdf_to_xml.py`):
   - Input: Chapter PDFs from `pdf_sections/`
   - Output: Timestamped run in `output/runs/<YYYYMMDD_HHMMSS>/documents/`
   - Core AI-powered extraction engine using Gemini 2.5 Pro

3. **FoundryVTT Upload** (`src/foundry/upload_to_foundry.py`):
   - Input: XML files from run directory (converted to HTML on-the-fly)
   - Output: Journal entries in FoundryVTT
   - Uses `JournalManager` class for create/replace operations
   - Returns journal UUID for step 4

4. **FoundryVTT Export** (`src/foundry/export_from_foundry.py`):
   - Input: Journal UUID from step 3 (or searches by name)
   - Output: HTML file in `output/runs/<timestamp>/foundry_export/`
   - Exports final rendered journal for verification and archival

### FoundryVTT Integration

The project includes full integration with FoundryVTT for uploading and exporting journal entries.

**Architecture:**
- Uses ThreeHats REST API module (relay server → WebSocket → FoundryVTT)
- `src/foundry/client.py`: Base `FoundryClient` class with API configuration
- `src/foundry/journals.py`: `JournalManager` class with all journal CRUD operations
- `src/foundry/upload_to_foundry.py`: Batch upload script
- `src/foundry/export_from_foundry.py`: Export journals as HTML or JSON
- `scripts/full_pipeline.py`: Complete workflow orchestration

**Key Features:**
- **Create or Replace**: Automatically searches for existing journals and replaces them (no duplicates)
- **Export Support**: Download journals from FoundryVTT as HTML or JSON
- **UUID Optimization**: Returns journal UUID from upload to avoid extra API call during export
- **Pages Structure**: Compatible with FoundryVTT v10+ pages architecture
- **Environment-based Config**: Supports both local FoundryVTT and The Forge
- **Error Handling**: Graceful handling of search failures, network errors, and API issues

**JournalManager API:**
```python
from foundry.client import FoundryClient

client = FoundryClient(target="local")  # or "forge"

# Create or replace journal (returns UUID)
uuid = client.journals.create_or_replace_journal(
    name="Chapter 1",
    pages=[{"name": "Page 1", "content": "<h1>...</h1>"}]
)

# Get journal by UUID or name
entry = client.journals.get_journal_entry(
    journal_name="Chapter 1",
    journal_uuid="JournalEntry.abc123"  # optional, avoids search
)

# Search for journals by name
results = client.journals.search_journals(name="Chapter 1")

# Delete journal
client.journals.delete_journal(journal_uuid="JournalEntry.abc123")
```

**API Response Formats:**
- Create: `{'entity': {...}, 'uuid': 'JournalEntry.{id}'}`
- Update: `{'entity': [...], 'uuid': 'JournalEntry.{id}'}`  (entity is a list!)
- Delete: `{'success': True}`
- Search: `[{'id': '...', 'uuid': 'JournalEntry.{id}', 'name': '...'}]`
- Get: `{'_id': '...', 'uuid': 'JournalEntry.{id}', 'name': '...', 'pages': [...]}`

**Important Implementation Notes:**
- Update/delete operations require `uuid` as query parameter: `/update?clientId={id}&uuid={uuid}`
- Update payload is `{"data": {...}}`, NOT `{"entityType": "JournalEntry", "id": "...", "data": {...}}`
- Search results may return `id` OR `uuid` field; JournalManager normalizes to both `_id` and `uuid`
- FoundryVTT v10+ requires pages structure: `{"pages": [{"name": "...", "type": "text", "text": {"content": "..."}}]}`
- `create_or_replace_journal` returns the journal UUID for efficient subsequent operations

**Search API (via QuickInsert module):**

The `/search` endpoint uses the QuickInsert module on FoundryVTT and has specific behavior:

- **Hard 200-result limit**: Hardcoded in the FoundryVTT module (`src/ts/network/routers/search.ts:54`)
- **No pagination or bulk endpoints**: Cannot retrieve all compendium items in one call
- **Correct parameter is `filter`, NOT `type`**:
  - ❌ `type=Item` - ignored, just echoed back as metadata
  - ✅ `filter=Item` - filters to Items only (shorthand for `documentType:Item`)
  - ✅ `filter=documentType:Item,package:dnd5e.items` - multi-property filtering
  - ✅ `filter=documentType:Item,folder:abc123` - filter by folder

- **Filter syntax**:
  - Simple: `filter="Item"` → `{documentType: "Item"}`
  - Property-based: `filter="key:value,key2:value2"` → multiple filters
  - Supported properties: `documentType`, `package`, `folder`, `resultType`, or any item property

- **Request flow**: HTTP → Relay Server → WebSocket → FoundryVTT → QuickInsert → Response

- **Recommended approach for bulk operations**: Build a local cache by querying with common terms ("a", "of", "the") and specific compendium packs, then perform lookups locally

**FoundryVTT Item Types:**

In FoundryVTT, "Item" is a broad document type that includes character options, spells, and physical items. Filter by `subType` to narrow down:

- **Physical Items** (treasure/loot):
  - `equipment` - armor, wondrous items, accessories, rings, cloaks
  - `weapon` - weapons (mundane and magical)
  - `consumable` - potions, scrolls, ammunition
  - `container` - bags of holding, chests, backpacks
  - `loot` - treasure, gems, art objects, trade goods

- **Character Options** (NOT physical items):
  - `spell` - spells (Aid, Fireball, etc.)
  - `feat` - feats and features (Alert, Action Surge, etc.)
  - `subclass` - subclass features
  - `background` - background features
  - `race` - racial traits

**Magic Item Identification:**
- Magic items span multiple subTypes: `equipment`, `weapon`, `consumable`, `container`
- No direct filter for "magic only" - must fetch full item data and check `system.properties` for `'mgc'`
- Example: Hat of Disguise has `system.properties: ['mgc']`, `system.rarity: 'uncommon'`, `system.attunement: 'required'`

**Caching Strategy for Physical Items:**
- Search alphabet (a-z) for each physical subType separately (API only supports AND filtering, not OR)
- 5 subTypes × 26 letters = 130 API calls for comprehensive coverage of all physical items
- Deduplicate by UUID (items appear in multiple compendiums like `dnd5e.items` and `dnd5e.equipment24`)

### Key Architecture Patterns

**pdf_to_xml.py** (main conversion engine):

- **Parallel Processing**: Uses `ThreadPoolExecutor` (max 5 workers) for both page-level and chapter-level processing
- **Text Extraction Strategy**: Two-tier fallback system
  1. First attempts embedded text extraction from PDF
  2. Falls back to local Tesseract OCR if embedded text is corrupted (checks legibility via word length heuristics)
- **AI-Powered XML Generation**: Each page uploaded to Gemini 2.5 Pro with structured prompt requesting semantic XML
- **Retry Logic**: 3 attempts per page with exponential backoff (2^attempt seconds)
- **Self-Healing XML**: If Gemini produces malformed XML, automatically sends it back to Gemini for correction with original text as reference
- **Quality Validation**:
  - Word count comparison between source PDF and generated XML (15% tolerance threshold)
  - Validates at both page-level and final chapter-level
  - Stores word frequency analysis as JSON when validation fails
- **Comprehensive Logging**: Each run preserves:
  - `intermediate_logs/<chapter>/pages/` - per-page PDFs, embedded text, OCR text, raw Gemini responses, XML attempts
  - `documents/<chapter>.xml` - final merged XML
  - `error_report.txt` - summary of all failures

**Output Directory Structure**:
```
output/runs/<timestamp>/
├── documents/
│   └── <chapter>.xml          # Final merged XML files
├── intermediate_logs/
│   └── <chapter>/
│       ├── pages/
│       │   ├── page_N.pdf
│       │   ├── page_N_embedded.txt
│       │   ├── page_N_ocr.txt (if fallback triggered)
│       │   ├── page_N_attempt_1_raw.xml
│       │   ├── page_N_corrected.xml (if malformed)
│       │   └── page_N.xml (final)
│       ├── final_unverified.xml
│       └── <chapter>_corrected.xml (if needed)
└── error_report.txt
```

### Critical Implementation Details

1. **PROJECT_ROOT Pattern**:
   - Scripts in `src/pdf_processing/` calculate project root as `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` (pdf_processing/ → src/ → root)
   - Scripts in `src/` calculate project root as `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (src/ → root)

2. **Import Pattern**: Scripts in `src/pdf_processing/` add parent directory to sys.path before importing from src/:
   ```python
   import sys
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from logging_config import setup_logging
   ```

3. **Gemini Model**: Hardcoded to `gemini-2.5-pro` (see `GEMINI_MODEL_NAME` constant)

4. **XML Generation Prompt**: Instructs Gemini to use Markdown syntax for styling (`*italic*`, `**bold**`) instead of HTML tags, with specialized tags for D&D elements like `<monster>` stat blocks

5. **HTML Tag Replacement**: Post-processes Gemini output to convert any `<i>`, `<b>`, `<italic>` tags to Markdown equivalents before validation

6. **Error Handling Philosophy**:
   - Page errors mark entire chapter as failed
   - Preserves partial outputs for debugging
   - Never edits generated outputs in place—regenerate instead

7. **Chapter Boundaries**: Hardcoded in `src/pdf_processing/split_pdf.py` sections array (0-indexed page ranges with display names)

8. **XML Mixed Content Handling**: `xml_to_html.py` properly processes XML elements with both text content and child elements (e.g., `<definition>text<p>child</p></definition>`) by extracting `elem.text`, processing children, and capturing `child.tail`

9. **Heading Hierarchy Prompt**: Updated in `pdf_to_xml.py` to emphasize semantic context over font size when determining section/subsection levels

## Testing

### Test Structure

The test suite mirrors the `src/` directory structure:

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_main.py             # End-to-end pipeline tests (PDF → XML → HTML)
├── pdf_processing/          # Tests for src/pdf_processing/
│   ├── __init__.py
│   ├── test_split_pdf.py   # Tests for split_pdf.py
│   ├── test_pdf_to_xml.py  # Tests for pdf_to_xml.py
│   ├── test_get_toc.py     # Tests for get_toc.py (uses FULL PDF)
│   └── test_xml_to_html.py # Tests for xml_to_html.py
├── foundry/                 # Tests for src/foundry/
│   ├── __init__.py
│   ├── test_client.py       # Tests for FoundryClient API
│   ├── test_upload_script.py # Tests for upload_to_foundry.py
│   └── test_xml_to_journal_html.py # Tests for XML to journal HTML converter
└── output/                  # Persistent test output (not auto-cleaned)
    └── test_runs/           # Timestamped test runs from end-to-end tests
```

### Running Tests

```bash
# Unit tests only (fast, no API calls)
uv run pytest -m "not integration and not slow"

# All tests including Gemini API integration tests
uv run pytest

# Specific test file
uv run pytest tests/pdf_processing/test_split_pdf.py

# Verbose output
uv run pytest -v

# Tests matching pattern
uv run pytest -k "test_word_count"
```

### Test Markers

- `@pytest.mark.unit`: Fast unit tests (no external dependencies)
- `@pytest.mark.integration`: Tests that make real Gemini API calls
- `@pytest.mark.slow`: Slow tests (API calls, large file processing)
- `@pytest.mark.requires_api`: Tests requiring Gemini API key
- `@pytest.mark.requires_pdf`: Tests requiring PDF files

### Key Fixtures (from `conftest.py`)

- `test_pdf_path`: Path to `Lost_Mine_of_Phandelver_test.pdf` (7 pages, for most tests)
- `full_pdf_path`: Path to full PDF (for TOC tests only)
- `test_output_dir`: Temporary directory (auto-cleaned)
- `clean_test_output`: Persistent `tests/output/` (NOT auto-cleaned)
- `check_api_key`: Verifies Gemini API key is configured
- `sample_xml_content`: Valid XML for testing
- `sample_malformed_xml`: Invalid XML for error handling tests

### Test Coverage

**PDF Processing** (`test_split_pdf.py`):
- Chapter boundary detection
- PDF page extraction and validation
- Output file creation
- Edge cases (empty PDFs, single page)
- XML element name sanitization

**XML Generation** (`test_pdf_to_xml.py`):
- XML element name sanitization (numeric prefixes)
- Word counting and frequency analysis
- Text legibility detection
- Text extraction (embedded and OCR fallback)
- XML structure validation
- Error handling and retry logic
- **Gemini API integration** (real API calls in `@pytest.mark.integration` tests)

**TOC Extraction** (`test_get_toc.py`):
- TOC structure validation (level, title, page tuples)
- Level hierarchy correctness
- Page number validity and ordering
- Expected section detection
- Page mapping and content verification
- **Note**: Uses FULL PDF (`Lost_Mine_of_Phandelver.pdf`), not test PDF

**HTML Conversion** (`test_xml_to_html.py`):
- XML to HTML content conversion
- HTML structure generation (headings, paragraphs, lists)
- Navigation link creation
- CSS styling inclusion
- Malformed XML error handling
- Multiple file conversion
- Output validation (valid HTML structure, UTF-8, viewport)

**End-to-End Pipeline** (`test_main.py`):
- Complete PDF → XML → HTML workflow
- Single-page and multi-page pipeline tests
- Timestamped test run directory creation
- Output directory structure validation
- Run isolation (separate timestamped runs don't interfere)
- Error handling throughout pipeline
- **Integration tests**: Make REAL Gemini API calls for full workflow testing

**FoundryVTT Integration** (`tests/foundry/`):
- **Journal Manager Tests** (`test_journals.py`): `JournalManager` class tests
  - Create, search, get, delete journal operations
  - `create_or_replace_journal` flow (searches, then creates/replaces)
  - UUID-based operations and normalization
  - Error handling for API failures
- **Client Tests** (`test_client.py`): `FoundryClient` delegation tests
  - Environment-based initialization (local and forge)
  - Delegation to `JournalManager`
- **Upload Script Tests** (`test_upload_script.py`): Upload workflow tests
  - XML to HTML conversion and batching
  - Upload statistics tracking
  - Error handling for failed uploads
- **Export Script Tests**: Export workflow validation
- All tests use mocked HTTP requests (no real API calls to FoundryVTT)

### Writing New Tests

Follow these patterns when adding tests:

1. **Mirror src/ structure**: Tests for `src/foo/bar.py` go in `tests/foo/test_bar.py`
2. **Use fixtures**: Import from `conftest.py` rather than creating test data
3. **Mark appropriately**: Use `@pytest.mark.integration` for API calls, `@pytest.mark.slow` for long tests
4. **Test real behavior**: Integration tests make REAL Gemini API calls (not mocked)
5. **Organize by class**: Group related tests in classes (e.g., `TestWordCounting`, `TestXMLValidation`)
6. **End-to-end tests**: Use `test_main.py` for full pipeline tests that save to timestamped `tests/output/test_runs/` directories

### Integration Test Warning

Tests marked with `@pytest.mark.integration` make **real Gemini API calls** and will:
- Consume API quota
- Cost money
- Be slow (API latency)
- Require valid API key in `.env`

Run unit tests only for fast feedback: `uv run pytest -m "not integration and not slow"`

## Coding Conventions

**General Principles:**
- **Write clean, concise code**: Prioritize readability and simplicity over cleverness
- **Keep functions focused**: Each function should do one thing well
- **Avoid unnecessary complexity**: Use straightforward solutions unless performance requires otherwise
- **Clear is better than compact**: Favor explicit, readable code over terse one-liners

From AGENTS.md:

- **Style**: PEP 8 with 4-space indentation, snake_case names, UPPER_SNAKE_CASE for constants
- **Module Naming**: Follow `verb_noun.py` pattern (e.g., `split_pdf.py`, `get_toc.py`)
- **Strings**: Prefer f-strings
- **Validation**: Early validation of external resources
- **Helpers**: Keep helpers near call sites, confine I/O to small adapters
- **Docstrings**: Concise module-level docstrings for entry points

## Commit Style

Based on git history:
- Short, imperative mood summaries ("added requirements.txt", "updated", "fixes")
- Group related changes
- Mention impacted scripts

## Future Development Notes

- README mentions long-term goal: map XML to FoundryVTT module manifests
- Need to normalize XML schema before building Foundry exporter
- Consider adding pytest suites under `tests/` directory
- Mock Gemini calls for offline testing
- Use fixtures from `xml_examples/` or trimmed pages
