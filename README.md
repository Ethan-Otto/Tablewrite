# D&D Module Converter

Utilities for turning official Dungeons & Dragons PDFs into structured assets that can be post-processed into FoundryVTT content. The current pipeline extracts chapter PDFs, feeds them through Gemini for XML generation, and renders quick HTML previews for review.

## Layout
- `src/pdf_processing/` – PDF processing scripts:
  - `split_pdf.py` – slices `data/pdfs/Lost_Mine_of_Phandelver.pdf` into chapter PDFs under `pdf_sections/`
  - `pdf_to_xml.py` – uploads each chapter page to Gemini (`GEMINI_MODEL_NAME`) and writes XML plus logs to `output/runs/<timestamp>/`
  - `get_toc.py` – extracts table of contents from PDF
  - `xml_to_html.py` – converts XML to browsable HTML (local previews and FoundryVTT uploads)
  - `valid_xml_tags.py` – XML tag validation utilities
- `src/foundry/` – FoundryVTT integration:
  - `client.py` – REST API client base class
  - `journals.py` – `JournalManager` class for journal CRUD operations
  - `upload_to_foundry.py` – batch upload script for journals
  - `export_from_foundry.py` – export journals from FoundryVTT to HTML/JSON
- `scripts/full_pipeline.py` – complete pipeline: split → XML generation → upload → export
- `src/logging_config.py` – centralized logging configuration
- `xml_examples/` – reference markup while refining the converters
- `pdf_sections/` – cache of manually curated chapter PDFs used as input for the XML step

## Setup
1. Install uv if not already installed: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`)
2. Create virtual environment and install dependencies: `uv venv && source .venv/bin/activate && uv pip sync`
3. Add a `.env` file at the project root with `GeminiImageAPI=<your key>` so the XML step can reach Gemini 2.5.
4. Drop source PDFs under `data/pdfs/`; the default workflow expects `Lost_Mine_of_Phandelver.pdf`.

## Workflow

**Full Pipeline (recommended):**
```bash
# Complete workflow: split → XML → upload → export
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip steps as needed
uv run python scripts/full_pipeline.py --skip-split --skip-xml  # Only upload + export
uv run python scripts/full_pipeline.py --skip-export             # Skip final export
```

**Individual Steps:**
```bash
1. uv run src/pdf_processing/split_pdf.py           # Split PDF into chapters
2. uv run src/pdf_processing/pdf_to_xml.py          # Generate XML via Gemini
3. uv run src/foundry/upload_to_foundry.py          # Upload to FoundryVTT
4. uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver"  # Export HTML
```

Or activate the virtual environment first (`source .venv/bin/activate`) and use `python ...` directly.

Each run preserves logs, raw model responses, and word-count checks beneath `output/runs/<timestamp>/`; avoid editing outputs in place so history stays intact.

## FoundryVTT Integration

The project includes optional integration for uploading generated HTML content directly to FoundryVTT as journal entries.

### Setup

1. **Install FoundryVTT REST API Module:**
   - In FoundryVTT, go to Add-on Modules > Install Module
   - Paste manifest URL: `https://github.com/ThreeHats/foundryvtt-rest-api/releases/latest/download/module.json`
   - Enable the module in your world
   - Generate an API key in Module Settings

2. **Configure Environment:**
   Add to your `.env` file:
   ```bash
   FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
   FOUNDRY_LOCAL_URL=http://localhost:30000
   FOUNDRY_LOCAL_API_KEY=<your_api_key>
   FOUNDRY_LOCAL_CLIENT_ID=<your_client_id>
   FOUNDRY_AUTO_UPLOAD=false
   FOUNDRY_TARGET=local
   ```

3. **Upload and Export:**
   ```bash
   # Full pipeline (recommended)
   uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

   # Manual upload of latest run
   uv run src/foundry/upload_to_foundry.py

   # Export journal from FoundryVTT
   uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver" --format html
   ```

### Features

- **Create or Replace**: Automatically searches for existing journals by name and replaces them (no duplicates)
- **Export Support**: Download journals from FoundryVTT as HTML or JSON
- **UUID-based Operations**: Proper UUID handling for all journal operations
- **Pages Structure**: Compatible with FoundryVTT v10+ pages architecture
- **Dual Environment Support**: Works with both local FoundryVTT and The Forge

