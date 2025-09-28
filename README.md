# D&D Module Converter

Utilities for turning official Dungeons & Dragons PDFs into structured assets that can be post-processed into FoundryVTT content. The current pipeline extracts chapter PDFs, feeds them through Gemini for XML generation, and renders quick HTML previews for review.

## Layout
- `src/split_pdf.py` – slices `data/pdfs/Lost_Mine_of_Phandelver.pdf` into chapter PDFs under `pdf_sections/`.
- `src/pdf_to_xml.py` – uploads each chapter page to Gemini (`GEMINI_MODEL_NAME`) and writes XML plus logs to `output/runs/<timestamp>/`.
- `src/xml_to_html.py` – converts the latest run’s XML into browsable HTML inside the same run directory.
- `xml_examples/` – reference markup while refining the converters.
- `pdf_sections/` – cache of manually curated chapter PDFs used as input for the XML step.

## Setup
1. Activate the provided Conda env: `conda activate dnd`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Add a `.env` file at the project root with `GeminiImageAPI=<your key>` so the XML step can reach Gemini 2.5.
4. Drop source PDFs under `data/pdfs/`; the default workflow expects `Lost_Mine_of_Phandelver.pdf`.

## Workflow
1. `python src/split_pdf.py` – refreshes chapter PDFs in `pdf_sections/<module>/`.
2. `python src/pdf_to_xml.py` – generates XML plus per-page artifacts in a timestamped run directory.
3. `python src/xml_to_html.py` – emits HTML previews for the most recent run to speed up spot checks.

Each run preserves logs, raw model responses, and word-count checks beneath `output/runs/<timestamp>/`; avoid editing outputs in place so history stays intact.

## Validation & Next Steps
- Use `python -m compileall src` after edits to catch syntax errors; add offline-friendly `pytest` suites under `tests/` as the pipeline evolves.
- The long-term target is an exporter that maps the generated XML into FoundryVTT module manifests. Upcoming work includes normalising the XML schema, attaching media assets, and wiring an actual Foundry package builder.
