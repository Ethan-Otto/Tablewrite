import os
import fitz  # PyMuPDF
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging

# Project root is three levels up from the script's directory (pdf_processing -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logging(__name__)

def get_toc():
    """
    This script extracts the table of contents from the PDF file.
    """
    pdf_file_path = os.path.join(PROJECT_ROOT, "data", "pdfs", "Lost_Mine_of_Phandelver.pdf")
    doc = fitz.open(pdf_file_path)
    toc = doc.get_toc()
    doc.close()

    if toc:
        logger.info("Table of Contents:")
        for item in toc:
            level, title, page = item
            logger.info(f"  Level {level}: {title} (Page {page})")
    else:
        logger.info("No table of contents found in the PDF")

if __name__ == "__main__":
    get_toc()