### Architecture

The integration uses the ThreeHats REST API module with a relay server:
- Script → HTTP → Relay Server → WebSocket → FoundryVTT Module → FoundryVTT

**JournalManager Pattern:**
- `src/foundry/journals.py` - `JournalManager` class handles all journal CRUD operations
- `src/foundry/client.py` - Base `FoundryClient` delegates to specialized managers

## Logging
All scripts use Python's standard `logging` module for structured output:
- **DEBUG**: Detailed processing steps (page uploads, file creation)
- **INFO**: Normal workflow progress (chapter/page processing)
- **WARNING**: Non-fatal issues (OCR fallback, retries, word count mismatches)
- **ERROR**: Processing failures

Logs are written to both console and `<run_dir>/pdf_to_xml.log` for the main conversion script.

## Testing

The project includes a comprehensive pytest test suite that mirrors the `src/` directory structure:

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_main.py             # End-to-end pipeline tests (PDF → XML → HTML)
├── pdf_processing/          # Tests for PDF processing scripts
│   ├── test_split_pdf.py   # PDF splitting tests
│   ├── test_pdf_to_xml.py  # XML generation tests
│   ├── test_get_toc.py     # TOC extraction tests
│   └── test_xml_to_html.py # HTML conversion tests
└── foundry/                 # Tests for FoundryVTT integration
    ├── test_client.py       # FoundryClient API tests
    ├── test_upload_script.py # Upload script tests
    └── test_xml_to_journal_html.py # XML to journal converter tests
```

### Running Tests

```bash
# Run all unit tests (excludes slow API tests)
uv run pytest -m "not integration and not slow"

# Run all tests including integration tests with Gemini API
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/pdf_processing/test_split_pdf.py

# Run tests matching a pattern
uv run pytest -k "test_word_count"
```

### Test Categories

- **Unit tests**: Fast tests that don't require API calls (default)
- **Integration tests**: Tests that make real Gemini API calls (marked with `@pytest.mark.integration` and `@pytest.mark.slow`)
- **PDF tests**: Tests requiring PDF files (marked with `@pytest.mark.requires_pdf`)
- **End-to-end tests**: Full pipeline tests in `test_main.py` that run PDF → XML → HTML conversion with timestamped test runs

### Test Configuration

- Configuration: `pytest.ini`
- Fixtures: `tests/conftest.py`
- Test PDF: `data/pdfs/Lost_Mine_of_Phandelver_test.pdf` (7 pages)
- Full PDF: `data/pdfs/Lost_Mine_of_Phandelver.pdf` (for TOC tests)
- Output: `tests/output/` (persistent, not cleaned automatically)
- Test runs: `tests/output/test_runs/<timestamp>/` (created by end-to-end tests)

## Continuous Integration

GitHub Actions automatically runs the full test suite on all pull requests. See [GitHub Actions Setup Guide](.github/SETUP.md) for configuration details.

**Required**: Add your Gemini API key as a GitHub Secret named `GEMINI_API_KEY` for integration tests to run.

## Validation & Next Steps
- Use `uv run python -m compileall src` after edits to catch syntax errors
- Run `uv run pytest` to verify changes don't break functionality
- GitHub Actions runs all tests automatically on pull requests

### Current Status
✅ **Full Pipeline**: Complete workflow from PDF → XML → FoundryVTT → HTML export
✅ **FoundryVTT Integration**: Upload, export, create/replace journals with UUID-based operations
✅ **Bug Fixes**: Mixed XML content handling, improved heading hierarchy detection

### Recent Updates
- **Full Pipeline Script** (`scripts/full_pipeline.py`): Orchestrates all 4 stages with skip flags
- **Journal Export**: Download journals from FoundryVTT as HTML or JSON
- **JournalManager Refactor**: Specialized manager class for journal operations
- **XML Mixed Content Fix**: Properly handles bare text + child elements in definitions
- **Improved Prompts**: Better heading hierarchy detection (context over font size)

### Future Work
- Normalize XML schema for consistent journal structure
- Attach media assets (images, maps) to journal entries
- Build complete FoundryVTT module manifest exporter
- Add folder organization for journal entries
