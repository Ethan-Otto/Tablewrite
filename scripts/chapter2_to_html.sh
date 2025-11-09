#!/bin/bash
set -e

echo "Processing Chapter 2: PDF -> XML -> HTML with images"

# Step 1: PDF to XML
uv run python src/pdf_processing/pdf_to_xml.py --file "02_Part_1_Goblin_Arrows.pdf"

LATEST_RUN=$(ls -td output/runs/*/ | head -1)
XML_FILE=$(ls ${LATEST_RUN}documents/*.xml | head -1)

# Step 2: Extract maps
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py \
    --pdf "data/pdf_sections/Lost_Mine_of_Phandelver/02_Part_1_Goblin_Arrows.pdf" \
    --output "${LATEST_RUN}map_assets"

# Step 3: Generate scene artwork
uv run python scripts/generate_scene_art.py \
    --xml-file "$XML_FILE" \
    --output "${LATEST_RUN}scene_artwork"

# Step 4: Export standalone HTML
cat > /tmp/export.py << 'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from foundry.upload_journal_to_foundry import load_and_position_images

run_dir = Path(sys.argv[1])
journal = load_and_position_images(run_dir)
html_file = journal.export_standalone_html(run_dir / "standalone_export")
print(f"✅ HTML: {html_file}")
PY

uv run python /tmp/export.py "${LATEST_RUN}"
open "${LATEST_RUN}standalone_export/journal.html"
