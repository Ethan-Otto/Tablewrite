#!/usr/bin/env python3
"""Quick script to process Chapter 2 to HTML."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_processing.pdf_to_html import process_pdf_to_html


if __name__ == "__main__":
    html_path = process_pdf_to_html(
        pdf_path="02_Part_1_Goblin_Arrows.pdf",
        map_positioning_mode="semantic",
        extract_maps=True,
        open_html=True
    )

    print(f"\n✅ Generated: {html_path}")
