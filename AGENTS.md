# Repository Guidelines

## Project Structure & Module Organization
The codebase centers on Python converters that transform D&D modules into XML and HTML. Keep primary logic in `src/`, where:
- `pdf_to_xml.py` orchestrates Gemini-powered extraction and logging under `output/runs/<timestamp>/`.
- `split_pdf.py` and `get_toc.py` manage source PDFs stored in `data/pdfs/`.
- `xml_to_html.py` renders run artifacts into navigable HTML.
Reference assets live in `xml_examples/`, while `pdf_sections/` caches manually curated chapter splits. Avoid editing generated outputs in place; regenerate them instead.

## Build, Test, and Development Commands
Create an isolated environment with `uv venv && source .venv/bin/activate`, then install dependencies via `uv pip sync`. The extraction workflow expects `GeminiImageAPI` in `.env`; run `python src/pdf_to_xml.py` after placing the module PDF under `data/pdfs/`. Use `python src/split_pdf.py` to refresh chapter PDFs and `python src/xml_to_html.py` to rebuild HTML previews from the latest run. Each command writes logs beneath `output/runs/`, so clear that directory only when you intend to reset history.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, descriptive snake_case names, and module-level constants in UPPER_SNAKE_CASE. Preserve the existing functional layout—helpers near their call sites and I/O confined to small adapters. When adding modules, mirror the pattern `verb_noun.py` and document entry points with concise docstrings. Prefer f-strings and early validation of external resources.

## Testing Guidelines
Automated coverage is minimal; introduce `pytest` suites under `tests/` that exercise OCR fallbacks, XML validation, and HTML generation. Name files `test_<module>.py` and mock Gemini calls so tests can run offline. Execute `pytest` before pushing, and include sample fixtures sourced from `xml_examples/` or trimmed pages under `pdf_sections/`. Flag nondeterministic behavior (e.g., OCR variance) with deterministic seeds or skipped tests.

## Commit & Pull Request Guidelines
Commits follow short, imperative summaries (see `git log`: `added requirements.txt`, `fixed rebase`). Group related changes and mention impacted scripts. Pull requests should describe the workflow touched, reference any related issues, summarize testing (e.g., `pytest`, manual PDF-to-XML run), and attach relevant output paths or screenshots. Highlight configuration changes—especially updates to `.env` expectations—so reviewers can reproduce results.
